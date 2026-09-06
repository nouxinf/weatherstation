import time
from breakout_bme280 import BreakoutBME280
from helpers import temp_to_sprite, hum_to_sprite, pres_to_sprite

last_read = 0
readings = (0.0, 0.0, 0.0)
no_multisensor = True
bme = None
_i2c = None


def init_sensor(i2c):
    global _i2c, bme, no_multisensor, last_read, readings
    _i2c = i2c
    try:
        bme = BreakoutBME280(_i2c)
        readings = bme.read()
        no_multisensor = False
    except Exception:
        no_multisensor = True
        bme = None
    last_read = time.ticks_ms()


def sensor_loop(temp_unit, sprites, VECTOR_FONT, BACKGROUND_COLOR, WHITE):
    global last_read, readings, no_multisensor, i2c, bme
    screen.font = VECTOR_FONT

    try:
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
    screen.pen = WHITE
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
