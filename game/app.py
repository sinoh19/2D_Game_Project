import gc
import os
import time
from pathlib import Path
import pico2d as p2d
from pico2d import pico2d as backend
from game.config import ROOT, TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, TARGET_FPS, NATIVE_WIDTH, NATIVE_HEIGHT, SCALE
from game.resources import Resources
from game.storage import Storage
from game.config import DEFAULT_TILED_MAP
from game import drawing
from game.config import DEBUG_SKIP_ENABLED, DEBUG_SKIP_BOUNDS


class App:
    def __init__(self, data_directory=None, hidden=False, map_path=None):
        os.environ["SDL_RENDER_SCALE_QUALITY"] = "0"
        p2d.SDL_SetHint(b"SDL_RENDER_SCALE_QUALITY", b"0")
        p2d.open_canvas(WINDOW_WIDTH, WINDOW_HEIGHT, sync=True)
        self.closed = False
        if hidden:
            p2d.SDL_HideWindow(backend.window)
        p2d.hide_lattice()
        self.native_target = p2d.SDL_CreateTexture(backend.renderer, p2d.SDL_PIXELFORMAT_RGBA32,
                                                   p2d.SDL_TEXTUREACCESS_TARGET, NATIVE_WIDTH, NATIVE_HEIGHT)
        if not self.native_target:
            p2d.close_canvas()
            raise RuntimeError("640×360 렌더 타깃 생성 실패")
        self.begin_native_frame()
        self.storage = Storage(Path(data_directory) if data_directory else ROOT / "user_data")
        selected_map = Path(map_path) if map_path else DEFAULT_TILED_MAP
        self.map_path = selected_map.resolve() if selected_map.is_absolute() else (ROOT/selected_map).resolve()
        self.animation = self.storage.animation_enabled()
        self.running = True
        self.debug_skip_hovered = False
        self.scene = None
        self.resources = None
        try:
            self.resources = Resources()
            self.resources.map_path = self.map_path
            self.show_title()
        except Exception:
            self.close()
            raise

    def begin_native_frame(self):
        p2d.SDL_SetRenderTarget(backend.renderer, self.native_target)
        p2d.SDL_RenderSetScale(backend.renderer, 1.0/SCALE, 1.0/SCALE)

    def present(self):
        """640×360에서 완성된 화면만 최근접 정수 배율로 확대합니다."""
        p2d.SDL_SetRenderTarget(backend.renderer, None)
        p2d.SDL_RenderSetScale(backend.renderer, 1.0, 1.0)
        p2d.SDL_RenderCopy(backend.renderer, self.native_target, None, None)
        p2d.SDL_RenderPresent(backend.renderer)
        self.begin_native_frame()

    def show_title(self):
        from game.scenes.title import TitleScene
        self.scene = TitleScene(self)

    def start_opening(self, background_time=0.0):
        from game.scenes.opening import OpeningScene
        self.scene = OpeningScene(self, background_time)

    def start_dialogue(self):
        from game.scenes.dialogue import DialogueScene
        self.scene = DialogueScene(self)

    def start_book(self):
        from game.scenes.book import BookScene
        self.scene = BookScene(self)

    def start_book_to_field(self, book):
        from game.scenes.field import FieldScene
        from game.scenes.tile_flip import TileFlipScene
        self.scene = TileFlipScene(self, book, FieldScene(self, None, new_game=True))

    def start_field(self, position):
        from game.scenes.field import FieldScene
        self.scene = FieldScene(self, position)

    def start_melee(self, field, enemy, cause):
        from game.scenes.melee import MeleeScene
        self.scene = MeleeScene(self, field, enemy, cause)

    def reload_field_map(self):
        previous = self.scene
        previous.save()
        position = (previous.x, previous.y)
        assets = self.resources.dungeon
        self.resources.dungeon = None
        try:
            self.start_field(position)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.scene = previous
            self.resources.dungeon = assets
            previous.map_notice = '맵 오류: '+str(error)[:50]
            previous.map_notice_time = 5.0
            return False
        self.scene.map_notice = 'Tiled 맵을 다시 불러왔습니다.'
        self.scene.map_notice_time = 2.5
        return True

    def can_skip_intro(self):
        from game.scenes.title import TitleScene
        from game.scenes.opening import OpeningScene
        from game.scenes.dialogue import DialogueScene
        from game.scenes.book import BookScene
        from game.scenes.tile_flip import TileFlipScene
        return DEBUG_SKIP_ENABLED and isinstance(self.scene,
            (TitleScene, OpeningScene, DialogueScene, BookScene, TileFlipScene))

    def skip_intro_to_field(self):
        from game.scenes.field import FieldScene
        previous = self.scene
        destination = FieldScene(self, None, new_game=True)
        if hasattr(previous, 'close'):
            previous.close()
        self.scene = destination
        self.debug_skip_hovered = False
        destination.on_enter()

    def draw(self):
        self.scene.draw()
        if self.can_skip_intro():
            color = (52, 61, 68) if self.debug_skip_hovered else (25, 30, 37)
            drawing.rectangle(DEBUG_SKIP_BOUNDS, color, filled=True)
            drawing.rectangle(DEBUG_SKIP_BOUNDS, (149, 137, 108))
            drawing.text(self.resources.small, DEBUG_SKIP_BOUNDS[0]+8,
                         DEBUG_SKIP_BOUNDS[1]+15, '디버그: 인게임', (224, 216, 190))

    def handle_event(self, event):
        if (self.can_skip_intro() and event.type in (p2d.SDL_MOUSEMOTION, p2d.SDL_MOUSEBUTTONDOWN)
                and getattr(event, 'x', None) is not None and getattr(event, 'y', None) is not None):
            self.debug_skip_hovered = drawing.contains(DEBUG_SKIP_BOUNDS, event.x/SCALE, event.y/SCALE)
            if (self.debug_skip_hovered and event.type == p2d.SDL_MOUSEBUTTONDOWN
                    and event.button == p2d.SDL_BUTTON_LEFT):
                self.skip_intro_to_field()
                return
        if event.type == p2d.SDL_QUIT:
            self.running = False
        else:
            self.scene.handle_event(event)

    def capture(self, path):
        import ctypes
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        surface = p2d.SDL_CreateRGBSurfaceWithFormat(0, NATIVE_WIDTH, NATIVE_HEIGHT, 32, p2d.SDL_PIXELFORMAT_RGBA32)
        if not surface:
            raise RuntimeError("캡처 surface 생성 실패")
        try:
            if p2d.SDL_RenderReadPixels(backend.renderer, None, p2d.SDL_PIXELFORMAT_RGBA32,
                                        surface.contents.pixels, surface.contents.pitch) != 0:
                raise RuntimeError("화면 픽셀 읽기 실패")
            if p2d.SDL_SaveBMP(surface, os.fsencode(str(path))) != 0:
                raise RuntimeError("캡처 저장 실패")
        finally:
            p2d.SDL_FreeSurface(surface)

    def run(self):
        previous = time.perf_counter()
        try:
            while self.running:
                started = time.perf_counter()
                dt = min(started - previous, 0.1)
                previous = started
                for event in p2d.get_events():
                    self.handle_event(event)
                    if not self.running:
                        break
                p2d.SDL_SetWindowTitle(backend.window, TITLE.encode("utf-8"))
                if not self.running:
                    break
                self.scene.update(dt)
                p2d.clear_canvas()
                self.draw()
                self.present()
                remaining = 1 / TARGET_FPS - (time.perf_counter() - started)
                if remaining > 0:
                    time.sleep(remaining)
        finally:
            self.close()

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.scene is not None and hasattr(self.scene, "save"):
                self.scene.save()
        finally:
            if self.scene is not None and hasattr(self.scene, "close"):
                self.scene.close()
            self.scene = None
            if self.resources is not None:
                self.resources.close()
            gc.collect()
            p2d.SDL_SetRenderTarget(backend.renderer, None)
            p2d.SDL_RenderSetScale(backend.renderer, 1.0, 1.0)
            if self.native_target:
                p2d.SDL_DestroyTexture(self.native_target)
                self.native_target = None
            p2d.close_canvas()
