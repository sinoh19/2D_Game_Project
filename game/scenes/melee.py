"""Melee arena and player attack sequence."""
import ctypes
from types import SimpleNamespace

import pico2d as p2d

from game import drawing
from game.combat import HIT_DAMAGE
from game.config import ASSETS, NATIVE_HEIGHT, NATIVE_WIDTH, SCALE

DIRECTIONS = ('상단', '중단', '하단')
BUTTONS = ((93, 306, 238, 343), (247, 306, 392, 343), (401, 306, 546, 343))
KEYS = (p2d.SDLK_1, p2d.SDLK_2, p2d.SDLK_3)
FLOOR = 245
HOME_X = 215
STRIKE_X = 350
WALK_SECONDS = .55
GOLD = (190, 145, 82)


def panel(bounds, fill, border):
    drawing.rectangle(bounds, fill, filled=True)
    drawing.rectangle(bounds, border)


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
        attack = field.assets.animations['clips']['attack']
        hit_frame = min(int(index) for index in field.assets.attack_hitboxes['frames'])
        self.attack_duration = attack['duration']
        self.impact_time = WALK_SECONDS + attack['frames'][hit_frame]['time']
        self.selected = 1
        self.background = p2d.load_image(str(ASSETS / 'dungeon' / 'melee-chamber.png'))
        self.slime_pose = SimpleNamespace(x=425, y=FLOOR, scale=2, facing=-1, frame=0)

    def start_attack(self, index):
        if self.attack_elapsed is not None or self.enemy.hp == 0:
            return
        self.selected = index
        self.attack_elapsed = 0.0
        self.message = f'{DIRECTIONS[index]} 공격!'

    def update(self, dt):
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
        self.field.assets.draw_character(clip, time, x, FLOOR, facing, 0, actor_scale=2)

    def save(self):
        self.field.save()

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN:
            if event.key == p2d.SDLK_ESCAPE:
                self.save()
                self.app.show_title()
            elif event.key in KEYS:
                self.start_attack(KEYS.index(event.key))
        elif event.type == p2d.SDL_MOUSEBUTTONDOWN and event.button == p2d.SDL_BUTTON_LEFT:
            for index, bounds in enumerate(BUTTONS):
                if drawing.contains(bounds, event.x / SCALE, event.y / SCALE):
                    self.start_attack(index)
                    break

    def draw(self):
        width, height = NATIVE_WIDTH * SCALE, NATIVE_HEIGHT * SCALE
        self.background.draw(width // 2, height // 2, width, height)
        assets = self.field.assets
        self.draw_mercenary()
        if self.enemy.hp > 0:
            assets.slime_art.draw(self.slime_pose, 0, SCALE, NATIVE_WIDTH)

        small, normal = self.app.resources.small, self.app.resources.normal
        drawing.text(small, 20, 29, f'용병 HP {self.player.hp} / {self.player.max_hp}')
        centered(small, 320, 29, self.message)
        drawing.text(small, 514, 29, f'슬라임 HP {self.enemy.hp} / {self.enemy.max_hp}')

        panel((231, 272, 408, 295), (24, 25, 31), (75, 76, 91))
        if self.attack_elapsed is not None:
            instruction = '공격 진행 중'
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
