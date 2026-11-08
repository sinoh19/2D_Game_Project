"""Behavior checks for connected stone shading, independent of an SDL window."""
import copy,json,math,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from game.terrain_interior import rasterize,interior_alpha,TerrainInterior
from game.tiled_map import load_map


def sprite(x=0,y=0,**values):
    return dict(image='stone',rect=[0,0,2,2],x=x,y=y,width=4,height=4,
                angle=0,flip='',opacity=1,terrainInterior=True,**values)


class InteriorTests(unittest.TestCase):
    def test_surface_is_visible_and_deep_stone_becomes_dark(self):
        mask=bytearray([0]*32+[1]*128)
        a=interior_alpha(mask,8,20,step=1,surface=2,fade=8)
        self.assertEqual(a[4*8+4],0)
        self.assertEqual(a[6*8+4],0)
        self.assertGreater(a[10*8+4],0)
        self.assertEqual(a[18*8+4],248)
        self.assertFalse(any(a[:32]))

    def test_map_edge_is_not_an_exposed_air_surface(self):
        mask=bytearray([0]*16+[1]*112)
        a=interior_alpha(mask,8,16,step=1,surface=0,fade=5)
        self.assertEqual(a[12*8],a[12*8+4])
        self.assertEqual(a[12*8+4],248)
        self.assertEqual(interior_alpha(bytearray([1]*64),8,8)[27],248)

    def test_hole_reveals_both_side_edges_without_covering_air(self):
        mask=bytearray([1]*121)
        for y in range(11):mask[y*11+5]=0
        a=interior_alpha(mask,11,11,step=1,surface=0,fade=3)
        self.assertEqual(a[5*11+5],0)
        self.assertEqual(a[5*11+4],0)
        self.assertEqual(a[5*11+6],0)
        self.assertGreater(a[5*11+1],a[5*11+3])

    def test_adjacent_tiles_share_depth_without_a_seam(self):
        images={'stone':(2,2,bytes([255]*4))}
        mask,w,h=rasterize([sprite(0,2),sprite(4,2)],images,8,8,step=1)
        alpha=interior_alpha(mask,w,h,step=1,surface=0,fade=4)
        self.assertGreater(alpha[3*w+3],0)
        self.assertEqual(alpha[3*w+3],alpha[3*w+4])

    def test_transparent_half_and_flips_follow_the_sprite(self):
        images={'stone':(2,2,bytes([255,0,255,0]))}
        original=sprite()
        mask,w,_=rasterize([original],images,4,4,step=1)
        self.assertEqual(list(mask[:4]),[1,1,0,0])
        flipped={**original,'flip':'h'}
        mask,_,_=rasterize([flipped],images,4,4,step=1)
        self.assertEqual(list(mask[:4]),[0,0,1,1])
        rotated={**original,'angle':math.pi/2}
        mask,_,_=rasterize([rotated],images,4,4,step=1)
        self.assertFalse(any(mask[:8]));self.assertTrue(all(mask[8:]))

    def test_decorations_do_not_contribute_solid_material(self):
        prop={**sprite(),'terrainInterior':False}
        mask,_,_=rasterize([prop],{},4,4,step=1)
        self.assertFalse(any(mask))

    def test_disabled_effect_does_not_read_or_upload_textures(self):
        effect=TerrainInterior(SimpleNamespace(layout={'terrainInteriorShading':False},scale=2))
        self.assertIsNone(effect.image)

    def test_loader_marks_only_stone_and_keeps_map_options(self):
        base=json.loads((ROOT/'assets/dungeon/dungeon_01.json').read_text(encoding='utf-8'))
        path=ROOT/'maps/dungeon_01.tmj';layout=load_map(path,base,ROOT/'assets/dungeon')
        marked=0;unmarked=0
        for v in layout['tiledVisuals']:
            name=Path(layout['images'][v['image']]).name
            if name=='terrain.png' or name=='stair-floor-joins.png' or name.startswith('platform-'):
                self.assertTrue(v.get('terrainInterior'));marked+=1
            else:
                self.assertFalse(v.get('terrainInterior'));unmarked+=1
        self.assertGreater(marked,0);self.assertGreater(unmarked,0)
        data=json.loads(path.read_text(encoding='utf-8'))
        for t in data['tilesets']:t['source']=str((path.parent/t['source']).resolve())
        for layer in data['layers']:
            if layer['type']=='imagelayer':layer['image']=str((path.parent/layer['image']).resolve())
        data['properties'] += [dict(name='terrainInteriorShading',type='bool',value=False),
                               dict(name='terrainInteriorDepth',type='float',value=72)]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.tmj';p.write_text(json.dumps(data),encoding='utf-8')
            result=load_map(p,base,ROOT/'assets/dungeon')
        self.assertFalse(result['terrainInteriorShading']);self.assertEqual(result['terrainInteriorDepth'],72)
        for key in ('solids','platforms','slopes','props','spawn','sidePassages'):
            self.assertEqual(result[key],layout[key])


if __name__=='__main__':unittest.main()
