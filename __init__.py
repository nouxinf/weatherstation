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


def update():
    global last_read, readings
    now = time.ticks_ms()
    if time.ticks_diff(now, last_read) > 100:  # refresh ten times a second
        readings = bme.read()
        last_read = now
        print(readings)

    temp = round(readings[0], 1)
    humidity = round(readings[2], 0)

    screen.pen = BACKGROUND_COLOR
    screen.clear()
    screen.pen = color.white
    biggest_rectangle = shape.rounded_rectangle(5, 5, 150, 110, 10)
    smaller_rectangle = shape.rounded_rectangle(7, 7, 146, 106, 10)
    screen.shape(biggest_rectangle)
    screen.pen = BACKGROUND_COLOR
    screen.shape(smaller_rectangle)
    screen.pen = WHITE
    screen.text(f"{temp:.1f}°C", 15, 5, 20)


run(update)
