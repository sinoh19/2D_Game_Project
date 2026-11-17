"""A one-shot ceiling spike trap placed as a Tiled object."""
import pico2d as p2d

from game import drawing
from game.config import ASSETS, SCALE, WINDOW_HEIGHT


class SpikeTrap:
    WARNING_SECONDS = .45
    FALL_SPEED = 310.0
    DAMAGE = 5

    def __init__(self, spec, solids):
        self.x = spec['x'] + spec['width'] / 2
        self.width = spec['width']
        self.height = spec['height']
        self.start_y = spec['y']
        self.y = self.start_y
        floor = min((top for left, top, right, bottom in solids
                     if left <= self.x <= right and top > self.start_y + self.height),
                    default=spec['y'] + 160)
        self.landing_y = floor - self.height
        self.state = 'idle'
        self.clock = 0.0
        self.hit = False

    def update(self, dt, player):
        if self.state == 'idle':
            if abs(player.x - self.x) <= self.width / 2 + 12 and player.y > self.start_y + self.height:
                self.state = 'warning'
                self.clock = 0.0
        elif self.state == 'warning':
            self.clock += dt
            if self.clock >= self.WARNING_SECONDS:
                self.state = 'falling'
        elif self.state == 'falling':
            self.y = min(self.landing_y, self.y + self.FALL_SPEED * dt)
            if not self.hit and self.collides(player):
                player.take_damage(self.DAMAGE)
                self.hit = True
                if self.y >= self.landing_y:
                    self.state = 'landed'
                return True
            if self.y >= self.landing_y:
                self.state = 'landed'
        elif self.state == 'landed' and not self.hit and self.collides(player):
            player.take_damage(self.DAMAGE)
            self.hit = True
            return True
        return False

    def collides(self, player):
        left, right = self.x - self.width * .38, self.x + self.width * .38
        top, bottom = self.y + self.height * .18, self.y + self.height * .65
        return (player.x + player.HALF_WIDTH > left and player.x - player.HALF_WIDTH < right
                and player.y > top and player.y - player.HEIGHT < bottom)

    def draw(self, image, camera):
        screen_x = self.x - camera
        if screen_x < -self.width or screen_x > 640 + self.width:
            return
        if self.state == 'warning' and int(self.clock * 12) % 2 == 0:
            drawing.rectangle((screen_x - self.width / 2, self.start_y,
                               screen_x + self.width / 2, self.start_y + 2),
                              (170, 53, 51), filled=True)
        image.draw(round(screen_x * SCALE),
                   round(WINDOW_HEIGHT - (self.y + self.height / 2) * SCALE),
                   round(self.width * SCALE), round(self.height * SCALE))
