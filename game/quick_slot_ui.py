"""The field HUD artwork reused for the bag's registered item slots."""

from game import drawing
from game.config import NATIVE_HEIGHT, SCALE


def hit_quick_slot(bounds, x, y):
    left, top, right, bottom = bounds
    return drawing.contains((left, top, right, bottom + 7), x, y)


def draw_bag_quick_slots(sheet, bounds_list, icons, item_ids, *, hovered=None):
    """Draw the same PixelLab frames, then full-size icons under the key badges."""
    left, top = bounds_list[0][:2]
    right = bounds_list[-1][2]
    width = right - left + 1
    height = round(57 * width / 155)
    sheet.clip_draw(14, sheet.h - 90, 155, 57,
                    round((left + width / 2) * SCALE),
                    round((NATIVE_HEIGHT - top - height / 2) * SCALE),
                    width * SCALE, height * SCALE)

    for index, (bounds, item_id) in enumerate(zip(bounds_list, item_ids)):
        slot_left, slot_top, slot_right, _ = bounds
        center_x = (slot_left + slot_right) / 2
        if item_id is not None:
            icons[item_id].draw(round(center_x * SCALE),
                                round((NATIVE_HEIGHT - slot_top - 17.5) * SCALE),
                                30 * SCALE, 30 * SCALE)
        if hovered == index:
            drawing.rectangle(bounds, (224, 189, 121))
        # Repaint the original PixelLab badge above the icon, without shrinking it.
        sheet.clip_draw(27 + index * 54, sheet.h - 89, 21, 21,
                        round(center_x * SCALE),
                        round((NATIVE_HEIGHT - top - round(45 * width / 155)) * SCALE),
                        16 * SCALE, 16 * SCALE)
