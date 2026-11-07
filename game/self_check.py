"""SDL 창/에셋/마우스 메뉴/이동/저장/설정/종료를 실제로 확인합니다."""
import json
import tempfile
from types import SimpleNamespace
from pathlib import Path
import pico2d as p2d
from game.app import App
from game.config import MENU_BUTTONS, SCALE, ROOT, NATIVE_WIDTH, NATIVE_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT
from game.scenes.title import TitleScene
from game.scenes.field import FieldScene
from game.scenes.settings import SettingsScene
from game.scenes.opening import OpeningScene
from game.scenes.dialogue import DialogueScene, text_width, TEXT_WIDTH
from game.scenes.book import BookScene
from game.scenes.tile_flip import TileFlipScene
from game.config import TILE_FLIP_BLACK_SECONDS
from game.config import BOOK_FADE_IN_SECONDS, BOOK_CLOSED_HOLD_SECONDS
from game.config import OPENING_DIALOGUE_DELAY, DIALOGUE_CHARACTERS_PER_SECOND
from game.config import OPENING_DURATION, OPENING_FADE_START, OPENING_WINDOW, OPENING_MAX_ZOOM


def run(capture=None, map_path=None):
    with tempfile.TemporaryDirectory(prefix=".self-check-", dir=ROOT) as directory:
        app = App(data_directory=Path(directory), hidden=True, map_path=map_path)
        try:
            title = app.scene
            assert len(app.resources.menu_images) == 4
            assert app.resources.animation["containsUI"] is False
            if capture:
                app.resources.draw_title(0)
                app.capture(Path(capture).with_name(Path(capture).stem + "-background.bmp"))
            for frame in (0, 5, 6, 23):
                app.resources.draw_title(frame)
            app.scene.draw()
            if capture:
                app.capture(capture)
            title.update(0.15)
            assert title.frame == 1

            def click(index):
                bounds = MENU_BUTTONS[index]
                event = SimpleNamespace(type=p2d.SDL_MOUSEBUTTONDOWN, button=p2d.SDL_BUTTON_LEFT,
                                        x=(bounds[0]+bounds[2])*SCALE/2, y=(bounds[1]+bounds[3])*SCALE/2)
                app.handle_event(event)

            def key(symbol, kind=p2d.SDL_KEYDOWN):
                app.handle_event(SimpleNamespace(type=kind, key=symbol))

            click(1)
            assert isinstance(app.scene, TitleScene) and app.scene.notice
            click(0)
            assert isinstance(app.scene, OpeningScene)
            opening = app.scene
            assert opening.camera == (1.0, (NATIVE_WIDTH/2, NATIVE_HEIGHT/2))
            opening.update(OPENING_DURATION / 2)
            assert 1.0 < opening.camera[0] < OPENING_MAX_ZOOM
            zoom, camera = opening.camera
            target_x = NATIVE_WIDTH/2 + (OPENING_WINDOW[0] - camera[0]) * zoom
            target_y = NATIVE_HEIGHT/2 + (OPENING_WINDOW[1] - camera[1]) * zoom
            assert 0 < target_x < NATIVE_WIDTH and 0 < target_y < NATIVE_HEIGHT
            opening.draw()
            if capture:
                app.capture(Path(capture).with_name(Path(capture).stem + "-zoom.bmp"))
            opening.update(OPENING_FADE_START + 0.5 - opening.elapsed)
            assert 0 < opening.darkness < 1
            opening.draw()
            opening.update(OPENING_DURATION)
            assert opening.phase == "black" and opening.darkness == 1
            opening.draw()
            if capture:
                app.capture(Path(capture).with_name(Path(capture).stem + "-black.bmp"))
            opening.update(OPENING_DIALOGUE_DELAY - 0.01)
            assert app.scene is opening
            opening.update(0.02)
            assert isinstance(app.scene, DialogueScene)
            dialogue = app.scene
            dialogue.update(1.1 / DIALOGUE_CHARACTERS_PER_SECOND)
            assert dialogue.visible_count == 1 and dialogue.visible_text == dialogue.text[:1]
            key(None)  # pico2d reports held-key repeats as key=None.
            assert dialogue.index == 0 and dialogue.visible_count == 1
            app.handle_event(SimpleNamespace(type=p2d.SDL_MOUSEBUTTONDOWN, button=p2d.SDL_BUTTON_RIGHT))
            assert dialogue.visible_count == 1
            app.handle_event(SimpleNamespace(type=p2d.SDL_MOUSEBUTTONDOWN, button=p2d.SDL_BUTTON_LEFT))
            assert dialogue.index == 0 and dialogue.fully_visible
            dialogue.update(3600)
            assert dialogue.index == 0 and not dialogue.finished
            dialogue.draw()
            if capture:
                app.capture(Path(capture).with_name(Path(capture).stem + "-dialogue.bmp"))
            key(p2d.SDLK_SPACE)
            assert dialogue.index == 1 and dialogue.visible_count == 0
            while dialogue.index < len(dialogue.lines) - 1:
                dialogue.update(60)
                for start, end in dialogue.layouts[dialogue.index]:
                    assert text_width(app.resources.dialogue, dialogue.text[start:end]) <= TEXT_WIDTH
                if capture and dialogue.index == 5:
                    dialogue.draw()
                    app.capture(Path(capture).with_name(Path(capture).stem + "-long-dialogue.bmp"))
                key(p2d.SDLK_SPACE)
                assert dialogue.visible_count == 0
            dialogue.update(3600)
            assert not dialogue.finished and dialogue.fully_visible
            key(p2d.SDLK_SPACE)
            assert dialogue.finished
            assert isinstance(app.scene, BookScene)
            book = app.scene
            assert book.frame == 0 and book.phase == "fade_in"
            book.update(BOOK_FADE_IN_SECONDS + BOOK_CLOSED_HOLD_SECONDS / 2)
            assert book.phase == "closed" and book.frame == 0
            book.draw()
            if capture:
                app.capture(Path(capture).with_name(Path(capture).stem + "-book-closed.bmp"))
            book.update(book.opening_start - book.elapsed + (book.duration - book.opening_start) * 0.25)
            assert book.phase == "opening" and 0 < book.frame < book.animation["frameCount"] - 1
            book.draw()
            if capture:
                app.capture(Path(capture).with_name(Path(capture).stem + "-book-mid.bmp"))
            book.update(book.transition_start - book.elapsed + 0.001)
            assert book.phase == "opening" and book.frame < book.animation["frameCount"] - 1
            assert isinstance(app.scene, TileFlipScene)
            transition = app.scene
            assert transition.phase == 'cover'
            transition.draw()
            start_frame = book.frame
            transition.update(0.5)
            assert book.frame > start_frame and book.phase == "opening"
            assert transition.tile_progress(0, 0) > transition.tile_progress(15, 8)
            transition.draw()
            if capture:
                app.capture(Path(capture).with_name(Path(capture).stem + '-tiles-cover.bmp'))
            transition.update(transition.wave_duration - transition.elapsed)
            assert transition.phase == 'black'
            assert abs(book.elapsed - min(book.duration, book.transition_start + transition.wave_duration)) < 0.01
            transition.draw()
            import ctypes
            from pico2d import pico2d as backend
            pixel = (ctypes.c_ubyte * 4)()
            for x, y in ((0, 0), (NATIVE_WIDTH//2, NATIVE_HEIGHT//2), (NATIVE_WIDTH-1, NATIVE_HEIGHT-1)):
                rect = p2d.SDL_Rect(x, y, 1, 1)
                assert p2d.SDL_RenderReadPixels(backend.renderer, rect, p2d.SDL_PIXELFORMAT_RGBA32, pixel, 4) == 0
                assert tuple(pixel[:3]) == (0, 0, 0)
            if capture:
                app.capture(Path(capture).with_name(Path(capture).stem + '-tiles-black.bmp'))
            transition.update(TILE_FLIP_BLACK_SECONDS / 2)
            assert transition.phase == 'black' and app.scene is transition
            transition.update(TILE_FLIP_BLACK_SECONDS / 2 + 0.6)
            assert transition.phase == 'reveal'
            transition.draw()
            if capture:
                app.capture(Path(capture).with_name(Path(capture).stem + '-tiles-reveal.bmp'))
            key(p2d.SDLK_RIGHT)  # No held movement leaks into the field.
            transition.update(100)
            assert isinstance(app.scene, FieldScene)
            assert not app.scene.keys and (app.scene.x, app.scene.y) == tuple(app.scene.layout['spawn'])
            assert transition.source_texture is None and transition.destination_texture is None
            app.scene.draw()
            if capture:
                app.capture(Path(capture).with_name(Path(capture).stem + '-field.bmp'))
            key(p2d.SDLK_ESCAPE)
            assert isinstance(app.scene, TitleScene)
            # Escape during a transition releases both snapshots.
            app.start_book()
            app.start_book_to_field(app.scene)
            cancelled = app.scene
            key(p2d.SDLK_ESCAPE)
            assert isinstance(app.scene, TitleScene)
            assert cancelled.source_texture is None and cancelled.destination_texture is None
            app.start_field((52.0, 100.0))
            assert isinstance(app.scene, FieldScene)
            start = app.scene.x
            key(p2d.SDLK_RIGHT)
            app.scene.update(0.25)
            key(p2d.SDLK_RIGHT, p2d.SDL_KEYUP)
            assert app.scene.x > start
            saved = (app.scene.x, app.scene.y)
            app.scene.draw()
            key(p2d.SDLK_ESCAPE)
            assert app.storage.load_position() == saved
            click(1)
            assert isinstance(app.scene, FieldScene) and (app.scene.x, app.scene.y) == saved
            key(p2d.SDLK_ESCAPE)
            click(2)
            assert isinstance(app.scene, SettingsScene)
            key(p2d.SDLK_RETURN)
            assert app.animation is False and app.storage.animation_enabled() is False
            app.scene.draw()
            key(p2d.SDLK_ESCAPE)
            assert isinstance(app.scene, TitleScene)
            click(3)
            assert app.running is False
            print(json.dumps({"passed": True, "title_frames": 24, "checks": ["SDL rendering", "mouse menu", "window zoom/fade", "typewriter/wait/input", "book/transition overlap", "tile flip/black/reveal/cleanup", "movement", "save/continue", "settings", "exit"]}, ensure_ascii=False))
        finally:
            app.close()
