import time
from machine import I2C
from breakout_bme280 import BreakoutBME280
from lsm6ds3 import LSM6DS3, NORMAL_MODE_104HZ
from breakout_ltr559 import BreakoutLTR559

i2c = I2C()
bme = BreakoutBME280(i2c)
gyro = LSM6DS3(i2c, mode=NORMAL_MODE_104HZ)
ltr = BreakoutLTR559(i2c)

last_read = 0
readings = bme.read()

# COLOR PALLETTE
BACKGROUND_COLOR = color.rgb(59, 145, 173)
WHITE = color.white

FONT = font.load("/system/assets/fonts/MonaSans-Medium.af")
screen.font = FONT

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


def update():
    global last_read, readings
    now = time.ticks_ms()
    if time.ticks_diff(now, last_read) > 100:  # refresh ten times a second
        readings = bme.read()
        last_read = now
        print(readings)

    temp = round(readings[0], 1)
    humidity = round(readings[2], 0)
    pressure = round(readings[1], 2) / 100

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
    screen.text(f"{temp:.1f}°C", 25, 25, 20)
    screen.text(f"{humidity:.1f}%", 25, 45, 20)
    screen.text(f"{pressure:.2f}hPa", 25, 68, 20)
    # draw sprite

    screen.blit(sprites.sprite(temp_to_sprite(temp), 0), vec2(7, 28))
    screen.blit(sprites.sprite(hum_to_sprite(humidity), 0), vec2(7, 50))
    screen.blit(sprites.sprite(pres_to_sprite(pressure), 0), vec2(7, 72))


run(update)
