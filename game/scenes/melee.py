"""Directional attack and guard turns in the melee arena."""
import ctypes
from random import randrange
from types import SimpleNamespace

import pico2d as p2d

from game import drawing
from game.combat import HIT_DAMAGE
from game.config import ASSETS, NATIVE_HEIGHT, NATIVE_WIDTH, SCALE
from game.dungeon import MERCENARY_REACTION_DURATION
from game.field_inventory import BAG_SLOTS, CLOSE, PANEL
from game.items import ITEMS
from game.loot_ui import panel, slots
from game.pixel_style import simplify

DIRECTIONS = ('상단', '중단', '하단')
BUTTONS = ((270, 274, 407, 295), (270, 299, 407, 320), (270, 324, 407, 345))
SPEED_BUTTONS = ((1, (20, 5, 49, 19)), (2, (54, 5, 83, 19)))
KEYS = (p2d.SDLK_1, p2d.SDLK_2, p2d.SDLK_3)
FLOOR = 245
HOME_X = 215
STRIKE_X = 350
WALK_SECONDS = .55
UPPER_ATTACK = 0
MIDDLE_ATTACK = 1
LOWER_ATTACK = 2
SLASH_HIGHLIGHTS = {
    MIDDLE_ATTACK: ('melee-mid-slash.png', (35, 54)),
    LOWER_ATTACK: ('melee-low-slash.png', (42, 54)),
}
SLASH_PREP_FRAMES = 6
UPPER_HIGHLIGHT_FRAME = 8
SLASH_HIGHLIGHT_SECONDS = .20
SLASH_ZOOM_FACTOR = .18
SLASH_ZOOM_FOCUS = (388, 194)
IMPACT_HIT_STOP = .075
SLASH_RECOIL_SECONDS = .24
SLASH_RECOIL_PIXELS = 12
GOLD = (190, 145, 82)
ITEM_BUTTON = (471, 292, 603, 328)
LOG_ROWS = 3
USE_BUTTON = (359, 228, 429, 252)
SLIME_LAUNCH_TIME = .08
SLIME_IMPACT_TIME = .42
SLIME_LAND_TIME = .62
SLIME_RETURN_TIME = .70
SLIME_ATTACK_DURATION = 1.40
SLIME_IMPACT_HEIGHT = 24
SLIME_ARC_HEIGHT = 30
SLIME_HOME_X = 425
SLIME_STRIKE_X = 246
SLIME_ZOOM_FOCUS = ((HOME_X + SLIME_STRIKE_X) / 2, FLOOR - 51)
GUARD_PULSE_SECONDS = .12


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
        if cause == 'debug':
            self.record('디버그 전투 시작')
        else:
            self.record('선제공격 성공' if cause == 'player_attack' else '슬라임 접촉 피격')
        self.attack_elapsed = None
        self.attack_blocked = False
        self.hit_stop_left = 0.0
        self.idle_elapsed = 0.0
        self.enemy_direction = None
        self.enemy_elapsed = None
        self.bag_open = False
        self.item_selection = None
        self.item_message = ''
        self.selected = 1
        self.background = p2d.load_image(str(ASSETS / 'dungeon' / 'melee-chamber.png'))
        character_art = ASSETS / 'dungeon' / 'character'
        self.guard_shield = p2d.load_image(str(character_art / 'guard-shield.png'))
        self.slash_highlights = {
            direction: (simplify(p2d.load_image(str(character_art / filename)), block=1, preserve_white=True),
                        pivot)
            for direction, (filename, pivot) in SLASH_HIGHLIGHTS.items()
        }
        self.slime_pose = SimpleNamespace(x=SLIME_HOME_X, y=FLOOR, scale=2, facing=-1, frame=0)

    def record(self, message):
        self.message = message
        self.log.append(message)
        self.log_offset = 0

    def hovered(self, bounds):
        return self.pointer is not None and drawing.contains(bounds, *self.pointer)

    def can_choose(self):
        return (self.attack_elapsed is None and self.enemy_elapsed is None
                and self.player.hp > 0 and self.enemy.hp > 0)

    def can_act(self):
        return self.can_choose() and self.enemy_direction is None

    def start_attack(self, index):
        if self.bag_open or not self.can_act():
            return
        self.selected = index
        self.attack_frames = self.field.assets.animations['clips']['attack']['frames']
        self.slash_prep_duration = self.attack_frames[SLASH_PREP_FRAMES]['time']
        self.attack_duration = 2 * self.slash_prep_duration + SLASH_HIGHLIGHT_SECONDS
        self.impact_time = WALK_SECONDS + self.slash_prep_duration
        self.attack_elapsed = 0.0
        self.hit_stop_left = 0.0
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
                self.enemy_elapsed = SLIME_IMPACT_TIME
                self.hit_stop_left = IMPACT_HIT_STOP
                return
        if self.enemy_elapsed >= SLIME_ATTACK_DURATION:
            self.enemy_elapsed = self.enemy_direction = None
            self.pointer = None
            if self.player.hp == 0:
                self.record('용병이 쓰러졌다!')

    def update(self, dt):
        dt = max(0.0, dt) * self.app.battle_speed
        if self.hit_stop_left > 0:
            paused = min(dt, self.hit_stop_left)
            self.hit_stop_left -= paused
            dt -= paused
        self.idle_elapsed += dt
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
            # Render the contact frame even if a slow update crossed its start.
            self.attack_elapsed = self.impact_time
            if not self.attack_blocked:
                self.hit_stop_left = IMPACT_HIT_STOP
            return

        if self.attack_elapsed >= 2 * WALK_SECONDS + self.attack_duration:
            self.attack_elapsed = None
            if self.enemy.hp == 0:
                self.record('슬라임을 쓰러뜨렸다!')
            else:
                self.start_enemy_turn()

    def slash_impact_strength(self):
        if (self.attack_elapsed is None or self.attack_blocked
                or self.attack_elapsed < self.impact_time):
            return 0.0
        return max(0.0, 1 - (self.attack_elapsed - self.impact_time) / SLASH_RECOIL_SECONDS)

    def slash_attack_time(self, time):
        if time < self.slash_prep_duration - 1e-8:
            return time
        recovery = time - self.slash_prep_duration - SLASH_HIGHLIGHT_SECONDS
        if recovery < -1e-8:
            return None
        # Sample just below the next frame boundary so the first reverse pose is frame 6.
        return max(0.0, self.slash_prep_duration - recovery - 1e-6)

    def impact_zoom(self):
        if self.attack_elapsed is not None:
            elapsed = self.attack_elapsed - self.impact_time
        elif self.enemy_elapsed is not None and self.selected != self.enemy_direction:
            elapsed = self.enemy_elapsed - SLIME_IMPACT_TIME
        else:
            return 1.0
        if not 0 <= elapsed < SLASH_HIGHLIGHT_SECONDS:
            return 1.0
        release = min(1.0, (SLASH_HIGHLIGHT_SECONDS - elapsed) / .10)
        return 1 + SLASH_ZOOM_FACTOR * release**2

    def zoom_point(self, x, y, zoom):
        focus_x, focus_y = SLIME_ZOOM_FOCUS if self.enemy_elapsed is not None else SLASH_ZOOM_FOCUS
        return focus_x + (x - focus_x) * zoom, focus_y + (y - focus_y) * zoom

    def draw_slime(self, art, zoom=1.0):
        hit_elapsed = None
        if self.attack_elapsed is not None:
            elapsed_since_hit = self.attack_elapsed - self.impact_time
            if 0 <= elapsed_since_hit < art.HIT_DURATION:
                hit_elapsed = elapsed_since_hit
        if self.enemy.hp == 0 and hit_elapsed is None:
            return
        pose = self.slime_pose
        pose.x, pose.y, pose.frame, pose.facing, pose.scale = SLIME_HOME_X, FLOOR, 0, -1, 2
        pose.x += SLASH_RECOIL_PIXELS * self.slash_impact_strength() ** 2
        attack_elapsed = None
        if self.enemy_elapsed is not None:
            elapsed = self.enemy_elapsed
            if elapsed < SLIME_RETURN_TIME:
                attack_elapsed = min(1.0, elapsed / SLIME_LAND_TIME) * art.ATTACK_DURATION
                if elapsed < SLIME_IMPACT_TIME:
                    flight = max(0.0, (elapsed - SLIME_LAUNCH_TIME)
                                 / (SLIME_IMPACT_TIME - SLIME_LAUNCH_TIME))
                    pose.x += (SLIME_STRIKE_X - SLIME_HOME_X) * flight
                    height = SLIME_IMPACT_HEIGHT * flight + 4 * SLIME_ARC_HEIGHT * flight * (1 - flight)
                else:
                    pose.x = SLIME_STRIKE_X
                    fall = min(1.0, (elapsed - SLIME_IMPACT_TIME) / (SLIME_LAND_TIME - SLIME_IMPACT_TIME))
                    height = SLIME_IMPACT_HEIGHT * (1 - fall**2)
                pose.y -= height
            else:
                retreat = elapsed - SLIME_RETURN_TIME
                progress = retreat / (SLIME_ATTACK_DURATION - SLIME_RETURN_TIME)
                pose.x = SLIME_STRIKE_X + (SLIME_HOME_X - SLIME_STRIKE_X) * progress
                pose.facing = 1
                motion = art.motion
                pose.frame = int(retreat * motion['fps'] * 2) % motion['frameCount']
                # Keep each return frame's actual foot edge on the floor.
                pose.y += (motion['pivot'][1] - motion['frames'][pose.frame]['footY']) * pose.scale
        pose.x, pose.y = self.zoom_point(pose.x, pose.y, zoom)
        pose.scale *= zoom
        art.draw(pose, 0, SCALE, NATIVE_WIDTH, hit_elapsed=hit_elapsed,
                 attack_elapsed=attack_elapsed, guarded=self.attack_blocked)
        if self.attack_blocked and hit_elapsed is not None:
            x, y = self.zoom_point(SLIME_HOME_X + 34, FLOOR - 52, zoom)
            self.draw_guard_shield(x, y, hit_elapsed)

    def draw_guard_shield(self, x, y, elapsed):
        if elapsed >= MERCENARY_REACTION_DURATION:
            return
        pulse = max(0.0, 1 - elapsed / GUARD_PULSE_SECONDS)
        scale = 1 + .25 * pulse
        image = self.guard_shield
        p2d.SDL_SetTextureColorMod(image.texture, round(175 - 65 * pulse),
                                   round(216 - 31 * pulse), 255)
        try:
            image.draw(round(x * SCALE), round((NATIVE_HEIGHT - y) * SCALE),
                       round(image.w * SCALE * scale), round(image.h * SCALE * scale))
        finally:
            p2d.SDL_SetTextureColorMod(image.texture, 255, 255, 255)

    def player_in_hit_stop(self):
        return self.enemy_elapsed is not None and self.hit_stop_left > 0

    def draw_mercenary(self, zoom=1.0):
        if self.enemy_elapsed is not None and self.enemy_elapsed >= SLIME_IMPACT_TIME:
            since_contact = self.enemy_elapsed - SLIME_IMPACT_TIME
            guarded = self.selected == self.enemy_direction
            elapsed = since_contact if guarded else since_contact + IMPACT_HIT_STOP - self.hit_stop_left
            if elapsed < MERCENARY_REACTION_DURATION:
                x, y = self.zoom_point(HOME_X, FLOOR, zoom)
                self.field.assets.draw_mercenary_hit(x, y, 1, 0, elapsed,
                                                     actor_scale=2 * zoom, guarded=guarded)
                if guarded:
                    self.draw_guard_shield(HOME_X - 42, FLOOR - 79, elapsed)
                return
        elapsed = self.attack_elapsed
        if elapsed is None:
            clip, time, x, facing = 'idle', self.idle_elapsed, HOME_X, 1
        elif elapsed < WALK_SECONDS:
            clip, time, facing = 'walk', elapsed, 1
            x = HOME_X + (STRIKE_X - HOME_X) * elapsed / WALK_SECONDS
        elif elapsed < WALK_SECONDS + self.attack_duration:
            clip = 'attack'
            time, x, facing = self.slash_attack_time(elapsed - WALK_SECONDS), STRIKE_X, 1
        else:
            clip, time, facing = 'walk', elapsed - WALK_SECONDS - self.attack_duration, -1
            x = STRIKE_X - (STRIKE_X - HOME_X) * time / WALK_SECONDS
        x, y = self.zoom_point(x, FLOOR, zoom)
        if time is None:
            if self.selected != UPPER_ATTACK:
                image, (pivot_x, pivot_y) = self.slash_highlights[self.selected]
                scale = 2 * zoom * SCALE
                image.draw(round(x * SCALE + (image.w / 2 - pivot_x) * scale),
                           round((NATIVE_HEIGHT - y) * SCALE - (image.h / 2 - pivot_y) * scale),
                           round(image.w * scale), round(image.h * scale))
                return
            time = self.attack_frames[UPPER_HIGHLIGHT_FRAME]['time']
        self.field.assets.draw_character(
            clip, time, x, y, facing, 0, actor_scale=2 * zoom, melee_detail=True)

    def save(self):
        if self.cause != 'debug':
            self.field.save()

    def close_bag(self):
        self.bag_open = False
        self.item_selection = None
        self.pointer = None

    def click_bag(self, x, y):
        bag = self.field.inventory.bag
        if drawing.contains(CLOSE, x, y):
            self.close_bag()
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
            if self.cause != 'debug':
                self.field.chests.save()
            self.close_bag()
            self.record(message)
            self.start_enemy_turn()
        else:
            self.item_selection = next((i for i, bounds in enumerate(BAG_SLOTS)
                                        if bag[i] is not None and drawing.contains(bounds, x, y)), None)
            if not any(bag):
                self.item_message = '가방이 비어 있습니다.'
            elif not self.can_act():
                self.item_message = '내 턴에 아이템을 사용할 수 있습니다.'
            elif self.item_selection is not None:
                self.item_message = ITEMS[bag[self.item_selection]].name
            else:
                self.item_message = '사용할 아이템을 선택하세요.'

    def handle_event(self, event):
        if event.type == p2d.SDL_MOUSEMOTION:
            self.pointer = (event.x / SCALE, event.y / SCALE)
        elif (event.type == p2d.SDL_WINDOWEVENT
              and getattr(event, 'event', None) == p2d.SDL_WINDOWEVENT_FOCUS_LOST):
            self.pointer = None
        elif event.type == p2d.SDL_KEYDOWN:
            if event.key == p2d.SDLK_ESCAPE:
                if self.bag_open:
                    self.close_bag()
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
                return
            for speed, bounds in SPEED_BUTTONS:
                if drawing.contains(bounds, x, y):
                    self.app.battle_speed = speed
                    return
            if drawing.contains(ITEM_BUTTON, x, y) and self.can_choose():
                self.bag_open = True
                self.item_selection = None
                if not any(self.field.inventory.bag):
                    self.item_message = '가방이 비어 있습니다.'
                elif not self.can_act():
                    self.item_message = '내 턴에 아이템을 사용할 수 있습니다.'
                else:
                    self.item_message = '사용할 아이템을 선택하세요.'
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
        enabled = self.item_selection is not None and self.can_act()
        panel(USE_BUTTON, (66, 48, 37) if enabled else (32, 34, 43),
              GOLD if enabled else (62, 64, 73))
        centered(normal, 394, 240, '사용')
        drawing.text(small, 214, 240, self.item_message)

    def draw(self):
        width, height = NATIVE_WIDTH * SCALE, NATIVE_HEIGHT * SCALE
        zoom = self.impact_zoom()
        x, y = self.zoom_point(NATIVE_WIDTH / 2, NATIVE_HEIGHT / 2, zoom)
        self.background.draw(round(x * SCALE), round((NATIVE_HEIGHT - y) * SCALE),
                             round(width * zoom), round(height * zoom))
        assets = self.field.assets
        impact = ((zoom - 1) / SLASH_ZOOM_FACTOR if self.enemy_elapsed is not None
                  else self.slash_impact_strength())
        if impact:
            drawing.black_overlay(.38 * impact)
        if self.attack_elapsed is not None:
            self.draw_slime(assets.slime_art, zoom)
            self.draw_mercenary(zoom)
        else:
            self.draw_mercenary(zoom)
            self.draw_slime(assets.slime_art, zoom)
        if self.hit_stop_left > 0:
            # Stepped highlight at the point of contact, on the logical pixel grid.
            x, y = ((HOME_X + 9, FLOOR - 51) if self.player_in_hit_stop()
                    else (SLIME_HOME_X - 13, FLOOR - 26))
            for step in range(5):
                left, top = self.zoom_point(x + 3 * step, y + 3 * step, zoom)
                drawing.rectangle((left, top, left + 4 * zoom, top + 2 * zoom),
                                  (255, 221, 165), filled=True)

        small, normal = self.app.resources.small, self.app.resources.normal
        for speed, bounds in SPEED_BUTTONS:
            left, top, right, bottom = bounds
            selected = self.app.battle_speed == speed
            highlighted = selected or (not self.bag_open and self.hovered(bounds))
            panel(bounds, (67, 48, 35) if selected else (30, 33, 44),
                  GOLD if highlighted else (76, 75, 86))
            centered(small, (left + right) / 2, (top + bottom) / 2, f'x{speed}')
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
        can_choose = not self.bag_open and self.can_choose()
        action = '방어' if self.enemy_direction is not None else '공격'
        for index, (bounds, label) in enumerate(zip(BUTTONS, DIRECTIONS)):
            left, top, right, bottom = bounds
            active = can_choose and self.hovered(bounds)
            panel(bounds, (67, 48, 35) if active else (30, 33, 44), GOLD if active else line)
            drawing.text(small, left + 11, top + 10, str(index + 1),
                         GOLD if active else (172, 174, 184))
            centered(small, (left + right) / 2 + 5, (top + bottom) / 2, f'{label} {action}')

        item_hover = can_choose and self.hovered(ITEM_BUTTON)
        panel(ITEM_BUTTON, (67, 48, 35) if item_hover else (31, 34, 45),
              GOLD if item_hover else line)
        centered(normal, 537, 310, '아이템')
        if self.bag_open:
            self.draw_bag()
