"""Build a deterministic background layer with real openings and selected windows."""
import ctypes
import pico2d as p2d
from pico2d import pico2d as backend
from game.config import SCALE, WINDOW_HEIGHT


def damage_mask(image):
    """Use the panel's opening and chipped rim without its rectangular wall patch."""
    renderer=backend.renderer
    previous=p2d.SDL_GetRenderTarget(renderer)
    sx,sy=ctypes.c_float(),ctypes.c_float()
    p2d.SDL_RenderGetScale(renderer,ctypes.byref(sx),ctypes.byref(sy))
    temporary=p2d.SDL_CreateTexture(renderer,p2d.SDL_PIXELFORMAT_RGBA32,
                                    p2d.SDL_TEXTUREACCESS_TARGET,image.w,image.h)
    if not temporary:
        raise RuntimeError('파손 벽 알파 마스크 생성 실패')
    pixels=(ctypes.c_ubyte*(image.w*image.h*4))()
    try:
        p2d.SDL_SetRenderTarget(renderer,temporary)
        p2d.SDL_RenderSetScale(renderer,1,1)
        p2d.SDL_SetRenderDrawColor(renderer,0,0,0,0)
        p2d.SDL_RenderClear(renderer)
        p2d.SDL_RenderCopy(renderer,image.texture,None,None)
        if p2d.SDL_RenderReadPixels(renderer,None,p2d.SDL_PIXELFORMAT_RGBA32,pixels,image.w*4)!=0:
            raise RuntimeError('파손 벽 알파 읽기 실패')
    finally:
        p2d.SDL_SetRenderTarget(renderer,previous)
        p2d.SDL_RenderSetScale(renderer,sx.value,sy.value)
        p2d.SDL_DestroyTexture(temporary)
    raw=bytes(pixels)
    holes=[raw[i*4+3]==0 for i in range(image.w*image.h)]
    edge=bytearray(len(raw));runs=[]
    for y in range(image.h):
        x=0
        while x<image.w:
            if holes[y*image.w+x]:
                start=x
                while x<image.w and holes[y*image.w+x]:x+=1
                runs.append((start,y,x-start))
            else:x+=1
        for x in range(image.w):
            if holes[y*image.w+x]:continue
            touches=any(0<=x+dx<image.w and 0<=y+dy<image.h and holes[(y+dy)*image.w+x+dx]
                        for dx,dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)))
            if touches:
                i=(y*image.w+x)*4;edge[i:i+4]=raw[i:i+4]
    texture=p2d.SDL_CreateTexture(renderer,p2d.SDL_PIXELFORMAT_RGBA32,
                                  p2d.SDL_TEXTUREACCESS_STATIC,image.w,image.h)
    if not texture:raise RuntimeError('파손 벽 테두리 텍스처 생성 실패')
    data=(ctypes.c_ubyte*len(edge)).from_buffer_copy(edge)
    if p2d.SDL_UpdateTexture(texture,None,data,image.w*4)!=0:
        p2d.SDL_DestroyTexture(texture);raise RuntimeError('파손 벽 테두리 업로드 실패')
    p2d.SDL_SetTextureBlendMode(texture,p2d.SDL_BLENDMODE_BLEND)
    return runs,p2d.Image(texture)


def build_layer(assets):
    layout=assets.layout
    if layout['background'].get('mode') == 'panorama':
        return assets.images[layout['background']['panorama']['image']]
    width,height=layout['width'],layout['height']
    renderer=backend.renderer
    previous=p2d.SDL_GetRenderTarget(renderer)
    old_x,old_y=ctypes.c_float(),ctypes.c_float()
    p2d.SDL_RenderGetScale(renderer,ctypes.byref(old_x),ctypes.byref(old_y))
    blend=ctypes.c_int()
    p2d.SDL_GetRenderDrawBlendMode(renderer,ctypes.byref(blend))
    texture=p2d.SDL_CreateTexture(renderer,p2d.SDL_PIXELFORMAT_RGBA32,
                                  p2d.SDL_TEXTUREACCESS_TARGET,width,height)
    if not texture:
        raise RuntimeError('던전 배경 레이어 생성 실패')
    try:
        p2d.SDL_SetTextureBlendMode(texture,p2d.SDL_BLENDMODE_BLEND)
        p2d.SDL_SetRenderTarget(renderer,texture)
        p2d.SDL_RenderSetScale(renderer,1/SCALE,1/SCALE)
        p2d.SDL_SetRenderDrawBlendMode(renderer,p2d.SDL_BLENDMODE_NONE)
        p2d.SDL_SetRenderDrawColor(renderer,0,0,0,0)
        p2d.SDL_RenderClear(renderer)

        def stamp(key,x,top):
            image=assets.images[key]
            image.draw((x+image.w/2)*SCALE,
                       WINDOW_HEIGHT-(top+image.h/2)*SCALE,
                       image.w*SCALE,image.h*SCALE)

        for cell in layout['background']['cells']:
            stamp('bg_intact_%02d'%cell['variant'],cell['x'],cell['y'])
        masks={}
        for panel in layout['background']['damage']:
            variant=panel['variant']
            if variant not in masks:
                masks[variant]=damage_mask(assets.images['bg_broken_%02d'%variant])
            runs,rim=masks[variant]
            p2d.SDL_SetRenderDrawColor(renderer,0,0,0,0)
            p2d.SDL_SetRenderDrawBlendMode(renderer,p2d.SDL_BLENDMODE_NONE)
            for x,y,length in runs:
                rect=p2d.SDL_Rect((panel['x']+x)*SCALE,(panel['y']+y)*SCALE,length*SCALE,SCALE)
                p2d.SDL_RenderFillRect(renderer,rect)
            rim.draw((panel['x']+rim.w/2)*SCALE,
                     WINDOW_HEIGHT-(panel['y']+rim.h/2)*SCALE,rim.w*SCALE,rim.h*SCALE)
        for window in layout['background']['windows']:
            stamp('bg_window_%02d'%window['variant'],window['x'],window['y'])
        return p2d.Image(texture)
    except Exception:
        p2d.SDL_DestroyTexture(texture)
        raise
    finally:
        p2d.SDL_SetRenderTarget(renderer,previous)
        p2d.SDL_RenderSetScale(renderer,old_x.value,old_y.value)
        p2d.SDL_SetRenderDrawBlendMode(renderer,blend.value)


def draw_layer(assets,camera):
    if assets.layout['background'].get('mode') == 'panorama':
        spec = assets.layout['background']['panorama']
        image = assets.background_layer
        scroll = round(max(0, min(image.w-assets.view_width, camera*spec['scrollRatio'])))
        image.clip_draw(scroll, 0, assets.view_width, assets.view_height,
                        assets.view_width*SCALE/2, WINDOW_HEIGHT/2,
                        assets.view_width*SCALE, assets.view_height*SCALE)
        return
    # Distant cool light lives behind the wall, not baked into its PNGs.
    renderer=backend.renderer
    for y in range(0,assets.view_height,8):
        t=y/max(1,assets.view_height-1)
        color=(round(55+45*t),round(102+58*t),round(120+45*t))
        p2d.SDL_SetRenderDrawColor(renderer,*color,255)
        rect=p2d.SDL_Rect(0,y*SCALE,assets.view_width*SCALE,min(8,assets.view_height-y)*SCALE)
        p2d.SDL_RenderFillRect(renderer,rect)
    assets.background_layer.clip_draw(round(camera),0,assets.view_width,assets.view_height,
                                       assets.view_width*SCALE/2,WINDOW_HEIGHT/2,
                                       assets.view_width*SCALE,assets.view_height*SCALE)
