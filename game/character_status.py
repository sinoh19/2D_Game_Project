"""Character and equipped gear overview for the field scene."""
import pico2d as p2d

from game import drawing
from game.config import SCALE, WINDOW_HEIGHT
from game.loot_ui import GOLD, draw_drag_icon, panel


PANEL = (70, 46, 569, 319)
CLOSE = (540, 53, 560, 73)
DISCARD = (466, 168, 554, 191)
WEAPON_SLOT = (404, 116, 554, 164)
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
        self.weapon_hovered = False
        self.idle_elapsed = 0.0
        self.cancel_pointer()

    def open(self):
        self.is_open = True
        self.weapon_hovered = False
        self.idle_elapsed = 0.0
        self.cancel_pointer()

    def cancel_pointer(self):
        self.press = self.drag = None
        self.discard_menu = False

    def drop_weapon(self):
        player = self.field.player
        self.field.drop_item(player.weapon.id)
        player.weapon = None
        self.field.chests.save()
        self.cancel_pointer()

    def move_pointer(self, x, y):
        self.weapon_hovered = drawing.contains(WEAPON_SLOT, x, y)
        if self.press is not None:
            start_x, start_y = self.press
            if self.drag is not None or (x - start_x)**2 + (y - start_y)**2 >= 9:
                self.drag = (x, y)

    def handle_event(self, event):
        keys = self.field.keys
        if event.type == p2d.SDL_KEYUP:
            keys.discard(event.key)
        elif (event.type == p2d.SDL_WINDOWEVENT
              and event.event == p2d.SDL_WINDOWEVENT_FOCUS_LOST):
            keys.clear()
            self.weapon_hovered = False
            self.cancel_pointer()
        elif event.type == p2d.SDL_MOUSEMOTION:
            self.move_pointer(event.x / SCALE, event.y / SCALE)
        elif (event.type == p2d.SDL_KEYDOWN and event.key not in keys
              and event.key in (p2d.SDLK_e, p2d.SDLK_ESCAPE)):
            keys.add(event.key)
            self.is_open = False
        elif event.type == p2d.SDL_MOUSEBUTTONDOWN:
            x, y = event.x / SCALE, event.y / SCALE
            weapon_slot = self.field.player.weapon is not None and drawing.contains(WEAPON_SLOT, x, y)
            if event.button == p2d.SDL_BUTTON_RIGHT:
                self.cancel_pointer()
                self.discard_menu = weapon_slot
            elif event.button == p2d.SDL_BUTTON_LEFT:
                if drawing.contains(CLOSE, x, y):
                    self.is_open = False
                elif self.discard_menu:
                    if drawing.contains(DISCARD, x, y):
                        self.drop_weapon()
                    self.discard_menu = False
                elif weapon_slot:
                    self.press = (x, y)
        elif event.type == p2d.SDL_MOUSEBUTTONUP and event.button == p2d.SDL_BUTTON_LEFT:
            x, y = event.x / SCALE, event.y / SCALE
            self.move_pointer(x, y)
            if self.drag is not None and not drawing.contains(PANEL, x, y):
                self.drop_weapon()
            self.press = self.drag = None

    def draw(self):
        player = self.field.player
        resources = self.field.app.resources
        text = drawing.text
        drawing.black_overlay(.45)
        panel(PANEL, (23, 24, 34), (140, 112, 74))
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
            ('무기', player.weapon.name if player.weapon and self.drag is None else None), ('방어구', player.armor), ('장신구', player.accessory),
        )):
            y = 116 + index * 54
            border = GOLD if index == 0 and self.weapon_hovered else BORDER
            panel((404, y, 554, y + 48), CARD, border)
            panel((412, y + 8, 444, y + 40), (23, 24, 32), (98, 83, 64))
            if index == 0 and item:
                icon = self.field.chests.icons[player.weapon.id]
                icon.draw(428.5 * SCALE, WINDOW_HEIGHT - (y + 24.5) * SCALE, 30 * SCALE, 30 * SCALE)
            else:
                drawing.rectangle((424, y + 24, 432, y + 24), MUTED)
            text(resources.normal, 453, y + 13, name)
            text(resources.small, 453, y + 31, item or '빈 슬롯', MUTED)

        if self.drag is not None:
            draw_drag_icon(self.field.chests.icons[player.weapon.id], *self.drag)
        elif self.discard_menu:
            panel(DISCARD, CARD, GOLD)
            text(resources.normal, 477, 180, '버리기')
        elif self.weapon_hovered and player.weapon is not None:
            weapon = player.weapon
            panel((235, 116, 395, 190), (20, 20, 29), GOLD)
            text(resources.normal, 246, 132, weapon.name, GOLD)
            text(resources.small, 246, 152, weapon.description, MUTED)
            text(resources.small, 246, 174, f'기본 공격력  {weapon.base_attack}')
