"""One-time migration of the original hand-authored map into editable Tiled JSON.

Run before changing maps. Existing editor maps are never overwritten.
"""
from pathlib import Path
import ctypes,json,math,struct,sys,tempfile,zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pico2d as p2d
from pico2d import pico2d as backend
from game.app import App


def write_png(path,width,height,pixels):
    def chunk(kind,value):
        return struct.pack('>I',len(value))+kind+value+struct.pack('>I',zlib.crc32(kind+value)&0xffffffff)
    rows=b''.join(b'\0'+pixels[y*width*4:(y+1)*width*4] for y in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))
                     +chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b''))


def props(**values):
    return [{'name':k,'type':'bool' if isinstance(v,bool) else 'int' if isinstance(v,int) else 'float' if isinstance(v,float) else 'string','value':v} for k,v in values.items()]


def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    maps=ROOT/'maps';palette=maps/'tilesets';images=palette/'images'
    if (maps/'dungeon_01.tmj').exists():raise SystemExit('기존 Tiled 맵을 덮어쓰지 않습니다.')
    images.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        app=App(data_directory=Path(tmp),hidden=True)
        try:
            app.resources.map_path=None # This one-time tool reads the legacy source explicitly.
            app.start_field(None);assets=app.scene.assets;layout=assets.layout
            def render(path,width,height,draw):
                previous=p2d.SDL_GetRenderTarget(backend.renderer)
                texture=p2d.SDL_CreateTexture(backend.renderer,p2d.SDL_PIXELFORMAT_RGBA32,p2d.SDL_TEXTUREACCESS_TARGET,width,height)
                pixels=(ctypes.c_ubyte*(width*height*4))()
                try:
                    p2d.SDL_SetRenderTarget(backend.renderer,texture);p2d.SDL_RenderSetScale(backend.renderer,.5,.5)
                    p2d.SDL_SetRenderDrawColor(backend.renderer,0,0,0,0);p2d.SDL_RenderClear(backend.renderer)
                    draw()
                    if p2d.SDL_RenderReadPixels(backend.renderer,None,p2d.SDL_PIXELFORMAT_RGBA32,pixels,width*4):raise RuntimeError('Tile export failed')
                    write_png(path,width,height,bytes(pixels))
                finally:
                    p2d.SDL_SetRenderTarget(backend.renderer,previous);p2d.SDL_DestroyTexture(texture)
                    p2d.SDL_RenderSetScale(backend.renderer,.5,.5)
            names=['Floor','Fill','Ceiling','Ceiling','Ceiling','Stairs_UpRight_1','Stairs_UpRight_2','Stairs_UpLeft_1','Stairs_UpLeft_2',
                   'passage_wall_left','passage_wall_right','passage_corner_bl','passage_corner_br','passage_ceiling']
            def atlas():
                for i,name in enumerate(names):
                    x,y=(i%4)*32,(i//4)*32
                    if name.startswith('Stairs'):
                        assets.tile('Fill',x,y+31,32,1)
                        if name in ('Stairs_UpRight_2','Stairs_UpLeft_1'):assets.tile('Fill',x+(31 if 'Right' in name else 0),y,1,32)
                    if name=='Ceiling':
                        old=assets.layout['unitySprites']['Ceiling'].copy()
                        assets.layout['unitySprites']['Ceiling'].update(rect=[(i-2)*32,0,32,32],horizontalVariants=1)
                        assets.tile(name,x,y)
                        assets.layout['unitySprites']['Ceiling']=old
                    else:assets.tile(name,x,y)
            render(images/'terrain.png',128,128,atlas)
            # Editor sprites are rendered from the same runtime palette and pivots.
            for name,key in (('torch','torch_body'),('armor','armor')):
                spec=layout['unitySprites'][key];w,h=spec['rect'][2:];px,py=spec['pivot']
                def icon(name=name,key=key,spec=spec,w=w,h=h,px=px,py=py):
                    x,y=w*px,h*(1-py)
                    assets.unity_sprite(key,x,y,spec['ppu'],0)
                    if name=='torch':
                        ox,oy=layout['torchAnimation']['offset']
                        assets.unity_sprite('torch_flame_0',x+ox*spec['ppu'],y-oy*spec['ppu'],spec['ppu'],0)
                render(images/f'{name}.png',w,h,icon)
            for side,camera in (('left',0),('right',2496)):
                render(images/f'passage-{side}.png',64,288,lambda camera=camera:app.scene.passages.draw(camera))
            definitions=[]
            for i,name in enumerate(names):
                d={'id':i,'properties':props(label=name)}
                if i in (5,6,7,8):
                    endpoints={5:[(0,32),(32,16)],6:[(0,16),(32,0)],7:[(0,0),(32,16)],8:[(0,16),(32,32)]}[i]
                    shape={'id':1,'class':'Slope','x':0,'y':0,'polyline':[{'x':x,'y':y} for x,y in endpoints]}
                else:shape={'id':1,'class':'Solid','x':0,'y':0,'width':32,'height':24 if i in (2,3,4,11,12,13) else 32}
                d['objectgroup']={'type':'objectgroup','objects':[shape]};definitions.append(d)
            dump(palette/'terrain.tsj',{'type':'tileset','version':'1.10','tiledversion':'1.12.2','name':'동굴 지형 32px','tilewidth':32,'tileheight':32,
                'columns':4,'tilecount':len(names),'image':'images/terrain.png','imagewidth':128,'imageheight':128,'margin':0,'spacing':0,'tiles':definitions})
            object_tiles=[]
            for i,(name,klass,w,h,extra) in enumerate([
                ('torch','Torch',33,64,{}),('armor','Armor',38,76,{}),
                ('passage-left','Passage',64,288,{'side':'left','openingHeight':104,'gateWidth':24}),
                ('passage-right','Passage',64,288,{'side':'right','openingHeight':104,'gateWidth':24})]):
                object_tiles.append({'id':i,'class':klass,'image':f'images/{name}.png','imagewidth':w,'imageheight':h,'properties':props(**extra)})
            dump(palette/'objects.tsj',{'type':'tileset','version':'1.10','tiledversion':'1.12.2','name':'장식·통로','tilewidth':64,'tileheight':288,'columns':0,'tilecount':4,'objectalignment':'bottomleft','tiles':object_tiles})
            width,height=math.ceil(layout['width']/32),math.ceil(layout['height']/32)
            grid0=[0]*(width*height);grid16=[0]*(width*height);free=[];decor=[];colliders=[];slopes=[];gates=[];oid=0
            def obj(**value):
                nonlocal oid
                oid+=1;return {'id':oid,'rotation':0,'visible':True,**value}
            for p in layout['props']:
                key='torch_body' if p['kind']=='torch' else 'armor';s=layout['unitySprites'][key]
                w,h=[n/s['ppu']*p['unitScale'] for n in s['rect'][2:]];px,py=s['pivot']
                decor.append(obj(name=p['kind'],gid=1001 if p['kind']=='torch' else 1002,x=p['x']-w*px,y=p['bottom']+h*py,width=w,height=h))
            # Collect the actual legacy paint calls to retain its half-cell placements.
            trace=[];original=assets.tile;old_view=assets.view_width
            assets.tile=lambda name,x,top,width=32,height=32,camera=0:trace.append((name,x,top,width,height))
            assets.view_width=layout['width'];assets.draw_world(0,0);assets.tile=original;assets.view_width=old_view
            for name,x,y,w,h in trace:
                if x>=layout['width'] or y>=height*32:continue
                if name=='Fill' and (w==1 or h==1):continue # Baked into the stair palette tiles above.
                tid=(2+(int(x//32)%3)) if name=='Ceiling' else names.index(name)
                gid=tid+1
                if w==h==32 and y%32==0 and x%32 in (0,16):
                    offset=0 if x%32==0 else 16;col=int((x-offset)//32);row=int(y//32)
                    (grid0 if offset==0 else grid16)[row*width+col]=gid
                else:free.append(obj(name=name,gid=gid,x=x,y=y+h,width=w,height=h))
            for i,r in enumerate(layout['solids']):colliders.append(obj(name=f'지형-{i+1}',**{'class':'Solid'},x=r[0],y=r[1],width=r[2]-r[0],height=r[3]-r[1]))
            for i,r in enumerate(layout['platforms']):colliders.append(obj(name=f'발판-{i+1}',**{'class':'Platform'},x=r[0],y=r[1],width=r[2]-r[0],height=r[3]-r[1]))
            for s in layout['slopes']:slopes.append(obj(name='경사면',**{'class':'Slope'},x=s['x1'],y=s['y1'],polyline=[{'x':0,'y':0},{'x':s['x2']-s['x1'],'y':s['y2']-s['y1']}]))
            for s in layout['sidePassages']:
                gates.append(obj(name=s['id'],gid=1003 if s['side']=='left' else 1004,x=s['left'],y=s['bottom'],width=s['right']-s['left'],height=s['bottom']-s.get('top',0),properties=props(gateId=s['id'])))
            spawn=obj(name='플레이어 시작',**{'class':'Spawn'},x=layout['spawn'][0],y=layout['spawn'][1],point=True)
            lid=0
            def layer(name,kind,**kw):
                nonlocal lid
                lid+=1;return {'id':lid,'name':name,'type':kind,'opacity':1,'visible':True,'x':0,'y':0,**kw}
            background=layout['background']['panorama']
            import os
            image_path=Path(os.path.relpath(ROOT/'assets/dungeon'/layout['images'][background['image']],maps)).as_posix()
            layers=[layer('배경 이미지','imagelayer',image=image_path,imagewidth=1080,imageheight=360,parallaxx=background['scrollRatio'],locked=True,properties=props(role='background',fitToMap=True)),
                layer('횃불·갑옷','objectgroup',draworder='index',objects=decor),
                layer('기존 지형 32px','tilelayer',width=width,height=height,data=grid0,properties=props(autoCollision=False)),
                layer('기존 지형 16px 보정','tilelayer',width=width,height=height,data=grid16,offsetx=16,properties=props(autoCollision=False)),
                layer('기존 세밀 배치','objectgroup',draworder='index',objects=free),
                layer('새 지형 (자동 충돌)','tilelayer',width=width,height=height,data=[0]*(width*height),properties=props(autoCollision=True)),
                layer('기존 충돌·발판','objectgroup',visible=False,color='#ff7160',objects=colliders,properties=props(role='collision')),
                layer('대각선 경사면','objectgroup',visible=False,color='#49d4ce',objects=slopes,properties=props(role='collision')),
                layer('좌우 철문 통로','objectgroup',draworder='index',objects=gates),
                layer('시작 위치','objectgroup',color='#f5d178',objects=[spawn])]
            m={'type':'map','version':'1.10','tiledversion':'1.12.2','orientation':'orthogonal','renderorder':'right-down','infinite':False,
                'width':width,'height':height,'tilewidth':32,'tileheight':32,'nextlayerid':lid+1,'nextobjectid':oid+1,
                'properties':props(worldHeight=layout['height'],displayName=layout['name'],characterScale=layout['characterScale']),
                'tilesets':[{'firstgid':1,'source':'tilesets/terrain.tsj'},{'firstgid':1001,'source':'tilesets/objects.tsj'}],'layers':layers}
            dump(maps/'dungeon_01.tmj',m)
            # A clean starting map for new levels; its painted terrain has automatic collision.
            blank=json.loads(json.dumps(m));blank['properties']=props(worldHeight=360,displayName='새 던전',characterScale=1)
            for l in blank['layers']:
                if l['type']=='tilelayer':l['data']=[0]*(width*height)
                if l['type']=='objectgroup' and l['name']!='시작 위치':l['objects']=[]
                if l['name']=='새 지형 (자동 충돌)':
                    for row in range(9,height):
                        for col in range(width):l['data'][row*width+col]=1 if row==9 else 2
            dump(maps/'new_level_template.tmj',blank)
            classes=[]
            for i,(name,color) in enumerate([('Spawn','#ffe6c45c'),('Solid','#ffff7160'),('Platform','#ff8fbd66'),('Slope','#ff49d4ce'),('Torch','#ffe7a755'),('Armor','#ffb6c4d2'),('Passage','#ffbb90d6')],1):
                classes.append({'id':i,'name':name,'type':'class','color':color,'drawFill':True,'useAs':['object','tile'],'members':[]})
            dump(maps/'mercenary.tiled-project',{'folders':['.'],'extensionsPath':'extensions','automappingRulesFile':'','propertyTypes':classes})
            print(json.dumps({'map':str(maps/'dungeon_01.tmj'),'terrainTiles':len(names),'paintedTiles':sum(bool(g) for g in grid0+grid16),'freeTiles':len(free),'props':len(decor),'slopes':len(slopes),'passages':len(gates)}))
        finally:app.close()


if __name__=='__main__':main()
