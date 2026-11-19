"""Pause the current game behind a three-choice menu."""
import pico2d as p2d
from game import drawing
from game.config import SCALE


class PauseScene:
    BUTTONS = tuple((216, 119 + i * 54, 424, 161 + i * 54) for i in range(3))
    LABELS = ('메인화면', '게임 종료', '설정')

    def __init__(self, app, previous):
        self.app, self.previous = app, previous
        self.selected = 0

    def update(self, dt):
        pass

    def save(self):
        if hasattr(self.previous, 'save'):
            self.previous.save()

    def activate(self, index):
        if index == 0:
            self.save()
            self.app.show_title()
        elif index == 1:
            self.save()
            self.app.running = False
        else:
            from game.scenes.settings import SettingsScene
            self.app.scene = SettingsScene(self.app, self)

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN:
            if event.key == p2d.SDLK_ESCAPE:
                self.app.scene = self.previous
            elif event.key in (p2d.SDLK_DOWN, p2d.SDLK_s):
                self.selected = (self.selected + 1) % 3
            elif event.key in (p2d.SDLK_UP, p2d.SDLK_w):
                self.selected = (self.selected - 1) % 3
            elif event.key in (p2d.SDLK_RETURN, p2d.SDLK_SPACE):
                self.activate(self.selected)
        elif event.type in (p2d.SDL_MOUSEMOTION, p2d.SDL_MOUSEBUTTONDOWN):
            index = next((i for i, bounds in enumerate(self.BUTTONS)
                          if drawing.contains(bounds, event.x / SCALE, event.y / SCALE)), None)
            if index is not None:
                self.selected = index
                if event.type == p2d.SDL_MOUSEBUTTONDOWN and event.button == p2d.SDL_BUTTON_LEFT:
                    self.activate(index)

    def draw(self):
        self.previous.draw()
        drawing.black_overlay(.65)
        drawing.rectangle((192, 59, 448, 301), (20, 23, 34), filled=True)
        drawing.rectangle((192, 59, 448, 301), (174, 134, 81))
        label = '일시정지'
        width = self.app.resources.normal.measure(label)[0]
        drawing.text(self.app.resources.normal, 320 - width / 2, 93, label)
        for index, (bounds, label) in enumerate(zip(self.BUTTONS, self.LABELS)):
            selected = index == self.selected
            drawing.rectangle(bounds, (61, 46, 33) if selected else (29, 31, 43), filled=True)
            drawing.rectangle(bounds, (224, 189, 121) if selected else (105, 89, 69))
            width = self.app.resources.normal.measure(label)[0]
            drawing.text(self.app.resources.normal, 320 - width / 2, bounds[1] + 26, label)
        drawing.text(self.app.resources.small, 262, 285, 'ESC · 게임으로 복귀')
