"""Directional attack and guard turns in the melee arena."""
import ctypes
from random import randrange
from types import SimpleNamespace

import pico2d as p2d

from game import drawing
from game.hp_ui import draw_hp_bar
from game.combat import apply_strength, roll_player_damage
from game.config import ASSETS, NATIVE_HEIGHT, NATIVE_WIDTH, SCALE
from game.dungeon import MERCENARY_REACTION_DURATION
from game.enemies import Lich, LichImpact, Slime, SlimeArt
from game.items import ITEMS
from game.loot_ui import panel
from game.pixel_style import simplify
from game.quick_slot_ui import draw_bag_quick_slots
from game.lighting import WorldDarkness

DIRECTIONS = ('상단', '중단', '하단')
COMBAT_POPUP_SECONDS = .85
DODGE_FADE_SECONDS = .24
BUTTONS = ((170, 255, 205, 290), (211, 255, 246, 290), (252, 255, 287, 290))
SPEED_BUTTONS = ((1, (20, 5, 49, 19)), (2, (54, 5, 83, 19)))
KEYS = (p2d.SDLK_1, p2d.SDLK_2, p2d.SDLK_3)
FLOOR = 245
HUD_TOP = 264
HOME_X = 215
PLAYER_SLOTS = (125, 170, HOME_X)
ENEMY_SLOTS = (425, 485, 545)
MOVE_SECONDS = .28
ENEMY_STEP_SECONDS = .42
JOIN_START_X = NATIVE_WIDTH + 48
JOIN_SPEED = 240
RETREAT_HEAL = 4
REINFORCEMENT_RANGE = 224
STRIKE_X = 350
DASH_APPROACH_SECONDS = .28
RETURN_SECONDS = .28
BACKHOP_FRAME_SIZE = 56
BACKHOP_FRAME_COUNT = 9
BACKHOP_FEET = (53, 53, 53, 53, 52, 53, 52, 53, 53)
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
ITEM_BUTTON = (295, 255, 330, 290)
SLIME_LAUNCH_TIME = .08
SLIME_IMPACT_TIME = .42
SLIME_LAND_TIME = .62
SLIME_RETURN_TIME = .70
SLIME_ATTACK_DURATION = 1.40
SLIME_IMPACT_HEIGHT = 24
SLIME_ARC_HEIGHT = 30
SLIME_HOME_X = 425
LICH_PROJECTILE_LAUNCH_TIME = .35
LICH_PROJECTILE_SIZE = 2.0


def centered(font, x, y, label, color=(240, 231, 207)):
    width = ctypes.c_int()
    height = ctypes.c_int()
    p2d.TTF_SizeUTF8(font.font, label.encode('utf-8'), ctypes.byref(width), ctypes.byref(height))
    drawing.text(font, x - width.value / 2, y, label, color)


def draw_battle_background(background, *, zoom=1.0, transform=None):
    """Draw clean wall sections over the chamber's baked candles and glow."""
    def point(x, y):
        return transform(x, y, zoom) if transform is not None else (x, y)

    x, y = point(NATIVE_WIDTH / 2, NATIVE_HEIGHT / 2)
    background.draw(round(x * SCALE), round((NATIVE_HEIGHT - y) * SCALE),
                    round(NATIVE_WIDTH * zoom * SCALE), round(NATIVE_HEIGHT * zoom * SCALE))
    for source_x, target_x in ((96, 48), (448, 592)):
        x, y = point(target_x, 187)
        background.clip_draw(source_x, background.h - 246, 96, 118,
                             round(x * SCALE), round((NATIVE_HEIGHT - y) * SCALE),
                             round(96 * zoom * SCALE), round(118 * zoom * SCALE))


class MeleeScene:
    def __init__(self, app, field, enemy, cause):
        self.app = app
        self.field = field
        self.player = field.player
        self.enemy = enemy
        self.inspected_enemy = enemy
        self.encounter_enemy = enemy
        self.active_enemy = None
        self.enemy_slots = [enemy, None, None]
        self.player_slot = 2
        self.move_elapsed = None
        self.move_from = HOME_X
        self.move_to = HOME_X
        self.pending_enemy_actions = []
        self.enemy_motions = {}
        self.enemy_motion_next = None
        self.support_bonus = 0
        self.prepared_rear = None
        self.recovering_slimes = set()
        self.defeated = []
        self.reserve = (sorted((monster for monster in (*field.enemies, *field.liches)
                                if monster is not enemy and monster.hp > 0
                                and abs(monster.x - enemy.x) <= REINFORCEMENT_RANGE
                                and abs(monster.y - enemy.y) <= 32),
                               key=lambda monster: abs(monster.x - enemy.x))
                        if cause != 'debug' else [])
        self.cause = cause
        self.is_lich = isinstance(enemy, Lich)
        self.enemy_name = enemy.melee_name
        self.enemy_home_x = enemy.melee_home_x
        self.enemy_impact_time = enemy.melee_impact_time
        self.enemy_attack_duration = enemy.melee_attack_duration
        self.log = []
        self.pointer = None
        if cause == 'debug':
            self.record('디버그 전투 시작')
        else:
            self.record('선제공격 성공' if cause == 'player_attack' else
                        '리치 투사체 적중  ·  근접 전투 시작' if cause == 'lich_projectile' else
                        '리치에게 접근  ·  근접 전투 시작' if self.is_lich else '슬라임 접촉 피격')
        self.attack_elapsed = None
        self.death_elapsed = 0.0 if enemy.hp == 0 else None
        self.attack_blocked = False
        self.player_attack_landed = False
        self.player_attack_evaded = False
        self.hit_stop_left = 0.0
        self.idle_elapsed = 0.0
        self.combat_popup = None
        self.enemy_direction = None
        self.enemy_forecast = None
        self.enemy_elapsed = None
        self.enemy_attack_evaded = False
        self.debug_dodge_pending = cause == 'debug'
        self.debug_critical_pending = cause == 'debug'
        self.item_page = False
        self.item_message = ''
        self.selected = 1
        self.preview_index = 1
        self.background = p2d.load_image(str(ASSETS / 'dungeon' / 'melee-chamber.png'))
        self.darkness = WorldDarkness(None)
        self.hud = p2d.load_image(str(ASSETS / 'ui' / 'pixellab-melee-hud.png'))
        self.switch_icon = p2d.load_image(str(ASSETS / 'ui' / 'battle-switch.png'))
        character_art = ASSETS / 'dungeon' / 'character'
        self.backhop = p2d.load_image(str(character_art / 'melee-backhop.png'))
        self.slash_highlights = {
            direction: (simplify(p2d.load_image(str(character_art / filename)), block=1, preserve_white=True),
                        pivot)
            for direction, (filename, pivot) in SLASH_HIGHLIGHTS.items()
        }
        self.slime_pose = SimpleNamespace(x=SLIME_HOME_X, y=FLOOR, scale=2, facing=-1, frame=0)

    @property
    def player_x(self):
        if self.move_elapsed is None:
            return PLAYER_SLOTS[self.player_slot]
        progress = min(1.0, self.move_elapsed / MOVE_SECONDS)
        return self.move_from + (self.move_to - self.move_from) * progress

    def set_front(self):
        if self.enemy_slots[0] is None:
            for slot in (1, 2):
                if self.enemy_slots[slot] is not None:
                    self.enemy_slots[0], self.enemy_slots[slot] = self.enemy_slots[slot], None
                    self.start_enemy_motion(self.enemy_slots[0], ENEMY_SLOTS[slot], ENEMY_SLOTS[0])
                    break
        front = self.enemy_slots[0]
        if front is not None:
            self.recovering_slimes.discard(front)
            self.enemy = front
            self.is_lich = isinstance(front, Lich)
            self.enemy_name = front.melee_name
            self.enemy_home_x = front.melee_home_x
            self.enemy_impact_time = front.melee_impact_time
            self.enemy_attack_duration = front.melee_attack_duration

    def start_enemy_motion(self, actor, start_x, target_x, duration=ENEMY_STEP_SECONDS):
        if start_x == target_x:
            return
        self.enemy_motions[actor] = SimpleNamespace(start=start_x, target=target_x,
                                                     elapsed=0.0, duration=duration)

    def enemy_x(self, actor):
        motion = self.enemy_motions.get(actor)
        if motion is None:
            return ENEMY_SLOTS[self.enemy_slots.index(actor)]
        progress = min(1.0, motion.elapsed / motion.duration)
        return motion.start + (motion.target - motion.start) * progress

    def update_enemy_motions(self, dt):
        for actor, motion in tuple(self.enemy_motions.items()):
            motion.elapsed += dt
            if motion.elapsed >= motion.duration:
                del self.enemy_motions[actor]
        if self.enemy_motions:
            return
        continuation = self.enemy_motion_next
        self.enemy_motion_next = None
        if continuation == 'start_turn':
            self.start_enemy_turn()
        elif continuation == 'next_action':
            self.next_enemy_action()

    def move_player(self, step):
        if not self.can_act():
            return
        target = max(0, min(2, self.player_slot + step))
        if target == self.player_slot:
            return
        self.move_from = PLAYER_SLOTS[self.player_slot]
        self.move_to = PLAYER_SLOTS[target]
        self.player_slot = target
        self.move_elapsed = 0.0
        self.record(f'용병 {target + 1}번 칸으로 이동')

    def retire_front(self):
        fallen = self.enemy_slots[0]
        if fallen is None or fallen.hp > 0:
            return
        self.defeated.append(fallen)
        self.recovering_slimes.discard(fallen)
        self.enemy_slots[0] = None
        self.death_elapsed = None
        self.set_front()
        if self.inspected_enemy is fallen:
            self.inspected_enemy = self.enemy_slots[0]
        if self.enemy_slots[0] is not None or self.reserve:
            if self.enemy_motions:
                self.enemy_motion_next = 'start_turn'
            else:
                self.start_enemy_turn()
            return
        if self.cause == 'debug':
            self.app.show_title()
            destination = self.app.scene
        else:
            self.field.resume_after_victory(self.encounter_enemy, self.defeated)
            destination = self.field
        self.fade_to(destination)

    def record(self, message):
        self.message = message
        self.log.append(message)

    def hovered(self, bounds):
        return self.pointer is not None and drawing.contains(bounds, *self.pointer)

    def enemy_at(self, x, y):
        zoom = self.impact_zoom()
        for actor in self.enemy_slots:
            if actor is None:
                continue
            half = 48 if isinstance(actor, Lich) else 31
            top = FLOOR - (136 if isinstance(actor, Lich) else 70)
            center_x, top = self.zoom_point(self.enemy_x(actor), top, zoom)
            _, bottom = self.zoom_point(self.enemy_x(actor), FLOOR, zoom)
            if abs(x - center_x) <= half * zoom and top <= y <= bottom:
                return actor
        return None

    def enemy_status(self, actor):
        statuses = []
        if actor in self.recovering_slimes and actor in self.enemy_slots[1:]:
            statuses.append('후열 회복 +4 HP/턴')
        if actor is self.prepared_rear:
            statuses.append('교대 준비')
        if actor is self.enemy and self.support_bonus:
            statuses.append(f'공격 지원 +{self.support_bonus}')
        return ' · '.join(statuses) if statuses else '상태 없음'

    @staticmethod
    def fit_text(font, label, width):
        if font.measure(label)[0] <= width:
            return label
        while label and font.measure(label + '…')[0] > width:
            label = label[:-1]
        return label + '…'

    def hud_text(self, x, y, label, width, color, *, center=False, compact=False, height=None):
        resources = self.app.resources
        font = resources.compact if compact else resources.small
        if font.measure(label)[0] > width:
            font = resources.compact
        text_width, text_height = font.measure(label)
        factor = min(1.0, width / text_width) if text_width else 1.0
        if height is not None and text_height:
            factor = min(factor, height / text_height)
        measured = text_width * factor
        if center:
            x -= measured / 2
        font.draw(round(x * SCALE), round((NATIVE_HEIGHT - y) * SCALE), label, color,
                  max_width=width, max_height=height)

    def can_choose(self):
        return (self.attack_elapsed is None and self.enemy_elapsed is None
                and self.move_elapsed is None and self.death_elapsed is None
                and not self.enemy_motions
                and self.player.hp > 0 and self.enemy.hp > 0)

    def can_act(self):
        return self.can_choose() and self.enemy_direction is None

    def start_attack(self, index):
        if not self.can_act():
            return
        self.selected = index
        self.preview_index = index
        self.attack_frames = self.field.assets.animations['clips']['attack']['frames']
        self.slash_prep_duration = self.attack_frames[SLASH_PREP_FRAMES]['time']
        self.attack_duration = 2 * self.slash_prep_duration + SLASH_HIGHLIGHT_SECONDS
        self.impact_time = DASH_APPROACH_SECONDS + self.slash_prep_duration
        self.attack_elapsed = 0.0
        self.hit_stop_left = 0.0
        self.pointer = None
        self.attack_blocked = not self.debug_critical_pending and index == randrange(len(DIRECTIONS))
        self.player_attack_landed = False
        self.player_attack_evaded = False
        self.record(f'{DIRECTIONS[index]} 공격!')

    def start_enemy_turn(self):
        self.item_page = False
        self.pointer = None
        if self.enemy_slots[0] is None:
            self.set_front()
        for slime in tuple(self.recovering_slimes):
            if slime not in self.enemy_slots[1:] or slime.hp == 0:
                self.recovering_slimes.discard(slime)
                continue
            healed = min(RETREAT_HEAL, slime.max_hp - slime.hp)
            if healed > 0:
                slime.hp += healed
                self.record(f'뒤로 물러난 슬라임 HP +{healed}  ({slime.hp}/{slime.max_hp})')
        if (self.prepared_rear is not None and self.prepared_rear is self.enemy_slots[2]
                and self.enemy_slots[0] is not None
                and self.enemy_slots[0].hp <= self.enemy_slots[0].max_hp // 2
                and self.enemy_slots[2].hp > self.enemy_slots[0].hp):
            self.enemy_slots[0], self.enemy_slots[2] = self.enemy_slots[2], self.enemy_slots[0]
            if isinstance(self.enemy_slots[2], Slime):
                self.recovering_slimes.add(self.enemy_slots[2])
            self.start_enemy_motion(self.enemy_slots[0], ENEMY_SLOTS[2], ENEMY_SLOTS[0])
            self.start_enemy_motion(self.enemy_slots[2], ENEMY_SLOTS[0], ENEMY_SLOTS[2])
            self.set_front()
            self.record('뒷줄 슬라임이 앞줄과 교대했다!')
        self.prepared_rear = None
        # The lineup snapshot precedes joining: a newcomer first acts next turn.
        self.pending_enemy_actions = [actor for actor in self.enemy_slots if actor is not None and actor.hp > 0]
        if self.reserve:
            for slot in range(3):
                if self.enemy_slots[slot] is None:
                    joined = self.reserve.pop(0)
                    self.enemy_slots[slot] = joined
                    duration = max(ENEMY_STEP_SECONDS, (JOIN_START_X - ENEMY_SLOTS[slot]) / JOIN_SPEED)
                    self.start_enemy_motion(joined, JOIN_START_X, ENEMY_SLOTS[slot], duration)
                    self.set_front()
                    self.record(f'{joined.melee_name}이(가) {slot + 1}번 칸에 합류했다!')
                    break
        if self.enemy_motions:
            self.enemy_motion_next = 'next_action'
        else:
            self.next_enemy_action()

    def next_enemy_action(self):
        while self.pending_enemy_actions:
            actor = self.pending_enemy_actions.pop(0)
            if actor.hp == 0 or actor not in self.enemy_slots:
                continue
            slot = self.enemy_slots.index(actor)
            if slot == 1 and isinstance(actor, Slime):
                front = self.enemy_slots[0]
                if front is not None and front.hp <= front.max_hp // 2 and actor.hp > front.hp:
                    self.enemy_slots[0], self.enemy_slots[1] = actor, front
                    if isinstance(front, Slime):
                        self.recovering_slimes.add(front)
                    self.start_enemy_motion(actor, ENEMY_SLOTS[1], ENEMY_SLOTS[0])
                    self.start_enemy_motion(front, ENEMY_SLOTS[0], ENEMY_SLOTS[1])
                    self.set_front()
                    self.record('중간 슬라임이 앞줄과 교대했다!')
                    self.enemy_direction = None
                    self.enemy_forecast = None
                    self.enemy_motion_next = 'next_action'
                    return
                else:
                    self.support_bonus = min(2, self.support_bonus + 1)
                    self.record('중간 슬라임이 앞줄을 밀어준다! 다음 공격 +1')
                continue
            if slot == 2 and isinstance(actor, Slime):
                self.prepared_rear = actor
                self.record('뒷줄 슬라임이 교대를 준비한다!')
                continue
            self.prepare_enemy_attack(actor)
            return
        self.active_enemy = None
        self.enemy_direction = None
        self.enemy_forecast = None
        self.pointer = None

    def prepare_enemy_attack(self, actor):
        self.active_enemy = actor
        self.enemy_impact_time = actor.melee_impact_time
        self.enemy_attack_duration = actor.melee_attack_duration
        self.enemy_direction = randrange(len(DIRECTIONS))
        intelligence = max(0, min(20, self.player.stat_value('intelligence')))
        # 50/150 at intelligence 0, increasing to 90/150 at intelligence 20.
        correct_weight = 50 + 2 * intelligence
        predicted = self.enemy_direction
        if randrange(150) >= correct_weight:
            predicted = (predicted + randrange(1, len(DIRECTIONS))) % len(DIRECTIONS)
        chance = correct_weight / 150
        self.enemy_forecast = tuple(chance if i == predicted else (1 - chance) / 2
                                    for i in range(len(DIRECTIONS)))

    def choose_direction(self, index):
        if self.enemy_motions or self.enemy.hp == 0 or self.player.hp == 0:
            return
        if self.enemy_direction is None:
            if self.item_page:
                self.use_item(index)
            else:
                self.start_attack(index)
        elif self.enemy_elapsed is None:
            self.selected = index
            self.preview_index = index
            self.enemy_elapsed = 0.0
            self.enemy_attack_evaded = False
            self.pointer = None
            self.record(f'{DIRECTIONS[index]} 방어!')

    def update_enemy_attack(self, dt):
        previous = self.enemy_elapsed
        self.enemy_elapsed += dt
        if previous < self.enemy_impact_time <= self.enemy_elapsed:
            actor = self.active_enemy
            direction = DIRECTIONS[self.enemy_direction]
            force_dodge = self.debug_dodge_pending
            self.debug_dodge_pending = False
            guarded = self.selected == self.enemy_direction
            dodge_weight = min(250, 5 * self.player.stat_value('agility') + self.player.stat_value('luck'))
            if force_dodge or (not guarded and dodge_weight > 0
                               and randrange(1000) < dodge_weight):
                self.enemy_attack_evaded = True
                self.combat_popup = ('MISS', self.player_x, FLOOR - 109, 0.0)
                self.record(f'{actor.melee_name} {direction} 공격 회피  ·  피해 0')
            elif guarded:
                self.record(f'{actor.melee_name} {direction} 공격 방어 성공  ·  피해 0')
            else:
                hp_before = self.player.hp
                damage, critical = actor.roll_damage()
                if actor is self.enemy:
                    damage += self.support_bonus
                self.player.take_damage(damage, damage_type=actor.melee_damage_type)
                damage = hp_before - self.player.hp
                label = f'-{damage}!' if critical else f'-{damage}'
                self.combat_popup = (label, self.player_x, FLOOR - 109, 0.0)
                result = '치명타!' if critical else '명중'
                self.record(f'{actor.melee_name} {direction} 공격 {result}  ·  용병 HP -{damage}')
                self.enemy_elapsed = self.enemy_impact_time
                self.hit_stop_left = IMPACT_HIT_STOP
                if actor is self.enemy:
                    self.support_bonus = 0
                return
            if actor is self.enemy:
                self.support_bonus = 0
        if self.enemy_elapsed >= self.enemy_attack_duration:
            self.enemy_elapsed = None
            if self.player.hp == 0:
                self.enemy_direction = None
                self.pending_enemy_actions.clear()
                self.record('용병이 쓰러졌다!')
            else:
                self.next_enemy_action()

    def update(self, dt):
        dt = max(0.0, dt) * self.app.battle_speed
        if self.combat_popup is not None:
            label, x, y, elapsed = self.combat_popup
            elapsed += dt
            self.combat_popup = ((label, x, y, elapsed) if elapsed < COMBAT_POPUP_SECONDS else None)
        if self.hit_stop_left > 0:
            paused = min(dt, self.hit_stop_left)
            self.hit_stop_left -= paused
            dt -= paused
        self.idle_elapsed += dt
        if self.death_elapsed is not None:
            self.death_elapsed += dt
        if self.move_elapsed is not None:
            self.move_elapsed += dt
            if self.move_elapsed >= MOVE_SECONDS:
                self.move_elapsed = None
                self.start_enemy_turn()
            return
        if self.enemy_motions:
            self.update_enemy_motions(dt)
            return
        if self.enemy_elapsed is not None:
            self.update_enemy_attack(dt)
            return
        if self.attack_elapsed is None:
            if self.death_elapsed is not None and self.death_elapsed >= (self.field.assets.lich_art.DEATH_DURATION if self.is_lich else SlimeArt.DEATH_DURATION):
                self.retire_front()
            return
        previous = self.attack_elapsed
        self.attack_elapsed += dt
        if previous < self.impact_time <= self.attack_elapsed:
            force_critical = self.debug_critical_pending
            self.debug_critical_pending = False
            if self.attack_blocked:
                self.record(f'{self.enemy_name}이(가) {DIRECTIONS[self.selected]} 공격을 막았다  ·  피해 0')
            elif (not force_critical
                  and not self.is_lich
                  and randrange(1000) < min(250, 5 * self.enemy.agility + self.enemy.luck)):
                self.player_attack_evaded = True
                self.combat_popup = ('MISS', self.enemy_home_x, FLOOR - 58, 0.0)
                self.record(f'{self.enemy_name}이(가) {DIRECTIONS[self.selected]} 공격을 피했다  ·  피해 0')
            else:
                hp_before = self.enemy.hp
                damage, critical = roll_player_damage(
                    self.player.stat_value('strength'), self.player.stat_value('luck'),
                    base_attack=self.player.base_attack, force_critical=force_critical)
                self.enemy.take_damage(damage)
                if self.enemy.hp == 0 and not self.is_lich:
                    self.death_elapsed = -SlimeArt.HIT_DURATION
                elif self.enemy.hp == 0:
                    self.death_elapsed = 0.0
                damage = hp_before - self.enemy.hp
                self.player_attack_landed = damage > 0
                label = f'-{damage}!' if critical else f'-{damage}'
                self.combat_popup = (label, self.enemy_home_x, FLOOR - 58, 0.0)
                result = '치명타!' if critical else '공격 성공!'
                self.record(f'{DIRECTIONS[self.selected]} {result}  {self.enemy_name} HP -{damage}')
            # Render the contact frame even if a slow update crossed its start.
            self.attack_elapsed = self.impact_time
            if not self.attack_blocked and not self.player_attack_evaded:
                self.hit_stop_left = IMPACT_HIT_STOP
            return

        if self.attack_elapsed >= DASH_APPROACH_SECONDS + self.attack_duration + RETURN_SECONDS:
            self.attack_elapsed = None
            if self.enemy.hp == 0:
                self.record(f'{self.enemy_name}를 쓰러뜨렸다!')
            else:
                self.start_enemy_turn()

    def slash_impact_strength(self):
        if (self.attack_elapsed is None or self.attack_blocked or self.player_attack_evaded
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
            if self.player_attack_evaded:
                return 1.0
            elapsed = self.attack_elapsed - self.impact_time
        elif (self.enemy_elapsed is not None and self.selected != self.enemy_direction
              and not self.enemy_attack_evaded):
            elapsed = self.enemy_elapsed - self.enemy_impact_time
        else:
            return 1.0
        if not 0 <= elapsed < SLASH_HIGHLIGHT_SECONDS:
            return 1.0
        release = min(1.0, (SLASH_HIGHLIGHT_SECONDS - elapsed) / .10)
        return 1 + SLASH_ZOOM_FACTOR * release**2

    def zoom_point(self, x, y, zoom):
        if self.enemy_elapsed is None:
            focus_x, focus_y = SLASH_ZOOM_FOCUS
        elif isinstance(self.active_enemy, Lich):
            focus_x, focus_y = (self.player_x + self.actor_x(self.active_enemy)) / 2, FLOOR - 51
        else:
            focus_x, focus_y = self.player_x + 15.5, FLOOR - 51
        return focus_x + (x - focus_x) * zoom, focus_y + (y - focus_y) * zoom

    def actor_x(self, actor):
        return self.enemy_x(actor)

    def draw_slime(self, art, zoom=1.0, actor=None, slot=0):
        actor = self.enemy if actor is None else actor
        front = actor is self.enemy
        casting = actor is self.active_enemy and self.enemy_elapsed is not None
        hit_elapsed = None
        death_elapsed = self.death_elapsed if front else None
        alpha = 255
        if front and self.attack_elapsed is not None:
            elapsed_since_hit = self.attack_elapsed - self.impact_time
            if self.player_attack_evaded:
                progress = min(1.0, elapsed_since_hit / DODGE_FADE_SECONDS)
                alpha = round(105 + 150 * progress)
            elif 0 <= elapsed_since_hit < art.HIT_DURATION:
                hit_elapsed = elapsed_since_hit
        if death_elapsed is not None:
            if death_elapsed < 0:
                death_elapsed = None
            elif death_elapsed >= art.DEATH_DURATION:
                return
            else:
                hit_elapsed = None
        pose = self.slime_pose
        home_x = self.enemy_x(actor)
        strike_x = self.player_x + 31
        pose.x, pose.y, pose.frame, pose.facing, pose.scale = home_x, FLOOR, 0, -1, 2
        motion = self.enemy_motions.get(actor)
        if motion is not None:
            pose.frame = int(motion.elapsed * art.motion['fps']) % art.motion['frameCount']
            pose.facing = -1 if motion.target < motion.start else 1
        if front:
            pose.x += SLASH_RECOIL_PIXELS * self.slash_impact_strength() ** 2
        attack_elapsed = None
        if casting:
            elapsed = self.enemy_elapsed
            if elapsed < SLIME_RETURN_TIME:
                attack_elapsed = min(1.0, elapsed / SLIME_LAND_TIME) * art.ATTACK_DURATION
                if elapsed < SLIME_IMPACT_TIME:
                    flight = max(0.0, (elapsed - SLIME_LAUNCH_TIME)
                                 / (SLIME_IMPACT_TIME - SLIME_LAUNCH_TIME))
                    pose.x += (strike_x - home_x) * flight
                    height = SLIME_IMPACT_HEIGHT * flight + 4 * SLIME_ARC_HEIGHT * flight * (1 - flight)
                else:
                    pose.x = strike_x
                    fall = min(1.0, (elapsed - SLIME_IMPACT_TIME) / (SLIME_LAND_TIME - SLIME_IMPACT_TIME))
                    height = SLIME_IMPACT_HEIGHT * (1 - fall**2)
                pose.y -= height
            else:
                retreat = elapsed - SLIME_RETURN_TIME
                progress = retreat / (SLIME_ATTACK_DURATION - SLIME_RETURN_TIME)
                pose.x = strike_x + (home_x - strike_x) * progress
                pose.facing = 1
                motion = art.motion
                pose.frame = int(retreat * motion['fps'] * 2) % motion['frameCount']
                # Keep each return frame's actual foot edge on the floor.
                pose.y += (motion['pivot'][1] - motion['frames'][pose.frame]['footY']) * pose.scale
        pose.x, pose.y = self.zoom_point(pose.x, pose.y, zoom)
        pose.scale *= zoom
        art.draw(pose, 0, SCALE, NATIVE_WIDTH, hit_elapsed=hit_elapsed,
                 attack_elapsed=attack_elapsed, death_elapsed=death_elapsed,
                 guarded=front and self.attack_blocked, alpha=alpha)

    def draw_lich(self, art, zoom=1.0, actor=None, slot=0):
        actor = self.enemy if actor is None else actor
        front = actor is self.enemy
        death_elapsed = self.death_elapsed if front else None
        if death_elapsed is not None and death_elapsed >= art.DEATH_DURATION:
            return
        hit_elapsed = (self.attack_elapsed - self.impact_time
                       if front and self.attack_elapsed is not None else -1)
        recoil = (12 * max(0.0, 1 - hit_elapsed / .24) ** 2
                  if hit_elapsed >= 0 and self.player_attack_landed else 0)
        attacking = self.enemy_elapsed is not None and actor is self.active_enemy and death_elapsed is None
        casting = attacking and self.enemy_elapsed < LICH_PROJECTILE_LAUNCH_TIME
        if death_elapsed is not None:
            frame = min(art.DEATH_FRAME_COUNT - 1, int(death_elapsed * art.DEATH_FPS))
            sprite = art.melee_death_frames[frame]
            width = art.FRAME_WIDTH
        elif casting:
            frame = min(Lich.CAST_FRAMES - 3, int(self.enemy_elapsed * Lich.CAST_FPS))
            sprite = art.melee_cast_frames[frame]
            width = art.CAST_WIDTH
        else:
            frame = int(self.idle_elapsed * 10) % art.FRAME_COUNT
            hover_frame = frame if frame < len(art.melee_frames) else art.FRAME_COUNT - frame
            sprite = art.melee_frames[hover_frame]
            width = art.FRAME_WIDTH
        home_x = self.enemy_x(actor)
        center_x, center_y = self.zoom_point(home_x + recoil - (24 if casting else 0),
                                             FLOOR - 72, zoom)
        blue_guard = self.attack_blocked and 0 <= hit_elapsed < .12
        red_hit = 0 <= hit_elapsed < .18 and self.player_attack_landed
        if blue_guard:
            p2d.SDL_SetTextureColorMod(sprite.texture, 100, 105, 255)
        elif red_hit:
            p2d.SDL_SetTextureColorMod(sprite.texture, 255, 64, 55)
        try:
            sprite.clip_composite_draw(0, 0, sprite.w, sprite.h, 0, '',
                                       round(center_x * SCALE), round((NATIVE_HEIGHT - center_y) * SCALE),
                                       round(width * 2 * zoom * SCALE),
                                       round(art.FRAME_HEIGHT * 2 * zoom * SCALE))
        finally:
            if blue_guard or red_hit:
                p2d.SDL_SetTextureColorMod(sprite.texture, 255, 255, 255)
        if not attacking:
            return
        core_x = home_x - 35
        core_y = FLOOR - 88
        if LICH_PROJECTILE_LAUNCH_TIME <= self.enemy_elapsed < self.enemy_impact_time:
            progress = ((self.enemy_elapsed - LICH_PROJECTILE_LAUNCH_TIME)
                        / (self.enemy_impact_time - LICH_PROJECTILE_LAUNCH_TIME))
            x = (core_x - 8) + (self.player_x + 8 - (core_x - 8)) * progress
            x, y = self.zoom_point(x, core_y, zoom)
            orb = SimpleNamespace(x=x, y=y, age=self.enemy_elapsed, facing=-1, draw_angle=0)
            art.draw_projectile(orb, 0, SCALE, NATIVE_WIDTH, melee_detail=True,
                                size_scale=LICH_PROJECTILE_SIZE * zoom)
        if self.enemy_elapsed >= self.enemy_impact_time:
            elapsed = self.enemy_elapsed - self.enemy_impact_time
            if elapsed < LichImpact.DURATION and not self.enemy_attack_evaded:
                x, y = self.zoom_point(self.player_x + 8, core_y, zoom)
                art.draw_impact(SimpleNamespace(x=x, y=y, elapsed=elapsed,
                                                DURATION=LichImpact.DURATION),
                                0, SCALE, NATIVE_WIDTH)

    def player_in_hit_stop(self):
        return self.enemy_elapsed is not None and self.hit_stop_left > 0

    def player_draw_x(self):
        elapsed = self.attack_elapsed
        if elapsed is None:
            return self.player_x
        if elapsed < DASH_APPROACH_SECONDS:
            progress = elapsed / DASH_APPROACH_SECONDS
            progress = 1 - (1 - progress) ** 2
            return self.player_x + (STRIKE_X - self.player_x) * progress
        if elapsed < DASH_APPROACH_SECONDS + self.attack_duration:
            return STRIKE_X
        progress = min(1.0, (elapsed - DASH_APPROACH_SECONDS - self.attack_duration) / RETURN_SECONDS)
        progress = 1 - (1 - progress) ** 2
        return STRIKE_X + (self.player_x - STRIKE_X) * progress

    def draw_mercenary(self, zoom=1.0):
        if (self.enemy_elapsed is not None and self.enemy_elapsed >= self.enemy_impact_time
                and not self.enemy_attack_evaded):
            since_contact = self.enemy_elapsed - self.enemy_impact_time
            guarded = self.selected == self.enemy_direction
            elapsed = since_contact if guarded else since_contact + IMPACT_HIT_STOP - self.hit_stop_left
            if elapsed < MERCENARY_REACTION_DURATION:
                x, y = self.zoom_point(self.player_x, FLOOR, zoom)
                self.field.assets.draw_mercenary_hit(x, y, 1, 0, elapsed,
                                                     actor_scale=2 * zoom, guarded=guarded)
                return
        elapsed = self.attack_elapsed
        x = self.player_draw_x()
        if elapsed is None:
            if self.move_elapsed is not None:
                clip, time = 'walk', self.move_elapsed
                facing = 1 if self.move_to > self.move_from else -1
            else:
                clip, time, facing = 'idle', self.idle_elapsed, 1
        elif elapsed < DASH_APPROACH_SECONDS:
            clip, facing = 'dash', 1
            time = (self.field.assets.animations['clips']['dash']['duration']
                    * elapsed / DASH_APPROACH_SECONDS)
        elif elapsed < DASH_APPROACH_SECONDS + self.attack_duration:
            clip = 'attack'
            time, facing = self.slash_attack_time(elapsed - DASH_APPROACH_SECONDS), 1
        else:
            time = elapsed - DASH_APPROACH_SECONDS - self.attack_duration
            frame = min(BACKHOP_FRAME_COUNT - 1, int(time / RETURN_SECONDS * BACKHOP_FRAME_COUNT))
            x, y = self.zoom_point(x, FLOOR, zoom)
            scale = 2 * zoom
            # Keep facing the enemy and anchor each frame's feet to the floor.
            self.backhop.clip_draw(frame * BACKHOP_FRAME_SIZE, 0, BACKHOP_FRAME_SIZE, BACKHOP_FRAME_SIZE,
                                   round(x * SCALE),
                                   round((NATIVE_HEIGHT - y + (BACKHOP_FEET[frame] - 28) * scale) * SCALE),
                                   round(BACKHOP_FRAME_SIZE * scale * SCALE),
                                   round(BACKHOP_FRAME_SIZE * scale * SCALE))
            return
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
        alpha = 255
        if self.enemy_attack_evaded and self.enemy_elapsed is not None:
            progress = min(1.0, (self.enemy_elapsed - self.enemy_impact_time) / DODGE_FADE_SECONDS)
            alpha = round(105 + 150 * progress)
        self.field.assets.draw_character(
            clip, time, x, y, facing, 0, actor_scale=2 * zoom, melee_detail=True, alpha=alpha)

    def save(self):
        if self.cause != 'debug':
            self.field.save()

    def fade_to(self, destination):
        from game.scenes.melee_exit import MeleeExitScene
        self.app.scene = MeleeExitScene(self.app, self, destination)

    def use_item(self, index):
        if not self.can_act():
            return
        self.preview_index = index
        consumed, message = self.field.chests.use_quick_slot(index, persist=self.cause != 'debug')
        self.item_message = message
        if consumed:
            self.record(message)
            self.start_enemy_turn()

    def handle_event(self, event):
        if event.type == p2d.SDL_MOUSEMOTION:
            self.pointer = (event.x / SCALE, event.y / SCALE)
        elif (event.type == p2d.SDL_WINDOWEVENT
              and getattr(event, 'event', None) == p2d.SDL_WINDOWEVENT_FOCUS_LOST):
            self.pointer = None
        elif event.type == p2d.SDL_KEYDOWN:
            if event.key == p2d.SDLK_ESCAPE:
                if self.item_page:
                    self.item_page = False
                else:
                    self.save()
                    self.app.show_title()
                    self.fade_to(self.app.scene)
            elif event.key in KEYS:
                self.choose_direction(KEYS.index(event.key))
            elif event.key in (p2d.SDLK_LEFT, p2d.SDLK_a):
                self.move_player(-1)
            elif event.key in (p2d.SDLK_RIGHT, p2d.SDLK_d):
                self.move_player(1)
        elif event.type == p2d.SDL_MOUSEBUTTONDOWN and event.button == p2d.SDL_BUTTON_LEFT:
            x, y = event.x / SCALE, event.y / SCALE
            for speed, bounds in SPEED_BUTTONS:
                if drawing.contains(bounds, x, y):
                    self.app.battle_speed = speed
                    return
            if y < FLOOR:
                actor = self.enemy_at(x, y)
                if actor is not None:
                    self.inspected_enemy = actor
                    return
            if drawing.contains(ITEM_BUTTON, x, y) and self.can_act():
                self.item_page = not self.item_page
                self.item_message = ''
                if self.item_page:
                    self.preview_index = next((slot for slot, item in enumerate(self.field.chests.quick_slots)
                                               if item is not None), self.preview_index)
            else:
                for index, bounds in enumerate(BUTTONS):
                    if drawing.contains(bounds, x, y):
                        self.choose_direction(index)
                        break

    def draw_enemies(self, zoom):
        for slot in (2, 1, 0):
            actor = self.enemy_slots[slot]
            if actor is None:
                continue
            if isinstance(actor, Lich):
                self.draw_lich(self.field.assets.lich_art, zoom, actor, slot)
            else:
                self.draw_slime(self.field.assets.slime_art, zoom, actor, slot)

    def draw_selection(self, zoom):
        actor = self.inspected_enemy
        if actor is None or actor not in self.enemy_slots:
            return
        x = self.enemy_x(actor)
        if x < -48 or x > NATIVE_WIDTH + 48:
            return
        half = 46 if isinstance(actor, Lich) else 29
        top = FLOOR - (136 if isinstance(actor, Lich) else 68)
        for side in (-1, 1):
            for edge_y, vertical in ((top, 1), (FLOOR - 13, -1)):
                corner_x, corner_y = self.zoom_point(x + side * half, edge_y, zoom)
                inner_x = corner_x - side * 8 * zoom
                drawing.rectangle((min(corner_x, inner_x), corner_y,
                                   max(corner_x, inner_x), corner_y + 2 * zoom),
                                  GOLD, filled=True)
                vertical_x = corner_x if side < 0 else corner_x - 2 * zoom
                drawing.rectangle((vertical_x,
                                   corner_y if vertical > 0 else corner_y - 8 * zoom,
                                   vertical_x + 2 * zoom,
                                   corner_y + 8 * zoom if vertical > 0 else corner_y),
                                  GOLD, filled=True)

    def draw_enemy_hp(self):
        for actor in self.enemy_slots:
            if actor is None:
                continue
            slot = self.enemy_slots.index(actor)
            x = (ENEMY_SLOTS[slot] if actor is self.active_enemy and self.enemy_elapsed is not None
                 else self.enemy_x(actor))
            if x < -28 or x > NATIVE_WIDTH + 28:
                continue
            y = FLOOR + 11
            half = 27
            top, bottom = y - 7, y + 7
            drawing.rectangle((x - half, top, x + half, bottom),
                              GOLD if actor is self.inspected_enemy else (90, 80, 80), filled=True)
            drawing.rectangle((x - half + 1, top + 1, x + half - 1, bottom - 1),
                              (69, 37, 43), filled=True)
            fill = (2 * half - 4) * max(0, actor.hp) / actor.max_hp
            if fill > 0:
                drawing.rectangle((x - half + 2, top + 2,
                                   x - half + 2 + fill, bottom - 2),
                                  (179, 57, 72), filled=True)
            label = f'{actor.hp}/{actor.max_hp}'
            self.hud_text(x + 1, y + 1, label, 48, (30, 17, 23), center=True, compact=True)
            self.hud_text(x, y, label, 48, (250, 240, 223), center=True, compact=True)

    def attack_hit_chance(self):
        if self.player.base_attack == 0:
            return 0.0
        if self.debug_critical_pending:
            return 1.0
        dodge = (0.0 if self.is_lich else
                 min(250, 5 * self.enemy.agility + self.enemy.luck) / 1000)
        return (2 / 3) * (1 - dodge)

    def action_preview(self):
        hovered_index = next((index for index, bounds in enumerate(BUTTONS)
                              if self.hovered(bounds)), None)
        if hovered_index is not None and self.can_choose():
            self.preview_index = hovered_index
        index = self.preview_index
        if self.player.hp == 0:
            return '전투 패배', 'ESC를 눌러 메인으로 이동'
        if self.enemy_direction is not None:
            probability = (self.enemy_forecast[index] if self.enemy_forecast else 1 / 3)
            return f'{DIRECTIONS[index]} 방어', f'예측 확률 {probability:.1%}'
        if self.enemy_motions:
            return '몬스터 이동 중', '이동이 끝나면 행동 선택'
        if self.attack_elapsed is not None:
            return f'{DIRECTIONS[self.selected]} 공격', '공격 진행 중'
        if self.item_page:
            item_id = self.field.chests.quick_slots[index]
            if item_id is None:
                return '아이템 선택', self.item_message or '등록된 아이템이 없습니다'
            item = ITEMS[item_id]
            return item.name, self.item_message or item.description
        return f'{DIRECTIONS[index]} 공격', f'적중 확률 {self.attack_hit_chance():.1%}'

    def draw_combat_hud(self):
        ivory = (240, 231, 207)
        muted = (181, 174, 169)
        # Match the left frame to the current layout instead of the baked two-row skin.
        panel((8, 250, 336, 355), (29, 29, 41), (174, 134, 81))
        drawing.rectangle((10, 252, 334, 353), (76, 70, 77))
        drawing.rectangle((16, 255, 330, 315), (29, 29, 41), filled=True)
        title, detail = self.action_preview()
        self.hud_text(88, 271, title, 140, GOLD, center=True)
        self.hud_text(88, 289, detail, 140, ivory, center=True)

        can_choose = self.can_choose()
        guarding = self.enemy_direction is not None
        displayed_items = (self.field.chests.quick_slots if self.item_page and not guarding
                           else (None, None, None))
        hover_index = next((index for index, bounds in enumerate(BUTTONS)
                            if can_choose and self.hovered(bounds)), None)
        draw_bag_quick_slots(self.field.field_quick_hud, self.field.inventory.quick_badges,
                             BUTTONS, self.field.chests.icons, displayed_items, hovered=hover_index)
        for index, (bounds, direction) in enumerate(zip(BUTTONS, DIRECTIONS)):
            left, top, right, bottom = bounds
            if ((self.attack_elapsed is not None or self.enemy_elapsed is not None)
                    and self.selected == index):
                drawing.rectangle(bounds, GOLD)
            color = ivory if can_choose else muted
            if self.item_page and not guarding:
                continue
            if guarding and self.enemy_forecast is not None:
                self.hud_text((left + right) / 2, top + 10, direction,
                              right - left - 6, color, center=True, compact=True)
                self.hud_text((left + right) / 2, top + 21,
                              f'{self.enemy_forecast[index]:.1%}', right - left - 6,
                              GOLD, center=True, compact=True)
            else:
                self.hud_text((left + right) / 2, top + 17, direction,
                              right - left - 6, color, center=True)
        # Reuse the slot artwork edges without its numbered badge.
        left, top, right, bottom = ITEM_BUTTON
        sheet = self.field.field_quick_hud
        drawing.rectangle(ITEM_BUTTON, (17, 21, 32), filled=True)
        for sx, sy, sw, sh, x, y, width, height in (
                (14, 33, 47, 4, left + 17.5, top + 1.5, 35, 3),
                (14, 37, 4, 36, left + 1.5, top + 18, 3, 29),
                (57, 37, 4, 36, right - 1.5, top + 18, 3, 29),
                (18, 77, 10, 3, left + 17.5, bottom - 1, 35, 2)):
            sheet.clip_draw(sx, sheet.h - sy - sh, sw, sh,
                            round(x * SCALE), round((NATIVE_HEIGHT - y) * SCALE),
                            width * SCALE, height * SCALE)
        self.switch_icon.draw(round((ITEM_BUTTON[0] + ITEM_BUTTON[2]) / 2 * SCALE),
                              round((NATIVE_HEIGHT - (ITEM_BUTTON[1] + ITEM_BUTTON[3]) / 2) * SCALE),
                              24 * SCALE, 24 * SCALE)

        base = self.player.base_attack
        strength = self.player.stat_value('strength')
        luck = self.player.stat_value('luck')
        agility = self.player.stat_value('agility')
        middle = apply_strength(base, strength) if base else 0
        damage = f'{max(0, middle - 2)}~{middle + 2}' if base else '0'
        critical = min(200, max(0, 4 + luck)) / 2 if base else 0
        dodge = min(250, max(0, 5 * agility + luck)) / 10
        panel((14, 320, 104, 350), (20, 20, 29), (82, 78, 90))
        self.hud_text(20, 328, '용병', 82, ivory, compact=True)
        self.hud_text(20, 342, f'HP {self.player.hp}/{self.player.max_hp}', 82, ivory, compact=True)
        # One taller panel replaces the two baked stat boxes and their divider.
        panel((110, 300, 330, 352), (20, 20, 29), (82, 78, 90))
        rows = (
            ('공격력', damage),
            ('방어력', f'물리 {self.player.physical_defense} · 마법 {self.player.magic_defense}'),
            ('치명타', f'{critical:.1f}%'),
            ('회피', f'{dodge:.1f}%'),
        )
        for row, (label, value) in enumerate(rows):
            y = 307 + row * 12
            self.hud_text(116, y, label, 48, ivory, compact=True)
            text_width = self.app.resources.compact.measure(value)[0]
            self.hud_text(324 - min(150, text_width), y, value, 150, ivory, compact=True)

        actor = self.inspected_enemy
        if actor is None or actor not in self.enemy_slots:
            actor = self.enemy_slots[0]
            self.inspected_enemy = actor
        if actor is None:
            return
        self.hud_text(489, 285, actor.melee_name, 260, ivory, center=True)
        self.hud_text(352, 317, 'HP', 22, ivory, compact=True)
        if actor.hp > 0:
            drawing.rectangle((377, 313, 377 + 244 * actor.hp / actor.max_hp, 319),
                              (156, 54, 70), filled=True)
        self.hud_text(500, 316, f'{actor.hp}/{actor.max_hp}', 236, ivory, center=True, compact=True)
        for cx, name, attribute in ((382, '힘', 'strength'), (451, '민첩', 'agility'),
                                    (520, '지능', 'intelligence'), (589, '운', 'luck')):
            value = getattr(actor, attribute, '—')
            self.hud_text(cx, 331, f'{name} {value}', 60, ivory, center=True, compact=True)
        self.hud_text(353, 345, '상태·버프', 64, GOLD, compact=True)
        self.hud_text(422, 345, self.enemy_status(actor), 128, (168, 211, 169), compact=True)

    def draw(self):
        zoom = self.impact_zoom()
        draw_battle_background(self.background, zoom=zoom, transform=self.zoom_point)
        impact = ((zoom - 1) / SLASH_ZOOM_FACTOR if self.enemy_elapsed is not None
                  else self.slash_impact_strength())
        if impact:
            drawing.black_overlay(.38 * impact)
        if self.attack_elapsed is not None:
            self.draw_enemies(zoom)
            self.draw_mercenary(zoom)
        else:
            self.draw_mercenary(zoom)
            self.draw_enemies(zoom)
        lights = [(self.player_draw_x(), FLOOR - 55, 180, 148)]
        lights.extend((self.actor_x(actor), FLOOR - 45, 155, 148)
                      for actor in self.enemy_slots if actor is not None)
        sources = []
        for lx, ly, radius, clearing in lights:
            lx, ly = self.zoom_point(lx, ly, zoom)
            sources.append((lx, ly, radius * zoom, clearing))
        self.darkness.draw_sources(0, sources, ambient=158)
        self.hud.draw(320 * SCALE, round((NATIVE_HEIGHT - HUD_TOP - self.hud.h / 2) * SCALE),
                      NATIVE_WIDTH * SCALE, self.hud.h * SCALE)
        self.draw_selection(zoom)
        self.draw_combat_hud()
        self.draw_enemy_hp()
        if self.hit_stop_left > 0:
            # Stepped highlight at the point of contact, on the logical pixel grid.
            x, y = ((self.player_x + 9, FLOOR - 51) if self.player_in_hit_stop()
                    else (self.enemy_home_x - 13, FLOOR - 26))
            for step in range(5):
                left, top = self.zoom_point(x + 3 * step, y + 3 * step, zoom)
                drawing.rectangle((left, top, left + 4 * zoom, top + 2 * zoom),
                                  (255, 221, 165), filled=True)

        small, normal = self.app.resources.small, self.app.resources.normal
        if self.combat_popup is not None:
            label, x, y, elapsed = self.combat_popup
            progress = elapsed / COMBAT_POPUP_SECONDS
            x, y = self.zoom_point(x, y - 20 * progress, zoom)
            alpha = round(255 * min(1.0, (1 - progress) / .75))
            color = (195, 226, 255) if label == 'MISS' else (255, 139, 108)
            font = normal
            if label.endswith('!'):
                color = (255, 72, 65)
                font = self.app.resources.heading
            centered(font, x + 1, y + 1, label, (32, 20, 24, alpha))
            centered(font, x, y, label, (*color, alpha))
        for speed, bounds in SPEED_BUTTONS:
            left, top, right, bottom = bounds
            selected = self.app.battle_speed == speed
            highlighted = selected or self.hovered(bounds)
            panel(bounds, (67, 48, 35) if selected else (30, 33, 44),
                  GOLD if highlighted else (76, 75, 86))
            centered(small, (left + right) / 2, (top + bottom) / 2, f'x{speed}')
        draw_hp_bar(small, 20, 22, self.player.hp, self.player.max_hp)
