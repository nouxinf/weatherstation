import time
from machine import I2C
from breakout_bme280 import BreakoutBME280
from lsm6ds3 import LSM6DS3, NORMAL_MODE_104HZ
from breakout_ltr559 import BreakoutLTR559
import json
import network
import urequests as requests

# COLOR PALLETTE
BACKGROUND_COLOR = color.rgb(59, 145, 173)
BLACK = color.black
WHITE = color.white

screen.pen = BLACK
screen.clear()

messages = []


def show_status(message):
    global messages
    screen.pen = BLACK
    screen.clear()
    screen.pen = WHITE

    screen.text("Loading app...", 10, 10)

    for index, msg in enumerate(messages):
        screen.text(msg, 10, 20 + (index * 10))

    new_y = 20 + (len(messages) * 10)
    screen.text(message, 10, new_y)

    messages.append(message)
    display.update()


show_status("Loading sensor...")

# try to initialise the multisensor
try:
    i2c = I2C()
    bme = BreakoutBME280(i2c)
    gyro = LSM6DS3(i2c, mode=NORMAL_MODE_104HZ)
    ltr = BreakoutLTR559(i2c)
except RuntimeError:
    no_multisensor = True
else:
    no_multisensor = False
    last_read = 0
    readings = bme.read()

if no_multisensor:
    show_status("No multisensor found")
else:
    show_status("Multisensor found")
show_status("Finding Wi-Fi details...")
try:
    from secrets import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    show_status(
        "Couldn't find Wi-Fi details, write them in secrets.py or else you won't be able to use internet"
    )
    raise

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
show_status("Connecting to Wi-Fi...")
if not wlan.isconnected():
    print("Connecting to Wi-Fi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    # Wait for connection
    while not wlan.isconnected():
        time.sleep(1)

print("Connected to Wi-Fi:", wlan.ipconfig("addr4"))
show_status("Connected")
show_status("Loading options.json")
try:
    with open("options.json") as f:
        options = json.load(f)
except Exception as e:
    show_status("Failed to load options.json!!")
    raise SystemExit("Failed to load options.json!!")
# fetching stuff
url = "https://nominatim.openstreetmap.org/reverse"
headers = {"User-Agent": "Weatherstation on the Tufty 2350"}

try:
    show_status("Making GET requests...")
    MIN_VALUE = -90.0
    MAX_VALUE = 90.0
    nicknames = []
    try:
        locations = options["locations"]

        if not isinstance(locations, list) or len(locations) < 1:
            raise ValueError("Locations must be a non-empty list")

        for idx, entry in enumerate(locations):
            # must be a list/tuple of 2 or 3 values
            if not isinstance(entry, (list, tuple)) or len(entry) not in (2, 3):
                raise ValueError(f"Entry {idx} must be an array of 2 or 3 values")

            val1, val2 = entry[0], entry[1]
            if len(entry) == 3:
                nicknames.append(entry[2])
                # Optional: validate that the nickname is a string
                if not isinstance(entry[2], str):
                    raise ValueError(
                        f"Entry {idx}: third value (nickname) must be a string"
                    )
            else:
                nicknames.append(None)

            # must be numbers within the latlon range
            if not (isinstance(val1, (int, float)) and isinstance(val2, (int, float))):
                raise ValueError(f"Entry {idx} contains non-numeric values")

            if not (MIN_VALUE <= val1 <= MAX_VALUE and MIN_VALUE <= val2 <= MAX_VALUE):
                raise ValueError(
                    f"Entry {idx} values {entry} are outside the range [{MIN_VALUE}, {MAX_VALUE}]"
                )

        # if we reach here without exceptions data is valid
        print(f"Valid locations: {locations}")
        location_names = []
        country_names = []
        for i in locations:
            response = requests.get(
                f"{url}?lat={i[0]}&lon={i[1]}&format=json&addressdetails=1",
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                print(data)
                address_data = data["address"]
                # find the smallest settlement type if possible
                specific_keys = ["neighbourhood", "quarter", "suburb"]
                found_specific = None
                for key in specific_keys:
                    value = address_data.get(key)
                    if value and value.strip():
                        found_specific = value
                        break
                # find more broader settlement type if possible
                parent_keys = ["hamlet", "village", "town", "city", "municipality"]
                found_parent = None
                for key in parent_keys:
                    value = address_data.get(key)
                    if value and value.strip():
                        found_parent = value
                        break

                combined_location = None
                if found_specific and found_parent and found_specific != found_parent:
                    combined_location = f"{found_specific}, {found_parent}"
                elif found_specific:
                    combined_location = found_specific
                elif found_parent:
                    combined_location = found_parent
                else:
                    fallback_keys = ["county", "state", "country"]
                    for key in fallback_keys:
                        value = address_data.get(key)
                        if value and value.strip():
                            combined_location = value
                            break
                if combined_location:
                    location_names.append(combined_location)

                if address_data.get("country"):
                    country_names.append(address_data["country"])
            else:
                print(f"Failed with status {response.status_code}, {response.text}")

    except (KeyError, ValueError) as e:
        show_status("Failed to get locations")
        raise SystemExit
except Exception as e:
    print("An error occurred:", e)


VECTOR_FONT = font.load("/system/assets/fonts/MonaSans-Medium.af")

sprites = SpriteSheet(
    f"assets/spritesheet.png", 30, 1
)  # remember to update column count


def temp_to_sprite(temp, low=-20, high=45, step=5, num_sprites=13):
    temp = max(low, min(temp, high - 0.0001))
    index = int((temp - low) // step)
    return max(0, min(index, num_sprites - 1))


def hum_to_sprite(hum, low=0, high=100, step=10, num_sprites=10, start_col=14):
    hum = max(low, min(hum, high - 0.0001))
    index = int((hum - low) // step)
    index = max(0, min(index, num_sprites - 1))
    return start_col + index


def pres_to_sprite(pres, low=950, high=1050, step=14.29, num_sprites=7, start_col=24):
    pres = max(low, min(pres, high - 0.0001))
    index = int((pres - low) // step)
    index = max(0, min(index, num_sprites - 1))
    return start_col + index


current_screen = 0
screens = ["sensor"] + options.get("locations")
print(screens)

prev_down = False
prev_up = False


def move_current_screen():
    global current_screen, prev_down, prev_up

    down_now = badge.pressed(BUTTON_DOWN)
    up_now = badge.pressed(BUTTON_UP)

    if down_now and not prev_down:
        current_screen = (current_screen + 1) % len(screens)
    if up_now and not prev_up:
        current_screen = (current_screen - 1) % len(screens)

    prev_down = down_now
    prev_up = up_now
    # print(current_screen)
    # print(screens)


def wrap_text(surface, message, max_width, size=None):
    words = message.split(" ")
    lines = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        if size is not None:
            w, h = surface.measure_text(candidate, size)
        else:
            w, h = surface.measure_text(candidate)

        if w <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_wrapped_text(surface, message, x, y, max_width, line_height, size=None):
    lines = wrap_text(surface, message, max_width, size)
    for i, line in enumerate(lines):
        if size is not None:
            surface.text(line, x, y + i * line_height, size)
        else:
            surface.text(line, x, y + i * line_height)


def update():
    move_current_screen()
    if current_screen == 0:
        screen.font = VECTOR_FONT
        if not no_multisensor:
            global last_read, readings
            now = time.ticks_ms()
            if (
                time.ticks_diff(now, last_read) > 100
            ):  # refresh ten times a second, going faster makes it freeze
                readings = bme.read()
                last_read = now
            # print(readings)

            temp = round(readings[0], 1)
            humidity = round(readings[2], 0)
            pressure = round(readings[1], 2) / 100

        # Draw UI

        screen.pen = BACKGROUND_COLOR
        screen.clear()
        screen.pen = color.white
        biggest_rectangle = shape.rounded_rectangle(5, 5, 150, 110, 10)
        smaller_rectangle = shape.rounded_rectangle(7, 7, 146, 106, 10)
        screen.shape(biggest_rectangle)
        screen.pen = BACKGROUND_COLOR
        screen.shape(smaller_rectangle)
        screen.pen = WHITE
        screen.text("Local sensor data", 10, 10, 15)

        # Display info

        temp_unit = options.get("tempmeasurement", "unknown")
        if not no_multisensor:
            if temp_unit == "F":
                screen.text(f"{((temp * 1.8) + 32):.1f}°F", 25, 25, 20)
            elif temp_unit == "K":
                screen.text(f"{(temp + 273.15):.1f}°K", 25, 25, 20)
            else:
                screen.text(f"{temp}°C", 25, 25, 20)
            screen.text(f"{humidity:.1f}%", 25, 45, 20)
            screen.text(f"{pressure:.2f}hPa", 25, 68, 20)
            screen.blit(sprites.sprite(temp_to_sprite(temp), 0), vec2(7, 28))
            screen.blit(sprites.sprite(hum_to_sprite(humidity), 0), vec2(7, 50))
            screen.blit(sprites.sprite(pres_to_sprite(pressure), 0), vec2(7, 72))
        else:
            screen.text("No sensor detected", 10, 25, 15)
    elif current_screen != 0 and current_screen <= len(screens):
        screen.font = rom_font.yolk
        screen.pen = BACKGROUND_COLOR
        screen.clear()
        screen.pen = color.white
        biggest_rectangle = shape.rounded_rectangle(5, 5, 150, 110, 10)
        smaller_rectangle = shape.rounded_rectangle(7, 7, 146, 106, 10)
        screen.shape(biggest_rectangle)
        screen.pen = BACKGROUND_COLOR
        screen.shape(smaller_rectangle)
        screen.pen = WHITE
        if nicknames[current_screen - 1] == None:
            draw_wrapped_text(
                screen,
                f"{location_names[current_screen - 1]}",
                20,
                10,
                max_width=100,
                line_height=7,
            )
        else:
            draw_wrapped_text(
                screen,
                f"{nicknames[current_screen - 1]}",
                20,
                10,
                max_width=100,
                line_height=7,
            )
    else:
        screen.font = VECTOR_FONT
        screen.pen = BACKGROUND_COLOR
        screen.clear()
        screen.pen = color.white
        biggest_rectangle = shape.rounded_rectangle(5, 5, 150, 110, 10)
        smaller_rectangle = shape.rounded_rectangle(7, 7, 146, 106, 10)
        screen.shape(biggest_rectangle)
        screen.pen = BACKGROUND_COLOR
        screen.shape(smaller_rectangle)
        screen.pen = WHITE
        screen.text("Invalid screen", 10, 10, 15)


run(update)
