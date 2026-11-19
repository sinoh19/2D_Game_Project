import pico2d as p2d
from game.config import SCALE, RESOLUTIONS
from game import drawing


class SettingsScene:
    TOGGLE = (188, 111, 452, 148)
    RESOLUTION_BUTTONS = tuple((188, 160 + i * 39, 452, 193 + i * 39)
                               for i in range(3))
    BACK = (188, 284, 452, 318)

    def __init__(self, app, previous):
        self.app, self.previous = app, previous
        self.selected = 1 + RESOLUTIONS.index(app.resolution)

    def activate(self, index):
        if index == 0:
            self.app.animation = not self.app.animation
            self.app.storage.save_settings(self.app.animation)
        elif 1 <= index <= 3:
            self.app.set_resolution(RESOLUTIONS[index - 1])
        else:
            self.app.scene = self.previous

    def handle_event(self, event):
        bounds_list = (self.TOGGLE, *self.RESOLUTION_BUTTONS, self.BACK)
        if event.type == p2d.SDL_KEYDOWN:
            if event.key == p2d.SDLK_ESCAPE:
                self.app.scene = self.previous
            elif event.key in (p2d.SDLK_DOWN, p2d.SDLK_s):
                self.selected = (self.selected + 1) % len(bounds_list)
            elif event.key in (p2d.SDLK_UP, p2d.SDLK_w):
                self.selected = (self.selected - 1) % len(bounds_list)
            elif event.key in (p2d.SDLK_RETURN, p2d.SDLK_SPACE):
                self.activate(self.selected)
        elif event.type in (p2d.SDL_MOUSEMOTION, p2d.SDL_MOUSEBUTTONDOWN):
            index = next((i for i, bounds in enumerate(bounds_list)
                          if drawing.contains(bounds, event.x / SCALE, event.y / SCALE)), None)
            if index is not None:
                self.selected = index
                if event.type == p2d.SDL_MOUSEBUTTONDOWN and event.button == p2d.SDL_BUTTON_LEFT:
                    self.activate(index)

    def update(self, dt):
        from game.scenes.title import TitleScene
        if isinstance(self.previous, TitleScene):
            self.previous.update(dt)

    def save(self):
        if hasattr(self.previous, 'save'):
            self.previous.save()

    def draw(self):
        self.previous.draw()
        drawing.black_overlay(.5)
        drawing.rectangle((168, 44, 472, 333), (17, 23, 33), filled=True)
        drawing.rectangle((168, 44, 472, 333), (159, 119, 62))
        drawing.text(self.app.resources.heading, 290, 78, '설정')
        drawing.text(self.app.resources.small, 190, 103, '화면 해상도 · 선택하면 바로 적용')
        labels = [('배경 애니메이션: 켜짐' if self.app.animation else '배경 애니메이션: 꺼짐'),
                  *(f'{w} × {h}' + ('  · 적용 중' if (w, h) == self.app.resolution else '')
                    for w, h in RESOLUTIONS), '돌아가기']
        for index, (bounds, label) in enumerate(zip((self.TOGGLE, *self.RESOLUTION_BUTTONS, self.BACK), labels)):
            active = index == self.selected
            drawing.rectangle(bounds, (50, 39, 30) if active else (27, 30, 42), filled=True)
            drawing.rectangle(bounds, (220, 180, 107) if active else (113, 91, 65))
            width = self.app.resources.small.measure(label)[0]
            drawing.text(self.app.resources.small, 320 - width / 2, bounds[1] + 22, label)
