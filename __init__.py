from breakout_bme280 import BreakoutBME280
from pimoroni_i2c import PimoroniI2C

i2c = PimoroniI2C()
bme = BreakoutBME280(i2c)

def update():
    temp, pressure, humidity = bme.read()
    screen.pen = color.white
    screen.text(f"{temp:.1f}°C", 10, 10)