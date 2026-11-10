"""Directional attack and guard turns in the melee arena."""
import ctypes
from random import randrange
from types import SimpleNamespace

import pico2d as p2d

from game import drawing
from game.combat import HIT_DAMAGE
from game.config import ASSETS, NATIVE_HEIGHT, NATIVE_WIDTH, SCALE
from game.field_inventory import BAG_SLOTS, CLOSE, PANEL
from game.items import ITEMS
from game.loot_ui import panel, slots

DIRECTIONS = ('상단', '중단', '하단')
BUTTONS = ((270, 274, 407, 295), (270, 299, 407, 320), (270, 324, 407, 345))
KEYS = (p2d.SDLK_1, p2d.SDLK_2, p2d.SDLK_3)
FLOOR = 245
HOME_X = 215
STRIKE_X = 350
WALK_SECONDS = .55
GOLD = (190, 145, 82)
ITEM_BUTTON = (471, 292, 603, 328)
LOG_ROWS = 3
USE_BUTTON = (359, 228, 429, 252)
SLIME_IMPACT_TIME = .42
SLIME_ATTACK_DURATION = .9
SLIME_HOME_X = 425
SLIME_STRIKE_X = 246


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
        self.log = []
        self.log_offset = 0
        self.pointer = None
        self.record('선제공격 성공' if cause == 'player_attack' else '슬라임 접촉 피격')
        self.attack_elapsed = None
        self.attack_blocked = False
        self.enemy_direction = None
        self.enemy_elapsed = None
        self.bag_open = False
        self.item_selection = None
        self.item_message = ''
        attack = field.assets.animations['clips']['attack']
        hit_frame = min(int(index) for index in field.assets.attack_hitboxes['frames'])
        self.attack_duration = attack['duration']
        self.impact_time = WALK_SECONDS + attack['frames'][hit_frame]['time']
        self.selected = 1
        self.background = p2d.load_image(str(ASSETS / 'dungeon' / 'melee-chamber.png'))
        self.slime_pose = SimpleNamespace(x=SLIME_HOME_X, y=FLOOR, scale=2, facing=-1, frame=0)

    def record(self, message):
        self.message = message
        self.log.append(message)
        self.log_offset = 0

    def hovered(self, bounds):
        return self.pointer is not None and drawing.contains(bounds, *self.pointer)

    def can_act(self):
        return (self.attack_elapsed is None and self.enemy_direction is None
                and self.player.hp > 0 and self.enemy.hp > 0)

    def start_attack(self, index):
        if self.bag_open or not self.can_act():
            return
        self.selected = index
        self.attack_elapsed = 0.0
        self.pointer = None
        self.attack_blocked = index == randrange(len(DIRECTIONS))
        self.record(f'{DIRECTIONS[index]} 공격!')

    def start_enemy_turn(self):
        self.pointer = None
        self.enemy_direction = randrange(len(DIRECTIONS))

    def choose_direction(self, index):
        if self.bag_open or self.enemy.hp == 0 or self.player.hp == 0:
            return
        if self.enemy_direction is None:
            self.start_attack(index)
        elif self.enemy_elapsed is None:
            self.selected = index
            self.enemy_elapsed = 0.0
            self.pointer = None
            self.record(f'{DIRECTIONS[index]} 방어!')

    def update_enemy_attack(self, dt):
        previous = self.enemy_elapsed
        self.enemy_elapsed += dt
        if previous < SLIME_IMPACT_TIME <= self.enemy_elapsed:
            direction = DIRECTIONS[self.enemy_direction]
            if self.selected == self.enemy_direction:
                self.record(f'슬라임 {direction} 공격 방어 성공  ·  피해 0')
            else:
                hp_before = self.player.hp
                self.player.take_damage(HIT_DAMAGE)
                self.record(f'슬라임 {direction} 공격 명중  ·  용병 HP -{hp_before - self.player.hp}')
        if self.enemy_elapsed >= SLIME_ATTACK_DURATION:
            self.enemy_elapsed = self.enemy_direction = None
            self.pointer = None
            if self.player.hp == 0:
                self.record('용병이 쓰러졌다!')

    def update(self, dt):
        dt = max(0.0, dt)
        if self.enemy_elapsed is not None:
            self.update_enemy_attack(dt)
            return
        if self.attack_elapsed is None:
            return
        previous = self.attack_elapsed
        self.attack_elapsed += dt
        if previous < self.impact_time <= self.attack_elapsed:
            if self.attack_blocked:
                self.record(f'슬라임이 {DIRECTIONS[self.selected]} 공격을 막았다  ·  피해 0')
            else:
                hp_before = self.enemy.hp
                self.enemy.take_damage(HIT_DAMAGE)
                self.record(f'{DIRECTIONS[self.selected]} 공격 성공!  슬라임 HP -{hp_before - self.enemy.hp}')

        if self.attack_elapsed >= 2 * WALK_SECONDS + self.attack_duration:
            self.attack_elapsed = None
            if self.enemy.hp == 0:
                self.record('슬라임을 쓰러뜨렸다!')
            else:
                self.start_enemy_turn()

    def draw_slime(self, art):
        hit_elapsed = None
        if self.attack_elapsed is not None and not self.attack_blocked:
            elapsed_since_hit = self.attack_elapsed - self.impact_time
            if 0 <= elapsed_since_hit < art.HIT_DURATION:
                hit_elapsed = elapsed_since_hit
        if self.enemy.hp == 0 and hit_elapsed is None:
            return
        pose = self.slime_pose
        pose.x, pose.frame = SLIME_HOME_X, 0
        if self.enemy_elapsed is not None:
            progress = min(self.enemy_elapsed / SLIME_IMPACT_TIME,
                           (SLIME_ATTACK_DURATION - self.enemy_elapsed)
                           / (SLIME_ATTACK_DURATION - SLIME_IMPACT_TIME))
            pose.x += (SLIME_STRIKE_X - SLIME_HOME_X) * progress
            pose.facing = -1 if self.enemy_elapsed <= SLIME_IMPACT_TIME else 1
            pose.frame = int(self.enemy_elapsed * art.motion['fps'] * 2) % art.motion['frameCount']
        else:
            pose.facing = -1
        art.draw(pose, 0, SCALE, NATIVE_WIDTH, hit_elapsed=hit_elapsed)

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
            self.record(message)
            self.start_enemy_turn()
        else:
            self.item_selection = next((i for i, bounds in enumerate(BAG_SLOTS)
                                        if bag[i] is not None and drawing.contains(bounds, x, y)), None)
            self.item_message = '사용할 아이템을 선택하세요.'
            if self.item_selection is not None:
                self.item_message = ITEMS[bag[self.item_selection]].name

    def handle_event(self, event):
        if event.type == p2d.SDL_MOUSEMOTION:
            self.pointer = (event.x / SCALE, event.y / SCALE)
        elif (event.type == p2d.SDL_WINDOWEVENT
              and getattr(event, 'event', None) == p2d.SDL_WINDOWEVENT_FOCUS_LOST):
            self.pointer = None
        elif event.type == p2d.SDL_KEYDOWN:
            if event.key == p2d.SDLK_ESCAPE:
                if self.bag_open:
                    self.bag_open = False
                else:
                    self.save()
                    self.app.show_title()
            elif not self.bag_open and event.key == p2d.SDLK_PAGEUP:
                self.log_offset = min(max(0, len(self.log) - LOG_ROWS), self.log_offset + LOG_ROWS)
            elif not self.bag_open and event.key == p2d.SDLK_PAGEDOWN:
                self.log_offset = max(0, self.log_offset - LOG_ROWS)
            elif event.key in KEYS:
                self.choose_direction(KEYS.index(event.key))
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
                        self.choose_direction(index)
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
        self.draw_slime(assets.slime_art)

        small, normal = self.app.resources.small, self.app.resources.normal
        drawing.text(small, 20, 29, f'용병 HP {self.player.hp} / {self.player.max_hp}')
        centered(small, 320, 29, '근접 전투')
        drawing.text(small, 514, 29, f'슬라임 HP {self.enemy.hp} / {self.enemy.max_hp}')

        line = (76, 75, 86)
        panel((17, 264, 258, 348), (23, 24, 32), line)
        drawing.text(normal, 29, 277, '전투 로그', GOLD)
        if len(self.log) > LOG_ROWS:
            drawing.text(small, 180, 277, 'PgUp / PgDn', (163, 161, 173))
        drawing.rectangle((28, 288, 247, 288), line, filled=True)
        end = len(self.log) - self.log_offset
        for row, entry in enumerate(self.log[max(0, end - LOG_ROWS):end]):
            drawing.text(small, 29, 299 + row * 16, entry, (228, 216, 187))
        if self.attack_elapsed is not None:
            instruction = '공격 진행 중'
        elif self.enemy_elapsed is not None:
            instruction = '슬라임 공격 진행 중'
        elif self.player.hp == 0:
            instruction = '전투 패배  /  ESC 메인'
        elif self.enemy_direction is not None:
            instruction = '상대 턴  /  방어 방향 선택'
        elif self.enemy.hp == 0:
            instruction = '전투 승리  /  ESC 메인'
        else:
            instruction = '내 턴  /  공격 방향 선택'
        centered(small, 339, 263, instruction)
        can_choose = (not self.bag_open and self.attack_elapsed is None
                      and self.enemy_elapsed is None and self.player.hp > 0 and self.enemy.hp > 0)
        action = '방어' if self.enemy_direction is not None else '공격'
        for index, (bounds, label) in enumerate(zip(BUTTONS, DIRECTIONS)):
            left, top, right, bottom = bounds
            active = can_choose and self.hovered(bounds)
            panel(bounds, (67, 48, 35) if active else (30, 33, 44), GOLD if active else line)
            drawing.text(small, left + 11, top + 10, str(index + 1),
                         GOLD if active else (172, 174, 184))
            centered(small, (left + right) / 2 + 5, (top + bottom) / 2, f'{label} {action}')

        item_hover = not self.bag_open and self.can_act() and self.hovered(ITEM_BUTTON)
        panel(ITEM_BUTTON, (67, 48, 35) if item_hover else (31, 34, 45),
              GOLD if item_hover else line)
        centered(normal, 537, 310, '아이템')
        if self.bag_open:
            self.draw_bag()
