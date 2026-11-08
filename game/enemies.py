"""Animated field enemies with patrol motion and combat health."""
import json
import math
from game.terrain import slope_height
from game.combat import Vitals


class Slime(Vitals):
    def __init__(self, spec, motion):
        super().__init__()
        self.x, self.y = spec['x'], spec['y']
        self.left, self.right = spec['patrolLeft'], spec['patrolRight']
        self.speed, self.scale = spec['speed'], spec['scale']
        self.facing = -1 if spec['direction'] == 'left' else 1
        self.motion = motion
        self.time = 0.0

    @property
    def frame(self):
        return int((self.time + 1e-9) * self.motion['fps']) % self.motion['frameCount']

    def surface(self, scene, x):
        step = 8 * self.scale
        heights = [t for l, t, r, b in scene.solids + scene.platforms
                   if l <= x < r and abs(t - self.y) <= step]
        heights += [h for s in scene.slopes
                    if (h := slope_height(s, x)) is not None and abs(h - self.y) <= step]
        return min(heights, key=lambda h: abs(h - self.y)) if heights else None

    def update(self, dt, scene):
        # Split at animation boundaries, so only airborne poses translate.
        remaining = max(0.0, min(1.0, dt))
        fps = self.motion['fps']
        while remaining > 1e-9:
            boundary = (math.floor((self.time + 1e-9) * fps) + 1) / fps
            step = min(remaining, 1/120, boundary - self.time)
            frame = self.motion['frames'][self.frame]
            if frame['footY'] < self.motion['pivot'][1] and self.speed:
                span = self.right-self.left
                phase = self.x-self.left if self.facing > 0 else 2*span-(self.x-self.left)
                phase = (phase+self.speed*step) % (2*span)
                target = self.left+phase if phase < span else self.right-(phase-span)
                self.facing = 1 if phase < span else -1
                direction = 1 if target > self.x else -1
                half = 12 * self.scale
                ground = self.surface(scene, target)
                toe = self.surface(scene, target + direction * half)
                blocked = ground is None or toe is None
                if not blocked:
                    blocked = any(target+half > l+.01 and target-half < r-.01
                                  and ground > t+.01 and ground-16*self.scale < b-.01
                                  for l, t, r, b in scene.solids)
                if blocked:
                    self.facing = -direction
                else:
                    self.x, self.y = target, ground
            self.time += step
            remaining -= step


class SlimeArt:
    def __init__(self, folder):
        import pico2d as p2d
        self.motion = json.loads((folder/'move.json').read_text(encoding='utf-8'))
        self.image = p2d.load_image(str(folder/self.motion['image']))
        m = self.motion
        if (self.image.w, self.image.h) != (m['frameWidth']*m['frameCount'], m['frameHeight']):
            raise ValueError('슬라임 애니메이션 시트 크기가 잘못되었습니다.')

    def draw(self, enemy, camera, world_scale, view_width):
        from game.config import WINDOW_HEIGHT
        m = self.motion
        w, h = m['frameWidth']*enemy.scale, m['frameHeight']*enemy.scale
        if enemy.x+w/2 < camera or enemy.x-w/2 > camera+view_width:
            return
        top = enemy.y-m['pivot'][1]*enemy.scale
        self.image.clip_composite_draw(
            enemy.frame*m['frameWidth'], 0, m['frameWidth'], m['frameHeight'],
            0, 'h' if enemy.facing > 0 else '',
            round((enemy.x-camera)*world_scale),
            round(WINDOW_HEIGHT-(top+h/2)*world_scale),
            round(w*world_scale), round(h*world_scale))
