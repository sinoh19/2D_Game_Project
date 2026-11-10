"""Melee arena and player attack sequence."""
import ctypes
from types import SimpleNamespace

import pico2d as p2d

from game import drawing
from game.combat import HIT_DAMAGE
from game.config import ASSETS, NATIVE_HEIGHT, NATIVE_WIDTH, SCALE
from game.field_inventory import BAG_SLOTS, CLOSE, PANEL
from game.items import ITEMS
from game.loot_ui import panel, slots

DIRECTIONS = ('상단', '중단', '하단')
BUTTONS = ((93, 306, 238, 343), (247, 306, 392, 343), (401, 306, 546, 343))
KEYS = (p2d.SDLK_1, p2d.SDLK_2, p2d.SDLK_3)
FLOOR = 245
HOME_X = 215
STRIKE_X = 350
WALK_SECONDS = .55
GOLD = (190, 145, 82)
ITEM_BUTTON = (554, 306, 628, 343)
USE_BUTTON = (359, 228, 429, 252)
ENEMY_TURN_SECONDS = .9


def centered(font, x, y, label):
    width = ctypes.c_int()
    height = ctypes.c_int()
    p2d.TTF_SizeUTF8(font.font, label.encode('utf-8'), ctypes.byref(width), ctypes.byref(height))
    drawing.text(font, x - width.value / 2, y, label)


class MeleeScene:
    def __init__(self, app, field, enemy, cause):
        self.app = app
        self.field = field
        self.player = field.player
        self.enemy = enemy
        self.cause = cause
        self.message = '선제공격 성공' if cause == 'player_attack' else '슬라임 접촉 피격'
        self.attack_elapsed = None
        self.enemy_turn_remaining = 0.0
        self.bag_open = False
        self.item_selection = None
        self.item_message = ''
        attack = field.assets.animations['clips']['attack']
        hit_frame = min(int(index) for index in field.assets.attack_hitboxes['frames'])
        self.attack_duration = attack['duration']
        self.impact_time = WALK_SECONDS + attack['frames'][hit_frame]['time']
        self.selected = 1
        self.background = p2d.load_image(str(ASSETS / 'dungeon' / 'melee-chamber.png'))
        self.slime_pose = SimpleNamespace(x=425, y=FLOOR, scale=2, facing=-1, frame=0)

    def can_act(self):
        return (self.attack_elapsed is None and self.enemy_turn_remaining == 0
                and self.player.hp > 0 and self.enemy.hp > 0)

    def start_attack(self, index):
        if self.bag_open or not self.can_act():
            return
        self.selected = index
        self.attack_elapsed = 0.0
        self.message = f'{DIRECTIONS[index]} 공격!'

    def update(self, dt):
        if self.enemy_turn_remaining > 0:
            self.enemy_turn_remaining = max(0.0, self.enemy_turn_remaining - max(0.0, dt))
            return
        if self.attack_elapsed is None:
            return
        previous = self.attack_elapsed
        self.attack_elapsed += max(0.0, dt)
        if previous < self.impact_time <= self.attack_elapsed:
            hp_before = self.enemy.hp
            self.enemy.take_damage(HIT_DAMAGE)
            self.message = f'{DIRECTIONS[self.selected]} 공격 성공!  슬라임 HP -{hp_before - self.enemy.hp}'

        if self.attack_elapsed >= 2 * WALK_SECONDS + self.attack_duration:
            self.attack_elapsed = None
            if self.enemy.hp == 0:
                self.message = '슬라임을 쓰러뜨렸다!'

    def draw_mercenary(self):
        elapsed = self.attack_elapsed
        if elapsed is None:
            clip, time, x, facing = 'idle', 0, HOME_X, 1
        elif elapsed < WALK_SECONDS:
            clip, time, facing = 'walk', elapsed, 1
            x = HOME_X + (STRIKE_X - HOME_X) * elapsed / WALK_SECONDS
        elif elapsed < WALK_SECONDS + self.attack_duration:
            clip, time, x, facing = 'attack', elapsed - WALK_SECONDS, STRIKE_X, 1
        else:
            clip, time, facing = 'walk', elapsed - WALK_SECONDS - self.attack_duration, -1
            x = STRIKE_X - (STRIKE_X - HOME_X) * time / WALK_SECONDS
        self.field.assets.draw_character(
            clip, time, x, FLOOR, facing, 0, actor_scale=2, melee_detail=True)

    def save(self):
        self.field.save()

    def click_bag(self, x, y):
        bag = self.field.inventory.bag
        if drawing.contains(CLOSE, x, y):
            self.bag_open = False
        elif drawing.contains(USE_BUTTON, x, y):
            index = self.item_selection
            if index is None or not self.can_act():
                return
            item_id = bag[index]
            if item_id is None:
                return
            consumed, message = ITEMS[item_id].use(self.player)
            if not consumed:
                self.item_message = message
                return
            bag[index] = None
            self.field.chests.save()
            self.bag_open = False
            self.item_selection = None
            self.message = message
            self.enemy_turn_remaining = ENEMY_TURN_SECONDS
        else:
            self.item_selection = next((i for i, bounds in enumerate(BAG_SLOTS)
                                        if bag[i] is not None and drawing.contains(bounds, x, y)), None)
            self.item_message = '사용할 아이템을 선택하세요.'
            if self.item_selection is not None:
                self.item_message = ITEMS[bag[self.item_selection]].name

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN:
            if event.key == p2d.SDLK_ESCAPE:
                if self.bag_open:
                    self.bag_open = False
                else:
                    self.save()
                    self.app.show_title()
            elif event.key in KEYS:
                self.start_attack(KEYS.index(event.key))
        elif event.type == p2d.SDL_MOUSEBUTTONDOWN and event.button == p2d.SDL_BUTTON_LEFT:
            x, y = event.x / SCALE, event.y / SCALE
            if self.bag_open:
                self.click_bag(x, y)
            elif drawing.contains(ITEM_BUTTON, x, y) and self.can_act():
                self.bag_open = True
                self.item_selection = None
                self.item_message = ('사용할 아이템을 선택하세요.' if any(self.field.inventory.bag)
                                     else '가방이 비어 있습니다.')
            else:
                for index, bounds in enumerate(BUTTONS):
                    if drawing.contains(bounds, x, y):
                        self.start_attack(index)
                        break

    def draw_bag(self):
        small, normal = self.app.resources.small, self.app.resources.normal
        bag = self.field.inventory.bag
        drawing.black_overlay(.45)
        panel(PANEL, (25, 25, 34), (92, 80, 68))
        drawing.text(normal, 214, 77, '전투 아이템', GOLD)
        panel(CLOSE, (41, 34, 38), (115, 89, 68))
        centered(normal, 426, 77, '×')
        slots(BAG_SLOTS, bag, self.field.chests.icons, small)
        if self.item_selection is not None:
            left, top, right, bottom = BAG_SLOTS[self.item_selection]
            drawing.rectangle((left - 2, top - 2, right + 2, bottom + 2), (245, 198, 110))
            drawing.rectangle((left, top, right, bottom), (245, 198, 110))
        enabled = self.item_selection is not None
        panel(USE_BUTTON, (66, 48, 37) if enabled else (32, 34, 43),
              GOLD if enabled else (62, 64, 73))
        centered(normal, 394, 240, '사용')
        drawing.text(small, 214, 240, self.item_message)

    def draw(self):
        width, height = NATIVE_WIDTH * SCALE, NATIVE_HEIGHT * SCALE
        self.background.draw(width // 2, height // 2, width, height)
        assets = self.field.assets
        self.draw_mercenary()
        hit_elapsed = None
        if self.attack_elapsed is not None:
            elapsed_since_hit = self.attack_elapsed - self.impact_time
            if 0 <= elapsed_since_hit < assets.slime_art.HIT_DURATION:
                hit_elapsed = elapsed_since_hit
        if self.enemy.hp > 0 or hit_elapsed is not None:
            assets.slime_art.draw(self.slime_pose, 0, SCALE, NATIVE_WIDTH, hit_elapsed=hit_elapsed)

        small, normal = self.app.resources.small, self.app.resources.normal
        drawing.text(small, 20, 29, f'용병 HP {self.player.hp} / {self.player.max_hp}')
        centered(small, 320, 29, self.message)
        drawing.text(small, 514, 29, f'슬라임 HP {self.enemy.hp} / {self.enemy.max_hp}')

        panel((231, 272, 408, 295), (24, 25, 31), (75, 76, 91))
        if self.attack_elapsed is not None:
            instruction = '공격 진행 중'
        elif self.enemy_turn_remaining > 0:
            instruction = '상대 턴'
        elif self.enemy.hp == 0:
            instruction = '전투 승리  /  ESC 메인'
        else:
            instruction = '내 턴  /  공격 방향 선택'
        centered(small, 320, 284, instruction)
        for index, (bounds, label) in enumerate(zip(BUTTONS, DIRECTIONS)):
            left, top, right, bottom = bounds
            active = index == self.selected
            border = GOLD if active else (82, 89, 105)
            panel(bounds, (66, 48, 37) if active else (32, 36, 47), border)
            drawing.rectangle((left + 3, top + 3, right - 3, top + 3), border, filled=True)
            panel((left + 10, top + 10, left + 28, top + 28), (28, 25, 28), border)
            centered(small, left + 19, top + 19, str(index + 1))
            centered(normal, (left + right) / 2 + 10, (top + bottom) / 2, label)
        panel(ITEM_BUTTON, (32, 36, 47), GOLD if self.can_act() else (62, 64, 73))
        centered(normal, 591, 324, '아이템')
        if self.bag_open:
            self.draw_bag()
