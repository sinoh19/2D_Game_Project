"""책을 펼치는 도중 타일 전환을 겹쳐 필드에 진입."""
import pico2d as p2d
from game import drawing
from game.config import BOOK_FADE_IN_SECONDS, BOOK_CLOSED_HOLD_SECONDS, BOOK_TRANSITION_PROGRESS
from game.scenes.opening import smoothstep


class BookScene:
    def __init__(self, app):
        self.app = app
        app.resources.load_book()
        self.animation = app.resources.book_animation
        self.elapsed = 0.0
        self.opening_start = BOOK_FADE_IN_SECONDS + BOOK_CLOSED_HOLD_SECONDS
        self.duration = self.opening_start + (self.animation["frameCount"] - 1) / self.animation["fps"]

    @property
    def frame(self):
        time = max(0.0, self.elapsed - self.opening_start)
        return min(self.animation["frameCount"] - 1, int(time * self.animation["fps"] + 1e-8))

    @property
    def phase(self):
        if self.elapsed < BOOK_FADE_IN_SECONDS:
            return "fade_in"
        if self.elapsed < self.opening_start:
            return "closed"
        if self.elapsed < self.duration:
            return "opening"
        return "open"

    @property
    def transition_start(self):
        return self.opening_start + (self.duration - self.opening_start) * BOOK_TRANSITION_PROGRESS

    def advance_animation(self, dt):
        self.elapsed = min(self.duration, self.elapsed + max(0.0, dt))

    def update(self, dt):
        next_time = self.elapsed + max(0.0, dt)
        self.elapsed = min(self.transition_start, next_time)
        if next_time >= self.transition_start:
            self.app.start_book_to_field(self)
            self.app.scene.update(next_time - self.transition_start)

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN and event.key == p2d.SDLK_ESCAPE:
            self.app.show_title()

    def draw(self):
        self.app.resources.draw_book(self.frame)
        if self.phase == "fade_in":
            drawing.black_overlay(1 - smoothstep(self.elapsed / BOOK_FADE_IN_SECONDS))
