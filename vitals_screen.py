import time
from helpers import sizeof_fmt
import gc


def vitals_loop(sprites, VECTOR_FONT, BACKGROUND_COLOR, WHITE, YOLK_FONT):
    global battery_level, last_updated_battery_time, pending_level, pending_count
    """
    ╔════════════════════════════════════╗
    ║              BATTERY               ║
    ╚════════════════════════════════════╝
    """
    try:
        battery_level
    except NameError:
        battery_level = badge.battery_level()
        last_updated_battery_time = time.ticks_ms()
        pending_level = battery_level
        pending_count = 0

    if time.ticks_diff(time.ticks_ms(), last_updated_battery_time) >= 1000:
        new_level = badge.battery_level()

        if new_level != battery_level:
            if new_level == pending_level:
                pending_count += 1
            else:
                pending_level = new_level
                pending_count = 1

            if pending_count >= 2:
                battery_level = pending_level
                pending_count = 0
        else:
            pending_level = new_level
            pending_count = 0

        last_updated_battery_time = time.ticks_ms()
    screen.pen = BACKGROUND_COLOR
    screen.clear()
    screen.pen = WHITE
    biggest_rectangle = shape.rounded_rectangle(5, 5, 150, 110, 10)
    smaller_rectangle = shape.rounded_rectangle(7, 7, 146, 106, 10)
    screen.shape(biggest_rectangle)
    screen.pen = BACKGROUND_COLOR
    screen.shape(smaller_rectangle)
    screen.pen = WHITE
    screen.font = VECTOR_FONT
    screen.text("Vitals Info", 10, 10, 15)
    screen.text("Battery (can be inaccurate)", 10, 25, 12)
    bg_rect = shape.rectangle(10, 40, 104, 10)
    screen.shape(bg_rect)
    screen.pen = BACKGROUND_COLOR
    inside_rect = shape.rectangle(12, 42, 100, 6)
    screen.shape(inside_rect)
    screen.pen = color.rgb(66, 245, 81)  # bright green
    battery_rect = shape.rectangle(12, 42, battery_level, 6)
    screen.shape(battery_rect)
    # print(battery_level)

    if badge.is_charging():
        screen.blit(sprites.sprite(66, 0), vec2(110, 36))
    else:
        screen.pen = WHITE
        screen.text(f"{battery_level}%", 115, 37)
    """
    ╔════════════════════════════════════╗
    ║             DISK SPACE             ║
    ╚════════════════════════════════════╝
    """
    try:
        ram_free
    except NameError:
        gc.collect()
        ram_free = gc.mem_free()
        last_updated_ram_time = time.ticks_ms()
    if time.ticks_diff(time.ticks_ms(), last_updated_ram_time) >= 1000:
        gc.collect()
        ram_free = gc.mem_free()
        last_updated_ram_time = time.ticks_ms()
    screen.pen = WHITE
    screen.text(
        f"Flash space: {sizeof_fmt(badge.disk_free()[1])}/{sizeof_fmt(badge.disk_free()[0])}",
        10,
        50,
        12,
    )
    screen.text(f"Free RAM: {sizeof_fmt(ram_free)}/8MiB")
