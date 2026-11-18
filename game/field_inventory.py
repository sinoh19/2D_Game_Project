"""Field bag with an adjacent equipped gear summary."""
from time import monotonic

import pico2d as p2d

from game import drawing
from game.config import SCALE, WINDOW_HEIGHT
from game.items import BAG_SIZE, ITEMS, Equipment, Item
from game.loot_ui import GOLD, draw_drag_icon, draw_item_tooltip, panel, slot_bounds, slots

BAG_SLOTS = tuple(slot_bounds(130, 130, 5, i) for i in range(BAG_SIZE))
QUICK_SLOTS = tuple(slot_bounds(130, 211, 3, i) for i in range(3))
CLOSE = (325, 65, 348, 88)
PANEL = (106, 54, 353, 265)
GEAR_PANEL = (359, 54, 531, 265)
GEAR_ROWS = (
    ('weapon', '무기', (369, 101, 521, 144)),
    ('armor', '방어구', (369, 155, 521, 198)),
    ('accessory', '장신구', (369, 209, 521, 252)),
)


class FieldInventory:
    def __init__(self, field):
        self.field = field
        self.bag = field.chests.bag
        self.is_open = False
        self.menu = None
        self.message = ''
        self.press = None
        self.drag = None
        self.last_click = None
        self.pointer = None

    def open(self):
        self.is_open = True
        self.message = '장비 드래그 장착 · 아이템 단축 등록'

    def close(self):
        self.is_open = False
        self.menu = None
        self.cancel_drag()

    def click(self, event):
        x, y = event.x / SCALE, event.y / SCALE
        self.pointer = (x, y)
        if event.button == p2d.SDL_BUTTON_RIGHT:
            self.cancel_drag()
            self.menu = None
            for index, bounds in enumerate(BAG_SLOTS):
                if self.bag[index] is not None and drawing.contains(bounds, x, y):
                    item = ITEMS[self.bag[index]]
                    labels = (['장착'] if isinstance(item, Equipment) else
                              ['1번 등록', '2번 등록', '3번 등록']) + ['버리기']
                    left = max(PANEL[0], min(round(x), PANEL[2] - 74))
                    top = max(PANEL[1], min(round(y), PANEL[3] - 20 * len(labels)))
                    self.menu = (index, [(label, (left, top + 20 * row,
                                                   left + 74, top + 20 * (row + 1)))
                                         for row, label in enumerate(labels)])
                    self.message = ITEMS[self.bag[index]].name
                    break
        elif event.button == p2d.SDL_BUTTON_LEFT:
            if drawing.contains(CLOSE, x, y):
                self.close()
            elif self.menu is not None:
                index, options = self.menu
                self.menu = None
                for label, bounds in options:
                    if drawing.contains(bounds, x, y):
                        if label.endswith('번 등록'):
                            self.register(index, int(label[0]) - 1)
                        else:
                            self.apply(index, discard=label == '버리기')
                        break
            else:
                index = self.slot_at(x, y)
                if index is not None and self.bag[index] is not None:
                    now = monotonic()
                    item_id = self.bag[index]
                    if (isinstance(ITEMS[item_id], Equipment) and self.last_click is not None
                            and self.last_click[:2] == (index, item_id)
                            and now - self.last_click[2] <= .35):
                        self.cancel_drag()
                        self.apply(index, discard=False)
                    else:
                        self.last_click = (index, item_id, now)
                        self.press = (index, x, y)
                else:
                    self.last_click = None

    @staticmethod
    def slot_at(x, y):
        return next((index for index, bounds in enumerate(BAG_SLOTS)
                     if drawing.contains(bounds, x, y)), None)

    def gear_at(self, x, y):
        return next((slot for slot, _, bounds in GEAR_ROWS
                     if getattr(self.field.player, slot) is not None
                     and drawing.contains(bounds, x, y)), None)

    def register(self, bag_index, quick_index):
        item_id = self.bag[bag_index]
        if not isinstance(ITEMS.get(item_id), Item):
            self.message = '사용 아이템만 단축 슬롯에 등록할 수 있습니다.'
        elif self.field.chests.register_quick_slot(quick_index, item_id):
            self.message = f'{quick_index + 1}번 등록  ·  {ITEMS[item_id].name}'

    def cancel_drag(self):
        self.press = self.drag = self.last_click = None

    def mouse_move(self, x, y):
        self.pointer = (x, y)
        if self.press is None:
            return
        _, start_x, start_y = self.press
        if self.drag is not None or (x - start_x)**2 + (y - start_y)**2 >= 9:
            self.drag = (x, y)

    def mouse_up(self, x, y):
        if self.press is None:
            return
        self.mouse_move(x, y)
        source = self.press[0]
        dragging = self.drag is not None
        self.press = self.drag = None
        if not dragging:
            return
        self.last_click = None
        quick_target = next((index for index, bounds in enumerate(QUICK_SLOTS)
                             if drawing.contains(bounds, x, y)), None)
        if quick_target is not None:
            self.register(source, quick_target)
            return
        gear_target = next((slot for slot, _, bounds in GEAR_ROWS
                            if drawing.contains(bounds, x, y)), None)
        if gear_target is not None:
            item = ITEMS[self.bag[source]]
            if isinstance(item, Equipment) and item.slot == gear_target:
                self.apply(source, discard=False)
            else:
                self.message = '해당 장비 칸에 장착할 수 없습니다.'
            return
        target = self.slot_at(x, y)
        if target is not None and target != source:
            self.bag[source], self.bag[target] = self.bag[target], self.bag[source]
            self.field.chests.save()
            self.message = '가방 슬롯을 옮겼습니다.'
        elif not drawing.contains(PANEL, x, y) and not drawing.contains(GEAR_PANEL, x, y):
            self.apply(source, discard=True)

    def apply(self, index, discard):
        item_id = self.bag[index]
        item = ITEMS[item_id]
        player = self.field.player
        replacement = None
        if discard:
            self.field.drop_item(item_id)
            message = f'아이템 버림  ·  {item.name}'
        elif isinstance(item, Equipment):
            equipped = getattr(player, item.slot)
            replacement = equipped.id if equipped else None
            setattr(player, item.slot, item)
            message = f'장착  ·  {item.name}'
        else:
            self.message = '가방에서 단축 슬롯에 등록한 뒤 1·2·3 키로 사용하세요.'
            return
        self.bag[index] = replacement
        self.field.chests.save()
        self.message = message
        if discard:
            self.close()
            self.field.map_notice = message
            self.field.map_notice_time = 2.0

    def draw(self):
        resources = self.field.app.resources
        drawing.black_overlay(.45)
        panel(GEAR_PANEL, (25, 25, 34), (92, 80, 68))
        drawing.text(resources.normal, 375, 77, '장비', GOLD)
        dragged_item = ITEMS[self.bag[self.press[0]]] if self.drag is not None else None
        for slot, label, bounds in GEAR_ROWS:
            item = getattr(self.field.player, slot)
            compatible_drop = (isinstance(dragged_item, Equipment)
                               and dragged_item.slot == slot
                               and drawing.contains(bounds, *self.drag))
            panel(bounds, (39, 34, 42) if compatible_drop else (32, 33, 44),
                  GOLD if compatible_drop else (66, 65, 77))
            left, top, _, _ = bounds
            panel((left + 6, top + 6, left + 36, top + 36),
                  (23, 24, 32), (98, 83, 64))
            if item is not None:
                self.field.chests.icons[item.id].draw(
                    (left + 21) * SCALE, WINDOW_HEIGHT - (top + 21) * SCALE,
                    28 * SCALE, 28 * SCALE)
            drawing.text(resources.small, left + 44, top + 14, label, GOLD)
            drawing.text(resources.small, left + 44, top + 31,
                         item.name if item is not None else '빈 슬롯')
        panel(PANEL, (25, 25, 34), (92, 80, 68))
        drawing.text(resources.normal, 124, 77, '가방', GOLD)
        drawing.text(resources.small, 279, 77, 'I / ESC')
        panel(CLOSE, (41, 34, 38), (115, 89, 68))
        drawing.text(resources.normal, 332, 77, '×', GOLD)
        occupied = sum(item is not None for item in self.bag)
        drawing.text(resources.small, 130, 109, f'{occupied} / {BAG_SIZE}')
        hovered = self.slot_at(*self.pointer) if self.pointer is not None else None
        if hovered is not None and self.bag[hovered] is None:
            hovered = None
        selected = self.menu[0] if self.menu else hovered
        visible_bag = self.bag
        if self.drag is not None:
            visible_bag = self.bag.copy()
            visible_bag[self.press[0]] = None
            selected = self.slot_at(*self.drag)
        icons = self.field.chests.icons
        slots(BAG_SLOTS, visible_bag, icons, resources.small, selected)
        for index, bounds in enumerate(QUICK_SLOTS):
            item_id = self.field.chests.quick_slots[index]
            hover = self.drag is not None and drawing.contains(bounds, *self.drag)
            panel(bounds, (39, 31, 32) if item_id or hover else (17, 18, 25),
                  GOLD if item_id or hover else (65, 66, 79))
            drawing.text(resources.small, bounds[0] + 2, bounds[1] + 12, str(index + 1), GOLD)
            if item_id:
                icons[item_id].draw((bounds[0] + 23) * SCALE,
                                    WINDOW_HEIGHT - (bounds[1] + 18) * SCALE,
                                    22 * SCALE, 22 * SCALE)
        drawing.text(resources.small, 124, 257, self.message)
        if self.menu is not None:
            _, options = self.menu
            for label, bounds in options:
                panel(bounds, (41, 34, 38), (115, 89, 68))
                drawing.text(resources.small, bounds[0] + 7, bounds[1] + 13, label)
        if self.drag is not None:
            draw_drag_icon(icons[self.bag[self.press[0]]], *self.drag)
        elif self.menu is None and hovered is not None and self.pointer is not None:
            draw_item_tooltip(resources, ITEMS[self.bag[hovered]], self.pointer)
        elif self.menu is None and self.pointer is not None:
            slot = self.gear_at(*self.pointer)
            equipped = getattr(self.field.player, slot) if slot else None
            if equipped is not None:
                draw_item_tooltip(resources, equipped, self.pointer)
