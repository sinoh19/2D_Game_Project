"""Fade from the frozen battle screen back to the field or title."""

from game import drawing
from game.config import NATIVE_HEIGHT, NATIVE_WIDTH

FADE_OUT_SECONDS = .32
BLACK_SECONDS = .06
FADE_IN_SECONDS = .32


class MeleeExitScene:
    def __init__(self, app, source, destination):
        self.app = app
        self.source = source
        self.destination = destination
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed += max(0.0, dt)
        if self.elapsed >= FADE_OUT_SECONDS + BLACK_SECONDS + FADE_IN_SECONDS:
            self.app.scene = self.destination

    def save(self):
        self.source.save()

    def handle_event(self, event):
        pass

    def draw(self):
        if self.elapsed < FADE_OUT_SECONDS:
            self.source.draw()
            drawing.black_overlay(self.elapsed / FADE_OUT_SECONDS)
        elif self.elapsed < FADE_OUT_SECONDS + BLACK_SECONDS:
            drawing.rectangle((0, 0, NATIVE_WIDTH - 1, NATIVE_HEIGHT - 1),
                              (0, 0, 0), filled=True)
        else:
            self.destination.draw()
            progress = (self.elapsed - FADE_OUT_SECONDS - BLACK_SECONDS) / FADE_IN_SECONDS
            drawing.black_overlay(1 - progress)
