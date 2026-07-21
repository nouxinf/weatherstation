import time
from machine import I2C
from breakout_bme280 import BreakoutBME280
from lsm6ds3 import LSM6DS3, NORMAL_MODE_104HZ
from breakout_ltr559 import BreakoutLTR559

bme = BreakoutBME280(I2C())
gyro = LSM6DS3(I2C(), mode=NORMAL_MODE_104HZ)
ltr = BreakoutLTR559(I2C())

def update():
    temp, pressure, humidity = bme.read()
    screen.pen = color.white
    screen.text(f"{temp:.1f}°C", 10, 10)