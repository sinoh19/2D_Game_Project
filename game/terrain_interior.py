"""Cached stone-interior shading, measured across adjoining terrain sprites."""
import math


def bounds(item):
    x,y,w,h=item['x'],item['y'],item['width'],item['height']
    angle=item.get('angle',0);c=abs(math.cos(angle));s=abs(math.sin(angle))
    bw,bh=c*w+s*h,s*w+c*h
    return x+w/2-bw/2,y+h/2-bh/2,x+w/2+bw/2,y+h/2+bh/2


def rasterize(items,images,width,height,step=2):
    """Union the actual sprite silhouettes, not tile boxes or physics rectangles.

    images maps a key to (width, height, top-down alpha bytes).
    """
    columns,rows=math.ceil(width/step),math.ceil(height/step)
    mask=bytearray(columns*rows)
    for item in items:
        if not item.get('terrainInterior') or item.get('opacity',1)<=0:continue
        iw,ih,alpha=images[item['image']]
        sx,sy,sw,sh=item['rect'];source_top=ih-sy-sh
        x,y,w,h=item['x'],item['y'],item['width'],item['height']
        if w<=0 or h<=0:continue
        left,top,right,bottom=bounds(item)
        angle=item.get('angle',0);c,s=math.cos(angle),math.sin(angle)
        flip=item.get('flip','')
        for gy in range(max(0,math.floor(top/step)),min(rows,math.ceil(bottom/step))):
            dy=(gy+.5)*step-(y+h/2)
            for gx in range(max(0,math.floor(left/step)),min(columns,math.ceil(right/step))):
                dx=(gx+.5)*step-(x+w/2)
                # pico2d angle is counterclockwise in a bottom-up system.
                u=(c*dx-s*dy)/w+.5;v=(s*dx+c*dy)/h+.5
                if not (0<=u<1 and 0<=v<1):continue
                if 'h' in flip:u=1-u
                if 'v' in flip:v=1-v
                px=sx+min(sw-1,int(u*sw));py=source_top+min(sh-1,int(v*sh))
                if alpha[py*iw+px]*item.get('opacity',1)>=128:
                    mask[gy*columns+gx]=1
    return mask,columns,rows


def round_peaks(alpha,width,height,radius=4):
    """Grayscale disk opening removes narrow dark peaks without spreading darkness.

    Clamp the world edges rather than adding an artificial bright border.
    A pixel that was transparent or in the protected surface stays untouched.
    """
    if radius<=0:return bytearray(alpha)
    offsets=[(dx,dy) for dy in range(-radius,radius+1) for dx in range(-radius,radius+1)
             if dx*dx+dy*dy<=radius*radius and (dx or dy)]
    padded_width=width+radius*2;padded_height=height+radius*2
    eroded=bytearray(padded_width*padded_height)
    for i in range(len(eroded)):
        x,y=i%padded_width-radius,i//padded_width-radius
        value=alpha[max(0,min(height-1,y))*width+max(0,min(width-1,x))]
        if not value:continue
        lowest=value
        for dx,dy in offsets:
            nx=max(0,min(width-1,x+dx));ny=max(0,min(height-1,y+dy))
            lowest=min(lowest,alpha[ny*width+nx])
            if not lowest:break
        eroded[i]=lowest
    result=bytearray(alpha)
    for i,value in enumerate(alpha):
        if not value:continue
        ex,ey=i%width+radius,i//width+radius
        if eroded[ey*padded_width+ex]==value:continue
        highest=eroded[ey*padded_width+ex]
        for dx,dy in offsets:
            highest=max(highest,eroded[(ey+dy)*padded_width+ex+dx])
            if highest>=value:break
        result[i]=min(value,highest)
    return result


def interior_alpha(mask,width,height,step=2,surface=6,fade=40,max_alpha=248,rounding=8):
    """Near-Euclidean distance plus rounded dark contours; no tile-grid seams."""
    from array import array
    # A3/4 chamfer includes diagonal paths, unlike the old diamond-shaped
    # four-neighbor distance. Map boundaries continue as solid material.
    cap=min(65530,math.ceil((surface+fade)/step+2)*3)
    distance=array('H',(cap if solid else 0 for solid in mask))
    for y in range(height):
        for x in range(width):
            i=y*width+x
            if not mask[i]:continue
            d=distance[i]
            if x:d=min(d,distance[i-1]+3)
            if y:
                d=min(d,distance[i-width]+3)
                if x:d=min(d,distance[i-width-1]+4)
                if x+1<width:d=min(d,distance[i-width+1]+4)
            distance[i]=d
    for y in range(height-1,-1,-1):
        for x in range(width-1,-1,-1):
            i=y*width+x
            if not mask[i]:continue
            d=distance[i]
            if x+1<width:d=min(d,distance[i+1]+3)
            if y+1<height:
                d=min(d,distance[i+width]+3)
                if x:d=min(d,distance[i+width-1]+4)
                if x+1<width:d=min(d,distance[i+width+1]+4)
            distance[i]=d
    output=bytearray(len(mask))
    for i,solid in enumerate(mask):
        if not solid:continue
        depth=max(0,distance[i]/3-1)*step
        t=max(0,min(1,(depth-surface)/max(1,fade)))
        output[i]=round(max_alpha*t*t*(3-2*t))
    return round_peaks(output,width,height,math.ceil(rounding/step)) if rounding>0 else output

PASSAGE_KEYS=('Fill','passage_wall_left','passage_wall_right',
              'passage_ceiling','passage_corner_bl','passage_corner_br')


def legacy_item(layout,name,x,y,w,h):
    spec=layout['unitySprites'][name]
    return {'image':spec['image'],'rect':spec['rect'],'x':x,'y':y,'width':w,
            'height':h,'angle':0,'flip':spec.get('flip',''),'opacity':1,'terrainInterior':True}


def passage_items(layout):
    items=[]
    for passage in layout.get('sidePassages',[]):
        cap=passage['openingTop']-32
        for x in range(passage['left'],passage['right'],32):
            edge=None
            if passage['side']=='left' and x==passage['right']-32:edge='right'
            if passage['side']=='right' and x==passage['left']:edge='left'
            for y in range(passage.get('top',0),cap,32):
                name='passage_wall_'+edge if edge else 'Fill'
                items.append(legacy_item(layout,name,x,y,32,min(32,cap-y)))
            name='passage_corner_b'+('r' if edge=='right' else 'l') if edge else 'passage_ceiling'
            items.append(legacy_item(layout,name,x,cap,32,32))
    return items


def image_alpha(image):
    import ctypes
    import pico2d as p2d
    from pico2d import pico2d as backend
    renderer=backend.renderer;previous=p2d.SDL_GetRenderTarget(renderer)
    sx,sy=ctypes.c_float(),ctypes.c_float();p2d.SDL_RenderGetScale(renderer,ctypes.byref(sx),ctypes.byref(sy))
    blend=ctypes.c_int();p2d.SDL_GetTextureBlendMode(image.texture,ctypes.byref(blend))
    texture=p2d.SDL_CreateTexture(renderer,p2d.SDL_PIXELFORMAT_RGBA32,p2d.SDL_TEXTUREACCESS_TARGET,image.w,image.h)
    if not texture:raise RuntimeError('Terrain silhouette render target creation failed')
    raw=(ctypes.c_ubyte*(image.w*image.h*4))()
    try:
        p2d.SDL_SetRenderTarget(renderer,texture);p2d.SDL_RenderSetScale(renderer,1,1)
        p2d.SDL_SetTextureBlendMode(image.texture,p2d.SDL_BLENDMODE_NONE)
        p2d.SDL_RenderCopy(renderer,image.texture,None,None)
        if p2d.SDL_RenderReadPixels(renderer,None,p2d.SDL_PIXELFORMAT_RGBA32,raw,image.w*4)!=0:
            raise RuntimeError('Terrain silhouette read failed')
    finally:
        p2d.SDL_SetTextureBlendMode(image.texture,blend.value)
        p2d.SDL_SetRenderTarget(renderer,previous);p2d.SDL_RenderSetScale(renderer,sx.value,sy.value)
        p2d.SDL_DestroyTexture(texture)
    return image.w,image.h,bytes(raw[3::4])


class TerrainInterior:
    def __init__(self,assets):
        self.layout=assets.layout;self.scale=assets.scale;self.image=None;self.step=2
        layout=assets.layout
        if not layout.get('terrainInteriorShading',True) or 'tiledVisuals' not in layout:return
        items=[v for v in layout['tiledVisuals'] if v.get('terrainInterior')]
        if not items:return
        items+=passage_items(layout)
        alpha_sources={key:image_alpha(assets.images[key]) for key in {v['image'] for v in items}}
        world_height=max(layout['height'],max(bounds(v)[3] for v in items))
        mask,self.columns,self.rows=rasterize(items,alpha_sources,layout['width'],world_height,self.step)
        alpha=interior_alpha(mask,self.columns,self.rows,self.step,fade=layout.get('terrainInteriorDepth',40))
        import ctypes
        import pico2d as p2d
        from pico2d import pico2d as backend
        pixels=bytearray(len(alpha)*4)
        for i,a in enumerate(alpha):pixels[i*4:i*4+4]=bytes((4,5,8,a))
        texture=p2d.SDL_CreateTexture(backend.renderer,p2d.SDL_PIXELFORMAT_RGBA32,
            p2d.SDL_TEXTUREACCESS_STATIC,self.columns,self.rows)
        if not texture:raise RuntimeError('Terrain shading texture creation failed')
        data=(ctypes.c_ubyte*len(pixels)).from_buffer_copy(pixels)
        if p2d.SDL_UpdateTexture(texture,None,data,self.columns*4)!=0:
            p2d.SDL_DestroyTexture(texture);raise RuntimeError('Terrain shading texture upload failed')
        p2d.SDL_SetTextureBlendMode(texture,p2d.SDL_BLENDMODE_BLEND)
        self.image=p2d.Image(texture)

    def draw(self,item,camera):
        if self.image is None or not item.get('terrainInterior'):return
        from game.config import WINDOW_HEIGHT
        left,top,right,bottom=bounds(item);step=self.step
        l=max(0,math.floor(left/step));t=max(0,math.floor(top/step))
        r=min(self.columns,math.ceil(right/step));b=min(self.rows,math.ceil(bottom/step))
        if l>=r or t>=b:return
        scale=self.scale
        self.image.clip_composite_draw(l,self.rows-b,r-l,b-t,0,'',
            (round(l*step-camera)+(r-l)*step/2)*scale,
            WINDOW_HEIGHT-(t*step+(b-t)*step/2)*scale,
            (r-l)*step*scale,(b-t)*step*scale)

    def draw_legacy(self,name,x,y,w,h,camera):
        if self.image is not None and name in PASSAGE_KEYS:
            self.draw(legacy_item(self.layout,name,x,y,w,h),camera)
