"""Character and equipped gear overview for the field scene."""
import pico2d as p2d

from game import drawing
from game.config import SCALE
from game.loot_ui import GOLD, panel


CLOSE = (540, 53, 560, 73)
CARD = (32, 33, 44)
BORDER = (66, 65, 77)
MUTED = (175, 169, 164)
STATS = (
    ('힘', 'strength'),
    ('민첩', 'agility'),
    ('지능', 'intelligence'),
    ('행운', 'luck'),
)


class CharacterStatus:
    def __init__(self, field):
        self.field = field
        self.is_open = False
        self.idle_elapsed = 0.0

    def open(self):
        self.is_open = True
        self.idle_elapsed = 0.0

    def handle_event(self, event):
        keys = self.field.keys
        if event.type == p2d.SDL_KEYUP:
            keys.discard(event.key)
        elif (event.type == p2d.SDL_WINDOWEVENT
              and event.event == p2d.SDL_WINDOWEVENT_FOCUS_LOST):
            keys.clear()
        elif (event.type == p2d.SDL_KEYDOWN and event.key not in keys
              and event.key in (p2d.SDLK_e, p2d.SDLK_ESCAPE)):
            keys.add(event.key)
            self.is_open = False
        elif (event.type == p2d.SDL_MOUSEBUTTONDOWN and event.button == p2d.SDL_BUTTON_LEFT
              and drawing.contains(CLOSE, event.x / SCALE, event.y / SCALE)):
            self.is_open = False

    def draw(self):
        player = self.field.player
        resources = self.field.app.resources
        text = drawing.text
        drawing.black_overlay(.45)
        panel((70, 46, 569, 319), (23, 24, 34), (140, 112, 74))
        drawing.rectangle((71, 47, 568, 80), (37, 35, 43), filled=True)
        drawing.rectangle((71, 81, 568, 81), (95, 78, 60))
        text(resources.heading, 85, 65, '용병 정보')
        panel(CLOSE, CARD, BORDER)
        text(resources.normal, 545, 64, '×', GOLD)

        for x, label in ((85, '캐릭터'), (225, '능력치'), (404, '장비')):
            text(resources.normal, x, 101, label, GOLD)
        panel((85, 116, 212, 275), CARD, BORDER)
        drawing.rectangle((94, 240, 203, 240), BORDER)
        self.field.assets.draw_character(
            'idle', self.idle_elapsed, 149, 240, 1, 0, actor_scale=2, melee_detail=True)
        text(resources.small, 85, 290, 'HP')
        text(resources.small, 148, 290, f'{player.hp} / {player.max_hp}')
        panel((85, 302, 212, 308), (48, 34, 41), (84, 54, 50))
        health_width = round(126 * player.hp / player.max_hp)
        if health_width:
            drawing.rectangle((86, 303, 85 + health_width, 307), (155, 65, 65), filled=True)

        for index, (name, attr) in enumerate(STATS):
            y = 116 + index * 40
            panel((225, y, 391, y + 35), CARD, BORDER)
            text(resources.normal, 233, y + 18, name)
            text(resources.normal, 365, y + 18, str(getattr(player, attr)), GOLD)

        for index, (name, item) in enumerate((
            ('무기', player.weapon), ('방어구', player.armor), ('장신구', player.accessory),
        )):
            y = 116 + index * 54
            panel((404, y, 554, y + 48), CARD, BORDER)
            panel((412, y + 8, 444, y + 40), (23, 24, 32), (98, 83, 64))
            if index == 0 and item:
                self.draw_sword_icon(412, y + 8)
            else:
                drawing.rectangle((424, y + 24, 432, y + 24), MUTED)
            text(resources.normal, 453, y + 13, name)
            text(resources.small, 453, y + 31, item or '빈 슬롯', MUTED)

    @staticmethod
    def draw_sword_icon(left, top):
        def pixels(x, y, width, height, color):
            drawing.rectangle((left + x, top + y, left + x + width - 1,
                               top + y + height - 1), color, filled=True)

        for step in range(8):
            pixels(9 + 2 * step, 19 - 2 * step, 4, 4, (151, 160, 174))

        for step in range(6):
            pixels(5 + step, 27 - step, 4, 3, (108, 73, 44))
        pixels(4, 27, 5, 3, (108, 73, 44))

        for step in range(7):
            pixels(6 + step, 17 + step, 2, 2, (158, 115, 62))
        pixels(12, 23, 2, 2, (158, 115, 62))
