"""Real-time side-scrolling dungeon. Turn-based battles are a separate scene."""
import math
import pico2d as p2d
from game import drawing
from game.dungeon import Knight, get_assets
from game.gates import SidePassages
from game.enemies import Slime
from game.combat import resolve_encounter
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

    def handle_event(self, event):
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
                elif key == p2d.SDLK_c:
                    self.player.attack()
                elif key == p2d.SDLK_e:
                    self.passages.interact()
        elif event.type == p2d.SDL_KEYUP:
            self.keys.discard(event.key)

    def update(self, dt):
        if self.encounter is not None:
            return
        dt = max(0.0, min(1.0, dt))
        self.scenery_time += dt
        self.map_notice_time = max(0, self.map_notice_time-dt)
        self.passages.update(dt)
        steps = max(1, math.ceil(dt*120))
        direction = int(p2d.SDLK_RIGHT in self.keys)-int(p2d.SDLK_LEFT in self.keys)
        for _ in range(steps):
            self.player.step(dt/steps, direction)
            for enemy in self.enemies:
                enemy.update(dt/steps, self)
            if resolve_encounter(self):
                return
        self.camera_x = round(max(0.0, min(self.width-self.view_width, self.x-self.view_width*0.375)))

    def draw(self, *, hit_enemy=None, hit_elapsed=None):
        self.assets.draw_world(self.camera_x, self.scenery_time)
        self.passages.draw(self.camera_x)
        for enemy in self.enemies:
            if enemy is hit_enemy:
                self.assets.slime_art.draw(
                    enemy, self.camera_x, self.assets.scale, self.view_width,
                    hit_elapsed=hit_elapsed, hit_facing=-1 if self.player.x <= enemy.x else 1)
            else:
                self.assets.slime_art.draw(enemy, self.camera_x, self.assets.scale, self.view_width)
        clip, time = self.player.clip
        self.assets.draw_character(clip, time, self.x, self.y, self.player.facing, self.camera_x)
        self.assets.fire_lights.draw(self.camera_x,self.scenery_time)
        self.passages.draw_hint()
        drawing.rectangle((6,6,126,26),(20,19,22),filled=True)
        drawing.text(self.app.resources.small,12,21,f'HP {self.player.hp} / {self.player.max_hp}')
        drawing.rectangle((0, 334, 639, 359), (20, 19, 22), filled=True)
        drawing.text(self.app.resources.small, 10, 352,
                     '← → 이동   SPACE 점프   C 공격   E 상호작용   F6 맵 새로고침   ESC 저장/메인')
        if self.map_notice_time>0:
            drawing.rectangle((6,310,633,331),(20,22,28),filled=True)
            drawing.text(self.app.resources.small,10,325,self.map_notice,(224,201,148))
