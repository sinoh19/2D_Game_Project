"""A repeating ceiling spike trap placed as a Tiled object."""

from game.config import SCALE, WINDOW_HEIGHT


class SpikeTrap:
    WARNING_SECONDS = .45
    FALL_SPEED = 310.0
    LANDED_SECONDS = .8
    SHAKE_SECONDS = .35
    RISE_SPEED = 180.0
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
            if self.y >= self.landing_y:
                self.state = 'landed'
                self.clock = 0.0
        elif self.state == 'landed':
            self.clock += dt
            if self.clock >= self.LANDED_SECONDS:
                self.state = 'shaking'
                self.clock = 0.0
        elif self.state == 'shaking':
            self.clock += dt
            if self.clock >= self.SHAKE_SECONDS:
                self.state = 'rising'
                self.clock = 0.0
        elif self.state == 'rising':
            self.clock += dt
            self.y = max(self.start_y, self.y - self.RISE_SPEED * dt)
            if self.y <= self.start_y:
                self.state = 'idle'
                self.clock = 0.0
                self.hit = False
        if self.state in ('falling', 'landed', 'shaking') and not self.hit and self.collides(player):
            player.take_damage(self.DAMAGE)
            self.hit = True
            return True
        return False

    def collides(self, player):
        left, right = self.x - self.width * .38, self.x + self.width * .38
        top, bottom = self.y + self.height * .18, self.y + self.height * .90
        return (player.x + player.HALF_WIDTH > left and player.x - player.HALF_WIDTH < right
                and player.y > top and player.y - player.HEIGHT < bottom)

    def draw(self, image, camera):
        screen_x = self.x - camera
        if screen_x < -self.width or screen_x > 640 + self.width:
            return
        shake_x = (-2, 1, 2, -1)[int(self.clock * 24) % 4] if self.state == 'shaking' else 0
        image.draw(round((screen_x + shake_x) * SCALE),
                   round(WINDOW_HEIGHT - (self.y + self.height / 2) * SCALE),
                   round(self.width * SCALE), round(self.height * SCALE))
