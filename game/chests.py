"""Field treasure chests and their opening animation."""
import pico2d as p2d

from game import drawing
from game.config import ASSETS, NATIVE_WIDTH, SCALE, WINDOW_HEIGHT
from game.items import BAG_SIZE, ITEMS, POTION
from game.loot_ui import CHEST_SLOT, CLOSE_BUTTON, bag_slot_at, draw_loot

FRAME_SIZE = 44
FRAME_COUNT = 4
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
                        FRAME_SIZE * SCALE, FRAME_SIZE * SCALE)



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
        self.chests = [TreasureChest(spec, spec[0] in opened, spec[0] in looted)
                       for spec in field.layout.get('chests', [])]
        self.active = None
        self.message = ''
        self.press_origin = None
        self.bag_source = None
        self.drag = None
        if self.chests:
            self.sheet = p2d.load_image(str(ASSETS / 'dungeon' / 'scenery' / 'chest-open-sheet.png'))
        folder = ASSETS / 'dungeon' / 'items'
        self.icons = {item_id: p2d.load_image(str(folder / item.icon)) for item_id, item in ITEMS.items()}

    def nearby(self):
        player = self.field.player
        if not player.grounded:
            return None
        candidates = [chest for chest in self.chests
                      if abs(player.x - chest.x) <= 42 and abs(player.y - chest.y) <= 16]
        return min(candidates, key=lambda chest: abs(player.x - chest.x), default=None)

    def interact(self):
        chest = self.nearby()
        if chest is None:
            return False
        if chest.elapsed is None:
            chest.elapsed = 0.0
        self.active = chest
        self.message = '상자가 비어 있습니다.' if chest.looted else '회복 포션  ×1'
        return True

    def cancel_drag(self):
        self.press_origin = self.drag = self.bag_source = None

    def close(self):
        self.cancel_drag()
        self.active = None

    def mouse_down(self, x, y):
        chest = self.active
        if chest is None or chest.elapsed < OPEN_TIME:
            return
        if drawing.contains(CLOSE_BUTTON, x, y):
            self.close()
        elif not chest.looted and drawing.contains(CHEST_SLOT, x, y):
            self.press_origin = (x, y)
            self.message = '회복 포션  ×1'
        else:
            index = bag_slot_at(x, y)
            if index is not None and self.bag[index] is not None:
                self.press_origin = (x, y)
                self.bag_source = index

    def mouse_move(self, x, y):
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
        self.bag[index] = POTION
        chest.looted = True
        self.save()
        self.message = '회복 포션을 가방에 옮겼습니다.'

    def draw_loot(self):
        if self.active is not None and self.active.elapsed >= OPEN_TIME:
            draw_loot(self.field.app.resources, self.icons,
                      not self.active.looted, self.bag, self.message, self.drag, self.bag_source)

    def update(self, dt):
        for chest in self.chests:
            if chest.elapsed is not None:
                chest.elapsed = min(OPEN_TIME, chest.elapsed + dt)

    def save(self):
        opened = [chest.id for chest in self.chests if chest.elapsed is not None]
        looted = [chest.id for chest in self.chests if chest.looted]
        self.field.app.storage.write('chests.json', {
            'scene': self.map_id, 'opened': opened, 'looted': looted, 'bag': self.bag,
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
