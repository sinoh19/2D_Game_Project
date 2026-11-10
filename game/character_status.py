"""Character and equipped gear overview for the field scene."""
import pico2d as p2d

from game import drawing
from game.config import SCALE, WINDOW_HEIGHT
from game.loot_ui import GOLD, draw_drag_icon, panel


PANEL = (70, 46, 569, 319)
CLOSE = (540, 53, 560, 73)
GEAR = (
    ('weapon', '무기', (404, 116, 554, 164)),
    ('armor', '방어구', (404, 170, 554, 218)),
    ('accessory', '장신구', (404, 224, 554, 272)),
)
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
        self.hovered_slot = None
        self.idle_elapsed = 0.0
        self.cancel_pointer()

    def open(self):
        self.is_open = True
        self.hovered_slot = None
        self.idle_elapsed = 0.0
        self.cancel_pointer()

    def cancel_pointer(self):
        self.press = self.drag = None
        self.discard_menu = None

    def equipped_slot_at(self, x, y):
        return next((slot for slot, _, bounds in GEAR
                     if getattr(self.field.player, slot) is not None
                     and drawing.contains(bounds, x, y)), None)

    def drop_equipment(self, slot):
        player = self.field.player
        self.field.drop_item(getattr(player, slot).id)
        setattr(player, slot, None)
        self.field.chests.save()
        self.cancel_pointer()

    def move_pointer(self, x, y):
        self.hovered_slot = self.equipped_slot_at(x, y)
        if self.press is not None:
            _, start_x, start_y = self.press
            if self.drag is not None or (x - start_x)**2 + (y - start_y)**2 >= 9:
                self.drag = (x, y)

    def handle_event(self, event):
        keys = self.field.keys
        if event.type == p2d.SDL_KEYUP:
            keys.discard(event.key)
        elif (event.type == p2d.SDL_WINDOWEVENT
              and event.event == p2d.SDL_WINDOWEVENT_FOCUS_LOST):
            keys.clear()
            self.hovered_slot = None
            self.cancel_pointer()
        elif event.type == p2d.SDL_MOUSEMOTION:
            self.move_pointer(event.x / SCALE, event.y / SCALE)
        elif (event.type == p2d.SDL_KEYDOWN and event.key not in keys
              and event.key in (p2d.SDLK_e, p2d.SDLK_ESCAPE)):
            keys.add(event.key)
            self.is_open = False
        elif event.type == p2d.SDL_MOUSEBUTTONDOWN:
            x, y = event.x / SCALE, event.y / SCALE
            slot = self.equipped_slot_at(x, y)
            if event.button == p2d.SDL_BUTTON_RIGHT:
                self.cancel_pointer()
                if slot:
                    bottom = next(bounds[3] for attr, _, bounds in GEAR if attr == slot)
                    self.discard_menu = (slot, (466, bottom + 4, 554, bottom + 27))
            elif event.button == p2d.SDL_BUTTON_LEFT:
                if drawing.contains(CLOSE, x, y):
                    self.is_open = False
                elif self.discard_menu:
                    selected, bounds = self.discard_menu
                    if drawing.contains(bounds, x, y):
                        self.drop_equipment(selected)
                    self.discard_menu = None
                elif slot:
                    self.press = (slot, x, y)
        elif event.type == p2d.SDL_MOUSEBUTTONUP and event.button == p2d.SDL_BUTTON_LEFT:
            x, y = event.x / SCALE, event.y / SCALE
            self.move_pointer(x, y)
            if self.drag is not None and not drawing.contains(PANEL, x, y):
                self.drop_equipment(self.press[0])
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

        dragged_slot = self.press[0] if self.drag is not None else None
        icons = self.field.chests.icons
        for slot, name, bounds in GEAR:
            y = bounds[1]
            item = getattr(player, slot) if slot != dragged_slot else None
            border = GOLD if slot == self.hovered_slot else BORDER
            panel(bounds, CARD, border)
            panel((412, y + 8, 444, y + 40), (23, 24, 32), (98, 83, 64))
            if item:
                icons[item.id].draw(428.5 * SCALE, WINDOW_HEIGHT - (y + 24.5) * SCALE,
                                    30 * SCALE, 30 * SCALE)
            else:
                drawing.rectangle((424, y + 24, 432, y + 24), MUTED)
            text(resources.normal, 453, y + 13, name)
            text(resources.small, 453, y + 31, item.name if item else '빈 슬롯', MUTED)

        if dragged_slot:
            draw_drag_icon(icons[getattr(player, dragged_slot).id], *self.drag)
        elif self.discard_menu:
            _, bounds = self.discard_menu
            panel(bounds, CARD, GOLD)
            text(resources.normal, 477, bounds[1] + 12, '버리기')
        elif self.hovered_slot and (item := getattr(player, self.hovered_slot)):
            y = next(bounds[1] for slot, _, bounds in GEAR if slot == self.hovered_slot)
            panel((215, y, 395, y + 56 + 15 * len(item.stats)), (20, 20, 29), GOLD)
            text(resources.normal, 226, y + 16, item.name, GOLD)
            text(resources.small, 226, y + 36, item.description, MUTED)
            for index, (label, value) in enumerate(item.stats):
                text(resources.small, 226, y + 54 + 15 * index, f'{label}  {value}')
