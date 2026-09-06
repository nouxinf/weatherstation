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
