"""Shared pixel frames for field and bag item quick slots."""

from game import drawing
from game.config import NATIVE_HEIGHT, SCALE

GOLD = (174, 134, 81)
GOLD_LIGHT = (224, 189, 121)
INK = (16, 18, 29)


def hit_quick_slot(bounds, x, y):
    left, top, right, bottom = bounds
    badge_height = 9 if right - left >= 44 else 7
    return drawing.contains((left, top, right, bottom + badge_height), x, y)


def draw_quick_slot(bounds, font, icon, number, *, hovered=False):
    left, top, right, bottom = bounds
    width = right - left + 1
    cx = (left + right) // 2
    radius = 9 if width >= 44 else 7

    drawing.rectangle((left + 2, top + 2, right + 2, bottom + 2),
                      (8, 10, 17), filled=True)
    drawing.rectangle(bounds, INK, filled=True)
    drawing.rectangle(bounds, GOLD_LIGHT if hovered else GOLD)
    drawing.rectangle((left + 3, top + 3, right - 3, bottom - 3),
                      (19, 23, 34), filled=True)
    drawing.rectangle((left + 3, top + 3, right - 3, bottom - 3), (52, 56, 73))
    drawing.rectangle((left + 4, top + 4, right - 6, top + 5),
                      (99, 109, 120), filled=True)
    if icon is not None:
        size = 27 if width >= 44 else 22
        icon.draw(cx * SCALE, round((NATIVE_HEIGHT - (top + (bottom - top) * .43)) * SCALE),
                  size * SCALE, size * SCALE)

    # A stepped circular key cap straddles the middle of the slot's bottom edge.
    drawing.rectangle((cx - radius + 3, bottom - radius, cx + radius - 3, bottom + radius),
                      GOLD, filled=True)
    drawing.rectangle((cx - radius, bottom - radius + 3, cx + radius, bottom + radius - 3),
                      GOLD, filled=True)
    drawing.rectangle((cx - radius + 4, bottom - radius + 2,
                       cx + radius - 4, bottom + radius - 2), INK, filled=True)
    drawing.rectangle((cx - radius + 2, bottom - radius + 4,
                       cx + radius - 2, bottom + radius - 4), INK, filled=True)
    drawing.rectangle((cx - 2, bottom - radius + 2, cx + 2, bottom - radius + 2),
                      GOLD_LIGHT, filled=True)
    label = str(number)
    drawing.text(font, cx - font.measure(label)[0] / 2, bottom + 4,
                 label, (237, 224, 196))
