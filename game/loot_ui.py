"""Temporary side-by-side chest and bag panel."""
import pico2d as p2d

from game import drawing
from game.config import SCALE, WINDOW_HEIGHT
from game.items import BAG_SIZE, POTION

CLOSE_BUTTON = (545, 65, 570, 88)


def slot_bounds(x, y, columns, index):
    left = x + index % columns * 41
    top = y + index // columns * 41
    return left, top, left + 35, top + 35


CHEST_SLOT = slot_bounds(85, 130, 3, 0)
BAG_SLOTS = tuple(slot_bounds(352, 130, 5, i) for i in range(BAG_SIZE))
GOLD = (197, 155, 95)


def bag_slot_at(x, y):
    return next((i for i, bounds in enumerate(BAG_SLOTS)
                 if drawing.contains(bounds, x, y)), None)


def panel(bounds, fill, border):
    drawing.rectangle(bounds, fill, filled=True)
    drawing.rectangle(bounds, border)


def slots(bounds_list, items, icons, font, hover=None):
    for index, (bounds, item) in enumerate(zip(bounds_list, items)):
        left, top, _, _ = bounds
        filled = item in icons
        panel(bounds, (39, 31, 32) if filled or hover == index else (17, 18, 25),
              GOLD if filled or hover == index else (65, 66, 79))
        if filled:
            icons[item].draw((left + 17.5) * SCALE, WINDOW_HEIGHT - (top + 17) * SCALE,
                        30 * SCALE, 30 * SCALE)
            drawing.text(font, left + 27, top + 29, '1')


def draw_loot(resources, icons, has_potion, bag, message, drag=None, bag_source=None):
    small, normal = resources.small, resources.normal
    drawing.black_overlay(.45)
    panel((52, 54, 587, 265), (25, 25, 34), (92, 80, 68))
    drawing.rectangle((57, 59, 582, 260), (59, 53, 54))
    drawing.text(normal, 74, 77, '보물상자 루팅', GOLD)
    drawing.text(small, 488, 77, 'ESC  닫기')
    panel(CLOSE_BUTTON, (41, 34, 38), (115, 89, 68))
    drawing.text(normal, 553, 77, '×', GOLD)
    panel((71, 95, 302, 223), (29, 29, 39), (75, 73, 83))
    panel((338, 95, 568, 223), (29, 29, 39), (75, 73, 83))
    drawing.text(normal, 85, 111, '보물상자')
    drawing.text(normal, 352, 111, '플레이어 가방')
    drawing.text(small, 255, 111, f'{int(has_potion)} / 6')
    drawing.text(small, 515, 111, f'{sum(item is not None for item in bag)} / {BAG_SIZE}')
    chest_slots = (slot_bounds(85, 130, 3, index) for index in range(6))
    chest_visible = has_potion and (drag is None or bag_source is not None)
    slots(chest_slots, [POTION if chest_visible else None] + [None] * 5, icons, small)
    hover = bag_slot_at(*drag) if drag is not None else None
    visible_bag = bag
    if drag is not None and bag_source is not None:
        visible_bag = bag.copy()
        visible_bag[bag_source] = None
    elif hover is not None and bag[hover] is not None:
        hover = None
    slots(BAG_SLOTS, visible_bag, icons, small, hover)
    drawing.text(normal, 311, 169, '→', GOLD)
    drawing.text(small, 73, 245, message)
    if has_potion:
        drawing.text(small, 401, 245, '클릭 또는 드래그로 옮기기')
    elif any(bag):
        drawing.text(small, 401, 245, '드래그로 가방 정리')
    if drag is not None:
        draw_drag_icon(icons[POTION if bag_source is None else bag[bag_source]], *drag)


def draw_drag_icon(icon, x, y):
    p2d.SDL_SetTextureAlphaMod(icon.texture, 155)
    try:
        icon.draw(x * SCALE, WINDOW_HEIGHT - y * SCALE, 30 * SCALE, 30 * SCALE)
    finally:
        p2d.SDL_SetTextureAlphaMod(icon.texture, 255)
