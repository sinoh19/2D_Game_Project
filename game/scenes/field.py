"""Real-time side-scrolling dungeon. Turn-based battles are a separate scene."""
import math
import pico2d as p2d
from game import drawing
from game.config import ASSETS, SCALE
from game.quick_slot_ui import draw_bag_quick_slots
from game.dungeon import Knight, get_assets
from game.gates import SidePassages
from game.enemies import Slime, Lich
from game.combat import resolve_encounter
from game.chests import TreasureChests
from game.field_inventory import FieldInventory
from game.character_status import CharacterStatus
from game.items import ITEMS, DroppedItem, Equipment
from game.spike_trap import SpikeTrap
from game.pixel_style import simplify
from game.terrain import slope_surfaces, inside_slope
from game.lighting import WorldDarkness
from game.tutorial_bird import TutorialBird

FIELD_QUICK_SLOTS = tuple((8 + index * 41, 281, 43 + index * 41, 316)
                          for index in range(3))


class FieldScene:
    def __init__(self, app, position=None, *, new_game=False):
        self.app = app
        self.assets = get_assets(app.resources)
        self.darkness = WorldDarkness(self.assets.fire_lights)
        self.layout = self.assets.layout
        self.width = self.layout['width']
        self.view_width = self.assets.view_width
        self.solids = list(self.layout['solids'])
        self.platforms = self.layout['platforms']
        self.slopes = self.layout.get('slopes', [])
        self.keys = set()
        self.encounter = None
        self.camera_x = 0.0
        self.scenery_time = 0.0
        self.map_notice = ""
        self.map_notice_time = 0.0
        self.new_game = new_game
        self.passages = SidePassages(self, restore=not new_game)
        if position is not None:
            ramps=slope_surfaces(self,position[0],Knight.HALF_WIDTH)
            if ramps and abs(position[1]-min(ramps))<=Knight.STEP_HEIGHT:
                position=(position[0],min(ramps))
        if position is None or not self.valid_position(position):
            position = self.layout['spawn']
        self.player = Knight(self, position)
        self.tutorial_bird = TutorialBird(self)
        self.dropped_items = []
        self.chests = TreasureChests(self, restore=not new_game)
        self.field_quick_hud = p2d.load_image(str(ASSETS / 'ui' / 'field-quick-hud.png'))
        self.spike_traps = [SpikeTrap(spec, self.solids + self.platforms)
                            for spec in self.layout.get('spikeTraps', [])]
        # The 2172px source shrinks to a 48px trap in the field. A 90px
        # source block becomes roughly a 2px game pixel at that size.
        self.spike_image = (
            simplify(p2d.load_image(str(ASSETS / 'dungeon' / 'scenery' / 'falling-spikes-chunky.png')),
                     block=90)
            if self.spike_traps else None
        )
        self.trap_hit_time = 0.0
        self.inventory = FieldInventory(self)
        self.status = CharacterStatus(self)
        self.pickup_target = None
        self.enemies = [Slime(spec, self.assets.slime_art.motion) for spec in self.layout.get('enemies', [])]
        self.liches = [Lich(spec) for spec in self.layout.get('liches', [])]
        self.lich_projectiles = []
        self.lich_impacts = []
        self.camera_x = round(max(0.0, min(self.width-self.view_width, self.x-self.view_width*0.375)))

    @property
    def x(self):
        return self.player.x

    @property
    def y(self):
        return self.player.y

    def projectile_obstacles(self, owner):
        """Visible physical objects that stop a lich projectile."""
        yield from self.solids
        yield from self.platforms
        yield from self.layout.get('projectileObstacles', ())
        for chest in self.chests.chests:
            yield (chest.x - chest.width / 2, chest.y - chest.height,
                   chest.x + chest.width / 2, chest.y)
        for trap in self.spike_traps:
            yield (trap.x - trap.width / 2, trap.y,
                   trap.x + trap.width / 2, trap.y + trap.height)
        for enemy in self.enemies:
            half = 16 * enemy.scale
            yield (enemy.x - half, enemy.y - 32 * enemy.scale,
                   enemy.x + half, enemy.y)
        for lich in self.liches:
            if lich is not owner:
                yield (lich.x - lich.width / 2, lich.y - lich.height,
                       lich.x + lich.width / 2, lich.y)
        for item in self.dropped_items:
            size = 22 if isinstance(ITEMS[item.item_id], Equipment) else 14
            yield (item.x - size / 2, item.feet - size - 5,
                   item.x + size / 2, item.feet - 5)

    def valid_position(self, position):
        x, y = position
        if not (math.isfinite(x) and math.isfinite(y) and Knight.HALF_WIDTH <= x <= self.width-Knight.HALF_WIDTH and Knight.HEIGHT <= y <= self.layout['height']):
            return False
        if inside_slope(self,x,y,Knight.HEIGHT,Knight.HALF_WIDTH):return False
        return not any(x+Knight.HALF_WIDTH > l+0.01 and x-Knight.HALF_WIDTH < r-0.01 and y > t+0.01 and y-Knight.HEIGHT < b-0.01
                       for l,t,r,b in self.solids)

    def on_enter(self):
        # Commit only after the intro transition succeeds. Cancelling the
        # intro must leave the previous saved run untouched.
        if self.new_game:
            self.save()
            self.new_game = False

    def save(self):
        self.app.storage.save_position(self.x, self.y)
        self.passages.save()
        self.chests.save()

    def resume_after_victory(self, enemy, defeated=None):
        for fallen in (defeated if defeated is not None else (enemy,)):
            if fallen in self.enemies:
                self.enemies.remove(fallen)
            elif fallen in self.liches:
                self.liches.remove(fallen)
        player = self.player
        player.x = max(player.HALF_WIDTH, min(self.width - player.HALF_WIDTH, enemy.x))
        player.y = enemy.y
        player.vy = 0.0
        player.grounded = player.supported()
        player.clock = 0.0
        player.air_phase = None
        player.air_time = 0.0
        player.attack_time = None
        player.dash_time = None
        player.pickup_time = None
        player.prepare_time = None
        player.land_time = None
        player.dash_cooldown = 0.0
        player.coyote = 0.08 if player.grounded else 0.0
        player.jump_buffer = 0.0
        player.moving = False
        self.tutorial_bird.reset()
        self.keys.clear()
        self.pickup_target = None
        self.trap_hit_time = 0.0
        self.lich_projectiles.clear()
        self.lich_impacts.clear()
        self.encounter = None
        self.camera_x = round(max(0.0, min(self.width - self.view_width,
                                           player.x - self.view_width * 0.375)))
        self.app.scene = self

    def movement_direction(self):
        return int(p2d.SDLK_RIGHT in self.keys) - int(p2d.SDLK_LEFT in self.keys)

    def handle_event(self, event):
        if self.status.is_open:
            self.status.handle_event(event)
            return
        if self.inventory.is_open:
            if event.type == p2d.SDL_KEYUP:
                self.keys.discard(event.key)
            elif event.type == p2d.SDL_WINDOWEVENT and getattr(event, 'event', None) == p2d.SDL_WINDOWEVENT_FOCUS_LOST:
                self.keys.clear()
                self.inventory.menu = None
                self.inventory.cancel_drag()
            elif (event.type == p2d.SDL_KEYDOWN and event.key in (p2d.SDLK_i, p2d.SDLK_ESCAPE)
                  and event.key not in self.keys):
                self.keys.add(event.key)
                self.inventory.close()
            elif event.type == p2d.SDL_MOUSEBUTTONDOWN:
                self.inventory.click(event)
            elif event.type == p2d.SDL_MOUSEMOTION:
                self.inventory.mouse_move(event.x / SCALE, event.y / SCALE)
            elif event.type == p2d.SDL_MOUSEBUTTONUP and event.button == p2d.SDL_BUTTON_LEFT:
                self.inventory.mouse_up(event.x / SCALE, event.y / SCALE)
            return
        if self.chests.active is not None:
            if event.type == p2d.SDL_KEYUP:
                self.keys.discard(event.key)
            elif event.type == p2d.SDL_WINDOWEVENT and getattr(event, 'event', None) == p2d.SDL_WINDOWEVENT_FOCUS_LOST:
                self.keys.clear()
                self.chests.cancel_drag()
            elif event.type == p2d.SDL_KEYDOWN and event.key == p2d.SDLK_ESCAPE:
                self.keys.add(event.key)
                self.chests.close()
            elif event.type == p2d.SDL_MOUSEMOTION:
                self.chests.mouse_move(event.x / SCALE, event.y / SCALE)
            elif event.type == p2d.SDL_MOUSEBUTTONDOWN and event.button == p2d.SDL_BUTTON_LEFT:
                self.chests.mouse_down(event.x / SCALE, event.y / SCALE)
            elif event.type == p2d.SDL_MOUSEBUTTONUP and event.button == p2d.SDL_BUTTON_LEFT:
                self.chests.mouse_up(event.x / SCALE, event.y / SCALE)
            return
        if event.type == p2d.SDL_WINDOWEVENT and getattr(event, 'event', None) == p2d.SDL_WINDOWEVENT_FOCUS_LOST:
            self.keys.clear()
        elif event.type == p2d.SDL_KEYDOWN:
            key = event.key
            if key is None or key in self.keys:
                return
            if key == p2d.SDLK_ESCAPE:
                self.save()
                self.app.show_title()
            else:
                self.keys.add(key)
                if key == p2d.SDLK_F6:
                    self.app.reload_field_map()
                    return
                if key == p2d.SDLK_SPACE:
                    self.player.jump()
                elif key in (p2d.SDLK_LSHIFT, p2d.SDLK_RSHIFT):
                    self.player.dash(self.movement_direction())
                elif key == p2d.SDLK_c:
                    self.player.attack()
                elif key == p2d.SDLK_z:
                    self.start_pickup()
                elif key in (p2d.SDLK_1, p2d.SDLK_2, p2d.SDLK_3):
                    used, message = self.chests.use_quick_slot(
                        (p2d.SDLK_1, p2d.SDLK_2, p2d.SDLK_3).index(key))
                    self.map_notice = message
                    self.map_notice_time = 2.0
                elif key == p2d.SDLK_i:
                    self.keys.intersection_update({key})
                    self.inventory.open()
                elif key == p2d.SDLK_e:
                    self.keys.intersection_update({key})
                    self.status.open()
                elif key == p2d.SDLK_f:
                    if self.chests.interact():
                        self.keys.intersection_update({key})
                    else:
                        self.passages.interact()
        elif event.type == p2d.SDL_KEYUP:
            self.keys.discard(event.key)

    def drop_item(self, item_id):
        self.dropped_items.append(DroppedItem(item_id, self.x, self.y - self.player.HEIGHT / 2))

    def start_pickup(self):
        if self.player.pickup_time is not None:
            return
        nearby = [item for item in self.dropped_items if item.grounded
                  and abs(item.x - self.x) <= 24 and abs(item.feet - self.y) <= 12]
        target = min(nearby, key=lambda item: abs(item.x - self.x), default=None)
        if target is None:
            return
        if None not in self.inventory.bag:
            self.map_notice = '가방에 빈 슬롯이 없습니다.'
            self.map_notice_time = 2.0
        elif self.player.start_pickup(target.x):
            self.pickup_target = target

    def update_pickup(self, dt):
        if self.player.pickup_time is None:
            self.pickup_target = None
            return
        self.player.pickup_time += dt
        clip = self.assets.animations['clips']['pickup']
        target = self.pickup_target
        if target is not None and self.player.pickup_time >= clip['frames'][4]['time']:
            self.pickup_target = None
            bag = self.inventory.bag
            if target in self.dropped_items and target.grounded and None in bag:
                bag[bag.index(None)] = target.item_id
                self.dropped_items.remove(target)
                self.chests.save()
                self.map_notice = f'획득  ·  {ITEMS[target.item_id].name}'
                self.map_notice_time = 2.0
        if self.player.pickup_time >= clip['duration']:
            self.player.pickup_time = None

    def update(self, dt):
        if self.status.is_open:
            self.status.idle_elapsed += max(0.0, dt)
            return
        if self.encounter is not None or self.inventory.is_open:
            return
        dt = max(0.0, min(1.0, dt))
        self.chests.update(dt)
        if self.chests.active is not None:
            return
        self.scenery_time += dt
        self.trap_hit_time = max(0.0, self.trap_hit_time - dt)
        self.map_notice_time = max(0, self.map_notice_time-dt)
        self.passages.update(dt)
        for item in self.dropped_items:
            item.update(dt, self)
        self.dropped_items[:] = [item for item in self.dropped_items
                                 if item.feet <= self.layout['height'] + 32]
        steps = max(1, math.ceil(dt*120))
        direction = self.movement_direction()
        for _ in range(steps):
            self.lich_impacts[:] = [impact for impact in self.lich_impacts
                                   if impact.update(dt/steps)]
            self.player.step(dt/steps, direction)
            self.tutorial_bird.update(dt/steps)
            if self.passages.reached_exit():
                from game.scenes.stage_end import StageEndScene
                self.app.scene = StageEndScene(self.app)
                return
            for trap in self.spike_traps:
                if trap.update(dt/steps, self.player):
                    self.trap_hit_time = .30
            self.update_pickup(dt/steps)
            for enemy in self.enemies:
                enemy.update(dt/steps, self)
            # Resolve a landed sword strike before a simultaneous incoming projectile.
            if resolve_encounter(self, player_attack_only=True):
                return
            self.lich_projectiles[:] = [projectile for projectile in self.lich_projectiles
                                       if projectile.update(dt/steps, self)]
            if self.app.scene is not self:
                return
            for lich in self.liches:
                projectile = lich.update(dt/steps, self)
                if projectile is not None:
                    self.lich_projectiles.append(projectile)
            if resolve_encounter(self):
                return
        self.camera_x = round(max(0.0, min(self.width-self.view_width, self.x-self.view_width*0.375)))

    def draw(self, *, hit_enemy=None, hit_elapsed=None, hit_by=None):
        self.assets.draw_world(self.camera_x, self.scenery_time,
                               spike_traps=self.spike_traps, spike_image=self.spike_image)
        self.passages.draw(self.camera_x)
        self.chests.draw(self.camera_x)
        for enemy in self.enemies:
            if enemy is hit_enemy:
                self.assets.slime_art.draw(
                    enemy, self.camera_x, self.assets.scale, self.view_width,
                    hit_elapsed=hit_elapsed, hit_facing=-1 if self.player.x <= enemy.x else 1)
            else:
                self.assets.slime_art.draw(enemy, self.camera_x, self.assets.scale, self.view_width)
        for lich in self.liches:
            self.assets.lich_art.draw(lich, self.camera_x, self.assets.scale, self.view_width,
                                     hit_elapsed=hit_elapsed if lich is hit_enemy else None)
        for projectile in self.lich_projectiles:
            self.assets.lich_art.draw_projectile(
                projectile, self.camera_x, self.assets.scale, self.view_width)
        self.tutorial_bird.draw(self.camera_x)
        if hit_by is not None:
            facing = self.player.facing if hit_by.x == self.x else (1 if hit_by.x > self.x else -1)
            self.assets.draw_field_hit(self.x, self.y, facing, self.camera_x, hit_elapsed)
        elif self.trap_hit_time > 0:
            self.assets.draw_field_hit(self.x, self.y, self.player.facing, self.camera_x, .30 - self.trap_hit_time)
        else:
            clip, time = self.player.clip
            self.assets.draw_character(clip, time, self.x, self.y, self.player.facing, self.camera_x)
        for impact in self.lich_impacts:
            self.assets.lich_art.draw_impact(
                impact, self.camera_x, self.assets.scale, self.view_width)
        for item in self.dropped_items:
            item.draw(self.chests.icons[item.item_id], self.camera_x, self.scenery_time)
        # Keep the player and flames readable inside the darker dungeon.
        self.darkness.draw(self.camera_x, self.scenery_time, self.x, self.y)
        self.assets.fire_lights.draw(self.camera_x,self.scenery_time)
        if not self.chests.draw_hint(self.camera_x):
            self.passages.draw_hint()
        draw_bag_quick_slots(self.field_quick_hud, self.inventory.quick_badges,
                             FIELD_QUICK_SLOTS, self.chests.icons, self.chests.quick_slots)
        # Extend only the HP bar; the three item frames keep the bag's size.
        drawing.rectangle((8, 333, 303, 356), (16, 18, 29), filled=True)
        drawing.rectangle((8, 333, 303, 356), (174, 134, 81))
        drawing.rectangle((11, 336, 300, 353), (28, 32, 45), filled=True)
        drawing.rectangle((11, 336, 300, 353), (52, 56, 73))
        drawing.rectangle((14, 340, 297, 349), (19, 23, 34), filled=True)
        drawing.rectangle((8, 334, 10, 337), (224, 189, 121), filled=True)
        drawing.rectangle((301, 353, 303, 356), (224, 189, 121), filled=True)
        hp_ratio = max(0.0, min(1.0, self.player.hp / self.player.max_hp)) if self.player.max_hp else 0
        hp_width = round(284 * hp_ratio)
        if hp_width:
            drawing.rectangle((14, 340, 13 + hp_width, 349), (132, 45, 64), filled=True)
            drawing.rectangle((14, 340, 13 + hp_width, 341), (176, 68, 87), filled=True)
        hp_label = f'HP {self.player.hp} / {self.player.max_hp}'
        drawing.text(self.app.resources.small, 18, 345, hp_label, (246, 241, 228))
        drawing.text(self.app.resources.small, 19, 345, hp_label, (246, 241, 228))
        drawing.text(self.app.resources.small, 316, 343,
                     'C 공격   F 상호작용   Z 줍기')
        drawing.text(self.app.resources.small, 316, 355,
                     'I 가방   E 정보   ESC 메뉴')
        if self.map_notice_time>0:
            drawing.rectangle((176, 305, 633, 329), (20, 22, 28), filled=True)
            drawing.text(self.app.resources.small, 184, 322,
                         self.map_notice, (224, 201, 148))
        self.chests.draw_loot()
        if self.inventory.is_open:
            self.inventory.draw()
        if self.status.is_open:
            self.status.draw()
