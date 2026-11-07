import pico2d as p2d
from game.config import SCALE
from game import drawing


class SettingsScene:
    TOGGLE = (196, 160, 445, 209)
    BACK = (196, 226, 445, 275)

    def __init__(self, app, title):
        self.app, self.title = app, title

    def toggle(self):
        self.app.animation = not self.app.animation
        self.app.storage.save_settings(self.app.animation)

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN:
            if event.key == p2d.SDLK_ESCAPE:
                self.app.scene = self.title
            elif event.key in (p2d.SDLK_RETURN, p2d.SDLK_SPACE):
                self.toggle()
        elif event.type == p2d.SDL_MOUSEBUTTONDOWN and event.button == p2d.SDL_BUTTON_LEFT:
            x, y = event.x / SCALE, event.y / SCALE
            if drawing.contains(self.TOGGLE, x, y):
                self.toggle()
            elif drawing.contains(self.BACK, x, y):
                self.app.scene = self.title

    def update(self, dt):
        self.title.update(dt)

    def draw(self):
        self.app.resources.draw_title(self.title.frame)
        drawing.rectangle((152, 78, 489, 303), (17, 23, 33), filled=True)
        drawing.rectangle((152, 78, 489, 303), (159, 119, 62))
        drawing.text(self.app.resources.heading, 290, 124, "설정")
        for bounds in (self.TOGGLE, self.BACK):
            drawing.rectangle(bounds, (50, 39, 30), filled=True)
            drawing.rectangle(bounds, (159, 119, 62))
        label = "배경 애니메이션: 켜짐" if self.app.animation else "배경 애니메이션: 꺼짐"
        drawing.text(self.app.resources.normal, 208, 192, label)
        drawing.text(self.app.resources.normal, 266, 258, "돌아가기")
