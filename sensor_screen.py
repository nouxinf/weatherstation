import time
from breakout_bme280 import BreakoutBME280
from helpers import temp_to_sprite, hum_to_sprite, pres_to_sprite

# Known BME280 power-on default calibration values
DEFAULT_TEMP = 23.9
DEFAULT_HUM = 74.0
DEFAULT_PRES_RAW = 68752.0  # 687.52 hPa * 100

last_read = 0
readings = (0.0, 0.0, 0.0)
no_multisensor = True
bme = None
_i2c = None
_last_read_valid = False
_consecutive_defaults = 0


def init_sensor(i2c):
    global _i2c, bme, no_multisensor, last_read, readings, _last_read_valid, _consecutive_defaults

    _i2c = i2c
    found = False
    address = None

    try:
        devices = i2c.scan()

        if 0x76 in devices:
            address = 0x76
        elif 0x77 in devices:
            address = 0x77
    except Exception:
        address = None

    if address is not None:
        try:
            bme = BreakoutBME280(_i2c, address=address)
            readings = bme.read()

            no_multisensor = False
            _last_read_valid = True
            _consecutive_defaults = 0
            found = True
        except Exception:
            no_multisensor = True
            bme = None
            _last_read_valid = False
    else:
        no_multisensor = True
        bme = None
        _last_read_valid = False

    last_read = time.ticks_ms()
    return found


def _is_default_reading(r):
    """Check if reading matches BME280 power-on defaults."""
    return (
        abs(r[0] - DEFAULT_TEMP) < 0.2
        and abs(r[2] - DEFAULT_HUM) < 1.0
        and abs(r[1] - DEFAULT_PRES_RAW) < 10.0
    )


def sensor_loop(temp_unit, sprites, VECTOR_FONT, BACKGROUND_COLOR, WHITE):
    global last_read, readings, no_multisensor, bme, _last_read_valid, _consecutive_defaults

    screen.font = VECTOR_FONT
    now = time.ticks_ms()

    if time.ticks_diff(now, last_read) > 1000:
        if bme is not None:
            try:
                new_readings = bme.read()

                if _is_default_reading(new_readings):
                    _consecutive_defaults += 1
                    if _consecutive_defaults >= 2:
                        # sensor is stuck returning defaults, try reconfiguring to wake it
                        try:
                            bme.configure(2, 0, 16, 2, 1, 0)
                            time.sleep_ms(50)
                            new_readings = bme.read()
                            _consecutive_defaults = 0
                        except Exception:
                            _last_read_valid = False
                            no_multisensor = True
                            last_read = now
                            return
                    else:
                        # first default reading, discard and wait for next cycle
                        last_read = now
                        return
                else:
                    _consecutive_defaults = 0

                readings = new_readings
                _last_read_valid = True
                no_multisensor = False

            except Exception:
                _last_read_valid = False
                no_multisensor = True
        else:
            _last_read_valid = False
            no_multisensor = True

        last_read = now

    display_sensor = not no_multisensor and _last_read_valid and bme is not None

    if display_sensor:
        temp = round(readings[0], 1)
        humidity = round(readings[2], 0)
        pressure = round(readings[1], 2) / 100
    else:
        temp = 0.0
        humidity = 0.0
        pressure = 0.0

    # Draw UI
    screen.pen = BACKGROUND_COLOR
    screen.clear()
    screen.pen = WHITE
    biggest_rectangle = shape.rounded_rectangle(5, 5, 150, 110, 10)
    smaller_rectangle = shape.rounded_rectangle(7, 7, 146, 106, 10)
    screen.shape(biggest_rectangle)
    screen.pen = BACKGROUND_COLOR
    screen.shape(smaller_rectangle)
    screen.pen = WHITE
    screen.text("Local sensor data", 10, 10, 15)

    if display_sensor:
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
