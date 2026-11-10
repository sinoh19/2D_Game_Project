"""Field treasure chests and their opening animation."""
from math import isfinite
from random import choice

import pico2d as p2d

from game import drawing
from game.config import ASSETS, NATIVE_WIDTH, SCALE, WINDOW_HEIGHT
from game.items import (BAG_SIZE, ITEMS, LEATHER_ARMOR, POTION, RING_IDS, SWORD,
                        DroppedItem, Equipment)
from game.loot_ui import CHEST_SLOT, CLOSE_BUTTON, bag_slot_at, draw_loot

FRAME_SIZE = 192
DRAW_SIZE = 44
FRAME_COUNT = 5
OPEN_TIME = .4


class TreasureChest:
    def __init__(self, spec, opened, looted):
        self.id, self.x, self.y = spec
        self.elapsed = OPEN_TIME if opened or looted else None
        self.looted = looted

    def draw(self, sheet, camera):
        elapsed = self.elapsed or 0.0
        frame = min(FRAME_COUNT - 1, int(elapsed * FRAME_COUNT / OPEN_TIME))
        sheet.clip_draw(frame * FRAME_SIZE, 0, FRAME_SIZE, FRAME_SIZE,
                        (self.x - camera) * SCALE,
                        WINDOW_HEIGHT - (self.y - 21) * SCALE,
                        DRAW_SIZE * SCALE, DRAW_SIZE * SCALE)



class TreasureChests:
    def __init__(self, field, restore):
        self.field = field
        self.map_id = field.layout.get('mapId', 'dungeon_01')
        data = field.app.storage.read('chests.json', {}) if restore else {}
        opened = data.get('opened', []) if data.get('scene') == self.map_id else []
        looted = data.get('looted', []) if data.get('scene') == self.map_id else []
        if not isinstance(opened, list):
            opened = []
        if not isinstance(looted, list):
            looted = []
        bag = data.get('bag', [])
        bag = bag[:BAG_SIZE] if isinstance(bag, list) else []
        self.bag = [item if isinstance(item, str) and item in ITEMS else None for item in bag]
        self.bag.extend([None] * (BAG_SIZE - len(self.bag)))
        self.contents = data.get('contents', {}) if data.get('scene') == self.map_id else {}
        if not isinstance(self.contents, dict):
            self.contents = {}
        self.contents = {str(key): value for key, value in self.contents.items()
                         if isinstance(value, str) and value in ITEMS}
        for slot, starter_id in (('weapon', SWORD), ('armor', LEATHER_ARMOR), ('accessory', None)):
            item_id = data.get(slot, starter_id)
            item = ITEMS.get(item_id) if isinstance(item_id, str) else None
            setattr(field.player, slot, item if isinstance(item, Equipment) and item.slot == slot else None)
        if data.get('scene') == self.map_id:
            self.restore_drops(SWORD, data.get('dropped_weapons'))
            self.restore_drops(LEATHER_ARMOR, data.get('dropped_armor'))
            for ring_id in RING_IDS:
                self.restore_drops(ring_id, data.get('dropped_' + ring_id))
        self.chests = [TreasureChest(spec, spec[0] in opened, spec[0] in looted)
                       for spec in field.layout.get('chests', [])]
        if self.chests and not restore and not self.contents:
            self.contents[str(self.chests[0].id)] = choice(RING_IDS)
        elif self.chests and not self.contents and restore:
            # Keep older saved runs compatible with the chest's previous potion reward.
            self.contents[str(self.chests[0].id)] = POTION
        self.active = None
        self.message = ''
        self.press_origin = None
        self.bag_source = None
        self.drag = None
        self.pointer = None
        if self.chests:
            self.sheet = p2d.load_image(str(ASSETS / 'dungeon' / 'scenery' / 'chest-open-sheet.png'))
        folder = ASSETS / 'dungeon' / 'items'
        self.icons = {item_id: p2d.load_image(str(folder / item.icon)) for item_id, item in ITEMS.items()}

    def restore_drops(self, item_id, drops):
        if isinstance(drops, list):
            for position in drops:
                if (isinstance(position, list) and len(position) == 2
                        and all(type(value) in (int, float) and isfinite(value) for value in position)):
                    self.field.dropped_items.append(DroppedItem(item_id, *position))

    def nearby(self):
        player = self.field.player
        if not player.grounded:
            return None
        candidates = [chest for chest in self.chests
                      if abs(player.x - chest.x) <= 42 and abs(player.y - chest.y) <= 16]
        return min(candidates, key=lambda chest: abs(player.x - chest.x), default=None)

    def chest_item(self, chest):
        return self.contents.get(str(chest.id))

    def item_label(self, chest):
        item_id = self.chest_item(chest)
        if item_id is None:
            return '상자가 비어 있습니다.'
        item = ITEMS[item_id]
        if isinstance(item, Equipment):
            bonus = ', '.join(f'{name} +{value}' for name, value in item.stats)
            return f'{item.name}  ·  {bonus}'
        return f'{item.name}  ×1'

    def interact(self):
        chest = self.nearby()
        if chest is None:
            return False
        if chest.elapsed is None:
            chest.elapsed = 0.0
        self.active = chest
        self.message = '상자가 비어 있습니다.' if chest.looted else self.item_label(chest)
        return True

    def cancel_drag(self):
        self.press_origin = self.drag = self.bag_source = None

    def close(self):
        self.cancel_drag()
        self.active = None

    def mouse_down(self, x, y):
        self.pointer = (x, y)
        chest = self.active
        if chest is None or chest.elapsed < OPEN_TIME:
            return
        if drawing.contains(CLOSE_BUTTON, x, y):
            self.close()
        elif not chest.looted and drawing.contains(CHEST_SLOT, x, y):
            self.press_origin = (x, y)
            self.message = self.item_label(chest)
        else:
            index = bag_slot_at(x, y)
            if index is not None and self.bag[index] is not None:
                self.press_origin = (x, y)
                self.bag_source = index

    def mouse_move(self, x, y):
        self.pointer = (x, y)
        if self.press_origin is None:
            return
        start_x, start_y = self.press_origin
        if self.drag is not None or (x - start_x)**2 + (y - start_y)**2 >= 9:
            self.drag = (x, y)

    def mouse_up(self, x, y):
        if self.press_origin is None:
            return
        self.mouse_move(x, y)
        dragging = self.drag is not None
        source = self.bag_source
        self.cancel_drag()
        if source is not None:
            target = bag_slot_at(x, y) if dragging else None
            if target is not None and target != source:
                self.bag[source], self.bag[target] = self.bag[target], self.bag[source]
                self.save()
                self.message = '가방 슬롯을 옮겼습니다.'
            return
        if dragging:
            index = bag_slot_at(x, y)
            if index is None:
                return
            if self.bag[index] is not None:
                self.message = '빈 슬롯에 놓아 주세요.'
                return
        elif drawing.contains(CHEST_SLOT, x, y):
            if None not in self.bag:
                self.message = '가방에 빈 슬롯이 없습니다.'
                return
            index = self.bag.index(None)
        else:
            return
        chest = self.active
        if chest is None or chest.looted:
            return
        item_id = self.chest_item(chest)
        if item_id is None:
            self.message = '상자가 비어 있습니다.'
            return
        self.bag[index] = item_id
        chest.looted = True
        self.save()
        self.message = f'{ITEMS[item_id].name}을(를) 가방에 옮겼습니다.'

    def draw_loot(self):
        if self.active is not None and self.active.elapsed >= OPEN_TIME:
            draw_loot(self.field.app.resources, self.icons,
                      None if self.active.looted else self.chest_item(self.active),
                      self.bag, self.message, self.drag, self.bag_source, self.pointer)

    def update(self, dt):
        for chest in self.chests:
            if chest.elapsed is not None:
                chest.elapsed = min(OPEN_TIME, chest.elapsed + dt)

    def save(self):
        opened = [chest.id for chest in self.chests if chest.elapsed is not None]
        looted = [chest.id for chest in self.chests if chest.looted]
        self.field.app.storage.write('chests.json', {
            'scene': self.map_id, 'opened': opened, 'looted': looted, 'bag': self.bag,
            'contents': self.contents,
            'accessory': self.field.player.accessory.id if self.field.player.accessory else None,
            'weapon': self.field.player.weapon.id if self.field.player.weapon else None,
            'armor': self.field.player.armor.id if self.field.player.armor else None,
            'dropped_armor': [[item.x, item.feet] for item in self.field.dropped_items
                              if item.item_id == LEATHER_ARMOR],
            'dropped_weapons': [[item.x, item.feet] for item in self.field.dropped_items
                                if item.item_id == SWORD],
            **{'dropped_' + ring_id: [[item.x, item.feet] for item in self.field.dropped_items
                                      if item.item_id == ring_id] for ring_id in RING_IDS},
        })

    def draw(self, camera):
        for chest in self.chests:
            if camera - FRAME_SIZE <= chest.x <= camera + self.field.view_width + FRAME_SIZE:
                chest.draw(self.sheet, camera)

    def draw_hint(self, camera):
        chest = self.nearby()
        if chest is None or self.active is not None:
            return False
        label = 'F  상자 열기' if chest.elapsed is None else 'F  상자 보기'
        font = self.field.app.resources.small
        width, height = font.measure(label)
        x = max(5, min(NATIVE_WIDTH - width - 5, round(chest.x - camera - width / 2)))
        y = max(30, round(chest.y) - 46)
        top = y - height // 2
        drawing.rectangle((x - 5, top - 3, x + width + 4, top + height + 2),
                          (20, 19, 22), filled=True)
        drawing.text(font, x, y, label)
        return True
