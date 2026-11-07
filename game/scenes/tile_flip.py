"""책 → 타일 뒤집기 → 완전 암전 → 타일 뒤집기 → 필드."""
import ctypes
import math
import pico2d as p2d
from pico2d import pico2d as backend
from game.config import (WINDOW_WIDTH, WINDOW_HEIGHT, TILE_FLIP_COLUMNS,
                         TILE_FLIP_ROWS, TILE_FLIP_SECONDS,
                         TILE_FLIP_STAGGER_SECONDS, TILE_FLIP_BLACK_SECONDS, SCALE, NATIVE_WIDTH, NATIVE_HEIGHT)


class TileFlipScene:
    def __init__(self, app, source, destination):
        self.app = app
        self.source = source
        self.destination = destination
        self.elapsed = 0.0
        self.wave_duration = TILE_FLIP_SECONDS + TILE_FLIP_STAGGER_SECONDS
        self.duration = 2 * self.wave_duration + TILE_FLIP_BLACK_SECONDS
        self.source_texture = None
        self.destination_texture = None
        try:
            self.source_texture = self.snapshot(source)
            self.destination_texture = self.snapshot(destination)
        except Exception:
            self.close()
            raise

    @staticmethod
    def snapshot(scene):
        # Read the freshly rendered frame, never the previous presented buffer.
        p2d.clear_canvas()
        scene.draw()
        pixels = (ctypes.c_ubyte * (NATIVE_WIDTH * NATIVE_HEIGHT * 4))()
        renderer = backend.renderer
        if p2d.SDL_RenderReadPixels(renderer, None, p2d.SDL_PIXELFORMAT_RGBA32,
                                    pixels, NATIVE_WIDTH * 4) != 0:
            raise RuntimeError('타일 전환 화면 캡처 실패')
        texture = p2d.SDL_CreateTexture(renderer, p2d.SDL_PIXELFORMAT_RGBA32,
                                        p2d.SDL_TEXTUREACCESS_STATIC,
                                        NATIVE_WIDTH, NATIVE_HEIGHT)
        if not texture:
            raise RuntimeError('타일 전환 텍스처 생성 실패')
        if p2d.SDL_UpdateTexture(texture, None, pixels, NATIVE_WIDTH * 4) != 0:
            p2d.SDL_DestroyTexture(texture)
            raise RuntimeError('타일 전환 텍스처 업로드 실패')
        return texture

    @property
    def phase(self):
        if self.elapsed < self.wave_duration:
            return 'cover'
        if self.elapsed < self.wave_duration + TILE_FLIP_BLACK_SECONDS:
            return 'black'
        if self.elapsed < self.duration:
            return 'reveal'
        return 'done'

    def tile_progress(self, column, row):
        start = 0.0 if self.phase == 'cover' else self.wave_duration + TILE_FLIP_BLACK_SECONDS
        diagonal = (column + row) / (TILE_FLIP_COLUMNS + TILE_FLIP_ROWS - 2)
        delay = diagonal * TILE_FLIP_STAGGER_SECONDS
        return max(0.0, min(1.0, (self.elapsed - start - delay) / TILE_FLIP_SECONDS))

    def update(self, dt):
        previous = self.elapsed
        self.elapsed = min(self.duration, self.elapsed + max(0.0, dt))
        if hasattr(self.source, "advance_animation"):
            self.source.advance_animation(max(0.0, min(self.elapsed, self.wave_duration) - min(previous, self.wave_duration)))
        if self.elapsed >= self.duration:
            destination = self.destination
            self.close()
            self.app.scene = destination
            if hasattr(destination, 'on_enter'):
                destination.on_enter()

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN and event.key == p2d.SDLK_ESCAPE:
            self.close()
            self.app.show_title()

    def draw(self):
        renderer = backend.renderer
        p2d.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255)
        p2d.SDL_RenderClear(renderer)
        phase = self.phase
        if phase == 'black':
            return
        if phase == 'done':
            self.destination.draw()
            return
        texture = self.source_texture if phase == 'cover' else self.destination_texture
        live_book = phase == 'cover' and hasattr(self.source, 'animation')
        if live_book:
            texture = self.app.resources.book_sheet.texture
            data = self.source.animation
            frame = self.source.frame
            origin_x = frame % data['sheetColumns'] * data['width']
            origin_y = frame // data['sheetColumns'] * data['height']
        try:
            for row in range(TILE_FLIP_ROWS):
                for column in range(TILE_FLIP_COLUMNS):
                    progress = self.tile_progress(column, row)
                    # Face rotates edge-on; the back face is solid black.
                    cosine = math.cos(math.pi * progress)
                    width_ratio = max(0.0, cosine if phase == 'cover' else -cosine)
                    left = column * WINDOW_WIDTH // TILE_FLIP_COLUMNS
                    right = (column + 1) * WINDOW_WIDTH // TILE_FLIP_COLUMNS
                    top = row * WINDOW_HEIGHT // TILE_FLIP_ROWS
                    bottom = (row + 1) * WINDOW_HEIGHT // TILE_FLIP_ROWS
                    width = round((right-left)/SCALE * width_ratio) * SCALE
                    if width <= 0:
                        continue
                    shade = round(255 * (0.45 + 0.55 * width_ratio))
                    p2d.SDL_SetTextureColorMod(texture, shade, shade, shade)
                    source = p2d.SDL_Rect(left//SCALE, top//SCALE, (right-left)//SCALE, (bottom-top)//SCALE)
                    if live_book:
                        sx = column * data['width'] // TILE_FLIP_COLUMNS
                        sy = row * data['height'] // TILE_FLIP_ROWS
                        sw = (column + 1) * data['width'] // TILE_FLIP_COLUMNS - sx
                        sh = (row + 1) * data['height'] // TILE_FLIP_ROWS - sy
                        source = p2d.SDL_Rect(origin_x + sx, origin_y + sy, sw, sh)
                    target = p2d.SDL_Rect(left + ((right-left-width)//SCALE//2)*SCALE, top,
                                           width, bottom - top)
                    p2d.SDL_RenderCopy(renderer, texture, source, target)
        finally:
            p2d.SDL_SetTextureColorMod(texture, 255, 255, 255)

    def close(self):
        for name in ('source_texture', 'destination_texture'):
            texture = getattr(self, name, None)
            if texture:
                p2d.SDL_DestroyTexture(texture)
                setattr(self, name, None)
