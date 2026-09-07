from helpers import *
from secrets import TIMEZONE


def internet_screen(
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
):
    screen.font = YOLK_FONT
    screen.pen = BACKGROUND_COLOR
    screen.clear()
    screen.pen = WHITE
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
