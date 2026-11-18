"""Animated field enemies with patrol motion and combat health."""
import json
import math
from random import randint
from game.terrain import slope_height
from game.combat import Vitals, apply_strength, roll_critical_damage


def segment_box_time(x1, y1, x2, y2, box):
    """First contact of a moving point with an axis-aligned box, or None."""
    near, far = 0.0, 1.0
    for start, distance, low, high in ((x1, x2-x1, box[0], box[2]),
                                       (y1, y2-y1, box[1], box[3])):
        if abs(distance) < 1e-9:
            if start < low or start > high:
                return None
            continue
        a, b = (low-start)/distance, (high-start)/distance
        near, far = max(near, min(a, b)), min(far, max(a, b))
        if near > far:
            return None
    return near


class Slime(Vitals):
    melee_name = '슬라임'
    melee_damage_type = 'physical'
    melee_home_x = 425
    melee_impact_time = .42
    melee_attack_duration = 1.40

    def __init__(self, spec, motion):
        super().__init__(max_hp=20)
        self.strength = randint(0, 20)
        self.agility = randint(20, 40)
        self.intelligence = 0
        self.luck = randint(0, 5)
        self.x, self.y = spec['x'], spec['y']
        self.left, self.right = spec['patrolLeft'], spec['patrolRight']
        self.speed, self.scale = spec['speed'], spec['scale']
        self.facing = -1 if spec['direction'] == 'left' else 1
        self.motion = motion
        self.time = 0.0

    def roll_damage(self):
        damage = apply_strength(randint(1, 5), self.strength)
        return roll_critical_damage(damage, self.luck, base_chance=4)

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
    DEATH_FPS = 12
    DEATH_FRAMES = 10
    DEATH_DURATION = (DEATH_FRAMES - 1) / DEATH_FPS

    def __init__(self, folder):
        import pico2d as p2d
        self.motion = json.loads((folder/'move.json').read_text(encoding='utf-8'))
        self.image = p2d.load_image(str(folder/self.motion['image']))
        self.hit_image = p2d.load_image(str(folder/'hit.png'))
        self.attack_image = p2d.load_image(str(folder/'attack.png'))
        self.death_image = p2d.load_image(str(folder/'death.png'))
        m = self.motion
        if (self.death_image.w, self.death_image.h) != (m['frameWidth'] * self.DEATH_FRAMES, m['frameHeight']):
            raise ValueError('슬라임 사망 시트 크기가 잘못되었습니다.')
        if (self.attack_image.w, self.attack_image.h) != (m['frameWidth'] * self.ATTACK_FRAMES, m['frameHeight']):
            raise ValueError('슬라임 공격 시트 크기가 잘못되었습니다.')
        if (self.hit_image.w, self.hit_image.h) != (m['frameWidth']*self.HIT_FRAMES, m['frameHeight']):
            raise ValueError('슬라임 피격 시트 크기가 잘못되었습니다.')
        if (self.image.w, self.image.h) != (m['frameWidth']*m['frameCount'], m['frameHeight']):
            raise ValueError('슬라임 애니메이션 시트 크기가 잘못되었습니다.')

    def draw(self, enemy, camera, world_scale, view_width, *, hit_elapsed=None, hit_facing=None,
             attack_elapsed=None, death_elapsed=None, guarded=False, alpha=255):
        import pico2d as p2d
        from game.config import WINDOW_HEIGHT
        m = self.motion
        w, h = m['frameWidth']*enemy.scale, m['frameHeight']*enemy.scale
        if enemy.x+w/2 < camera or enemy.x-w/2 > camera+view_width:
            return
        top = enemy.y-m['pivot'][1]*enemy.scale
        image, frame, facing = self.image, enemy.frame, enemy.facing
        if death_elapsed is not None:
            image = self.death_image
            frame = min(self.DEATH_FRAMES - 1, int(death_elapsed * self.DEATH_FPS))
        elif hit_elapsed is not None:
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
        if alpha != 255:
            p2d.SDL_SetTextureAlphaMod(image.texture, alpha)
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
            if alpha != 255:
                p2d.SDL_SetTextureAlphaMod(image.texture, 255)


class Lich(Vitals):
    """Floating patrol that charges and fires when the player enters range."""

    melee_name = '리치'
    melee_damage_type = 'magic'
    melee_home_x = 425
    melee_impact_time = 1.50
    melee_attack_duration = 2.05

    ATTACK_RANGE = 200
    CAST_FPS = 12
    CAST_FRAMES = 13
    CAST_DURATION = CAST_FRAMES / CAST_FPS
    ATTACK_COOLDOWN = 2.2

    def __init__(self, spec):
        super().__init__(max_hp=35)
        self.x, self.y = spec['x'], spec['y']
        self.left, self.right = spec['patrolLeft'], spec['patrolRight']
        self.speed = spec['speed']
        self.move_distance = spec['moveDistance']
        self.move_pause = spec['movePause']
        self.turn_pause = spec['turnPause']
        self.width, self.height = spec['width'], spec['height']
        self.facing = -1 if spec['direction'] == 'left' else 1
        self.time = 0.0
        self.distance_left = self.move_distance
        self.pause_left = 0.0
        self.cast_elapsed = None
        self.attack_cooldown = 0.0
        self.aim = None

    @property
    def frame(self):
        return int(self.time * 10) % 16

    def roll_damage(self):
        return LichProjectile.DAMAGE, False

    def sees_player(self, scene):
        player = scene.player
        dx = player.x - self.x
        if (player.hp <= 0 or abs(dx) > self.ATTACK_RANGE
                or abs(player.y - self.y) > 64):
            return False
        muzzle_x = self.x + (28 if dx > 0 else -28)
        muzzle_y = self.y - 48
        target_y = player.y - player.HEIGHT / 2
        return not any(segment_box_time(muzzle_x, muzzle_y, player.x, target_y, rect)
                       is not None for rect in scene.solids)

    def update(self, dt, scene=None):
        dt = max(0.0, dt)
        self.time += dt
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        if self.cast_elapsed is not None:
            self.cast_elapsed += dt
            if self.cast_elapsed >= self.CAST_DURATION:
                self.cast_elapsed = None
                self.attack_cooldown = self.ATTACK_COOLDOWN
                return LichProjectile(self, *self.aim)
            return None
        if scene is not None and self.sees_player(scene):
            self.facing = 1 if scene.player.x > self.x else -1
            if self.attack_cooldown == 0:
                self.aim = (scene.player.x, scene.player.y - scene.player.HEIGHT / 2)
                self.cast_elapsed = 0.0
            return None
        if not self.speed:
            return None
        while dt > 1e-9:
            if self.pause_left > 0:
                step = min(dt, self.pause_left)
                self.pause_left -= step
                dt -= step
                continue
            edge = self.right if self.facing > 0 else self.left
            to_edge = max(0.0, (edge - self.x) * self.facing)
            if to_edge <= 1e-9:
                self.facing *= -1
                self.distance_left = self.move_distance
                self.pause_left = self.turn_pause
                continue
            step = min(dt, self.distance_left / self.speed, to_edge / self.speed)
            traveled = self.speed * step
            self.x += self.facing * traveled
            self.distance_left -= traveled
            dt -= step
            if abs(self.x - edge) <= 1e-8:
                self.x = edge
                self.facing *= -1
                self.distance_left = self.move_distance
                self.pause_left = self.turn_pause
            elif self.distance_left <= 1e-8:
                self.distance_left = self.move_distance
                self.pause_left = self.move_pause
        return None


class LichProjectile:
    SPEED = 190.0
    RANGE = 260.0
    DAMAGE = 6
    HALF_WIDTH = 7
    HALF_HEIGHT = 5

    def __init__(self, lich, target_x, target_y):
        self.owner = lich
        self.facing = lich.facing
        self.x = lich.x + self.facing * 28
        self.y = lich.y - 48
        dx = target_x - self.x
        if dx * self.facing <= 0:
            dx = self.facing * 80
        dy = target_y - self.y
        length = math.hypot(dx, dy)
        self.vx = self.SPEED * dx / length
        self.vy = self.SPEED * dy / length
        self.distance = 0.0
        self.age = 0.0

    @property
    def draw_angle(self):
        # Game coordinates grow downward; pico2d angles grow counterclockwise.
        # Each sprite faces its own horizontal travel direction before rotation.
        return -self.facing * math.atan2(self.vy, abs(self.vx))

    def update(self, dt, scene):
        if self.distance >= self.RANGE:
            scene.lich_impacts.append(LichImpact(self.x, self.y))
            return False
        time_to_range = (self.RANGE-self.distance)/self.SPEED
        dt = min(max(0.0, dt), time_to_range)
        reached_range = dt >= time_to_range
        end_x, end_y = self.x + self.vx*dt, self.y + self.vy*dt
        obstacles = (segment_box_time(self.x, self.y, end_x, end_y,
                                     (left-self.HALF_WIDTH, top-self.HALF_HEIGHT,
                                      right+self.HALF_WIDTH, bottom+self.HALF_HEIGHT))
                     for left, top, right, bottom in scene.projectile_obstacles(self.owner))
        obstacle_hit = min((hit for hit in obstacles if hit is not None), default=None)
        player = scene.player
        player_hit = None
        if player.hp > 0:
            player_hit = segment_box_time(
                self.x, self.y, end_x, end_y,
                (player.x-player.HALF_WIDTH-self.HALF_WIDTH,
                 player.y-player.HEIGHT-self.HALF_HEIGHT,
                 player.x+player.HALF_WIDTH+self.HALF_WIDTH,
                 player.y+self.HALF_HEIGHT))
        if player_hit is not None and (obstacle_hit is None or player_hit < obstacle_hit):
            scene.lich_impacts.append(LichImpact(
                self.x + (end_x - self.x) * player_hit,
                self.y + (end_y - self.y) * player_hit))
            player.take_damage(self.DAMAGE, damage_type='magic')
            scene.trap_hit_time = .30
            if scene.encounter is None:
                scene.encounter = (self.owner, 'lich_projectile')
                scene.keys.clear()
                scene.app.start_melee(scene, self.owner, 'lich_projectile')
            return False
        if obstacle_hit is not None:
            scene.lich_impacts.append(LichImpact(
                self.x + (end_x - self.x) * obstacle_hit,
                self.y + (end_y - self.y) * obstacle_hit))
            return False
        self.x, self.y = end_x, end_y
        self.distance += self.SPEED * dt
        self.age += dt
        if reached_range:
            scene.lich_impacts.append(LichImpact(self.x, self.y))
            return False
        return True


class LichImpact:
    DURATION = .22

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed += dt
        return self.elapsed < self.DURATION


class LichArt:
    FRAME_WIDTH = 48
    FRAME_HEIGHT = 64
    FRAME_COUNT = 16
    DEATH_FRAME_COUNT = 9
    DEATH_FPS = 12
    DEATH_DURATION = (DEATH_FRAME_COUNT - 1) / DEATH_FPS
    CAST_WIDTH = 72
    CAST_FRAMES = 13
    PROJECTILE_WIDTH = 28
    PROJECTILE_HEIGHT = 14
    PROJECTILE_FRAMES = 9
    # Lift the lich's midtones so its silhouette survives the field's dark overlay.
    PALETTE = (
        (26, 27, 34), (43, 45, 53), (60, 64, 73), (80, 86, 97),
        (103, 111, 122), (129, 138, 151), (158, 167, 178),
        (48, 35, 54), (72, 52, 77), (97, 70, 100), (126, 91, 129),
        (155, 117, 153), (184, 171, 165), (212, 202, 192),
        (63, 103, 125), (105, 166, 184), (111, 235, 239),
    )
    PROJECTILE_PALETTE = PALETTE + ((181, 114, 194), (161, 237, 241), (222, 247, 248))

    def __init__(self, folder):
        import pico2d as p2d
        from game.pixel_style import simplify

        source = p2d.load_image(str(folder / 'hover.png'))
        if (source.w, source.h) != (self.FRAME_WIDTH * self.FRAME_COUNT, self.FRAME_HEIGHT):
            raise ValueError('리치 이동 시트 크기가 잘못되었습니다.')
        self.image = simplify(source, block=2, palette=self.PALETTE)
        cast = p2d.load_image(str(folder / 'cast.png'))
        if (cast.w, cast.h) != (self.CAST_WIDTH * self.CAST_FRAMES, self.FRAME_HEIGHT):
            raise ValueError('리치 공격 시트 크기가 잘못되었습니다.')
        self.cast_image = simplify(cast, block=2, palette=self.PALETTE)
        # The original PixelLab frames retain the purple staff crystal that
        # becomes gray in the reduced field sheet.
        self.melee_frames = [p2d.load_image(str(path)) for path in
                             sorted((folder / 'source_frames').glob('frame-*.png'))]
        self.melee_death_frames = [p2d.load_image(str(path)) for path in
                                   sorted((folder / 'death_source_frames').glob('frame-*.png'))]
        self.melee_cast_frames = [p2d.load_image(str(path)) for path in
                                  sorted((folder / 'cast_source_frames').glob('frame-*.png'))]
        self.melee_projectile_frames = [p2d.load_image(str(path)) for path in
                                        sorted((folder / 'projectile_source_frames').glob('frame-*.png'))]
        if (len(self.melee_frames), len(self.melee_cast_frames),
                len(self.melee_projectile_frames)) != (9, self.CAST_FRAMES, self.PROJECTILE_FRAMES):
            raise ValueError('리치 원본 애니메이션 프레임 수가 잘못되었습니다.')
        if (len(self.melee_death_frames) != self.DEATH_FRAME_COUNT
                or any((frame.w, frame.h) != (128, 171) for frame in self.melee_death_frames)):
            raise ValueError('리치 사망 애니메이션 프레임 크기 또는 수가 잘못되었습니다.')
        projectile = p2d.load_image(str(folder / 'projectile.png'))
        if (projectile.w, projectile.h) != (self.PROJECTILE_WIDTH * self.PROJECTILE_FRAMES,
                                           self.PROJECTILE_HEIGHT):
            raise ValueError('리치 투사체 시트 크기가 잘못되었습니다.')
        self.projectile_image = simplify(projectile, block=2, palette=self.PROJECTILE_PALETTE)
        left_projectile = p2d.load_image(str(folder / 'projectile-left.png'))
        if (left_projectile.w, left_projectile.h) != (projectile.w, projectile.h):
            raise ValueError('리치 왼쪽 투사체 시트 크기가 잘못되었습니다.')
        self.projectile_left_image = simplify(left_projectile, block=2,
                                              palette=self.PROJECTILE_PALETTE)
        self.impact_image = simplify(
            p2d.load_image(str(folder / 'impact-concept.png')),
            block=32, palette=self.PROJECTILE_PALETTE)

    def draw(self, lich, camera, world_scale, view_width):
        from game.config import WINDOW_HEIGHT

        if lich.x + self.CAST_WIDTH < camera or lich.x - self.CAST_WIDTH > camera + view_width:
            return
        bob = round(2 * math.sin(lich.time * 2 * math.pi * 10 / self.FRAME_COUNT))
        center_y = lich.y - 8 - bob - lich.height / 2
        casting = lich.cast_elapsed is not None
        # The final source frames contain a horizontal bolt. Hold the charged
        # orb until the direction-aware projectile draws the release.
        frame = min(self.CAST_FRAMES-3, int(lich.cast_elapsed * Lich.CAST_FPS)) if casting else lich.frame
        width = self.CAST_WIDTH if casting else self.FRAME_WIDTH
        image = self.cast_image if casting else self.image
        center_x = lich.x + 12 * lich.facing if casting else lich.x
        image.clip_composite_draw(
            frame * width, 0, width, self.FRAME_HEIGHT,
            0, 'h' if lich.facing > 0 else '',
            round((center_x - camera) * world_scale),
            round((WINDOW_HEIGHT - center_y * world_scale)),
            round(width * world_scale), round(lich.height * world_scale))

    def draw_projectile(self, projectile, camera, world_scale, view_width, *,
                        melee_detail=False, size_scale=1.0):
        from game.config import WINDOW_HEIGHT

        if projectile.x + 16 < camera or projectile.x - 16 > camera + view_width:
            return
        frame = int(projectile.age * 12) % self.PROJECTILE_FRAMES
        if melee_detail:
            image = self.melee_projectile_frames[frame]
            source_x, source_width, source_height = 0, image.w, image.h
            flip = 'h' if projectile.facing < 0 else ''
        else:
            image = self.projectile_image if projectile.facing > 0 else self.projectile_left_image
            source_x, source_width, source_height = frame * self.PROJECTILE_WIDTH, self.PROJECTILE_WIDTH, self.PROJECTILE_HEIGHT
            flip = ''
        image.clip_composite_draw(
            source_x, 0, source_width, source_height,
            projectile.draw_angle, flip,
            round((projectile.x-camera) * world_scale),
            round(WINDOW_HEIGHT-projectile.y * world_scale),
            round(self.PROJECTILE_WIDTH * world_scale * size_scale),
            round(self.PROJECTILE_HEIGHT * world_scale * size_scale))

    def draw_impact(self, impact, camera, world_scale, view_width):
        import pico2d as p2d
        from game.config import WINDOW_HEIGHT

        if impact.x + 24 < camera or impact.x - 24 > camera + view_width:
            return
        progress = min(1.0, impact.elapsed / impact.DURATION)
        size = 0.8 + 0.3 * progress
        image = self.impact_image
        p2d.SDL_SetTextureAlphaMod(image.texture, round(255 * (1 - progress) ** 1.5))
        try:
            image.draw(round((impact.x - camera) * world_scale),
                       round(WINDOW_HEIGHT - impact.y * world_scale),
                       round(72 * size * world_scale), round(48 * size * world_scale))
        finally:
            p2d.SDL_SetTextureAlphaMod(image.texture, 255)
