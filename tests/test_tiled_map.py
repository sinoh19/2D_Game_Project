"""Portable regression checks for the project's Tiled map bridge."""
import base64,copy,json,struct,sys,tempfile,unittest,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from game.tiled_map import load_map


class TiledMapTests(unittest.TestCase):
    def setUp(self):
        self.map=ROOT/'maps/dungeon_01.tmj'
        self.base=json.loads((ROOT/'assets/dungeon/dungeon_01.json').read_text(encoding='utf-8'))
        self.data=json.loads(self.map.read_text(encoding='utf-8'))

    def load(self,data=None):
        if data is None:return load_map(self.map,self.base,ROOT/'assets/dungeon')
        data=copy.deepcopy(data)
        for ts in data['tilesets']:ts['source']=str((self.map.parent/ts['source']).resolve())
        for layer in data['layers']:
            if layer['type']=='imagelayer':layer['image']=str((self.map.parent/layer['image']).resolve())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'dungeon_01.tmj';path.write_text(json.dumps(data),encoding='utf-8')
            return load_map(path,self.base,ROOT/'assets/dungeon')

    def test_migration_preserves_gameplay_geometry(self):
        loaded=self.load()
        for key in ('width','height','spawn','solids','platforms','slopes','props'):
            self.assertEqual(loaded[key],self.base[key],key)
        for old,new in zip(self.base['sidePassages'],loaded['sidePassages']):
            for key in old:self.assertEqual(old[key],new[key],key)

    def test_painted_tile_adds_visual_and_collision(self):
        before=self.load();layer=next(l for l in self.data['layers'] if any(p.get('name')=='autoCollision' and p.get('value') for p in l.get('properties',[])))
        layer['data'][5*layer['width']+30]=1
        after=self.load(self.data)
        self.assertEqual(len(after['tiledVisuals']),len(before['tiledVisuals'])+1)
        self.assertIn([960,160,992,192],after['solids'])

    def test_prop_spawn_and_slope_edits_are_read(self):
        props=next(l for l in self.data['layers'] if l['name']=='횃불·갑옷')['objects']
        props[1]['x']+=40
        spawn=next(l for l in self.data['layers'] if l['name']=='시작 위치')['objects'][0];spawn['x']=140
        slope=next(l for l in self.data['layers'] if l['name']=='대각선 경사면')['objects'][0];slope['polyline'][1]['y']=-48
        loaded=self.load(self.data)
        self.assertEqual(loaded['props'][1]['x'],self.base['props'][1]['x']+40)
        self.assertEqual(loaded['spawn'],[140,288])
        self.assertEqual(loaded['slopes'][0]['y2'],240)

    def test_compressed_layer_and_horizontal_flip(self):
        layer=next(l for l in self.data['layers'] if l['type']=='tilelayer')
        baseline=self.load();layer['data'][0]=0x80000001
        layer['data']=base64.b64encode(zlib.compress(struct.pack('<'+'I'*(layer['width']*layer['height']),*layer['data']))).decode()
        layer.update(encoding='base64',compression='zlib')
        loaded=self.load(self.data)
        self.assertTrue(any(v['x']==0 and v['y']==0 and v['flip']=='h' for v in loaded['tiledVisuals']))
        self.assertEqual(len(loaded['solids']),len(baseline['solids']))

    def test_background_adapts_to_map_width(self):
        self.data['width']=160
        loaded=self.load(self.data)
        self.assertEqual(loaded['width'],5120)
        self.assertAlmostEqual(loaded['background']['panorama']['scrollRatio'],440/4480)

    def test_missing_spawn_is_reported(self):
        next(l for l in self.data['layers'] if l['name']=='시작 위치')['objects']=[]
        with self.assertRaisesRegex(ValueError,'Spawn'):self.load(self.data)

    def test_auto_collision_slopes_can_be_mirrored(self):
        layer=next(l for l in self.data['layers'] if l['name']=='새 지형 (자동 충돌)')
        layer['data'][5*80+35]=0x80000006
        loaded=self.load(self.data)
        self.assertIn({'x1':1120.0,'y1':176.0,'x2':1152.0,'y2':192.0,'bottom':360},loaded['slopes'])

    def test_visual_object_rotation_uses_bottom_left_anchor(self):
        layer=next(l for l in self.data['layers'] if l['name']=='기존 세밀 배치')
        layer['objects'].append({'id':999,'gid':1,'x':200,'y':200,'width':32,'height':16,'rotation':90})
        loaded=self.load(self.data)
        rotated=[v for v in loaded['tiledVisuals'] if abs(v['angle']+1.5707963267948966)<.001][-1]
        self.assertAlmostEqual(rotated['x'],192)
        self.assertAlmostEqual(rotated['y'],208)

    def test_platform_object_moves_its_picture_and_collision(self):
        layer=next(l for l in self.data['layers'] if l['name']=='발판')
        obj=layer['objects'][0]
        obj['x']+=32;obj['y']-=16
        loaded=self.load(self.data)
        self.assertIn([224,232,288,240],loaded['platforms'])
        self.assertNotIn([192,248,256,256],loaded['platforms'])
        self.assertTrue(any(v['x']==224 and v['y']==232 and v['width']==64 for v in loaded['tiledVisuals']))

    def test_new_platform_inherits_visible_one_way_collision(self):
        layer=next(l for l in self.data['layers'] if l['name']=='발판')
        layer['objects'].append({'id':999,'gid':2001,'x':800,'y':200,'width':32,'height':16,'rotation':0})
        loaded=self.load(self.data)
        self.assertIn([800,184,832,192],loaded['platforms'])
        self.assertNotIn([800,184,832,192],loaded['solids'])
        self.assertTrue(any(v['x']==800 and v['y']==184 and loaded['images'][v['image']].endswith('platform-32.png') for v in loaded['tiledVisuals']))

    def test_new_level_template_uses_automatic_collision(self):
        data=json.loads((ROOT/'maps/new_level_template.tmj').read_text(encoding='utf-8'))
        loaded=self.load(data)
        self.assertEqual(loaded['props'],[])
        self.assertGreater(len(loaded['solids']),100)
        self.assertEqual(loaded['spawn'],[88,288])


if __name__=='__main__':unittest.main()
