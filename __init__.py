import os
import sys

APP_DIR = "/system/apps/weatherstation"

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
if "/" not in sys.path:
    sys.path.insert(0, "/")
os.chdir(APP_DIR)

import time
from machine import I2C
from breakout_bme280 import BreakoutBME280
from lsm6ds3 import LSM6DS3, NORMAL_MODE_104HZ
from breakout_ltr559 import BreakoutLTR559
import json
import wifi

from helpers import *
from sensor_screen import *
from internet_screen import *

try:
    import urequests as requests
except ImportError:
    import requests

from secrets import TIMEZONE

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from badgeware import *  # type: ignore
"""
╔════════════════════════════════════╗
║          COLOUR PALLETTE           ║
╚════════════════════════════════════╝
"""

VECTOR_FONT = font.load("/system/assets/fonts/MonaSans-Medium.af")
DESERT_FONT = font.desert
YOLK_FONT = font.yolk

BACKGROUND_COLOR = color.rgb(59, 145, 173)
BLACK = color.black
WHITE = color.white
GREY = color.rgb(126, 129, 130)


screen.pen = BLACK
screen.clear()

"""
╔════════════════════════════════════╗
║              LOGGING               ║
╚════════════════════════════════════╝
"""

messages = []

no_internet = None


def show_status(message):
    """
    Logging function in the early stages of loading. Outputs logs to the screen
    """
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
    badge.update()


"""
╔════════════════════════════════════╗
║         INITIALISE SENSOR          ║
╚════════════════════════════════════╝
"""

show_status("Loading sensor...")
last_read = 0
readings = (0.0, 0.0, 0.0)
bme = None


def init_i2c():
    try:
        return I2C(timeout=50000, freq=100000)
    except TypeError:
        try:
            return I2C(freq=100000)
        except TypeError:
            return I2C()
    except Exception:
        return I2C()


# initialize the I2C bus ONCE globally to prevent hardware state machine lockups
i2c = init_i2c()

sensor_found = init_sensor(i2c)

if sensor_found:
    show_status("Multisensor found")
else:
    show_status("No multisensor found")

"""
╔════════════════════════════════════╗
║             NETWORKING             ║
╚════════════════════════════════════╝
"""

show_status("Finding Wi-Fi details...")
try:
    from secrets import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    show_status(
        "Couldn't find Wi-Fi details, write them in secrets.py or else you won't be able to use internet"
    )
    no_internet = True
show_status("Connecting to Wi-Fi...")

connected = False
for attempt in range(20):
    if wifi.connect():
        connected = True
        break
    time.sleep(0.5)

if connected:
    print("Connected to Wi-Fi")
    show_status("Connected")
else:
    no_internet = True
    show_status("No Wi-fi")

"""
╔════════════════════════════════════╗
║          LOAD PREFERENCES          ║
╚════════════════════════════════════╝
"""

show_status("Loading options.json")
try:
    with open("options.json") as f:
        options = json.load(f)
except Exception as e:
    show_status(f"Failed to load options.json!! {e}")
    time.sleep(3)
    raise RuntimeError(f"Failed to load options.json!! {e}")
show_status("Fetching locations...")

"""
╔════════════════════════════════════╗
║        FETCHING PLACE NAMES        ║
╚════════════════════════════════════╝
"""

url = "https://nominatim.openstreetmap.org/reverse"
headers = {"User-Agent": "Weatherstation on the Tufty 2350"}

try:
    response = None
    show_status("Fetching location names")
    LAT_MIN, LAT_MAX = -90.0, 90.0
    LON_MIN, LON_MAX = -180.0, 180.0
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
                if not isinstance(entry[2], str):
                    raise ValueError(
                        f"Entry {idx}: third value (nickname) must be a string"
                    )
            else:
                nicknames.append(None)

            # must be numbers within range
            if not (isinstance(val1, (int, float)) and isinstance(val2, (int, float))):
                raise ValueError(f"Entry {idx} contains non-numeric values")

            if not (LAT_MIN <= val1 <= LAT_MAX):
                raise ValueError(
                    f"Entry {idx}: latitude {val1} is outside the range [{LAT_MIN}, {LAT_MAX}]"
                )

            if not (LON_MIN <= val2 <= LON_MAX):
                raise ValueError(
                    f"Entry {idx}: longitude {val2} is outside the range [{LON_MIN}, {LON_MAX}]"
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
        show_status(f"Failed to get locations {e}")
        time.sleep(3)
        raise RuntimeError(f"Failed to get locations {e}")
except Exception as e:
    print(f"An error occurred: {e}")
    show_status(f"OSM.N error: e")
    no_internet = True
finally:
    try:
        response.close()
    except AttributeError:
        pass
    except NameError:
        pass

"""
╔════════════════════════════════════╗
║       FETCHING WEATHER DATA        ║
╚════════════════════════════════════╝
"""
weather_data = []
last_updated_time = ((),)
if not no_internet:
    rtc.time_from_ntp()
    show_status("Fetching weather...")

    def fetch_weather(locations_array=locations):
        """
        Fetches weather from the internet.
        """
        global weather_data, last_updated_time
        for i in locations_array:
            response = requests.get(
                f"https://api.open-meteo.com/v1/forecast?latitude={i[0]}&longitude={i[1]}&current=weather_code,temperature_2m,precipitation,wind_direction_10m&timezone=auto",
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                print(data)
                weather_data.append(data["current"])
                last_updated_time = rtc.datetime()
            else:
                raise RuntimeError(
                    f"failed fetching weather with status {response.status_code}, {response.text}"
                )
        try:
            response.close()
        except AttributeError:
            pass
        except NameError:
            pass

    fetch_weather()

fetching = False

sprites = image.load("assets/spritesheet.png").spritesheet(
    65, 1
)  # remember to update column count

current_screen = 0
screens = ["sensor"] + options.get("locations") + ["attribution"]
print(screens)

prev_down = False
prev_up = False
prev_a = False


def move_current_screen():
    """
    Function that runs every frame to check if button has been pressed to switch screens.
    """
    global current_screen, prev_down, prev_up, prev_a, fetching, weather_data

    down_now = badge.pressed(BUTTON_DOWN)
    up_now = badge.pressed(BUTTON_UP)
    a_now = badge.pressed(BUTTON_A)

    if down_now and not prev_down:
        current_screen = (current_screen + 1) % len(screens)
    elif up_now and not prev_up:
        current_screen = (current_screen - 1) % len(screens)
    elif a_now and not prev_a:
        time.sleep_ms(50)
        if badge.pressed(BUTTON_A) and not no_internet and not fetching:
            print("Refetching weather")
            fetching = True

    prev_down = down_now
    prev_up = up_now
    prev_a = a_now
    # print(current_screen)
    # print(screens)


temp_unit = options.get("tempmeasurement", "unknown")

if no_internet == None:
    no_internet = False
    # no_internet = True
    # alternate between these to debug

"""
╔════════════════════════════════════╗
║             MAIN LOOP              ║
╚════════════════════════════════════╝
"""


def update():
    """
    Main graphics loop
    """
    global fetching, weather_data, last_updated_time, a_now
    move_current_screen()
    if not no_internet:
        diff_time = (rtc.datetime()[3] * 60 + rtc.datetime()[4]) - (
            last_updated_time[3] * 60 + last_updated_time[4]
        )
        if diff_time < 0:
            diff_time += 24 * 60

        if diff_time >= 10:  # refreshes weather every 10 minutes
            print("auto fetching weather")
            fetching = True

    """
    ╔════════════════════════════════════╗
    ║           SENSOR SCREEN            ║
    ╚════════════════════════════════════╝
    """
    if current_screen == 0:
        badge.mode(LORES)
        sensor_loop(temp_unit, sprites, VECTOR_FONT, BACKGROUND_COLOR, WHITE)
        # current screen / total screen count display
        screen.font = DESERT_FONT
        progress_text = f"{current_screen + 1}/{len(screens)}"
        screen.text(
            progress_text, rect(0, 100, 160, 10), align=(image.CENTER, image.MIDDLE)
        )
    elif current_screen != 0 and current_screen <= len(weather_data):
        """
        ╔════════════════════════════════════╗
        ║          INTERNET WEATHER          ║
        ╚════════════════════════════════════╝
        """
        badge.mode(LORES)
        internet_screen(
            YOLK_FONT,
            BACKGROUND_COLOR,
            WHITE,
            no_internet,
            sprites,
            nicknames,
            current_screen,
            location_names,
            weather_data,
            VECTOR_FONT,
            last_updated_time,
            temp_unit,
        )
        # current screen / total screen count display
        screen.font = DESERT_FONT
        progress_text = f"{current_screen + 1}/{len(screens)}"
        screen.text(
            progress_text, rect(0, 100, 160, 10), align=(image.CENTER, image.MIDDLE)
        )
    elif screens[current_screen] == "attribution":
        badge.mode(HIRES)
        screen.pen = BACKGROUND_COLOR
        screen.font = VECTOR_FONT
        screen.clear()
        screen.pen = color.white
        biggest_rectangle = shape.rounded_rectangle(5, 5, 310, 230, 10)
        smaller_rectangle = shape.rounded_rectangle(7, 7, 306, 226, 10)
        screen.shape(biggest_rectangle)
        screen.pen = BACKGROUND_COLOR
        screen.shape(smaller_rectangle)
        screen.pen = WHITE
        screen.text("Attribution", 10, 10, 30)
        screen.text(
            "Weather data by Open-Meteo.com (https://open-meteo.com) \n Geocoding data (C) OpenStreetMap contributors (https://www.openstreetmap.org/\ncopyright)",
            rect(10, 60, 300, 160),
            20,
        )
        # current screen / total screen count display
        # screen.font = DESERT_FONT
        progress_text = f"{current_screen + 1}/{len(screens)}"
        screen.text(
            progress_text, rect(0, 215, 320, 15), 15, align=(image.CENTER, image.MIDDLE)
        )
    else:
        """
        ╔════════════════════════════════════════════════╗
        ║ ERROR SCREEN - This shouldn't display normally ║
        ╚════════════════════════════════════════════════╝
        """
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
        # current screen / total screen count display
        screen.font = DESERT_FONT
        progress_text = f"?/?"
        screen.text(
            progress_text, rect(0, 100, 160, 10), align=(image.CENTER, image.MIDDLE)
        )
    if fetching:
        screen.font = VECTOR_FONT
        screen.pen = WHITE
        outline = shape.rounded_rectangle(22, 47, 115, 35, 10)
        screen.shape(outline)

        screen.pen = GREY
        popup = shape.rounded_rectangle(25, 50, 110, 30, 10)
        screen.shape(popup)

        screen.pen = WHITE
        screen.text(
            "Fetching...", rect(25, 47, 110, 30), align=(image.CENTER, image.MIDDLE)
        )

        badge.update()

        old_weather_data = weather_data
        weather_data = []

        try:
            fetch_weather()
        except BaseException as e:
            print(f"Refetch failed: {e}")
            weather_data = old_weather_data
        finally:
            fetching = False


run(update)
