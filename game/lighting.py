"""Soft, cached additive candle light in native world coordinates."""
import math


def glow_pixels(size=96):
    pixels=bytearray(size*size*4)
    for y in range(size):
        for x in range(size):
            distance=((x+.5-size/2)/(size/2))**2+((y+.5-size/2)/(size/2))**2
            alpha=round(54*max(0,1-distance)**3)
            i=(y*size+x)*4
            pixels[i:i+4]=bytes((255,134,48,alpha))
    return bytes(pixels)


def light_sources(layout):
    sources=[]
    for prop in layout['props']:
        if prop['kind']!='torch':continue
        spec=layout['unitySprites']['torch_flame_0']
        scale=prop['unitScale']/spec['ppu']
        ox,oy=layout['torchAnimation']['offset']
        x=prop['x']+ox*prop['unitScale']+spec['rect'][2]*scale*(.5-spec['pivot'][0])
        y=prop['bottom']-oy*prop['unitScale']-spec['rect'][3]*scale*(.5-spec['pivot'][1])
        sources.append((x,y,52*scale,.9))
    for item in layout.get('tiledVisuals',[]):
        if item.get('light')!='chandelier':continue
        x,y,w,h=item['x'],item['y'],item['width'],item['height']
        scale=max(w/48,h/64);opacity=item['opacity']
        sources.append((x+w*.5,y+h*49/64,56*scale,.65*opacity))
        for px,py in ((5,48),(24,49),(42,48)):
            sources.append((x+w*px/48,y+h*py/64,20*scale,.3*opacity))
    return sources


def flicker(time,phase):
    return 1+.035*math.sin(time*5.3+phase)+.02*math.sin(time*11.7+phase*1.7)


class FireLights:
    def __init__(self,layout,scale,view_width):
        import ctypes
        import pico2d as p2d
        from pico2d import pico2d as backend
        self.sources=light_sources(layout)
        self.scale=scale;self.view_width=view_width
        self.image=None
        if not self.sources:return
        texture=p2d.SDL_CreateTexture(backend.renderer,p2d.SDL_PIXELFORMAT_RGBA32,
                                       p2d.SDL_TEXTUREACCESS_STATIC,96,96)
        if not texture:raise RuntimeError('Fire light texture creation failed')
        raw=glow_pixels();data=(ctypes.c_ubyte*len(raw)).from_buffer_copy(raw)
        if p2d.SDL_UpdateTexture(texture,None,data,96*4)!=0:
            p2d.SDL_DestroyTexture(texture)
            raise RuntimeError('Fire light upload failed')
        p2d.SDL_SetTextureBlendMode(texture,p2d.SDL_BLENDMODE_ADD)
        self.image=p2d.Image(texture)

    def draw(self,camera,time):
        if self.image is None:return
        import pico2d as p2d
        from game.config import WINDOW_HEIGHT
        try:
            for x,y,radius,strength in self.sources:
                if x+radius<camera or x-radius>camera+self.view_width:continue
                amount=max(0,min(255,round(255*strength*flicker(time,x*.17+y*.11))))
                if not amount:continue
                p2d.SDL_SetTextureAlphaMod(self.image.texture,amount)
                self.image.composite_draw(0,'',(round(x-camera))*self.scale,
                    WINDOW_HEIGHT-round(y)*self.scale,round(radius*2*self.scale),round(radius*2*self.scale))
        finally:
            p2d.SDL_SetTextureAlphaMod(self.image.texture,255)


class WorldDarkness:
    """Darken the world with soft clear areas around the player and flames."""
    STEP = 4

    def __init__(self, fire_lights):
        import pico2d as p2d
        from pico2d import pico2d as backend
        from game.config import NATIVE_WIDTH, NATIVE_HEIGHT
        self.fire_lights = fire_lights
        self.width = NATIVE_WIDTH // self.STEP
        self.height = NATIVE_HEIGHT // self.STEP
        texture = p2d.SDL_CreateTexture(backend.renderer, p2d.SDL_PIXELFORMAT_RGBA32,
                                       p2d.SDL_TEXTUREACCESS_STREAMING, self.width, self.height)
        if not texture:
            raise RuntimeError('World darkness texture creation failed')
        p2d.SDL_SetTextureBlendMode(texture, p2d.SDL_BLENDMODE_BLEND)
        self.image = p2d.Image(texture)

    def draw(self, camera, time, player_x, player_y):
        import ctypes
        import pico2d as p2d
        from game.config import WINDOW_WIDTH, WINDOW_HEIGHT
        ambient = 158
        pixels = bytearray(bytes((0, 0, 0, ambient)) * (self.width * self.height))
        sources = [(player_x, player_y - 22, 90, 138)]
        sources.extend((x, y, radius * flicker(time, x * .17 + y * .11), 135 * strength)
                       for x, y, radius, strength in self.fire_lights.sources)
        for x, y, radius, clearing in sources:
            x = (x - camera) / self.STEP
            y /= self.STEP
            radius /= self.STEP
            if x + radius < 0 or x - radius >= self.width:
                continue
            for row in range(max(0, int(y - radius)), min(self.height, math.ceil(y + radius))):
                dy = ((row + .5 - y) / radius) ** 2
                for col in range(max(0, int(x - radius)), min(self.width, math.ceil(x + radius))):
                    distance = dy + ((col + .5 - x) / radius) ** 2
                    if distance >= 1:
                        continue
                    alpha = round(ambient - clearing * (1 - distance) ** 2)
                    offset = (row * self.width + col) * 4 + 3
                    pixels[offset] = min(pixels[offset], max(0, alpha))
        data = (ctypes.c_ubyte * len(pixels)).from_buffer(pixels)
        if p2d.SDL_UpdateTexture(self.image.texture, None, data, self.width * 4) != 0:
            raise RuntimeError('World darkness upload failed')
        self.image.draw(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, WINDOW_WIDTH, WINDOW_HEIGHT)
