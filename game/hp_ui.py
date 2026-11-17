"""Compact pixel-art health bar shared by the field and melee HUD."""
from game import drawing


def draw_hp_bar(font, x, y, hp, max_hp, *, width=156):
    height = 23
    right = x + width - 1
    bottom = y + height - 1
    # Black silhouette, iron rails, and four restrained brass corner pixels.
    drawing.rectangle((x, y, right, bottom), (11, 12, 18), filled=True)
    drawing.rectangle((x + 2, y + 2, right - 2, bottom - 2), (130, 139, 148), filled=True)
    drawing.rectangle((x + 3, y + 4, right - 3, bottom - 4), (17, 19, 28), filled=True)
    inner_left, inner_right = x + 5, right - 5
    inner_top, inner_bottom = y + 6, bottom - 6
    drawing.rectangle((inner_left, inner_top, inner_right, inner_bottom), (30, 28, 37), filled=True)
    ratio = max(0.0, min(1.0, hp / max_hp)) if max_hp > 0 else 0.0
    fill_width = round((inner_right - inner_left + 1) * ratio)
    if fill_width:
        fill_right = inner_left + fill_width - 1
        drawing.rectangle((inner_left, inner_top, fill_right, inner_bottom), (111, 32, 49), filled=True)
        drawing.rectangle((inner_left, inner_top, fill_right, inner_top + 2), (151, 48, 63), filled=True)
    for corner_x in (x + 2, right - 4):
        for corner_y in (y + 2, bottom - 4):
            drawing.rectangle((corner_x, corner_y, corner_x + 2, corner_y + 2),
                              (194, 143, 66), filled=True)
    drawing.text(font, x + 10, y + 16, f'HP {hp} / {max_hp}', (246, 241, 228))
