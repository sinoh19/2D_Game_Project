"""pico2d/SDL 그리기를 원본 이미지의 왼쪽 위 좌표계로 통일합니다."""
import pico2d as p2d
from pico2d import pico2d as backend
from game.config import SCALE, NATIVE_WIDTH, NATIVE_HEIGHT


def rectangle(bounds, color, filled=False):
    left, top, right, bottom = bounds
    rect = p2d.SDL_Rect(round(left * SCALE), round(top * SCALE),
                        max(1, round((right - left + 1) * SCALE)),
                        max(1, round((bottom - top + 1) * SCALE)))
    p2d.SDL_SetRenderDrawColor(backend.renderer, *color[:3], color[3] if len(color) > 3 else 255)
    if filled:
        p2d.SDL_RenderFillRect(backend.renderer, rect)
    else:
        p2d.SDL_RenderDrawRect(backend.renderer, rect)


def text(font, x, y, message, color=(240, 231, 207)):
    font.draw(round(x * SCALE), round((NATIVE_HEIGHT - y) * SCALE), message, color)


def contains(bounds, x, y):
    return bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]


def black_overlay(opacity):
    """알파 블렌딩으로 완전 암전까지 진행하며 이전 SDL 상태를 복원합니다."""
    import ctypes
    alpha = round(max(0.0, min(1.0, opacity)) * 255)
    if alpha == 0:
        return
    previous = ctypes.c_int()
    p2d.SDL_GetRenderDrawBlendMode(backend.renderer, ctypes.byref(previous))
    p2d.SDL_SetRenderDrawBlendMode(backend.renderer, p2d.SDL_BLENDMODE_BLEND)
    try:
        rectangle((0, 0, NATIVE_WIDTH-1, NATIVE_HEIGHT-1), (0, 0, 0, alpha), filled=True)
    finally:
        p2d.SDL_SetRenderDrawBlendMode(backend.renderer, previous.value)
