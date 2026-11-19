"""Field treasure chests and their opening animation."""
from math import isfinite
from random import choice

import pico2d as p2d

from game import drawing
from game.config import ASSETS, NATIVE_WIDTH, SCALE, WINDOW_HEIGHT
from game.items import (BAG_SIZE, ITEMS, LEATHER_ARMOR, POTION, RING_IDS, SWORD,
                        DroppedItem, Equipment, Item)
from game.loot_ui import CLOSE_BUTTON, bag_slot_at, chest_slot_at, draw_loot

FRAME_SIZE = 192
DRAW_SIZE = 56  # Sheet canvas size that matches a 32px Tiled chest object.
TILED_SIZE = 32
FRAME_COUNT = 5
OPEN_TIME = .4


class TreasureChest:
    def __init__(self, spec, opened, looted):
        self.id, self.x, self.y = spec[:3]
        self.width, self.height = spec[3:] if len(spec) == 5 else (TILED_SIZE, TILED_SIZE)
        self.elapsed = OPEN_TIME if opened or looted else None
        self.looted = looted

    def draw(self, sheet, camera):
        elapsed = self.elapsed or 0.0
        frame = min(FRAME_COUNT - 1, int(elapsed * FRAME_COUNT / OPEN_TIME))
        # Keep the sheet's visible pixels aligned with the Tiled preview's
        # 24x16 art inside its 32x32 object, including the floor contact.
        sheet.clip_draw(frame * FRAME_SIZE, 0, FRAME_SIZE, FRAME_SIZE,
                        (self.x - camera) * SCALE,
                        WINDOW_HEIGHT - (self.y - self.height * 28 / TILED_SIZE) * SCALE,
                        DRAW_SIZE * self.width / TILED_SIZE * SCALE,
                        DRAW_SIZE * self.height / TILED_SIZE * SCALE)



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
        saved_slots = data.get('quick_slots', [])
        saved_slots = saved_slots if isinstance(saved_slots, list) else []
        self.quick_slots = [item if isinstance(item, str) and isinstance(ITEMS.get(item), Item)
                            else None for item in saved_slots[:3]]
        self.quick_slots.extend([None] * (3 - len(self.quick_slots)))
        if data.get('quick_slot_storage') != 1:
            # Legacy slots referenced bag items; transfer each owned copy once.
            for index, item_id in enumerate(self.quick_slots):
                if item_id is not None and item_id in self.bag:
                    self.bag[self.bag.index(item_id)] = None
                else:
                    self.quick_slots[index] = None
        raw_contents = data.get('contents', {}) if data.get('scene') == self.map_id else {}
        if not isinstance(raw_contents, dict):
            raw_contents = {}
        self.contents = {}
        for key, value in raw_contents.items():
            items = [value] if isinstance(value, str) else value
            if isinstance(items, list):
                valid = [item for item in items if isinstance(item, str) and item in ITEMS]
                if valid:
                    self.contents[str(key)] = valid
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
            self.contents[str(self.chests[0].id)] = [choice(RING_IDS), POTION]
        elif self.chests and not self.contents and restore and self.chests[0].id not in looted:
            # Older saves may predate persisted chest rewards.
            self.contents[str(self.chests[0].id)] = [POTION]
        self.starter_chest_prepared = True
        if self.chests and restore and not data.get('starterChestPrepared'):
            first = self.chests[0]
            key = str(first.id)
            if first.id not in looted:
                items = self.contents.setdefault(key, [])
                if POTION not in items:
                    items.append(POTION)
            self.starter_chest_prepared = True
        self.active = None
        self.message = ''
        self.press_origin = None
        self.bag_source = None
        self.chest_source = None
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
                      if abs(player.x - chest.x) <= 42
                      and chest.y - chest.height - 16 <= player.y <= chest.y + 72]
        return min(candidates, key=lambda chest: abs(player.x - chest.x), default=None)

    def chest_item(self, chest):
        return self.contents.get(str(chest.id), [])

    def item_label(self, chest):
        items = self.chest_item(chest)
        if not items:
            return '상자가 비어 있습니다.'
        if len(items) > 1:
            return f'상자 안에 아이템이 {len(items)}개 있습니다.'
        item = ITEMS[items[0]]
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
        self.press_origin = self.drag = self.bag_source = self.chest_source = None

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
        elif not chest.looted and chest_slot_at(x, y) is not None:
            index = chest_slot_at(x, y)
            items = self.chest_item(chest)
            if index < len(items):
                self.press_origin = (x, y)
                self.chest_source = index
                self.message = ITEMS[items[index]].name
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
        chest_source = self.chest_source
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
        elif chest_source is not None:
            index = bag_slot_at(x, y) if dragging else None
            if dragging and index is None:
                return
            if index is None:
                if None not in self.bag:
                    self.message = '가방에 빈 슬롯이 없습니다.'
                    return
                index = self.bag.index(None)
            elif self.bag[index] is not None:
                self.message = '빈 슬롯에 놓아 주세요.'
                return
        else:
            return
        chest = self.active
        if chest is None or chest.looted:
            return
        items = self.chest_item(chest)
        if chest_source is None or chest_source >= len(items):
            return
        item_id = items.pop(chest_source)
        self.bag[index] = item_id
        self.contents[str(chest.id)] = items
        chest.looted = not items
        self.save()
        self.message = f'{ITEMS[item_id].name}을(를) 가방에 옮겼습니다.'

    def draw_loot(self):
        if self.active is not None and self.active.elapsed >= OPEN_TIME:
            draw_loot(self.field.app.resources, self.icons,
                      [] if self.active.looted else self.chest_item(self.active),
                      self.bag, self.message, self.drag, self.bag_source, self.pointer, self.chest_source)

    def update(self, dt):
        for chest in self.chests:
            if chest.elapsed is not None:
                chest.elapsed = min(OPEN_TIME, chest.elapsed + dt)

    def register_quick_slot(self, index, item_id, bag_index=None):
        if not 0 <= index < 3 or not isinstance(ITEMS.get(item_id), Item) or item_id not in self.bag:
            return False
        if bag_index is None:
            bag_index = self.bag.index(item_id)
        if not 0 <= bag_index < len(self.bag) or self.bag[bag_index] != item_id:
            return False
        self.bag[bag_index] = self.quick_slots[index]
        self.quick_slots[index] = item_id
        self.save()
        return True

    def return_quick_slot(self, index):
        item_id = self.quick_slots[index]
        if item_id is None:
            return False, '주머니가 비어 있습니다.'
        if None not in self.bag:
            return False, '가방에 빈 슬롯이 없습니다.'
        self.bag[self.bag.index(None)] = item_id
        self.quick_slots[index] = None
        self.save()
        return True, f'{ITEMS[item_id].name}을(를) 가방에 옮겼습니다.'

    def sync_quick_slots(self):
        for index, item_id in enumerate(self.quick_slots):
            if item_id is not None and not isinstance(ITEMS.get(item_id), Item):
                self.quick_slots[index] = None

    def use_quick_slot(self, index, *, persist=True):
        item_id = self.quick_slots[index]
        if not isinstance(ITEMS.get(item_id), Item):
            self.sync_quick_slots()
            return False, '등록된 아이템이 없습니다.'
        consumed, message = ITEMS[item_id].use(self.field.player)
        if consumed:
            self.quick_slots[index] = None
            if persist:
                self.save()
        return consumed, message

    def save(self):
        self.sync_quick_slots()
        opened = [chest.id for chest in self.chests if chest.elapsed is not None]
        looted = [chest.id for chest in self.chests if chest.looted]
        self.field.app.storage.write('chests.json', {
            'scene': self.map_id, 'opened': opened, 'looted': looted, 'bag': self.bag,
            'quick_slots': self.quick_slots,
            'quick_slot_storage': 1,
            'contents': self.contents, 'starterChestPrepared': self.starter_chest_prepared,
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
        label = 'F'
        font = self.field.app.resources.small
        width, height = font.measure(label)
        x = max(5, min(NATIVE_WIDTH - width - 5, round(chest.x - camera - width / 2)))
        y = max(30, round(chest.y) - 46)
        top = y - height // 2
        drawing.rectangle((x - 5, top - 3, x + width + 4, top + height + 2),
                          (20, 19, 22), filled=True)
        drawing.text(font, x, y, label)
        return True
