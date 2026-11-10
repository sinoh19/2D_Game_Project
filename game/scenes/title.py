import pico2d as p2d
from game.config import DEBUG_SKIP_ENABLED, MENU_BUTTONS, SCALE
from game import drawing

DEBUG_MELEE_BOUNDS = (416, 8, 528, 29)


class TitleScene:
    def __init__(self, app):
        self.app = app
        self.elapsed = 0.0
        self.selected = None
        self.notice = ""
        self.notice_time = 0.0
        self.debug_melee_hovered = False

    @property
    def frame(self):
        return int(self.elapsed * self.app.resources.fps) % self.app.resources.frames if self.app.animation else 0

    def update(self, dt):
        if self.app.animation:
            self.elapsed += dt
        self.notice_time = max(0.0, self.notice_time - dt)

    def activate(self, index):
        if index == 0:
            self.app.start_opening(self.elapsed)
        elif index == 1:
            position = self.app.storage.load_position()
            if position is None:
                self.notice, self.notice_time = "저장된 게임이 없습니다.", 2.5
            else:
                self.app.start_field(position)
        elif index == 2:
            from game.scenes.settings import SettingsScene
            self.app.scene = SettingsScene(self.app, self)
        elif index == 3:
            self.app.running = False

    def handle_event(self, event):
        if event.type in (p2d.SDL_MOUSEMOTION, p2d.SDL_MOUSEBUTTONDOWN):
            x, y = event.x / SCALE, event.y / SCALE
            self.debug_melee_hovered = DEBUG_SKIP_ENABLED and drawing.contains(DEBUG_MELEE_BOUNDS, x, y)
            if (self.debug_melee_hovered and event.type == p2d.SDL_MOUSEBUTTONDOWN
                    and event.button == p2d.SDL_BUTTON_LEFT):
                self.app.start_debug_melee()
                return
            self.selected = next((i for i, bounds in enumerate(MENU_BUTTONS) if drawing.contains(bounds, x, y)), None)
            if event.type == p2d.SDL_MOUSEBUTTONDOWN and event.button == p2d.SDL_BUTTON_LEFT and self.selected is not None:
                self.activate(self.selected)
        elif event.type == p2d.SDL_KEYDOWN:
            if event.key in (p2d.SDLK_DOWN, p2d.SDLK_s):
                self.selected = 0 if self.selected is None else (self.selected + 1) % 4
            elif event.key in (p2d.SDLK_UP, p2d.SDLK_w):
                self.selected = 3 if self.selected is None else (self.selected - 1) % 4
            elif event.key in (p2d.SDLK_RETURN, p2d.SDLK_SPACE):
                self.activate(0 if self.selected is None else self.selected)
            elif event.key == p2d.SDLK_ESCAPE:
                self.app.running = False

    def draw(self):
        self.app.resources.draw_title(self.frame)
        self.app.resources.draw_menu()
        if DEBUG_SKIP_ENABLED:
            bounds = DEBUG_MELEE_BOUNDS
            color = (52, 61, 68) if self.debug_melee_hovered else (25, 30, 37)
            drawing.rectangle(bounds, color, filled=True)
            drawing.rectangle(bounds, (149, 137, 108))
            drawing.text(self.app.resources.small, bounds[0] + 8, bounds[1] + 15,
                         '디버그: 근접 전투', (224, 216, 190))
        if self.selected is not None:
            left, top, right, bottom = MENU_BUTTONS[self.selected]
            drawing.rectangle((left - 1, top - 1, right + 1, bottom + 1), (255, 221, 143))
        if self.notice_time > 0:
            drawing.rectangle((108, 314, 433, 351), (15, 20, 30), filled=True)
            drawing.text(self.app.resources.small, 132, 338, self.notice)
