"""Temporary side-by-side chest and bag panel."""
from game import drawing
from game.config import SCALE, WINDOW_HEIGHT

CHEST_SLOT = (85, 130, 120, 165)
POTION = 'health-potion'
BAG_SIZE = 10
GOLD = (197, 155, 95)


def panel(bounds, fill, border):
    drawing.rectangle(bounds, fill, filled=True)
    drawing.rectangle(bounds, border)


def slots(x, y, columns, items, potion, font):
    for index, item in enumerate(items):
        left = x + index % columns * 41
        top = y + index // columns * 41
        filled = item == POTION
        panel((left, top, left + 35, top + 35),
              (39, 31, 32) if filled else (17, 18, 25),
              GOLD if filled else (65, 66, 79))
        if filled:
            potion.draw((left + 17.5) * SCALE, WINDOW_HEIGHT - (top + 17) * SCALE,
                        30 * SCALE, 30 * SCALE)
            drawing.text(font, left + 27, top + 29, '1')


def draw_loot(resources, potion, has_potion, bag, message):
    small, normal = resources.small, resources.normal
    drawing.black_overlay(.45)
    panel((52, 54, 587, 265), (25, 25, 34), (92, 80, 68))
    drawing.rectangle((57, 59, 582, 260), (59, 53, 54))
    drawing.text(normal, 74, 77, '보물상자 루팅', GOLD)
    drawing.text(small, 496, 77, 'ESC  닫기')
    panel((71, 95, 302, 223), (29, 29, 39), (75, 73, 83))
    panel((338, 95, 568, 223), (29, 29, 39), (75, 73, 83))
    drawing.text(normal, 85, 111, '보물상자')
    drawing.text(normal, 352, 111, '플레이어 가방')
    drawing.text(small, 255, 111, f'{int(has_potion)} / 6')
    drawing.text(small, 515, 111, f'{sum(item is not None for item in bag)} / {BAG_SIZE}')
    slots(85, 130, 3, [POTION if has_potion else None] + [None] * 5, potion, small)
    slots(352, 130, 5, bag, potion, small)
    drawing.text(normal, 311, 169, '→', GOLD)
    drawing.text(small, 73, 245, message)
    if has_potion:
        drawing.text(small, 409, 245, '상자 슬롯 클릭  ·  가방으로 옮기기')
