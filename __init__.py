import time
from machine import I2C
from breakout_bme280 import BreakoutBME280
from lsm6ds3 import LSM6DS3, NORMAL_MODE_104HZ
from breakout_ltr559 import BreakoutLTR559
import json
import wifi

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
        # timeout=50000 (50ms) prevents the hardware I2C from freezing the app
        # if the sensor is partially inserted and SDA gets stuck low.
        return I2C(timeout=50000)
    except TypeError:
        # fallback if the firmware's I2C wrapper doesn't accept kwargs
        return I2C()
    except Exception:
        return I2C()


# initialize the I2C bus ONCE globally to prevent hardware state machine lockups
i2c = init_i2c()

try:
    bme = BreakoutBME280(i2c)
    # gyro = LSM6DS3(i2c, mode=NORMAL_MODE_104HZ)
    # ltr = BreakoutLTR559(i2c)
except Exception:
    no_multisensor = True
else:
    no_multisensor = False
    last_read = 0
    try:
        readings = bme.read()
    except Exception:
        no_multisensor = True
        bme = None

if no_multisensor:
    show_status("No multisensor found")
else:
    show_status("Multisensor found")

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
    show_status("Failed to load options.json!!")
    raise SystemExit("Failed to load options.json!!", e)
show_status("Fetching locations...")

"""
╔════════════════════════════════════╗
║        FETCHING PLACE NAMES        ║
╚════════════════════════════════════╝
"""

url = "https://nominatim.openstreetmap.org/reverse"
headers = {"User-Agent": "Weatherstation on the Tufty 2350"}

try:
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
        show_status("Failed to get locations")
        raise SystemExit
except Exception as e:
    print("An error occurred:", e)
    show_status("OSM.N error:", e)
    no_internet = True
finally:
    try:
        response.close()
    except AttributeError:
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
                raise SystemExit(
                    f"failed fetching weather with status {response.status_code}, {response.text}"
                )
        try:
            response.close()
        except AttributeError:
            pass

    fetch_weather()

fetching = False

VECTOR_FONT = font.load("/system/assets/fonts/MonaSans-Medium.af")
DESERT_FONT = font.desert
YOLK_FONT = font.yolk

sprites = image.load("assets/spritesheet.png").spritesheet(
    65, 1
)  # remember to update column count

"""
╔════════════════════════════════════╗
║          HELPER FUNCTIONS          ║
╚════════════════════════════════════╝
"""


def temp_to_sprite(temp, low=-20, high=45, step=5, num_sprites=13):
    """
    Converts temperature value to sprite
    """
    temp = max(low, min(temp, high - 0.0001))
    index = int((temp - low) // step)
    return max(0, min(index, num_sprites - 1))


def hum_to_sprite(hum, low=0, high=100, step=10, num_sprites=10, start_col=13):
    """
    Converts humidity value to sprite
    """
    hum = max(low, min(hum, high - 0.0001))
    index = int((hum - low) // step)
    index = max(0, min(index, num_sprites - 1))
    return start_col + index


def pres_to_sprite(pres, low=950, high=1050, step=14.29, num_sprites=7, start_col=24):
    """
    Converts air pressure value to sprite
    """
    pres = max(low, min(pres, high - 0.0001))
    index = int((pres - low) // step)
    index = max(0, min(index, num_sprites - 1))
    return start_col + index


def weather_code_to_sprite(weather_code):
    """
    Converts WMO weather code to sprite. These are the kind of icons you see in weather apps like cloud with sun etc.
    """
    weather_code_map = {
        0: 31,  # clear
        1: 32,  # mostly clear
        2: 33,  # partly cloudy
        3: 34,  # overcast/cloudy
        45: 35,  # fog
        48: 36,  # icy fog
        51: 37,  # light drizzle
        53: 37,  # drizzle
        55: 37,  # heavy drizzle
        80: 38,  # light showers
        81: 38,  # showers
        82: 38,  # heavy showers
        61: 39,  # light rain
        63: 39,  # rain
        65: 39,  # heavy rain
        56: 40,  # light icy drizzle
        57: 40,  # icy drizzle
        66: 41,  # light icy rain
        67: 41,  # icy rain
        77: 42,  # snow grains
        71: 43,  # light snow
        85: 43,  # light snow showers
        73: 44,  # snow
        75: 45,  # heavy snow
        86: 45,  # snow showers
        95: 46,  # thunder storm
        96: 47,  # thunder storm + light hail
        99: 47,  # thunder storm + hail
    }
    return weather_code_map.get(weather_code, 48 - 1) - 1


def wind_direction_to_sprite(wind_direction):
    """
    Converts wind direction to sprite. Note that there's a slight rounding error which might be a badgeware quirk.
    """
    wind_direction = float(wind_direction) % 360
    dir_sprites = [57, 58, 59, 60, 61, 62, 63, 64]
    index = int(((wind_direction * 2 + 45) % 720) // 90)
    return dir_sprites[index]


def precipitation_to_sprite(mm):
    """
    Converts precipitation to sprite
    """
    sprite_start = 48
    level = 0
    rain_thresholds = [0.1, 0.5, 2, 4, 8, 15, 25, 50]
    for threshold in rain_thresholds:
        if mm >= threshold:
            level += 1
    return sprite_start + level


current_screen = 0
screens = ["sensor"] + options.get("locations")
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
        if not no_internet:
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
        screen.font = VECTOR_FONT

        try:
            global last_read, readings, no_multisensor, i2c, bme
            now = time.ticks_ms()
            if time.ticks_diff(now, last_read) > 100:
                if no_multisensor or bme is None:
                    try:
                        # we do NOT re-initialize I2C() here to avoid hardware state machine lockups
                        bme = BreakoutBME280(i2c)
                        readings = bme.read()
                        no_multisensor = False
                        last_read = now
                    except Exception:
                        no_multisensor = True
                        bme = None
                        last_read = now
                else:
                    try:
                        readings = bme.read()
                        last_read = now
                    except Exception:
                        no_multisensor = True
                        bme = None
                        last_read = now

            if not no_multisensor and bme is not None:
                temp = round(readings[0], 1)
                humidity = round(readings[2], 0)
                pressure = round(readings[1], 2) / 100
            else:
                temp = 0.0
                humidity = 0.0
                pressure = 0.0

        except Exception:
            no_multisensor = True
            temp = 0.0
            humidity = 0.0
            pressure = 0.0

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
        # current screen / total screen count display
        screen.font = DESERT_FONT
        progress_text = f"{current_screen + 1}/{len(screens)}"
        screen.text(
            progress_text, rect(0, 100, 160, 10), align=(image.CENTER, image.MIDDLE)
        )
    elif current_screen != 0 and current_screen <= len(screens):
        """
        ╔════════════════════════════════════╗
        ║          INTERNET WEATHER          ║
        ╚════════════════════════════════════╝
        """
        screen.font = YOLK_FONT
        screen.pen = BACKGROUND_COLOR
        screen.clear()
        screen.pen = color.white
        biggest_rectangle = shape.rounded_rectangle(5, 5, 150, 110, 10)
        smaller_rectangle = shape.rounded_rectangle(7, 7, 146, 106, 10)
        screen.shape(biggest_rectangle)
        screen.pen = BACKGROUND_COLOR
        screen.shape(smaller_rectangle)
        screen.pen = WHITE
        if not no_internet:
            if nicknames[current_screen - 1] == None:
                screen.text(
                    f"{location_names[current_screen - 1]}",
                    rect(35, 10, 100, 30),
                    overflow=image.ELLIPSES,
                )
            else:
                screen.text(
                    f"{nicknames[current_screen - 1]}",
                    rect(35, 10, 100, 30),
                    overflow=image.ELLIPSES,
                )
            # screen.text(str(weather_data[current_screen - 1]["weather_code"]), 10, 10)
            screen.blit(
                sprites.sprite(
                    weather_code_to_sprite(
                        weather_data[current_screen - 1]["weather_code"]
                    ),
                    0,
                ),
                vec2(10, 10),
            )
            screen.blit(
                sprites.sprite(
                    temp_to_sprite(weather_data[current_screen - 1]["temperature_2m"]),
                    0,
                ),
                vec2(7, 33),
            )
            screen.blit(
                sprites.sprite(
                    precipitation_to_sprite(
                        weather_data[current_screen - 1]["precipitation"]
                    ),
                    0,
                ),
                vec2(7, 53),
            )
            screen.blit(
                sprites.sprite(
                    wind_direction_to_sprite(
                        weather_data[current_screen - 1]["wind_direction_10m"]
                    ),
                    0,
                ),
                vec2(7, 73),
            )
            screen.font = VECTOR_FONT
            if temp_unit == "F":
                screen.text(
                    f"{str(((weather_data[current_screen - 1]['temperature_2m']) * 1.8) + 32)}°F",
                    30,
                    30,
                    20,
                )
            elif temp_unit == "K":
                screen.text(
                    f"{str((weather_data[current_screen - 1]['temperature_2m']) + 273.15)}°K",
                    30,
                    30,
                    20,
                )
            else:
                screen.text(
                    f"{str(weather_data[current_screen - 1]['temperature_2m'])}°C",
                    30,
                    30,
                    20,
                )
            screen.text(
                f"{str(weather_data[current_screen - 1]['precipitation'])}mm",
                30,
                50,
                20,
            )
            screen.text(
                f"{str(weather_data[current_screen - 1]['wind_direction_10m'])}°",
                30,
                70,
                20,
            )
            screen.font = YOLK_FONT
            screen.text(
                f"Last updated: {str(last_updated_time[3] + TIMEZONE):0>2}:{str(last_updated_time[4]):0>2}",
                10,
                90,
            )
        else:
            screen.text("No internet", rect(35, 10, 100, 30))
        # current screen / total screen count display
        screen.font = DESERT_FONT
        progress_text = f"{current_screen + 1}/{len(screens)}"
        screen.text(
            progress_text, rect(0, 100, 160, 10), align=(image.CENTER, image.MIDDLE)
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
        except Exception as e:
            print("Refetch failed:", e)
            weather_data = old_weather_data

        fetching = False


run(update)
