import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from game.enemies import Slime
from game.tiled_map import load_map


class SlimeTests(unittest.TestCase):
    def setUp(self):
        self.motion=json.loads((ROOT/'assets/dungeon/monsters/slime/move.json').read_text(encoding='utf-8'))
        self.spec=dict(x=720,y=288,patrolLeft=640,patrolRight=800,speed=48,scale=1,direction='left')
        self.scene=SimpleNamespace(solids=[[0,288,2560,360]],platforms=[],slopes=[])

    def advance(self,e,seconds,dt=1/60):
        for _ in range(round(seconds/dt)): e.update(dt,self.scene)

    def test_round_trip_stays_in_range_and_faces_travel_direction(self):
        e=Slime(self.spec,self.motion);directions=set();xs=[]
        for _ in range(60*35):
            e.update(1/60,self.scene);xs.append(e.x);directions.add(e.facing)
            self.assertGreaterEqual(e.x,640);self.assertLessEqual(e.x,800)
        self.assertEqual(directions,{-1,1})
        self.assertLess(min(xs),641);self.assertGreater(max(xs),799)

    def test_grounded_frames_do_not_slide(self):
        e=Slime(self.spec,self.motion)
        self.advance(e,.25)
        self.assertAlmostEqual(e.x,720)
        self.advance(e,.25)
        self.assertLess(e.x,720)
        e.time=.625;x=e.x
        self.advance(e,.375)
        self.assertAlmostEqual(e.x,x)

    def test_frame_rate_independence(self):
        a=Slime(self.spec,self.motion);b=Slime(self.spec,self.motion)
        self.advance(a,20,1/30);self.advance(b,20,1/144)
        self.assertAlmostEqual(a.x,b.x,delta=.5)
        self.assertEqual(a.frame,b.frame)

    def test_turn_before_cliff(self):
        self.scene.solids=[[680,288,820,360]]
        e=Slime(self.spec,self.motion)
        for _ in range(300):
            e.update(1/60,self.scene)
            self.assertGreaterEqual(e.x-12,680)
        self.assertEqual(e.facing,1)

    def test_turn_before_wall(self):
        self.scene.solids.append([680,240,690,288])
        e=Slime(self.spec,self.motion)
        for _ in range(180):
            e.update(1/60,self.scene)
            self.assertGreaterEqual(e.x-12,690)
        self.assertEqual(e.facing,1)

    def load(self,edit=None,mapname='dungeon_01.tmj'):
        path=ROOT/'maps'/mapname
        base=json.loads((ROOT/'assets/dungeon/dungeon_01.json').read_text(encoding='utf-8'))
        if edit is None:return load_map(path,base,ROOT/'assets/dungeon')
        d=json.loads(path.read_text(encoding='utf-8'));edit(d)
        for t in d['tilesets']:t['source']=str(path.parent/t['source'])
        for l in d['layers']:
            if l['type']=='imagelayer':l['image']=str(path.parent/l['image'])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/path.name;p.write_text(json.dumps(d),encoding='utf-8')
            return load_map(p,base,ROOT/'assets/dungeon')

    def test_editor_properties_and_geometry_separate(self):
        before=self.load()
        def edit(d):
            o=next(l for l in d['layers'] if l['name']=='몬스터')['objects'][0]
            o['x']+=16
            next(p for p in o['properties'] if p['name']=='speed')['value']=60
        after=self.load(edit)
        self.assertEqual(after['enemies'][0]['x'],736)
        self.assertEqual(after['enemies'][0]['speed'],60)
        for k in ('solids','platforms','slopes','props','tiledVisuals'):
            self.assertEqual(before[k],after[k])

    def test_hidden_enemies_are_not_spawned(self):
        def edit(d):next(l for l in d['layers'] if l['name']=='몬스터')['visible']=False
        self.assertEqual(self.load(edit)['enemies'],[])

    def test_invalid_patrol_is_reported(self):
        def edit(d):
            o=next(l for l in d['layers'] if l['name']=='몬스터')['objects'][0]
            next(p for p in o['properties'] if p['name']=='patrolLeft')['value']=900
        with self.assertRaises(ValueError):self.load(edit)

    def test_template_has_palette_without_spawned_enemies(self):
        self.assertEqual(self.load(mapname='new_level_template.tmj')['enemies'],[])


if __name__=='__main__':unittest.main()
