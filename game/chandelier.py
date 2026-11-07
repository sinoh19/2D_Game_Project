"""Cached pixel flame motion; the chain, candles and iron frame stay still."""


def flame_frames(rgba, width, height):
    base = bytearray(rgba)
    flames = [[], [], []]
    for y in range(height//2, height):
        for x in range(width):
            i = (y*width+x)*4
            r, g, b, a = rgba[i:i+4]
            if a >= 128 and r > 170 and g > 60 and b < 110:
                flames[min(2, x*3//width)].append((x, y, bytes(rgba[i:i+4])))
                base[i:i+4] = b'\0\0\0\0'
    frames = []
    lean = (0, -1, -1, 0, 1, 0)
    lift = (0, 0, 1, 0, 0, 1)
    for frame in range(6):
        pixels = bytearray(base)
        for candle, points in enumerate(flames):
            if not points:
                continue
            top = min(p[1] for p in points)
            bottom = max(p[1] for p in points)
            phase = (frame + candle*2) % 6
            # Only the tip moves; the base remains attached to the wick.
            for x, y, color in sorted(points, key=lambda p: p[1]):
                weight = (bottom-y)/max(1, bottom-top)
                nx = x + round(lean[phase]*weight)
                ny = y - (lift[phase] if y == top else 0)
                if 0 <= nx < width and 0 <= ny < height:
                    i = (ny*width+nx)*4
                    pixels[i:i+4] = color
                    if ny < y:
                        # Extend the tip continuously, without a detached spark.
                        i = (y*width+nx)*4
                        pixels[i:i+4] = color
        frames.append(bytes(pixels))
    return frames


def frame_index(time):
    return int(time*8) % 6


def prepare(image):
    import ctypes
    import pico2d as p2d
    from pico2d import pico2d as backend
    renderer = backend.renderer
    previous = p2d.SDL_GetRenderTarget(renderer)
    sx, sy = ctypes.c_float(), ctypes.c_float()
    p2d.SDL_RenderGetScale(renderer, ctypes.byref(sx), ctypes.byref(sy))
    blend = ctypes.c_int()
    p2d.SDL_GetTextureBlendMode(image.texture, ctypes.byref(blend))
    temporary = p2d.SDL_CreateTexture(renderer, p2d.SDL_PIXELFORMAT_RGBA32,
                                     p2d.SDL_TEXTUREACCESS_TARGET, image.w, image.h)
    if not temporary:
        raise RuntimeError('Chandelier render target creation failed')
    raw = (ctypes.c_ubyte*(image.w*image.h*4))()
    try:
        p2d.SDL_SetRenderTarget(renderer, temporary)
        p2d.SDL_RenderSetScale(renderer, 1, 1)
        p2d.SDL_SetTextureBlendMode(image.texture, p2d.SDL_BLENDMODE_NONE)
        p2d.SDL_RenderCopy(renderer, image.texture, None, None)
        if p2d.SDL_RenderReadPixels(renderer, None, p2d.SDL_PIXELFORMAT_RGBA32, raw, image.w*4) != 0:
            raise RuntimeError('Chandelier pixel read failed')
    finally:
        p2d.SDL_SetTextureBlendMode(image.texture, blend.value)
        p2d.SDL_SetRenderTarget(renderer, previous)
        p2d.SDL_RenderSetScale(renderer, sx.value, sy.value)
        p2d.SDL_DestroyTexture(temporary)
    images = []
    for pixels in flame_frames(bytes(raw), image.w, image.h):
        texture = p2d.SDL_CreateTexture(renderer, p2d.SDL_PIXELFORMAT_RGBA32,
                                       p2d.SDL_TEXTUREACCESS_STATIC, image.w, image.h)
        if not texture:
            raise RuntimeError('Chandelier animation texture creation failed')
        data = (ctypes.c_ubyte*len(pixels)).from_buffer_copy(pixels)
        if p2d.SDL_UpdateTexture(texture, None, data, image.w*4) != 0:
            p2d.SDL_DestroyTexture(texture)
            raise RuntimeError('Chandelier animation upload failed')
        p2d.SDL_SetTextureBlendMode(texture, p2d.SDL_BLENDMODE_BLEND)
        images.append(p2d.Image(texture))
    return images
