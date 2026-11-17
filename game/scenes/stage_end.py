"""Black placeholder screen after leaving the tutorial stage."""
import pico2d as p2d

from game import drawing
from game.config import NATIVE_WIDTH, NATIVE_HEIGHT


class StageEndScene:
    def __init__(self, app):
        self.app = app

    def update(self, dt):
        pass

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN and event.key == p2d.SDLK_ESCAPE:
            self.app.show_title()

    def draw(self):
        drawing.rectangle((0, 0, NATIVE_WIDTH - 1, NATIVE_HEIGHT - 1),
                          (0, 0, 0), filled=True)
