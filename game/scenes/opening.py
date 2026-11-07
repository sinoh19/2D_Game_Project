"""오프닝 1단계: 메인 화면의 가운데 창문으로 줌인한 뒤 암전."""
import math
import pico2d as p2d
from game import drawing
from game.config import (NATIVE_WIDTH, NATIVE_HEIGHT, OPENING_WINDOW,
                         OPENING_DURATION, OPENING_FADE_START, OPENING_MAX_ZOOM,
                         OPENING_DIALOGUE_DELAY)


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


class OpeningScene:
    def __init__(self, app, background_time=0.0):
        self.app = app
        self.background_time = background_time
        self.elapsed = 0.0
        self.black_elapsed = 0.0

    @property
    def finished(self):
        return self.elapsed >= OPENING_DURATION

    @property
    def phase(self):
        if self.finished:
            return "black"
        return "fade" if self.elapsed >= OPENING_FADE_START else "zoom"

    @property
    def camera(self):
        progress = smoothstep(self.elapsed / OPENING_DURATION)
        zoom = math.exp(math.log(OPENING_MAX_ZOOM) * progress)
        focus_x, focus_y = OPENING_WINDOW
        # Move the target window smoothly from its original position to the
        # screen center. Compensating for zoom keeps it inside the viewport.
        camera_x = focus_x + (NATIVE_WIDTH / 2 - focus_x) * (1 - progress) / zoom
        camera_y = focus_y + (NATIVE_HEIGHT / 2 - focus_y) * (1 - progress) / zoom
        return zoom, (camera_x, camera_y)

    @property
    def darkness(self):
        return smoothstep((self.elapsed - OPENING_FADE_START) /
                          (OPENING_DURATION - OPENING_FADE_START))

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN and event.key == p2d.SDLK_ESCAPE:
            self.app.show_title()

    def update(self, dt):
        dt = max(0.0, dt)
        if self.finished:
            self.black_elapsed += dt
            if self.black_elapsed >= OPENING_DIALOGUE_DELAY:
                self.app.start_dialogue()
            return
        self.elapsed = min(OPENING_DURATION, self.elapsed + dt)
        if self.app.animation:
            self.background_time += dt

    def draw(self):
        if self.finished:
            # Hold a short fully black beat before the dialogue begins.
            drawing.rectangle((0, 0, NATIVE_WIDTH - 1, NATIVE_HEIGHT - 1),
                              (0, 0, 0), filled=True)
            return
        resources = self.app.resources
        frame = int(self.background_time * resources.fps) % resources.frames if self.app.animation else 0
        zoom, camera = self.camera
        resources.draw_title(frame, zoom=zoom, camera=camera)
        drawing.black_overlay(self.darkness)
