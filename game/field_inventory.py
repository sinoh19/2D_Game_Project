"""Standalone field bag and its right-click actions."""
import pico2d as p2d

from game import drawing
from game.config import SCALE
from game.items import BAG_SIZE, ITEMS, DroppedItem
from game.loot_ui import GOLD, draw_drag_icon, panel, slot_bounds, slots

BAG_SLOTS = tuple(slot_bounds(220, 130, 5, i) for i in range(BAG_SIZE))
CLOSE = (415, 65, 438, 88)
PANEL = (196, 54, 443, 265)


class FieldInventory:
    def __init__(self, field):
        self.field = field
        self.bag = field.chests.bag
        self.is_open = False
        self.menu = None
        self.message = ''
        self.press = None
        self.drag = None

    def open(self):
        self.is_open = True
        self.message = '드래그 정리  ·  가방 밖에 놓아 버리기'

    def close(self):
        self.is_open = False
        self.menu = None
        self.cancel_drag()

    def click(self, event):
        x, y = event.x / SCALE, event.y / SCALE
        if event.button == p2d.SDL_BUTTON_RIGHT:
            self.cancel_drag()
            self.menu = None
            for index, bounds in enumerate(BAG_SLOTS):
                if self.bag[index] is not None and drawing.contains(bounds, x, y):
                    left, top = min(round(x), 560), min(round(y), 308)
                    self.menu = (index, (left, top, left + 74, top + 21),
                                 (left, top + 22, left + 74, top + 43))
                    self.message = ITEMS[self.bag[index]].name
                    break
        elif event.button == p2d.SDL_BUTTON_LEFT:
            if drawing.contains(CLOSE, x, y):
                self.close()
            elif self.menu is not None:
                index, use, discard = self.menu
                self.menu = None
                if drawing.contains(use, x, y):
                    self.apply(index, discard=False)
                elif drawing.contains(discard, x, y):
                    self.apply(index, discard=True)
            else:
                index = self.slot_at(x, y)
                if index is not None and self.bag[index] is not None:
                    self.press = (index, x, y)

    @staticmethod
    def slot_at(x, y):
        return next((index for index, bounds in enumerate(BAG_SLOTS)
                     if drawing.contains(bounds, x, y)), None)

    def cancel_drag(self):
        self.press = self.drag = None

    def mouse_move(self, x, y):
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
        self.cancel_drag()
        if not dragging:
            return
        target = self.slot_at(x, y)
        if target is not None and target != source:
            self.bag[source], self.bag[target] = self.bag[target], self.bag[source]
            self.field.chests.save()
            self.message = '가방 슬롯을 옮겼습니다.'
        elif not drawing.contains(PANEL, x, y):
            self.apply(source, discard=True)

    def apply(self, index, discard):
        item_id = self.bag[index]
        item = ITEMS[item_id]
        player = self.field.player
        if discard:
            self.field.dropped_items.append(DroppedItem(item_id, player.x, player.y - player.HEIGHT / 2))
            message = f'아이템 버림  ·  {item.name}'
        else:
            consumed, message = item.use(player)
            if not consumed:
                self.message = message
                return
        self.bag[index] = None
        self.field.chests.save()
        self.message = message
        if discard:
            self.close()
            self.field.map_notice = message
            self.field.map_notice_time = 2.0

    def draw(self):
        resources = self.field.app.resources
        drawing.black_overlay(.45)
        panel(PANEL, (25, 25, 34), (92, 80, 68))
        drawing.text(resources.normal, 214, 77, '플레이어 가방', GOLD)
        drawing.text(resources.small, 369, 77, 'I / ESC')
        panel(CLOSE, (41, 34, 38), (115, 89, 68))
        drawing.text(resources.normal, 422, 77, '×', GOLD)
        occupied = sum(item is not None for item in self.bag)
        drawing.text(resources.small, 220, 109, f'{occupied} / {BAG_SIZE}')
        selected = self.menu[0] if self.menu else None
        visible_bag = self.bag
        if self.drag is not None:
            visible_bag = self.bag.copy()
            visible_bag[self.press[0]] = None
            selected = self.slot_at(*self.drag)
        icons = self.field.chests.icons
        slots(BAG_SLOTS, visible_bag, icons, resources.small, selected)
        drawing.text(resources.small, 214, 245, self.message)
        if self.menu is not None:
            _, use, discard = self.menu
            for bounds, label in ((use, '사용'), (discard, '버리기')):
                panel(bounds, (41, 34, 38), (115, 89, 68))
                drawing.text(resources.normal, bounds[0] + 11, bounds[1] + 10, label)
        if self.drag is not None:
            draw_drag_icon(icons[self.bag[self.press[0]]], *self.drag)
