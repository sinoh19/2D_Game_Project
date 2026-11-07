"""Armor tile anchors align the visible feet with the editor's floor grid."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from game.tiled_map import load_map


class ArmorGroundingTests(unittest.TestCase):
    def test_visible_feet_follow_floor_anchor_at_both_scales(self):
        base = json.loads((ROOT/'assets/dungeon/dungeon_01.json').read_text(encoding='utf-8'))
        original = json.loads((ROOT/'maps/new_level_template.tmj').read_text(encoding='utf-8'))
        for scale in (1, 2):
            with self.subTest(scale=scale), tempfile.TemporaryDirectory() as tmp:
                data = copy.deepcopy(original)
                for ts in data['tilesets']:
                    if ts['source'].endswith('objects.tsj'):
                        armor_gid = ts['firstgid'] + 1
                    ts['source'] = str((ROOT/'maps'/ts['source']).resolve())
                for layer in data['layers']:
                    if layer['type'] == 'imagelayer':
                        layer['image'] = str((ROOT/'maps'/layer['image']).resolve())
                data['layers'].append(dict(type='objectgroup', name='test armor', objects=[
                    dict(id=900, gid=armor_gid, x=320, y=288, width=38*scale, height=76*scale)]))
                path = Path(tmp)/'grounding.tmj'
                path.write_text(json.dumps(data), encoding='utf-8')
                layout = load_map(path, base, ROOT/'assets/dungeon')
                armor = next(p for p in layout['props'] if p['kind'] == 'armor')
                spec = layout['unitySprites']['armor']
                # The shared 2px rendering treatment leaves two transparent
                # rows below the original armor. The anchor correction scales.
                image_bottom = armor['bottom'] + 76*scale*spec['pivot'][1]
                self.assertAlmostEqual(image_bottom - 2*scale, 288)
                self.assertAlmostEqual(armor['unitScale'], 24*scale)


if __name__ == '__main__':
    unittest.main()
