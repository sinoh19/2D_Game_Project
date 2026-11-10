"""Real-time side-scrolling dungeon. Turn-based battles are a separate scene."""
import math
import pico2d as p2d
from game import drawing
from game.config import SCALE
from game.dungeon import Knight, get_assets
from game.gates import SidePassages
from game.enemies import Slime
from game.combat import resolve_encounter
from game.chests import TreasureChests
from game.field_inventory import FieldInventory
from game.items import ITEMS
from game.terrain import slope_surfaces, inside_slope


class FieldScene:
    def __init__(self, app, position=None, *, new_game=False):
        self.app = app
        self.assets = get_assets(app.resources)
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
        self.chests = TreasureChests(self, restore=not new_game)
        self.inventory = FieldInventory(self)
        self.dropped_items = []
        self.pickup_target = None
        self.enemies = [Slime(spec, self.assets.slime_art.motion) for spec in self.layout.get('enemies', [])]
        self.camera_x = round(max(0.0, min(self.width-self.view_width, self.x-self.view_width*0.375)))

    @property
    def x(self):
        return self.player.x

    @property
    def y(self):
        return self.player.y

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

    def movement_direction(self):
        return int(p2d.SDLK_RIGHT in self.keys) - int(p2d.SDLK_LEFT in self.keys)

    def handle_event(self, event):
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
                elif key == p2d.SDLK_i:
                    self.keys.intersection_update({key})
                    self.inventory.open()
                elif key == p2d.SDLK_e:
                    if self.chests.interact():
                        self.keys.intersection_update({key})
                    else:
                        self.passages.interact()
        elif event.type == p2d.SDL_KEYUP:
            self.keys.discard(event.key)

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
        if self.encounter is not None or self.inventory.is_open:
            return
        dt = max(0.0, min(1.0, dt))
        self.chests.update(dt)
        if self.chests.active is not None:
            return
        self.scenery_time += dt
        self.map_notice_time = max(0, self.map_notice_time-dt)
        self.passages.update(dt)
        for item in self.dropped_items:
            item.update(dt, self)
        self.dropped_items[:] = [item for item in self.dropped_items
                                 if item.feet <= self.layout['height'] + 32]
        steps = max(1, math.ceil(dt*120))
        direction = self.movement_direction()
        for _ in range(steps):
            self.player.step(dt/steps, direction)
            self.update_pickup(dt/steps)
            for enemy in self.enemies:
                enemy.update(dt/steps, self)
            if resolve_encounter(self):
                return
        self.camera_x = round(max(0.0, min(self.width-self.view_width, self.x-self.view_width*0.375)))

    def draw(self, *, hit_enemy=None, hit_elapsed=None):
        self.assets.draw_world(self.camera_x, self.scenery_time)
        self.passages.draw(self.camera_x)
        self.chests.draw(self.camera_x)
        for enemy in self.enemies:
            if enemy is hit_enemy:
                self.assets.slime_art.draw(
                    enemy, self.camera_x, self.assets.scale, self.view_width,
                    hit_elapsed=hit_elapsed, hit_facing=-1 if self.player.x <= enemy.x else 1)
            else:
                self.assets.slime_art.draw(enemy, self.camera_x, self.assets.scale, self.view_width)
        clip, time = self.player.clip
        self.assets.draw_character(clip, time, self.x, self.y, self.player.facing, self.camera_x)
        for item in self.dropped_items:
            item.draw(self.chests.icons[item.item_id], self.camera_x)
        self.assets.fire_lights.draw(self.camera_x,self.scenery_time)
        if not self.chests.draw_hint(self.camera_x):
            self.passages.draw_hint()
        drawing.rectangle((6,6,126,26),(20,19,22),filled=True)
        drawing.text(self.app.resources.small,12,21,f'HP {self.player.hp} / {self.player.max_hp}')
        drawing.rectangle((0, 334, 639, 359), (20, 19, 22), filled=True)
        drawing.text(self.app.resources.small, 10, 352,
                     '← → 이동   SPACE 점프   SHIFT 대시   C 공격   E 상호작용   Z 줍기   I 가방   F6 맵 갱신   ESC 저장/메인')
        if self.map_notice_time>0:
            drawing.rectangle((6,310,633,331),(20,22,28),filled=True)
            drawing.text(self.app.resources.small,10,325,self.map_notice,(224,201,148))
        self.chests.draw_loot()
        if self.inventory.is_open:
            self.inventory.draw()
