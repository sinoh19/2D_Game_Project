"""Lich encounter: dodge across ranged tiles, then fight at close range."""
from copy import copy
import math
from random import randrange
from types import SimpleNamespace

import pico2d as p2d

from game import drawing
from game.combat import roll_player_damage
from game.config import ASSETS, NATIVE_HEIGHT, NATIVE_WIDTH, SCALE
from game.enemies import Lich, LichImpact, LichProjectile
from game.field_inventory import BAG_SLOTS, CLOSE, PANEL
from game.hp_ui import draw_hp_bar
from game.items import ITEMS, Equipment
from game.loot_ui import panel, slots
from game.pixel_style import simplify
from game.scenes.melee import (BUTTONS, COMBAT_POPUP_SECONDS, GOLD, ITEM_BUTTON,
                               KEYS, LOG_ROWS, SPEED_BUTTONS, USE_BUTTON, centered,
                               HOME_X, STRIKE_X, WALK_SECONDS, SLASH_HIGHLIGHTS,
                               SLASH_PREP_FRAMES, SLASH_HIGHLIGHT_SECONDS,
                               UPPER_ATTACK, UPPER_HIGHLIGHT_FRAME, IMPACT_HIT_STOP)

RANGED_DIRECTIONS = ('왼쪽', '중앙', '오른쪽')
MELEE_DIRECTIONS = ('상단', '중단', '하단')
FLOOR = 245
CONTACT_TIME = .48
TURN_SECONDS = .92
MELEE_CAST_CONTACT_TIME = .90
MELEE_CAST_DURATION = 1.40
MELEE_PROJECTILE_LAUNCH_TIME = .30
MELEE_PROJECTILE_SIZE = .65
MAX_DISTANCE_CELLS = math.ceil(LichProjectile.RANGE / 32)


class RangedScene:
    def __init__(self, app, field, enemy, *, distance_cells=None, debug=False):
        self.app, self.field, self.enemy = app, field, enemy
        self.player = field.player
        self.debug = debug
        self.cause = 'lich_projectile'
        self.initial_cells = max(1, distance_cells if distance_cells is not None
                                 else math.ceil(abs(enemy.x - field.x) / 32))
        self.distance = self.initial_cells
        self.cell_width = min(32, 420 / self.initial_cells)
        self.phase = 'ranged'
        self.turn = 'enemy'
        self.enemy_direction = None
        self.enemy_forecast = None
        self.selected = 1
        self.resolving = None
        self.action_elapsed = 0.0
        self.contact_time = CONTACT_TIME
        self.action_duration = TURN_SECONDS
        self.hit_stop_left = 0.0
        self.advance = True
        self.hit = False
        self.idle_elapsed = 0.0
        self.victory_wait = None
        self.transitioning = False
        self.popup = None
        self.pointer = None
        self.bag_open = False
        self.item_selection = None
        self.item_message = ''
        self.log = []
        self.log_offset = 0
        self.background = p2d.load_image(str(ASSETS / 'dungeon' / 'melee-chamber.png'))
        character_art = ASSETS / 'dungeon' / 'character'
        self.slash_highlights = {
            direction: (simplify(p2d.load_image(str(character_art / filename)),
                                 block=1, preserve_white=True), pivot)
            for direction, (filename, pivot) in SLASH_HIGHLIGHTS.items()
        }
        self.attack_frames = field.assets.animations['clips']['attack']['frames']
        self.slash_prep_duration = self.attack_frames[SLASH_PREP_FRAMES]['time']
        self.attack_duration = 2 * self.slash_prep_duration + SLASH_HIGHLIGHT_SECONDS
        self.record(f'리치 투사체 적중  ·  거리 {self.distance}칸')
        self.prepare_enemy_attack()

    def record(self, message):
        self.log.append(message)
        self.log_offset = 0

    def prepare_enemy_attack(self):
        self.enemy_direction = randrange(3)
        intelligence = max(0, min(20, self.player.stat_value('intelligence')))
        correct_weight = 50 + 2 * intelligence
        predicted = self.enemy_direction
        if randrange(150) >= correct_weight:
            predicted = (predicted + randrange(1, 3)) % 3
        chance = correct_weight / 150
        self.enemy_forecast = tuple(chance if i == predicted else (1 - chance) / 2
                                    for i in range(3))

    def hovered(self, bounds):
        return self.pointer is not None and drawing.contains(bounds, *self.pointer)

    def can_choose(self):
        return (not self.transitioning and self.resolving is None and self.victory_wait is None
                and self.player.hp > 0 and self.enemy.hp > 0)

    def can_act(self):
        return self.can_choose() and (self.phase == 'ranged' or self.turn == 'player')

    def choose_direction(self, index):
        if self.bag_open or not self.can_choose():
            return
        self.selected = index
        self.hit = False
        self.action_elapsed = 0.0
        self.contact_time = CONTACT_TIME
        self.action_duration = TURN_SECONDS
        self.hit_stop_left = 0.0
        self.pointer = None
        if self.phase == 'ranged':
            self.resolving = 'ranged'
            self.advance = True
            self.record(f'{RANGED_DIRECTIONS[index]}으로 회피하며 접근')
        elif self.turn == 'player':
            self.resolving = 'melee_player'
            self.contact_time = WALK_SECONDS + self.slash_prep_duration
            self.action_duration = 2 * WALK_SECONDS + self.attack_duration
            self.record(f'{MELEE_DIRECTIONS[index]} 공격!')
        else:
            self.resolving = 'melee_enemy'
            self.contact_time = MELEE_CAST_CONTACT_TIME
            self.action_duration = MELEE_CAST_DURATION
            self.record(f'{MELEE_DIRECTIONS[index]} 방어!')

    def resolve_contact(self):
        action = self.resolving
        if action == 'melee_player':
            damage, critical = roll_player_damage(
                self.player.stat_value('strength'), self.player.stat_value('luck'),
                base_attack=self.player.base_attack)
            before = self.enemy.hp
            self.enemy.take_damage(damage)
            damage = before - self.enemy.hp
            self.hit = damage > 0
            self.popup = (f'-{damage}!' if critical else f'-{damage}', 'enemy', 0.0)
            self.record(f'리치에게 {damage} 피해' + ('  ·  치명타!' if critical else ''))
            return
        if action == 'ranged' and self.selected is not None and self.selected != self.enemy_direction:
            self.popup = ('MISS', 'player', 0.0)
            self.record(f'리치 {RANGED_DIRECTIONS[self.enemy_direction]} 공격 회피!')
            return
        if action == 'melee_enemy' and self.selected == self.enemy_direction:
            self.record('리치 공격 방어 성공  ·  피해 0')
            return
        if action == 'melee_enemy':
            dodge = min(250, 5 * self.player.stat_value('agility')
                        + self.player.stat_value('luck'))
            if randrange(1000) < dodge:
                self.popup = ('MISS', 'player', 0.0)
                self.record('리치 공격 회피!')
                return
        before = self.player.hp
        self.player.take_damage(6, damage_type='magic')
        damage = before - self.player.hp
        self.hit = True
        self.popup = (f'-{damage}', 'player', 0.0)
        direction = (RANGED_DIRECTIONS if action == 'ranged' else MELEE_DIRECTIONS)[self.enemy_direction]
        self.record(f'리치 {direction} 공격 명중  ·  HP -{damage}')

    def finish_action(self):
        action = self.resolving
        self.resolving = None
        self.hit = False
        if self.player.hp == 0:
            self.record('용병이 쓰러졌다!')
            return
        if action == 'ranged':
            if self.advance:
                self.distance -= 1
            if self.distance <= 0:
                frozen = copy(self)
                frozen.distance = 1
                frozen.popup = None
                frozen.enemy_forecast = None
                frozen.log = list(self.log)
                frozen.transitioning = True
                self.distance = 0
                self.phase = 'melee'
                self.turn = 'player'
                self.enemy_direction = self.enemy_forecast = None
                self.record('리치에게 접근  ·  근접 전투 시작')
                from game.scenes.melee_transition import MeleeTransitionScene
                self.app.scene = MeleeTransitionScene(
                    self.app, frozen, self, battle_phase=True)
            else:
                self.prepare_enemy_attack()
        elif action == 'melee_player':
            if self.enemy.hp == 0:
                self.record('리치를 쓰러뜨렸다!')
                self.victory_wait = .7
            else:
                self.turn = 'enemy'
                self.prepare_enemy_attack()
        else:
            self.turn = 'player'
            self.enemy_direction = self.enemy_forecast = None

    def update(self, dt):
        dt = max(0.0, dt) * self.app.battle_speed
        self.idle_elapsed += dt
        if self.popup is not None:
            label, target, elapsed = self.popup
            elapsed += dt
            self.popup = (label, target, elapsed) if elapsed < COMBAT_POPUP_SECONDS else None
        if self.victory_wait is not None:
            self.victory_wait -= dt
            if self.victory_wait <= 0:
                if self.debug:
                    self.app.show_title()
                else:
                    self.field.resume_after_victory(self.enemy)
            return
        if self.resolving is None:
            return
        if self.hit_stop_left > 0:
            paused = min(dt, self.hit_stop_left)
            self.hit_stop_left -= paused
            dt -= paused
        previous = self.action_elapsed
        self.action_elapsed += dt
        if previous < self.contact_time <= self.action_elapsed:
            self.resolve_contact()
            if self.resolving == 'melee_player':
                self.action_elapsed = self.contact_time
                if self.hit:
                    self.hit_stop_left = IMPACT_HIT_STOP
                return
        if self.action_elapsed >= self.action_duration:
            self.finish_action()

    def save(self):
        if not self.debug:
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
            item = ITEMS[item_id]
            if isinstance(item, Equipment):
                self.item_message = '장비는 횡스크롤 가방에서 장착할 수 있습니다.'
                return
            consumed, message = item.use(self.player)
            if not consumed:
                self.item_message = message
                return
            bag[index] = None
            if not self.debug:
                self.field.chests.save()
            self.close_bag()
            self.record(message)
            if self.phase == 'ranged':
                self.selected = None
                self.advance = False
                self.resolving = 'ranged'
            else:
                self.turn = 'enemy'
                self.resolving = 'melee_enemy'
                self.selected = None
                self.prepare_enemy_attack()
            self.hit = False
            self.action_elapsed = 0.0
            self.contact_time = (MELEE_CAST_CONTACT_TIME if self.phase == 'melee'
                                 else CONTACT_TIME)
            self.action_duration = (MELEE_CAST_DURATION if self.phase == 'melee'
                                    else TURN_SECONDS)
            self.hit_stop_left = 0.0
        else:
            self.item_selection = next((i for i, bounds in enumerate(BAG_SLOTS)
                                        if bag[i] is not None and drawing.contains(bounds, x, y)), None)
            self.item_message = (ITEMS[bag[self.item_selection]].name if self.item_selection is not None
                                 else '사용할 아이템을 선택하세요.')

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
            if drawing.contains(ITEM_BUTTON, x, y) and self.can_act():
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
        enabled = self.item_selection is not None and self.can_act()
        panel(USE_BUTTON, (66, 48, 37) if enabled else (32, 34, 43),
              GOLD if enabled else (62, 64, 73))
        centered(normal, 394, 240, '사용')
        drawing.text(small, 214, 240, self.item_message)

    def slash_attack_time(self, time):
        if time < self.slash_prep_duration - 1e-8:
            return time
        recovery = time - self.slash_prep_duration - SLASH_HIGHLIGHT_SECONDS
        if recovery < -1e-8:
            return None
        return max(0.0, self.slash_prep_duration - recovery - 1e-6)

    def draw_melee_player(self):
        elapsed = self.action_elapsed
        if elapsed < WALK_SECONDS:
            clip, time, facing = 'walk', elapsed, 1
            x = HOME_X + (STRIKE_X - HOME_X) * elapsed / WALK_SECONDS
        elif elapsed < WALK_SECONDS + self.attack_duration:
            clip, time, facing = 'attack', self.slash_attack_time(elapsed - WALK_SECONDS), 1
            x = STRIKE_X
        else:
            clip, time, facing = 'walk', elapsed - WALK_SECONDS - self.attack_duration, -1
            x = STRIKE_X - (STRIKE_X - HOME_X) * time / WALK_SECONDS
        if time is None:
            if self.selected != UPPER_ATTACK:
                image, (pivot_x, pivot_y) = self.slash_highlights[self.selected]
                scale = 2 * SCALE
                image.draw(round(x * SCALE + (image.w / 2 - pivot_x) * scale),
                           round((NATIVE_HEIGHT - FLOOR) * SCALE - (image.h / 2 - pivot_y) * scale),
                           round(image.w * scale), round(image.h * scale))
                return
            time = self.attack_frames[UPPER_HIGHLIGHT_FRAME]['time']
        self.field.assets.draw_character(
            clip, time, x, FLOOR, facing, 0, actor_scale=2, melee_detail=True)

    def draw_actors(self):
        scale = 1.0 if self.phase == 'ranged' else 2.0
        lich_x = 500 if self.phase == 'ranged' else 425
        player_x = lich_x - self.distance * self.cell_width if self.phase == 'ranged' else HOME_X
        if self.phase == 'ranged':
            for step in range(self.distance):
                x = lich_x - (step + .5) * self.cell_width
                drawing.rectangle((x - self.cell_width / 2 + 2, FLOOR + 2,
                                   x + self.cell_width / 2 - 2, FLOOR + 8),
                                  (72, 78, 88), filled=True)
                drawing.rectangle((x - self.cell_width / 2 + 2, FLOOR + 2,
                                   x + self.cell_width / 2 - 2, FLOOR + 8),
                                  (117, 123, 132))
        art = self.field.assets.lich_art
        if self.resolving == 'melee_player' and self.hit:
            recoil = max(0.0, 1 - (self.action_elapsed - self.contact_time) / .24)
            lich_x += 12 * recoil * recoil
        casting = self.resolving in ('ranged', 'melee_enemy')
        frame = (min(Lich.CAST_FRAMES - 3, int(self.action_elapsed * Lich.CAST_FPS))
                 if casting else int(self.idle_elapsed * 10) % art.FRAME_COUNT)
        width = art.CAST_WIDTH if casting else art.FRAME_WIDTH
        if self.phase == 'melee':
            sprite = art.melee_cast_image if casting else art.melee_image
        else:
            sprite = art.cast_image if casting else art.image
        center_x = lich_x - 12 * scale if casting else lich_x
        hit_elapsed = self.action_elapsed - self.contact_time
        red_hit = (self.resolving == 'melee_player' and self.hit
                   and 0 <= hit_elapsed < .18)
        if red_hit:
            p2d.SDL_SetTextureColorMod(sprite.texture, 255, 64, 55)
        try:
            sprite.clip_composite_draw(
                frame * width, 0, width, art.FRAME_HEIGHT, 0, '',
                round(center_x * SCALE),
                round((NATIVE_HEIGHT - (FLOOR - 8 - 32 * scale)) * SCALE),
                round(width * scale * SCALE), round(art.FRAME_HEIGHT * scale * SCALE))
        finally:
            if red_hit:
                p2d.SDL_SetTextureColorMod(sprite.texture, 255, 255, 255)
        if self.phase == 'melee':
            core_x = lich_x - 17.5 * scale
            core_y = FLOOR - 8 - 40 * scale
            drawing.rectangle((core_x - 2 * scale, core_y - 2 * scale,
                               core_x + 2 * scale, core_y + 2 * scale),
                              (45, 103, 126), filled=True)
            drawing.rectangle((core_x - scale, core_y - scale,
                               core_x + scale, core_y + scale),
                              (111, 235, 239), filled=True)
        if red_hit:
            spread = 1 + hit_elapsed / .18
            for dx, dy in ((-7, -5), (5, -9), (-3, 6), (8, 4)):
                x, y = lich_x - 23 + dx * spread, FLOOR - 65 + dy * spread
                drawing.rectangle((x, y, x + 3, y + 3), (255, 78, 65), filled=True)
        launch_time = (MELEE_PROJECTILE_LAUNCH_TIME if self.phase == 'melee' else .18)
        if casting and launch_time <= self.action_elapsed < self.contact_time:
            progress = (self.action_elapsed - launch_time) / (self.contact_time - launch_time)
            orb_x = lich_x - 28 - (lich_x - player_x - 40) * progress
            orb = SimpleNamespace(x=orb_x, y=FLOOR - 54 * scale,
                                  age=self.action_elapsed, facing=-1, draw_angle=0)
            art.draw_projectile(orb, 0, SCALE, NATIVE_WIDTH,
                                melee_detail=self.phase == 'melee',
                                size_scale=MELEE_PROJECTILE_SIZE if self.phase == 'melee' else 1.0)
        if self.resolving in ('ranged', 'melee_enemy') and self.hit:
            elapsed = self.action_elapsed - self.contact_time
            if elapsed < .3:
                self.field.assets.draw_mercenary_hit(
                    player_x, FLOOR, 1, 0, elapsed, actor_scale=scale,
                    field_style=self.phase == 'ranged')
            else:
                self.field.assets.draw_character('idle', self.idle_elapsed, player_x, FLOOR,
                                                 1, 0, actor_scale=scale,
                                                 melee_detail=self.phase == 'melee')
            if elapsed < LichImpact.DURATION:
                art.draw_impact(SimpleNamespace(x=player_x + 8, y=FLOOR - 54 * scale,
                                                elapsed=elapsed, DURATION=LichImpact.DURATION),
                                0, SCALE, NATIVE_WIDTH)
        else:
            alpha = 110 if (self.resolving in ('ranged', 'melee_enemy')
                            and self.popup is not None and self.popup[0] == 'MISS') else 255
            if self.resolving == 'melee_player':
                self.draw_melee_player()
            else:
                self.field.assets.draw_character('idle', self.idle_elapsed, player_x, FLOOR,
                                                 1, 0, actor_scale=scale,
                                                 melee_detail=self.phase == 'melee', alpha=alpha)
        if self.popup is not None:
            label, target, elapsed = self.popup
            x = player_x if target == 'player' else lich_x
            y = FLOOR - 82 * scale - 14 * elapsed / COMBAT_POPUP_SECONDS
            color = (195, 226, 255) if label == 'MISS' else (255, 72, 65) if label.endswith('!') else (255, 139, 108)
            centered(self.app.resources.normal, x, y, label, color)

    def draw(self):
        self.background.draw(NATIVE_WIDTH * SCALE / 2, NATIVE_HEIGHT * SCALE / 2,
                             NATIVE_WIDTH * SCALE, NATIVE_HEIGHT * SCALE)
        self.draw_actors()
        small, normal = self.app.resources.small, self.app.resources.normal
        for speed, bounds in SPEED_BUTTONS:
            selected = self.app.battle_speed == speed
            panel(bounds, (67, 48, 35) if selected else (30, 33, 44),
                  GOLD if selected or self.hovered(bounds) else (76, 75, 86))
            left, top, right, bottom = bounds
            centered(small, (left + right) / 2, (top + bottom) / 2, f'x{speed}')
        draw_hp_bar(small, 20, 22, self.player.hp, self.player.max_hp)
        centered(small, 320, 29, f'원거리 전투  ·  {self.distance}칸' if self.phase == 'ranged'
                 else '리치 근접 전투')
        drawing.text(small, 514, 29, f'리치 HP {self.enemy.hp} / {self.enemy.max_hp}')
        line = (76, 75, 86)
        panel((17, 264, 258, 348), (23, 24, 32), line)
        drawing.text(normal, 29, 277, '전투 로그', GOLD)
        if len(self.log) > LOG_ROWS:
            drawing.text(small, 180, 277, 'PgUp / PgDn', (163, 161, 173))
        drawing.rectangle((28, 288, 247, 288), line, filled=True)
        end = len(self.log) - self.log_offset
        for row, entry in enumerate(self.log[max(0, end - LOG_ROWS):end]):
            drawing.text(small, 29, 299 + row * 16, entry, (228, 216, 187))
        if self.player.hp == 0:
            instruction = '전투 패배  /  ESC 메인'
        elif self.victory_wait is not None:
            instruction = '리치 처치!'
        elif self.resolving is not None:
            instruction = '리치 공격 진행 중' if self.resolving != 'melee_player' else '공격 진행 중'
        elif self.transitioning:
            instruction = '리치에게 접근  /  근접 전투 전환 중'
        elif self.phase == 'ranged':
            instruction = '회피 방향 선택  /  한 턴에 1칸 접근'
        elif self.turn == 'player':
            instruction = '내 턴  /  공격 방향 선택'
        else:
            instruction = '상대 턴  /  방어 방향 선택'
        centered(small, 339, 263, instruction)
        labels = RANGED_DIRECTIONS if self.phase == 'ranged' else MELEE_DIRECTIONS
        action = '회피' if self.phase == 'ranged' else '공격' if self.turn == 'player' else '방어'
        for index, (bounds, label) in enumerate(zip(BUTTONS, labels)):
            left, top, right, bottom = bounds
            active = self.can_choose() and self.hovered(bounds)
            panel(bounds, (67, 48, 35) if active else (30, 33, 44), GOLD if active else line)
            drawing.text(small, left + 11, top + 10, str(index + 1),
                         GOLD if active else (172, 174, 184))
            caption = f'{label} {action}'
            if self.can_choose() and self.enemy_forecast is not None:
                caption += f'  {self.enemy_forecast[index]:.1%}'
            centered(small, (left + right) / 2 + 5, (top + bottom) / 2, caption)
        item_hover = self.can_act() and self.hovered(ITEM_BUTTON)
        panel(ITEM_BUTTON, (67, 48, 35) if item_hover else (31, 34, 45),
              GOLD if item_hover else line)
        centered(normal, 537, 310, '아이템')
        if self.bag_open:
            self.draw_bag()
