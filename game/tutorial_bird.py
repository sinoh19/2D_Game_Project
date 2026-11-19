"""A cosmetic skeletal guide that hovers behind the field player."""
import math

import pico2d as p2d

from game.config import ASSETS, WINDOW_HEIGHT


class TutorialBird:
    FRAME_SIZE = 64
    FRAME_COUNT = 9
    FPS = 12
    DRAW_SCALE = .5
    FOLLOW_DISTANCE = 30
    FOLLOW_HEIGHT = 58
    FOLLOW_RATE = 7

    def __init__(self, field):
        self.field = field
        self.sheet = p2d.load_image(str(ASSETS / 'dungeon' / 'companions' / 'skeleton-bird-idle.png'))
        self.elapsed = 0.0
        self.reset()

    def target(self):
        player = self.field.player
        x = player.x - player.facing * self.FOLLOW_DISTANCE
        y = player.y - self.FOLLOW_HEIGHT
        return (max(16, min(self.field.width - 16, x)),
                max(16, min(self.field.layout['height'] - 16, y)))

    def reset(self):
        self.x, self.y = self.target()
        self.facing = self.field.player.facing

    def update(self, dt):
        dt = max(0.0, dt)
        self.elapsed += dt
        target_x, target_y = self.target()
        self.facing = self.field.player.facing
        if math.hypot(target_x - self.x, target_y - self.y) > 160:
            self.reset()
            return
        blend = 1 - math.exp(-self.FOLLOW_RATE * dt)
        self.x += (target_x - self.x) * blend
        self.y += (target_y - self.y) * blend

    def draw(self, camera):
        size = self.FRAME_SIZE * self.DRAW_SCALE
        if self.x + size / 2 < camera or self.x - size / 2 > camera + self.field.view_width:
            return
        frame = int(self.elapsed * self.FPS) % self.FRAME_COUNT
        scale = self.field.assets.scale
        self.sheet.clip_composite_draw(
            frame * self.FRAME_SIZE, 0, self.FRAME_SIZE, self.FRAME_SIZE,
            0, 'h' if self.facing < 0 else '',
            round((self.x - camera) * scale), round(WINDOW_HEIGHT - self.y * scale),
            round(size * scale), round(size * scale))
