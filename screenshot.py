#!/usr/bin/env python3
# Original implementation:
#   Copyright Jerry Gamblin / jgamblin
#   https://github.com/jgamblin/Tufty2350-Badgeware
#   Licensed under the Apache License, Version 2.0
#   https://www.apache.org/licenses/LICENSE-2.0
#
# Modifications:
#   Added --wait and --buttons support.
#   Change some things to have better windows support
"""
Capture what an installed app actually draws, as a PNG on the host.

The badge's framebuffer is plain RGBA8888 at 160x120 and `screen.raw` exposes
it, so this runs the app for a few frames on-device, dumps the buffer to the
badge's little internal filesystem, pulls it over, and saves an image. Much
faster than squinting at the panel.

    python3 tools/screenshot.py defcon34
    python3 tools/screenshot.py defcon34 --frames 90 --setup 'm.card.page = 1'
    python3 tools/screenshot.py recon --setup 'm.view = 2' -o flags.png
    python3 tools/screenshot.py myapp --wait
    python3 tools/screenshot.py myapp --buttons "A,B"

--setup runs after the app is imported and before the frames, with the app
module bound to `m`. It is how you reach a page that would otherwise need a
button press.
--wait pauses execution on the badge until a physical button is pressed.
--buttons simulates button presses (e.g., 'A,UP') by overriding badge.pressed.
"""

import argparse
import os
import subprocess
import sys
import tempfile
import platform

W, H = 160, 120
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)

# Runs on the badge. `run` is normally the firmware's infinite app loop; it is
# stubbed so importing the app hands back its update() instead of blocking.
DEVICE_SCRIPT = """
import badgeware, builtins, sys, os, time
_cap = []
class _R:
    result = None
builtins.run = lambda u: (_cap.append(u), _R())[1]

p = "/system/apps/{app}"
sys.path.insert(0, p)
os.chdir(p)
m = __import__(p)
u = _cap[0]
{setup}

sim_buttons = [{buttons}]
if sim_buttons:
    def _pressed(btn=None):
        if btn is None: return sim_buttons
        return btn in sim_buttons
    def _held(btn=None):
        if btn is None: return sim_buttons
        return btn in sim_buttons
    badge.pressed = _pressed
    badge.held = _held

if {wait}:
    badge.poll()
    while not badge.pressed() and not badge.held():
        badge.poll()
        time.sleep(0.01)

for _ in range({frames}):
    badge.poll()
    u()
    badge.update()
    # Slow down the loop to ~30fps so hardware debouncing has time to register physical presses
    time.sleep(0.03)

# One more frame with no update() after it. update() flips buffers, so calling
# it last would leave screen.raw pointing at the buffer we did not just draw.
badge.poll()
u()

with open("/shot.raw", "wb") as f:
    f.write(screen.raw)
print("SHOT_OK")
"""


def get_mpremote_cmd():
    """Get the appropriate mpremote command for the platform."""
    # Try to use mpremote directly if available
    try:
        subprocess.run(["mpremote", "--version"], capture_output=True, check=True)
        return ["mpremote"]
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fall back to python -m mpremote
        return [sys.executable, "-m", "mpremote"]


def port():
    """Find the badge's COM port on Windows or /dev path on Unix."""
    if os.environ.get("TUFTY_PORT"):
        return os.environ["TUFTY_PORT"]

    if platform.system() == "Windows":
        # On Windows, try to auto-detect COM ports
        import winreg

        ports = []
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM"
            )
            for i in range(winreg.QueryInfoKey(key)[1]):
                name, port, _ = winreg.EnumValue(key, i)
                if "USB" in name or "usbmodem" in name.lower():
                    ports.append(port)
            winreg.CloseKey(key)
        except Exception:
            pass

        if ports:
            return ports[0]
        sys.exit("No Tufty found. Plug it in, or set TUFTY_PORT (e.g., COM10).")
    else:
        # Unix/macOS path detection
        for name in sorted(os.listdir("/dev")):
            if name.startswith("cu.usbmodem"):
                return "/dev/" + name
        sys.exit("No Tufty found. Plug it in, or set TUFTY_PORT.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("app")
    ap.add_argument(
        "--frames",
        type=int,
        default=30,
        help="frames to run before capturing (default 30)",
    )
    ap.add_argument(
        "--setup", default="", help="python run after import, app module bound to `m`"
    )
    ap.add_argument(
        "--wait",
        action="store_true",
        help="wait for a physical button press on the device before starting frames",
    )
    ap.add_argument(
        "--buttons",
        default="",
        help="comma-separated list of buttons to simulate (e.g., 'A,UP')",
    )
    ap.add_argument("-o", "--out", help="output PNG (default shots/<app>.png)")
    args = ap.parse_args()

    out = args.out or os.path.join(ROOT, "shots", args.app + ".png")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    buttons = []
    if args.buttons:
        for b in args.buttons.split(","):
            b = b.strip().upper()
            if b and not b.startswith("BUTTON_"):
                b = f"BUTTON_{b}"
            if b:
                buttons.append(b)

    script = DEVICE_SCRIPT.format(
        app=args.app,
        frames=args.frames,
        setup=args.setup,
        wait=args.wait,
        buttons=", ".join(buttons),
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "capture.py")
        with open(path, "w") as f:
            f.write(script)

        p = port()
        mpremote_cmd = get_mpremote_cmd()

        res = subprocess.run(
            mpremote_cmd + ["connect", p, "run", path], capture_output=True, text=True
        )
        if "SHOT_OK" not in res.stdout:
            sys.stderr.write(res.stdout + res.stderr)
            sys.exit("capture failed")

        raw = os.path.join(tmp, "shot.raw")
        subprocess.run(
            mpremote_cmd + ["connect", p, "fs", "cp", ":/shot.raw", raw],
            check=True,
            capture_output=True,
        )
        data = open(raw, "rb").read()
        subprocess.run(
            mpremote_cmd + ["connect", p, "fs", "rm", ":/shot.raw"], capture_output=True
        )

    expected = W * H * 4
    if len(data) != expected:
        sys.exit("got %d bytes, expected %d" % (len(data), expected))

    from PIL import Image

    img = Image.frombytes("RGBA", (W, H), data)
    # The panel is 320x240 showing a 160x120 buffer, so doubling is what the
    # eye actually sees. Nearest keeps the pixel art crisp.
    img.resize((W * 2, H * 2), Image.NEAREST).save(out)
    print("wrote %s" % os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
