"""Rasterize text at native resolution, then enlarge by the integer display scale."""
import ctypes

import pico2d as p2d
from pico2d import pico2d as backend
from game.config import SCALE


class PixelFont:
    def __init__(self,path,size):
        self.font=p2d.TTF_OpenFont(str(path).encode('utf-8'),size)
        if not self.font:
            raise OSError('한글 폰트 열기 실패')

    def measure(self, message):
        width, height = ctypes.c_int(), ctypes.c_int()
        if p2d.TTF_SizeUTF8(self.font, message.encode('utf-8'),
                           ctypes.byref(width), ctypes.byref(height)) != 0:
            raise RuntimeError('글씨 크기 계산 실패')
        return width.value, height.value

    def draw(self,x,y,message,color=(240,231,207)):
        if not message:
            return
        surface=p2d.TTF_RenderUTF8_Blended(self.font,message.encode('utf-8'),p2d.SDL_Color(*color[:3],255))
        if not surface:
            raise RuntimeError('글씨 렌더링 실패')
        try:
            texture=p2d.SDL_CreateTextureFromSurface(backend.renderer,surface)
        finally:
            p2d.SDL_FreeSurface(surface)
        if not texture:
            raise RuntimeError('글씨 텍스처 생성 실패')
        image=p2d.Image(texture)
        if len(color) == 4:
            p2d.SDL_SetTextureAlphaMod(texture, color[3])
        image.draw(x+image.w*SCALE/2,y,image.w*SCALE,image.h*SCALE)

    def close(self):
        if self.font:
            p2d.TTF_CloseFont(self.font)
            self.font=None
