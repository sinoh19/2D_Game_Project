"""Animated field enemies with patrol motion and combat health."""
import json
import math
from random import randint
from game.terrain import slope_height
from game.combat import Vitals, apply_strength


class Slime(Vitals):
    def __init__(self, spec, motion):
        super().__init__(max_hp=20)
        self.strength = randint(0, 20)
        self.x, self.y = spec['x'], spec['y']
        self.left, self.right = spec['patrolLeft'], spec['patrolRight']
        self.speed, self.scale = spec['speed'], spec['scale']
        self.facing = -1 if spec['direction'] == 'left' else 1
        self.motion = motion
        self.time = 0.0

    def roll_damage(self):
        return apply_strength(randint(1, 5), self.strength)

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
    ATTACK_FPS = 16
    ATTACK_FRAMES = 9
    ATTACK_DURATION = ATTACK_FRAMES / ATTACK_FPS
    HIT_FPS = 12
    HIT_FRAMES = 5
    HIT_DURATION = HIT_FRAMES / HIT_FPS
    HIT_TINT_SECONDS = 2 / HIT_FPS

    def __init__(self, folder):
        import pico2d as p2d
        self.motion = json.loads((folder/'move.json').read_text(encoding='utf-8'))
        self.image = p2d.load_image(str(folder/self.motion['image']))
        self.hit_image = p2d.load_image(str(folder/'hit.png'))
        self.attack_image = p2d.load_image(str(folder/'attack.png'))
        m = self.motion
        if (self.attack_image.w, self.attack_image.h) != (m['frameWidth'] * self.ATTACK_FRAMES, m['frameHeight']):
            raise ValueError('슬라임 공격 시트 크기가 잘못되었습니다.')
        if (self.hit_image.w, self.hit_image.h) != (m['frameWidth']*self.HIT_FRAMES, m['frameHeight']):
            raise ValueError('슬라임 피격 시트 크기가 잘못되었습니다.')
        if (self.image.w, self.image.h) != (m['frameWidth']*m['frameCount'], m['frameHeight']):
            raise ValueError('슬라임 애니메이션 시트 크기가 잘못되었습니다.')

    def draw(self, enemy, camera, world_scale, view_width, *, hit_elapsed=None, hit_facing=None,
             attack_elapsed=None, guarded=False):
        import pico2d as p2d
        from game.config import WINDOW_HEIGHT
        m = self.motion
        w, h = m['frameWidth']*enemy.scale, m['frameHeight']*enemy.scale
        if enemy.x+w/2 < camera or enemy.x-w/2 > camera+view_width:
            return
        top = enemy.y-m['pivot'][1]*enemy.scale
        image, frame, facing = self.image, enemy.frame, enemy.facing
        if hit_elapsed is not None:
            image = self.hit_image
            frame = min(self.HIT_FRAMES - 1, int(hit_elapsed * self.HIT_FPS))
            if hit_facing is not None:
                facing = hit_facing
        elif attack_elapsed is not None:
            image = self.attack_image
            frame = min(self.ATTACK_FRAMES - 1, int(attack_elapsed * self.ATTACK_FPS))
        tint_seconds = .12 if guarded else self.HIT_TINT_SECONDS
        tinted = hit_elapsed is not None and 0 <= hit_elapsed < tint_seconds
        if tinted:
            tint = (100, 105, 255) if guarded else (255, 64, 55)
            p2d.SDL_SetTextureColorMod(image.texture, *tint)
        try:
            image.clip_composite_draw(
                frame*m['frameWidth'], 0, m['frameWidth'], m['frameHeight'],
                0, 'h' if facing > 0 else '',
                round((enemy.x-camera)*world_scale),
                round(WINDOW_HEIGHT-(top+h/2)*world_scale),
                round(w*world_scale), round(h*world_scale))
        finally:
            if tinted:
                p2d.SDL_SetTextureColorMod(image.texture, 255, 255, 255)
