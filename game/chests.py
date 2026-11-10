"""Field treasure chests and their opening animation."""
import pico2d as p2d

from game import drawing
from game.config import ASSETS, SCALE, WINDOW_HEIGHT

FRAME_SIZE = 44
FRAME_COUNT = 4
OPEN_TIME = .4


class TreasureChest:
    def __init__(self, spec, opened):
        self.id, self.x, self.y = spec
        self.elapsed = OPEN_TIME if opened else None

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
        if not isinstance(opened, list):
            opened = []
        self.chests = [TreasureChest(spec, spec[0] in opened) for spec in field.layout.get('chests', [])]
        if self.chests:
            self.sheet = p2d.load_image(str(ASSETS / 'dungeon' / 'scenery' / 'chest-open-sheet.png'))

    def nearby(self):
        player = self.field.player
        if not player.grounded:
            return None
        candidates = [chest for chest in self.chests if chest.elapsed is None
                      and abs(player.x - chest.x) <= 42 and abs(player.y - chest.y) <= 16]
        return min(candidates, key=lambda chest: abs(player.x - chest.x), default=None)

    def interact(self):
        chest = self.nearby()
        if chest is None:
            return False
        chest.elapsed = 0.0
        return True

    def update(self, dt):
        for chest in self.chests:
            if chest.elapsed is not None:
                chest.elapsed = min(OPEN_TIME, chest.elapsed + dt)

    def save(self):
        if self.chests:
            opened = [chest.id for chest in self.chests if chest.elapsed is not None]
            self.field.app.storage.write('chests.json', {'scene': self.map_id, 'opened': opened})

    def draw(self, camera):
        for chest in self.chests:
            if camera - FRAME_SIZE <= chest.x <= camera + self.field.view_width + FRAME_SIZE:
                chest.draw(self.sheet, camera)

    def draw_hint(self, camera):
        chest = self.nearby()
        if chest is None:
            return False
        x = min(553, max(3, round(chest.x - camera) - 30))
        y = max(30, round(chest.y) - 46)
        drawing.rectangle((x, y - 9, x + 76, y + 9), (20, 19, 22), filled=True)
        drawing.text(self.field.app.resources.small, x + 6, y, 'E  상자 열기')
        return True
