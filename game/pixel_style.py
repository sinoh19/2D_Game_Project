"""A cached low-resolution rendering treatment; source art stays untouched."""
import ctypes
import pico2d as p2d
from pico2d import pico2d as backend

PALETTE = (
    (22,24,30),(34,37,43),(48,52,59),(65,70,78),(83,90,100),
    (105,113,124),(132,140,149),(160,166,170),(188,190,184),
    (44,31,30),(65,45,35),(88,62,44),(115,83,56),(142,110,75),
    (70,34,37),(104,46,43),(139,64,49),
    (38,55,69),(54,77,92),(77,104,115),
    (153,96,43),(190,131,55),(215,165,76),(229,196,112),
)


def simplify(image, block=2, *, preserve_white=False):
    """Quantize a texture once, using a shared palette and 2px pixel grid."""
    renderer=backend.renderer
    previous=p2d.SDL_GetRenderTarget(renderer)
    sx,sy=ctypes.c_float(),ctypes.c_float()
    p2d.SDL_RenderGetScale(renderer,ctypes.byref(sx),ctypes.byref(sy))
    blend=ctypes.c_int()
    p2d.SDL_GetTextureBlendMode(image.texture,ctypes.byref(blend))
    temporary=p2d.SDL_CreateTexture(renderer,p2d.SDL_PIXELFORMAT_RGBA32,
                                    p2d.SDL_TEXTUREACCESS_TARGET,image.w,image.h)
    if not temporary:raise RuntimeError('Sprite style render target creation failed')
    raw=(ctypes.c_ubyte*(image.w*image.h*4))()
    try:
        p2d.SDL_SetRenderTarget(renderer,temporary)
        p2d.SDL_RenderSetScale(renderer,1,1)
        p2d.SDL_SetTextureBlendMode(image.texture,p2d.SDL_BLENDMODE_NONE)
        p2d.SDL_RenderCopy(renderer,image.texture,None,None)
        if p2d.SDL_RenderReadPixels(renderer,None,p2d.SDL_PIXELFORMAT_RGBA32,raw,image.w*4)!=0:
            raise RuntimeError('Sprite style pixel read failed')
    finally:
        p2d.SDL_SetTextureBlendMode(image.texture,blend.value)
        p2d.SDL_SetRenderTarget(renderer,previous)
        p2d.SDL_RenderSetScale(renderer,sx.value,sy.value)
        p2d.SDL_DestroyTexture(temporary)
    output=bytearray(len(raw));cache={}
    for y in range(0,image.h,block):
        for x in range(0,image.w,block):
            points=[(dy*image.w+dx)*4 for dy in range(y,min(y+block,image.h))
                    for dx in range(x,min(x+block,image.w))]
            visible=[i for i in points if raw[i+3]>=128]
            if not visible:continue
            color=tuple(round(sum(raw[i+c] for i in visible)/len(visible)) for c in range(3))
            if color not in cache:
                cache[color] = (color if preserve_white and color == (255, 255, 255)
                                else min(PALETTE, key=lambda p: sum((p[c]-color[c])**2 for c in range(3))))
            rgba=bytes((*cache[color],255))
            for i in points:output[i:i+4]=rgba
    texture=p2d.SDL_CreateTexture(renderer,p2d.SDL_PIXELFORMAT_RGBA32,
                                  p2d.SDL_TEXTUREACCESS_STATIC,image.w,image.h)
    if not texture:raise RuntimeError('Sprite style texture creation failed')
    data=(ctypes.c_ubyte*len(output)).from_buffer_copy(output)
    if p2d.SDL_UpdateTexture(texture,None,data,image.w*4)!=0:
        p2d.SDL_DestroyTexture(texture);raise RuntimeError('Sprite style upload failed')
    p2d.SDL_SetTextureBlendMode(texture,p2d.SDL_BLENDMODE_BLEND)
    return p2d.Image(texture)


def apply(assets):
    assets.sheets={key:simplify(image) for key,image in assets.sheets.items()}
    keys=('door','armor','torch_body',*(f'torch_flame_{i}' for i in range(6)))
    for key in keys:
        if key in assets.images:assets.images[key]=simplify(assets.images[key])
