"""검은 화면 대화: 한 글자씩 표시하고 클릭/SPACE를 기다립니다."""
import ctypes
import json
import pico2d as p2d
from game import drawing
from game.config import (DIALOGUE_SCRIPT, DIALOGUE_CHARACTERS_PER_SECOND,
                         NATIVE_WIDTH, NATIVE_HEIGHT, SCALE)

TEXT_LEFT = 92
TEXT_WIDTH = (NATIVE_WIDTH - TEXT_LEFT * 2) * SCALE
SPEAKER_Y = 126
BODY_Y = 172
LINE_SPACING = 30


def text_width(font, text):
    if not text:
        return 0
    width, height = ctypes.c_int(), ctypes.c_int()
    if p2d.TTF_SizeUTF8(font.font, text.encode("utf-8"), ctypes.byref(width), ctypes.byref(height)) != 0:
        raise RuntimeError("대사 글자 너비를 계산하지 못했습니다.")
    return width.value * SCALE


def wrap_ranges(text, font, maximum_width=TEXT_WIDTH):
    """완성 문장 기준으로 미리 줄을 나눠 타이핑 중 줄바꿈이 바뀌지 않게 합니다."""
    ranges = []
    start = 0
    while start < len(text):
        end = start
        while end < len(text) and text_width(font, text[start:end + 1]) <= maximum_width:
            end += 1
        if end == start:
            end += 1
        if end < len(text):
            space = text.rfind(" ", start, end + 1)
            if space > start:
                end = space
        ranges.append((start, end))
        start = end
        while start < len(text) and text[start] == " ":
            start += 1
    return ranges


class DialogueScene:
    def __init__(self, app):
        self.app = app
        self.lines = json.loads(DIALOGUE_SCRIPT.read_text(encoding="utf-8-sig"))
        if not isinstance(self.lines, list) or not self.lines:
            raise ValueError("대사 파일에 하나 이상의 대사가 필요합니다.")
        for entry in self.lines:
            if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) and entry[k] for k in ("speaker", "text")):
                raise ValueError("각 대사에 speaker와 text 문자열이 필요합니다.")
        self.layouts = [wrap_ranges(line["text"], app.resources.dialogue) for line in self.lines]
        self.index = 0
        self.character_progress = 0.0
        self.finished = False

    @property
    def speaker(self):
        return self.lines[self.index]["speaker"]

    @property
    def text(self):
        return self.lines[self.index]["text"]

    @property
    def visible_count(self):
        return min(len(self.text), int(self.character_progress))

    @property
    def visible_text(self):
        return "" if self.finished else self.text[:self.visible_count]

    @property
    def fully_visible(self):
        return self.visible_count == len(self.text)

    def advance(self):
        if self.finished:
            return
        if not self.fully_visible:
            # One input completes only this sentence. A fresh input is needed
            # to advance, so a fast click never skips an unread sentence.
            self.character_progress = float(len(self.text))
        elif self.index + 1 < len(self.lines):
            self.index += 1
            self.character_progress = 0.0
        else:
            self.finished = True
            self.app.start_book()

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN:
            if event.key == p2d.SDLK_ESCAPE:
                self.app.show_title()
            elif event.key == p2d.SDLK_SPACE:
                self.advance()
        elif event.type == p2d.SDL_MOUSEBUTTONDOWN and event.button == p2d.SDL_BUTTON_LEFT:
            self.advance()

    def update(self, dt):
        if not self.finished:
            self.character_progress = min(float(len(self.text)),
                                          self.character_progress + max(0.0, dt) * DIALOGUE_CHARACTERS_PER_SECOND)
        # No time-based transition: even a fully revealed sentence waits forever
        # until a new left click or SPACE keydown arrives.

    def draw(self):
        drawing.rectangle((0, 0, NATIVE_WIDTH - 1, NATIVE_HEIGHT - 1), (0, 0, 0), filled=True)
        if self.finished:
            return
        drawing.text(self.app.resources.normal, TEXT_LEFT, SPEAKER_Y, self.speaker, (208, 178, 120))
        for row, (start, end) in enumerate(self.layouts[self.index]):
            visible = self.text[start:min(end, self.visible_count)] if self.visible_count > start else ""
            if visible:
                drawing.text(self.app.resources.dialogue, TEXT_LEFT, BODY_Y + row * LINE_SPACING,
                             visible, (238, 235, 226))
        if self.fully_visible:
            drawing.text(self.app.resources.small, TEXT_LEFT, 298, "클릭 / SPACE", (122, 122, 128))
