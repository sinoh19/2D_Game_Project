import json
import os
from pathlib import Path
import pico2d as p2d
from game.pixel_font import PixelFont
from game.config import (ASSETS, NATIVE_WIDTH, NATIVE_HEIGHT, WINDOW_WIDTH,
                         WINDOW_HEIGHT, SCALE, MENU_BUTTONS, MENU_IMAGE_FILES, DIALOGUE_FONT_SIZE)


class Resources:
    def __init__(self):
        self.background_sheet = p2d.load_image(str(ASSETS / "title" / "background_sheet.png"))
        self.menu_images = [p2d.load_image(str(ASSETS / "ui" / name)) for name in MENU_IMAGE_FILES]
        self.book_sheet = None
        self.book_animation = None
        self.dungeon = None
        self.animation = json.loads((ASSETS / "title" / "animation.json").read_text(encoding="utf-8-sig"))
        self.frames = self.animation["frameCount"]
        self.fps = self.animation["fps"]
        self.columns = self.animation["sheetColumns"]
        rows = (self.frames + self.columns - 1) // self.columns
        expected = (self.columns * NATIVE_WIDTH, rows * NATIVE_HEIGHT)
        if (self.background_sheet.w, self.background_sheet.h) != expected:
            raise ValueError("배경 애니메이션 시트 크기가 올바르지 않습니다. assets/title을 확인하세요.")
        if len(self.menu_images) != len(MENU_BUTTONS):
            raise ValueError("메뉴 이미지와 클릭 영역 개수가 일치하지 않습니다.")
        font_candidates = [ASSETS / "fonts" / "NotoSansKR-Regular.ttf",
                           Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "malgun.ttf",
                           Path(os.environ["PICO2D_DATA_PATH"]) / "ConsolaMalgun.TTF"]
        font_path = next((p for p in font_candidates if p.is_file()), None)
        if font_path is None:
            raise FileNotFoundError("한글 폰트를 찾지 못했습니다. assets/fonts에 NotoSansKR-Regular.ttf를 넣어주세요.")
        self.small = PixelFont(font_path, 10)
        self.normal = PixelFont(font_path, 15)
        self.heading = PixelFont(font_path, 20)
        self.dialogue = PixelFont(font_path, DIALOGUE_FONT_SIZE)

    def draw_title(self, frame, zoom=1.0, camera=None):
        """UI가 없는 오두막/숲 배경 레이어만 그립니다."""
        frame %= self.frames
        column, row = frame % self.columns, frame // self.columns
        bottom = self.background_sheet.h - (row + 1) * NATIVE_HEIGHT
        camera_x, camera_y = camera or (NATIVE_WIDTH / 2, NATIVE_HEIGHT / 2)
        center_x = round(NATIVE_WIDTH / 2 + (NATIVE_WIDTH / 2 - camera_x) * zoom) * SCALE
        center_y = round(NATIVE_HEIGHT / 2 + (camera_y - NATIVE_HEIGHT / 2) * zoom) * SCALE
        self.background_sheet.clip_draw(column * NATIVE_WIDTH, bottom, NATIVE_WIDTH, NATIVE_HEIGHT,
                                        center_x, center_y, round(NATIVE_WIDTH * zoom) * SCALE, round(NATIVE_HEIGHT * zoom) * SCALE)

    def draw_menu(self, bounds=MENU_BUTTONS):
        """투명 PNG 버튼을 배경 위에 따로 그립니다. bounds는 클릭 영역과 같습니다."""
        for image, (left, top, right, bottom) in zip(self.menu_images, bounds):
            center_x = (left + right + 1) / 2
            center_y = NATIVE_HEIGHT - (top + bottom + 1) / 2
            image.draw(center_x * SCALE, center_y * SCALE, image.w * SCALE, image.h * SCALE)

    def load_book(self):
        if self.book_sheet is not None:
            return
        self.book_animation = json.loads((ASSETS / "book" / "opening.json").read_text(encoding="utf-8-sig"))
        self.book_sheet = p2d.load_image(str(ASSETS / "book" / "opening_sheet.png"))
        data = self.book_animation
        expected = (data["width"] * data["sheetColumns"], data["height"] * data["sheetRows"])
        if (self.book_sheet.w, self.book_sheet.h) != expected:
            raise ValueError("책 펼침 시트 크기가 올바르지 않습니다.")

    def draw_book(self, frame):
        self.load_book()
        data = self.book_animation
        frame = max(0, min(data["frameCount"] - 1, frame))
        column, row = frame % data["sheetColumns"], frame // data["sheetColumns"]
        bottom = self.book_sheet.h - (row + 1) * data["height"]
        self.book_sheet.clip_draw(column * data["width"], bottom, data["width"], data["height"],
                                  WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, WINDOW_WIDTH, WINDOW_HEIGHT)

    def close(self):
        for name in ("small", "normal", "heading", "dialogue"):
            font = getattr(self, name, None)
            if font is not None:
                font.close()
        self.background_sheet = self.small = self.normal = self.heading = self.dialogue = None
        self.menu_images.clear()
        self.dungeon = None
        self.book_sheet = None
