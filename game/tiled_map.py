"""Load the editable Tiled JSON map into the pico2d runtime layout."""
import base64
import copy
import gzip
import json
import math
from pathlib import Path
import struct
import zlib

H,V,D=0x80000000,0x40000000,0x20000000


def properties(value):
    return {p['name']:p.get('value') for p in value.get('properties',[])}


def png_size(path):
    with Path(path).open('rb') as stream:header=stream.read(24)
    if header[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError(f'PNG 이미지가 아닙니다: {path}')
    return struct.unpack('>II',header[16:24])


def _data(layer):
    data=layer.get('data',[])
    if isinstance(data,list):return data
    raw=base64.b64decode(data)
    compression=layer.get('compression','')
    if compression=='zlib':raw=zlib.decompress(raw)
    elif compression=='gzip':raw=gzip.decompress(raw)
    elif compression:raise ValueError('Tiled 레이어 압축은 CSV/비압축/zlib/gzip을 사용하세요.')
    return list(struct.unpack('<'+'I'*(len(raw)//4),raw))


def _transform(u,v,h,vflip,diagonal):
    if diagonal:u,v=v,u
    if h:u=1-u
    if vflip:v=1-v
    return u,v


def _draw_transform(gid):
    h,v,d=bool(gid&H),bool(gid&V),bool(gid&D)
    if not d:return 0,('h' if h else '')+('v' if v else '')
    if h and v:return -math.pi/2,'h'
    if h:return -math.pi/2,''
    if v:return math.pi/2,''
    return math.pi/2,'h'


def load_map(map_path,base_layout,asset_root):
    path=Path(map_path).resolve();asset_root=Path(asset_root).resolve()
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('orientation')!='orthogonal':raise ValueError('직교(Orthogonal) Tiled 맵을 사용하세요.')
    if data.get('infinite'):raise ValueError('현재는 고정 크기 맵을 사용하세요. 무한 맵은 지원하지 않습니다.')
    tw,th=data['tilewidth'],data['tileheight']
    if (tw,th)!=(32,32):raise ValueError('맵 타일 크기는 32×32이어야 합니다.')
    mp=properties(data);layout=copy.deepcopy(base_layout)
    layout.update(width=data['width']*tw,height=int(mp.get('worldHeight',data['height']*th)),
                  name=mp.get('displayName',path.stem),mapId=path.stem,tiledSource=str(path),
                  props=[],solids=[],platforms=[],slopes=[],sidePassages=[],tiledVisuals=[],tiledDrawOrder=[])
    if layout['width']<640 or layout['height']<360:raise ValueError('맵은 최소 640×360이어야 합니다.')
    layout['characterScale']=float(mp.get('characterScale',layout['characterScale']))
    tilesets=[];image_keys={};spawns=[];passage_ids=set();background_found=False

    def image_key(image_path):
        resolved=Path(image_path).resolve()
        if not resolved.is_file():raise ValueError(f'이미지를 찾을 수 없습니다: {resolved}')
        if resolved not in image_keys:
            key=f'tiled_image_{len(image_keys)}'
            # Asset paths stay portable in the committed map and tileset files.
            import os
            layout['images'][key]=Path(os.path.relpath(resolved,asset_root)).as_posix()
            image_keys[resolved]=key
        return image_keys[resolved]

    for entry in data.get('tilesets',[]):
        if 'source' in entry:
            tp=(path.parent/entry['source']).resolve()
            ts=json.loads(tp.read_text(encoding='utf-8-sig'));directory=tp.parent
        else:ts=entry;directory=path.parent
        tilesets.append((entry['firstgid'],ts,directory,{t['id']:t for t in ts.get('tiles',[])}))
    tilesets.sort(key=lambda item:item[0])

    def tile(gid):
        actual=gid&0x0fffffff
        candidates=[t for t in tilesets if t[0]<=actual]
        if not candidates:raise ValueError(f'알 수 없는 타일 GID: {actual}')
        first,ts,directory,definitions=candidates[-1];local=actual-first
        if local>=ts['tilecount']:raise ValueError(f'타일 범위를 벗어난 GID: {actual}')
        definition=definitions.get(local,{})
        if 'image' in definition:
            image=directory/definition['image'];w=definition['imagewidth'];h=definition['imageheight'];sx=sy=0
            ih=h
        else:
            image=directory/ts['image'];w=ts['tilewidth'];h=ts['tileheight'];ih=ts['imageheight']
            margin,spacing=ts.get('margin',0),ts.get('spacing',0)
            sx=margin+(local%ts['columns'])*(w+spacing)
            sy=margin+(local//ts['columns'])*(h+spacing)
        return definition,properties(definition),image_key(image),(sx,ih-sy-h,w,h)

    def visual(gid,x,y,w=None,h=None,rotation=0,opacity=1):
        definition,props,key,rect=tile(gid)
        angle,flip=_draw_transform(gid)
        w=rect[2] if w is None else w;h=rect[3] if h is None else h
        if rotation:
            # Tiled rotates tile objects about their bottom-left anchor;
            # pico2d rotates about their center.
            a=math.radians(rotation)
            cx=x+w/2*math.cos(a)+h/2*math.sin(a)
            cy=y+h+w/2*math.sin(a)-h/2*math.cos(a)
            x,y=cx-w/2,cy-h/2
        layout['tiledVisuals'].append({'image':key,'rect':list(rect),'x':x,'y':y,
            'width':rect[2] if w is None else w,'height':rect[3] if h is None else h,
            'angle':angle-math.radians(rotation),'flip':flip,'opacity':opacity})
        layout['tiledDrawOrder'].append({'kind':'tile','index':len(layout['tiledVisuals'])-1})
        return definition,props,rect

    def collision(definition,gid,x,y,w,h,rotation=0):
        if rotation:raise ValueError('자동 충돌 타일의 회전은 타일 뒤집기/90도 회전 도구를 사용하세요.')
        _,_,_,rect=tile(gid);sw,sh=rect[2:]
        hflip,vflip,diagonal=bool(gid&H),bool(gid&V),bool(gid&D)
        for shape in definition.get('objectgroup',{}).get('objects',[]):
            klass=shape.get('class',shape.get('type',''))
            def point(px,py):
                u,v=_transform(px/sw,py/sh,hflip,vflip,diagonal)
                return x+u*w,y+v*h
            if 'polyline' in shape:
                if gid&(V|D):raise ValueError('자동 충돌 경사 타일은 수평 뒤집기만 사용하세요.')
                points=[point(shape.get('x',0)+p['x'],shape.get('y',0)+p['y']) for p in shape['polyline']]
                add_slope(points)
            else:
                a=point(shape.get('x',0),shape.get('y',0))
                b=point(shape.get('x',0)+shape['width'],shape.get('y',0)+shape['height'])
                target=layout['platforms'] if klass=='Platform' else layout['solids']
                target.append([min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])])

    def add_slope(points):
        for a,b in zip(points,points[1:]):
            if a[0]==b[0]:raise ValueError('경사면 선은 수직이 아닌 대각선으로 그려주세요.')
            if a[0]>b[0]:a,b=b,a
            layout['slopes'].append({'x1':a[0],'y1':a[1],'x2':b[0],'y2':b[1],'bottom':layout['height']})

    def walk(layers,ox=0,oy=0,visible=True,opacity=1):
        nonlocal background_found
        for layer in layers:
            lp=properties(layer)
            if lp.get('enabled',True) is False:continue
            lx,ly=ox+layer.get('offsetx',0),oy+layer.get('offsety',0)
            shown=visible and layer.get('visible',True)
            alpha=opacity*layer.get('opacity',1)
            kind=layer['type'];role=lp.get('role','')
            if kind=='group':walk(layer['layers'],lx,ly,shown,alpha);continue
            if kind=='imagelayer' and role=='background':
                if background_found:raise ValueError('배경 이미지 레이어는 한 개만 사용하세요.')
                image=(path.parent/layer['image']).resolve();w,h=png_size(image)
                if w<640 or h<360:raise ValueError('배경 이미지는 최소 640×360이어야 합니다.')
                ratio=(w-640)/max(1,layout['width']-640) if lp.get('fitToMap',True) else layer.get('parallaxx',1)
                layout['background']={'mode':'panorama','panorama':{'image':image_key(image),'width':w,'height':h,
                    'scrollRatio':max(0,ratio),'offsetX':lx,'offsetY':ly}}
                background_found=True;continue
            if kind=='tilelayer':
                if not shown:continue
                gids=_data(layer)
                if len(gids)!=layer['width']*layer['height']:raise ValueError('타일 레이어 데이터 길이가 잘못되었습니다.')
                for index,gid in enumerate(gids):
                    if not gid:continue
                    x=lx+(layer.get('x',0)+index%layer['width'])*tw
                    y=ly+(layer.get('y',0)+index//layer['width'])*th
                    definition,props,_,rect=tile(gid)
                    y+=th-rect[3]
                    visual(gid,x,y,opacity=alpha)
                    if lp.get('autoCollision',False):collision(definition,gid,x,y,rect[2],rect[3])
                continue
            if kind!='objectgroup':continue
            for obj in layer.get('objects',[]):
                if not obj.get('visible',True):continue
                op=properties(obj)
                if op.get('enabled',True) is False:continue
                gid=obj.get('gid',0)
                definition,tp,_,rect=tile(gid) if gid else ({},{},None,(0,0,0,0))
                props={**tp,**op};klass=obj.get('class') or obj.get('type') or definition.get('class') or definition.get('type','')
                x,y=lx+obj.get('x',0),ly+obj.get('y',0)
                w,h=obj.get('width',rect[2]),obj.get('height',rect[3])
                rotation=obj.get('rotation',0)
                if klass=='Spawn':spawns.append([x,y]);continue
                if klass in ('Solid','Platform'):
                    if rotation:raise ValueError('사각 충돌은 회전하지 말고 경사면 선을 사용하세요.')
                    target=layout['platforms'] if klass=='Platform' else layout['solids']
                    top=y-h if gid else y
                    collision_height=h
                    if gid:
                        collision_height=float(props.get('collisionHeight',rect[3]))*h/rect[3]
                        collision_height=max(1,min(h,collision_height))
                        if shown:visual(gid,x,top,w,h,rotation,alpha)
                    target.append([x,top,x+w,top+collision_height]);continue
                if klass=='Slope':
                    if rotation:raise ValueError('경사면은 선 끝점을 움직여 편집하세요.')
                    points=obj.get('polyline',[])
                    if len(points)<2:raise ValueError('경사면에는 선 끝점 두 개가 필요합니다.')
                    add_slope([(x+p['x'],y+p['y']) for p in points]);continue
                if klass in ('Torch','Armor'):
                    if not shown:continue
                    if rotation or gid&(H|V|D):raise ValueError('애니메이션 장식은 회전/뒤집기 없이 배치하세요.')
                    key='torch_body' if klass=='Torch' else 'armor';spec=layout['unitySprites'][key]
                    px,py=spec['pivot'];sw,sh=spec['rect'][2:]
                    if abs(w/sw-h/sh)>.001:raise ValueError('횃불·갑옷 크기는 가로세로 비율을 유지하세요.')
                    layout['props'].append({'kind':'torch' if klass=='Torch' else 'armor','x':x+w*px,
                        'bottom':y-h*py+float(props.get('groundOffset',0))*h/sh,'unitScale':w/sw*spec['ppu']})
                    layout['tiledDrawOrder'].append({'kind':'prop','index':len(layout['props'])-1});continue
                if klass=='CeilingDecoration':
                    # Ceiling tilesets use a top-left editor anchor, so their
                    # hanging mount stays on the ceiling when snapping.
                    if rotation:raise ValueError('천장 장식은 회전 없이 배치하세요.')
                    if shown:
                        visual(gid,x,y,w,h,opacity=alpha)
                        if props.get('flameAnimation',False):
                            layout['tiledVisuals'][-1]['animation']='chandelier-flames'
                        if props.get('warmLight',False):
                            layout['tiledVisuals'][-1]['light']='chandelier'
                    continue
                if klass=='Passage':
                    if rotation or gid&(H|V|D):raise ValueError('통로는 회전하지 말고 좌/우 통로 타일을 선택하세요.')
                    top=y-h if gid else y;left=round(x);right=round(x+w);bottom=round(top+h)
                    side=props.get('side','left');opening=round(props.get('openingHeight',104));gw=round(props.get('gateWidth',24))
                    if side not in ('left','right') or (right-left)%32 or gw<=0 or gw>right-left or opening<=32 or opening>h-32:
                        raise ValueError('통로 너비는 32의 배수, 위쪽 암벽은 32 이상, 입구 높이는 32보다 크게 지정하세요.')
                    identity=props.get('gateId') or f'gate-{obj["id"]}'
                    if identity in passage_ids:raise ValueError(f'철문 gateId가 중복됩니다: {identity}')
                    passage_ids.add(identity)
                    layout['sidePassages'].append({'id':identity,'side':side,'left':left,'right':right,'top':round(top),
                        'openingTop':bottom-opening,'bottom':bottom,'gateX':left if side=='left' else right-gw,'gateWidth':gw})
                    continue
                if gid and shown:
                    visual(gid,x,y-h,w,h,rotation,alpha)
                    if lp.get('autoCollision',False):collision(definition,gid,x,y-h,w,h,rotation)
    walk(data['layers'])
    if len(spawns)!=1:raise ValueError('시작 위치(Spawn) 점은 정확히 하나 배치하세요.')
    layout['spawn']=spawns[0]
    if not background_found:raise ValueError('role=background인 배경 이미지 레이어가 필요합니다.')
    return layout
