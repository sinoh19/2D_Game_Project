"""Shared screen-space placement for movable field UI windows."""
from game import drawing
from game.config import NATIVE_HEIGHT, NATIVE_WIDTH
from game.loot_ui import panel


class DraggableWindow:
    def __init__(self, panel_bounds):
        self.panel_bounds = panel_bounds
        self.offset_x = 0
        self.offset_y = 0
        self.window_grab = None

    def bounds(self, rect):
        left, top, right, bottom = rect
        return (left + self.offset_x, top + self.offset_y,
                right + self.offset_x, bottom + self.offset_y)

    def contains(self, x, y):
        return drawing.contains(self.bounds(self.panel_bounds), x, y)

    def title_contains(self, x, y, close_bounds):
        left, top, right, _ = self.panel_bounds
        title = self.bounds((left + 1, top + 1, right - 1, top + 35))
        return (drawing.contains(title, x, y)
                and not drawing.contains(self.bounds(close_bounds), x, y))

    def begin_window_drag(self, x, y):
        self.window_grab = (x - self.offset_x, y - self.offset_y)

    def move_window(self, x, y):
        if self.window_grab is None:
            return False
        grab_x, grab_y = self.window_grab
        left, top, right, bottom = self.panel_bounds
        self.offset_x = max(-left, min(NATIVE_WIDTH - right, round(x - grab_x)))
        self.offset_y = max(-top, min(NATIVE_HEIGHT - bottom, round(y - grab_y)))
        return True

    def end_window_drag(self):
        was_dragging = self.window_grab is not None
        self.window_grab = None
        return was_dragging

    def panel(self, rect, fill, border):
        panel(self.bounds(rect), fill, border)

    def rectangle(self, rect, color, *, filled=False):
        drawing.rectangle(self.bounds(rect), color, filled=filled)

    def text(self, font, x, y, label, color=(240, 231, 207)):
        drawing.text(font, x + self.offset_x, y + self.offset_y, label, color)
