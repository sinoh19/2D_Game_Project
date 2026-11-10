"""Portable dungeon layout and original Unity sprite animation data."""
import json
import math
from functools import cached_property
import pico2d as p2d
from pico2d import pico2d as backend
from game.config import ASSETS, WINDOW_WIDTH, WINDOW_HEIGHT
from game import drawing
from game.terrain import slope_surfaces, inside_slope
from game.combat import Vitals


class DungeonAssets:
    def __init__(self, map_path=None):
        folder = ASSETS / 'dungeon'
        self.layout = json.loads((folder / 'dungeon_01.json').read_text(encoding='utf-8'))
        if map_path is not None:
            from game.tiled_map import load_map
            self.layout = load_map(map_path, self.layout, folder)
        self.view_width, self.view_height = self.layout['viewport']
        self.scale = WINDOW_WIDTH / self.view_width
        self.character_scale = self.layout['characterScale']
        self.tile_size = self.layout['tileSize']
        self.animations = json.loads((folder / 'character.json').read_text(encoding='utf-8'))
        self.attack_hitboxes = json.loads((folder/'attack-hitboxes.json').read_text(encoding='utf-8-sig'))
        self.images = {name: p2d.load_image(str(folder / path))
                       for name, path in self.layout['images'].items()}
        self.sheets = {name: p2d.load_image(str(folder / path))
                       for name, path in self.animations['sheets'].items()}
        if self.layout.get('spriteStyle', {}).get('enabled', False):
            from game.pixel_style import apply
            apply(self)
        from game.enemies import SlimeArt
        self.slime_art = SlimeArt(folder/'monsters/slime') if self.layout.get('enemies') else None
        from game.terrain_interior import TerrainInterior
        self.terrain_shading = TerrainInterior(self)
        self.chandelier_frames = {}
        from game.chandelier import prepare
        for item in self.layout.get('tiledVisuals',[]):
            key = item['image']
            if item.get('animation') == 'chandelier-flames' and key not in self.chandelier_frames:
                self.chandelier_frames[key] = prepare(self.images[key])
        from game.background import build_layer
        self.background_layer = build_layer(self)
        from game.lighting import FireLights
        self.fire_lights = FireLights(self.layout,self.scale,self.view_width)

    def image(self, name, x, top, width, height, camera=0, flip=False):
        image = self.images[name]
        if x + width < camera or x > camera + self.view_width:
            return
        image.composite_draw(0, 'v' if flip else '',
                             round((x - camera + width / 2) * self.scale),
                             round(WINDOW_HEIGHT - (top + height / 2) * self.scale),
                             round(width * self.scale), round(height * self.scale))

    def tile(self, name, x, top, width=32, height=32, camera=0):
        if x+width < camera or x > camera+self.view_width:
            return
        spec = self.layout['unitySprites'][name]
        sx, sy, sw, sh = spec['rect']
        variants = spec.get('horizontalVariants', 1)
        sx += (int(x // self.tile_size) % variants) * sw
        # Wang transition tiles can contain air above their visible surface.
        # Place the visible cap at the collision top and fill below it without
        # stretching the cap or moving the character/collider.
        inset = self.layout.get('tileSurfaceInsets', {}).get(name, 0)
        if inset:
            cap_pixels = sh - inset
            cap_height = height * cap_pixels / sh
            self.images[spec['image']].clip_composite_draw(
                sx, sy, sw, cap_pixels, 0, spec['flip'],
                (round(x-camera)+width/2)*self.scale,
                WINDOW_HEIGHT-(round(top)+cap_height/2)*self.scale,
                round(width*self.scale), round(cap_height*self.scale))
            fill = self.layout['unitySprites']['Fill']
            fx, fy, fw, fh = fill['rect']
            remaining = height-cap_height
            self.images[fill['image']].clip_composite_draw(
                fx, fy, fw, min(inset, fh), 0, fill['flip'],
                (round(x-camera)+width/2)*self.scale,
                WINDOW_HEIGHT-(round(top)+cap_height+remaining/2)*self.scale,
                round(width*self.scale), round(remaining*self.scale))
            return
        self.images[spec['image']].clip_composite_draw(
            sx, sy, sw, sh, 0, spec['flip'],
            (round(x-camera)+width/2)*self.scale,
            WINDOW_HEIGHT-(round(top)+height/2)*self.scale,
            round(width*self.scale), round(height*self.scale))
        self.terrain_shading.draw_legacy(name,x,top,width,height,camera)

    def unity_sprite(self, name, x, origin_y, units, camera):
        spec = self.layout['unitySprites'][name]
        sx, sy, sw, sh = spec['rect']
        width, height = sw/spec['ppu']*units, sh/spec['ppu']*units
        px, py = spec['pivot']
        left = round(x-camera-width*px)
        center_x = left+width/2
        top = round(origin_y-height*(1-py))
        center_y = top+height/2
        if center_x+width/2 < 0 or center_x-width/2 > self.view_width:
            return
        self.images[spec['image']].clip_composite_draw(
            sx, sy, sw, sh, 0, spec['flip'], round(center_x*self.scale),
            round(WINDOW_HEIGHT-center_y*self.scale), round(width*self.scale), round(height*self.scale))

    def draw_prop(self, prop, camera, time=0):
        if prop['kind'] == 'torch':
            self.unity_sprite('torch_body', prop['x'], prop['bottom'], prop['unitScale'], camera)
            animation = self.layout['torchAnimation']
            moment = time % animation['duration']
            frame = animation['frames'][0]
            for candidate in animation['frames']:
                if candidate['time'] > moment:
                    break
                frame = candidate
            ox, oy = animation['offset']
            self.unity_sprite(frame['sprite'], prop['x']+ox*prop['unitScale'],
                              prop['bottom']-oy*prop['unitScale'], prop['unitScale'], camera)
        else:
            self.unity_sprite(prop['kind'], prop['x'], prop['bottom'], prop['unitScale'], camera)

    def draw_tiled(self, camera, time):
        for command in self.layout['tiledDrawOrder']:
            if command['kind']=='prop':
                self.draw_prop(self.layout['props'][command['index']],camera,time)
                continue
            item=self.layout['tiledVisuals'][command['index']]
            x,y,w,h=item['x'],item['y'],item['width'],item['height']
            if x+w<camera or x>camera+self.view_width:continue
            image=self.images[item['image']]
            if item.get('animation') == 'chandelier-flames':
                from game.chandelier import frame_index
                image=self.chandelier_frames[item['image']][frame_index(time)]
            sx,sy,sw,sh=item['rect']
            alpha=round(max(0,min(1,item['opacity']))*255)
            if alpha!=255:p2d.SDL_SetTextureAlphaMod(image.texture,alpha)
            image.clip_composite_draw(sx,sy,sw,sh,item['angle'],item['flip'],
                (round(x-camera)+w/2)*self.scale,WINDOW_HEIGHT-(round(y)+h/2)*self.scale,
                round(w*self.scale),round(h*self.scale))
            if alpha!=255:p2d.SDL_SetTextureAlphaMod(image.texture,255)
            self.terrain_shading.draw(item,camera)

    def draw_world(self, camera, time=0):
        from game.background import draw_layer
        draw_layer(self, camera)
        if "tiledVisuals" in self.layout:
            self.draw_tiled(camera,time)
            return
        size = self.tile_size
        start = int(camera//size)*size
        for prop in self.layout['props']:
            self.draw_prop(prop,camera,time)
        for left, top, right, bottom in self.layout['renderRegions']:
            for x in range(round(left), round(right), size):
                width = min(size, right-x)
                self.tile('Floor', x, top, width, size, camera)
                for y in range(round(top+size), round(bottom), size):
                    self.tile('Fill', x, y, width, size, camera)
        for stair in self.layout['stairArt']:
            # The imported step strips have a translucent last row and
            # high-end column. Back those internal joins with rock before
            # drawing the step surface so the rear wall cannot show through.
            high_x = (stair['x']+len(stair['tiles'])*size-1
                      if stair['tiles'][0].startswith('Stairs_UpRight') else stair['x'])
            self.tile('Fill', high_x, stair['top'], 1, size, camera)
            for n in range(len(stair['tiles'])):
                self.tile('Fill', stair['x']+n*size, stair['top']+size-1, size, 1, camera)
            for n, name in enumerate(stair['tiles']):
                x = stair['x']+n*size
                self.tile(name, x, stair['top'], size, size, camera)
                for y in range(round(stair['top']+size), self.view_height+size, size):
                    self.tile('Fill', x, y, size, size, camera)
        for left, top, right, bottom in self.layout['platforms']:
            for x in range(round(left), round(right), size):
                self.tile('Floor', x, top, min(size, right-x), size/2, camera)
        for x in range(start, int(camera+self.view_width+size), size):
            self.tile('Ceiling', x, 0, size, size, camera)


    @cached_property
    def melee_sheets(self):
        from game.pixel_style import simplify

        clips = self.animations['clips']
        names = dict.fromkeys(clips[clip]['sheet'] for clip in ('idle', 'walk', 'attack'))
        return {
            name: simplify(p2d.load_image(str(ASSETS / 'dungeon' / self.animations['sheets'][name])), block=1)
            for name in names
        }

    def draw_character(self, clip_name, time, x, feet, facing, camera, *, actor_scale=None, melee_detail=False):
        clip = self.animations['clips'][clip_name]
        duration = clip['duration']
        time = time % duration if clip['loop'] else min(time, duration)
        frame = clip['frames'][0]
        for candidate in clip['frames']:
            if candidate['time'] > time + 1e-8:
                break
            frame = candidate
        sheets = self.melee_sheets if melee_detail else self.sheets
        image = sheets[clip['sheet']]
        sx, sy, width, height = frame['rect']
        px, py = frame['pivot']  # Unity pivot in pixels from lower-left.
        actor_scale = self.character_scale if actor_scale is None else actor_scale
        offset_x = (width / 2 - px)*actor_scale
        center_x = round(x - camera + (offset_x if facing > 0 else -offset_x))
        center_y = round(feet - (height / 2 - py)*actor_scale)
        image.clip_composite_draw(sx, sy, width, height, 0,
                                  'h' if facing < 0 else '',
                                  center_x*self.scale, WINDOW_HEIGHT-center_y*self.scale,
                                  round(width*actor_scale*self.scale), round(height*actor_scale*self.scale))


class Knight(Vitals):
    HALF_WIDTH = 6.125
    HEIGHT = 46.0
    SPEED = 140.0
    GRAVITY = 640.0
    JUMP_SPEED = 240.0
    STEP_HEIGHT = 8.0
    DASH_SPEED = 420.0
    DASH_PUSH_START = .10
    DASH_PUSH_END = .35
    DASH_REUSE_DELAY = .75

    def __init__(self, scene, position):
        super().__init__()
        self.scene = scene
        self.x, self.y = map(float, position)
        self.vy = 0.0
        self.facing = 1
        self.grounded = self.supported()
        self.clock = 0.0
        self.air_phase = None
        self.air_time = 0.0
        self.attack_time = None
        self.dash_time = None
        self.pickup_time = None
        self.dash_cooldown = 0.0
        self.prepare_time = None
        self.land_time = None
        self.coyote = 0.08 if self.grounded else 0.0
        self.jump_buffer = 0.0
        self.moving = False

    def overlaps_x(self, rect):
        return self.x + self.HALF_WIDTH > rect[0]+1e-6 and self.x-self.HALF_WIDTH < rect[2]-1e-6

    def ground_heights(self):
        return ([r[1] for r in self.scene.solids+self.scene.platforms if self.overlaps_x(r)]
                + slope_surfaces(self.scene,self.x,self.HALF_WIDTH))

    def supported(self):
        return any(abs(self.y-height)<.1 for height in self.ground_heights())

    def dash(self, direction=0):
        if (not self.grounded or self.dash_cooldown > 0 or self.dash_time is not None
                or self.attack_time is not None or self.prepare_time is not None
                or self.land_time is not None or self.pickup_time is not None):
            return
        self.facing = direction or self.facing
        self.dash_time = 0.0
        self.dash_cooldown = self.DASH_REUSE_DELAY
        self.jump_buffer = 0.0

    def attack(self):
        if (self.attack_time is None and self.prepare_time is None
                and self.land_time is None and self.dash_time is None
                and self.pickup_time is None):
            self.attack_time = 0.0

    def start_pickup(self, item_x):
        if (not self.grounded or self.pickup_time is not None or self.dash_time is not None
                or self.attack_time is not None or self.prepare_time is not None
                or self.land_time is not None):
            return False
        if item_x != self.x:
            self.facing = 1 if item_x > self.x else -1
        self.pickup_time = 0.0
        self.jump_buffer = 0.0
        return True

    def jump(self):
        if self.dash_time is None and self.pickup_time is None:
            self.jump_buffer = 0.12

    @property
    def clip(self):
        if self.pickup_time is not None:
            return 'pickup', self.pickup_time
        if self.dash_time is not None:
            return 'dash', self.dash_time
        if self.attack_time is not None:
            return 'attack', self.attack_time
        if self.prepare_time is not None:
            return 'prepare', self.prepare_time
        if not self.grounded:
            if self.vy < -45:
                return 'rise', self.air_time
            if self.vy > 45:
                return 'fall', self.air_time
            return 'apex', self.air_time
        if self.land_time is not None:
            return 'land', self.land_time
        return ('walk' if self.moving else 'idle'), self.clock

    def step(self, dt, direction):
        self.clock += dt
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.jump_buffer = max(0.0, self.jump_buffer-dt)
        self.coyote = 0.08 if self.grounded else max(0.0, self.coyote-dt)
        clips = self.scene.assets.animations['clips']
        if self.attack_time is not None:
            self.attack_time += dt
            if self.attack_time >= clips['attack']['duration']:
                self.attack_time = None
        if self.land_time is not None:
            self.land_time += dt
            if self.land_time >= clips['land']['duration']:
                self.land_time = None
        locked = (self.attack_time is not None or self.land_time is not None
                  or self.dash_time is not None or self.pickup_time is not None)
        if self.jump_buffer > 0 and self.coyote > 0 and not locked and self.prepare_time is None:
            self.prepare_time = 0.0
            self.jump_buffer = self.coyote = 0.0
        if self.prepare_time is not None:
            self.prepare_time += dt
            if self.prepare_time >= clips['prepare']['duration']:
                self.prepare_time = None
                self.vy = -self.JUMP_SPEED
                self.grounded = False
        locked = locked or self.prepare_time is not None
        dx = direction*self.SPEED*dt if not locked else 0.0
        if self.dash_time is not None:
            previous = self.dash_time
            self.dash_time += dt
            # Only move during the push frames, through the normal terrain checks.
            push = min(self.dash_time, self.DASH_PUSH_END) - max(previous, self.DASH_PUSH_START)
            dx = self.facing * self.DASH_SPEED * max(0.0, push)
            if self.dash_time >= clips['dash']['duration']:
                self.dash_time = None
        if dx:
            self.facing = 1 if dx > 0 else -1
        self.moving = bool(dx)
        previous_x = self.x
        self.x += dx
        if dx and self.grounded and self.vy>=0 and self.prepare_time is None:
            ramps=slope_surfaces(self.scene,self.x,self.HALF_WIDTH)
            if ramps:
                target=min(ramps)
                clear=not any(self.overlaps_x(r) and target>r[1]+.01
                              and target-self.HEIGHT<r[3]-.01 for r in self.scene.solids)
                if abs(target-self.y)<=self.STEP_HEIGHT+.01 and clear:self.y=target
        contacts = [r for r in self.scene.solids if self.overlaps_x(r)
                    and self.y > r[1]+0.01 and self.y-self.HEIGHT < r[3]-0.01]
        if contacts:
            # Resolve adjacent stair contour columns as one supporting surface.
            step_top = min(r[1] for r in contacts)
            headroom = not any(self.overlaps_x(other) and step_top > other[1]+0.01
                              and step_top-self.HEIGHT < other[3]-0.01
                              for other in self.scene.solids)
            if self.grounded and 0 < self.y-step_top <= self.STEP_HEIGHT+.01 and headroom:
                self.y = step_top
            elif dx > 0:
                self.x = min(r[0]-self.HALF_WIDTH for r in contacts)
            elif dx < 0:
                self.x = max(r[2]+self.HALF_WIDTH for r in contacts)
            else:
                self.x = previous_x
        if dx and inside_slope(self.scene,self.x,self.y,self.HEIGHT,self.HALF_WIDTH):
            # Prevent an airborne actor entering the solid body from its side.
            # Locate the continuous surface contact instead of adding stair boxes.
            safe,blocked=previous_x,self.x
            for _ in range(16):
                middle=(safe+blocked)/2
                if inside_slope(self.scene,middle,self.y,self.HEIGHT,self.HALF_WIDTH):blocked=middle
                else:safe=middle
            self.x=safe
        self.x = max(self.HALF_WIDTH, min(self.scene.width-self.HALF_WIDTH, self.x))
        # Walk down shallow steps as grounded movement, just as step-up is
        # handled above. Jump takeoff and real ledges retain normal gravity.
        if dx and self.grounded and self.vy >= 0 and self.prepare_time is None:
            supports = [height for height in self.ground_heights()
                        if 0 <= height-self.y <= self.STEP_HEIGHT+.01]
            if supports:
                self.y = min(supports)
        old_y = self.y
        previous_grounded = self.grounded
        old_vy = self.vy
        self.vy = min(350, self.vy+self.GRAVITY*dt)
        self.y += self.vy*dt
        self.grounded = False
        for rect in self.scene.solids + self.scene.platforms:
            if not self.overlaps_x(rect):
                continue
            if self.vy >= 0 and old_y <= rect[1]+0.1 and self.y >= rect[1]:
                self.y = rect[1]
                self.vy = 0.0
                self.grounded = True
            elif rect in self.scene.solids and self.vy < 0 and old_y-self.HEIGHT >= rect[3]-0.1 and self.y-self.HEIGHT <= rect[3]:
                self.y = rect[3]+self.HEIGHT
                self.vy = 0.0
        if self.vy>=0:
            for surface in slope_surfaces(self.scene,self.x,self.HALF_WIDTH):
                if old_y<=surface+.1 and self.y>=surface:
                    self.y=surface;self.vy=0.0;self.grounded=True
        if self.grounded and not previous_grounded and old_vy > 50:
            self.land_time = 0.0
        phase = None if self.grounded else ('rise' if self.vy < -45 else 'fall' if self.vy > 45 else 'apex')
        self.air_time = self.air_time + dt if phase == self.air_phase else 0.0
        self.air_phase = phase
        if self.y > self.scene.layout["height"]+80:
            self.x, self.y = self.scene.layout['spawn']
            self.dash_time = None
            self.pickup_time = None
            self.vy = 0.0
            self.grounded = True


def get_assets(resources):
    if getattr(resources, 'dungeon', None) is None:
        resources.dungeon = DungeonAssets(getattr(resources, "map_path", None))
    return resources.dungeon
