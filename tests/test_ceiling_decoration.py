"""Ceiling decoration placement must match Tiled's top-left anchor."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from game.tiled_map import load_map


class CeilingDecorationTests(unittest.TestCase):
    def test_chandelier_hangs_from_top_anchor_without_collision(self):
        base = json.loads((ROOT/'assets/dungeon/dungeon_01.json').read_text(encoding='utf-8'))
        data = json.loads((ROOT/'maps/new_level_template.tmj').read_text(encoding='utf-8'))
        for ts in data['tilesets']:
            if ts['source'].endswith('ceiling-decorations.tsj'):
                gid = ts['firstgid']
            ts['source'] = str((ROOT/'maps'/ts['source']).resolve())
        for layer in data['layers']:
            if layer['type'] == 'imagelayer':
                layer['image'] = str((ROOT/'maps'/layer['image']).resolve())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'ceiling.tmj'
            path.write_text(json.dumps(data), encoding='utf-8')
            before = load_map(path, base, ROOT/'assets/dungeon')
            data['layers'].append(dict(type='objectgroup', name='ceiling', objects=[
                dict(id=900, gid=gid, x=320, y=32, width=48, height=64)]))
            path.write_text(json.dumps(data), encoding='utf-8')
            after = load_map(path, base, ROOT/'assets/dungeon')
        sprite = after['tiledVisuals'][-1]
        self.assertEqual((sprite['x'],sprite['y'],sprite['width'],sprite['height']), (320,32,48,64))
        self.assertEqual(sprite['light'], 'chandelier')
        self.assertEqual(sprite['animation'], 'chandelier-flames')
        for key in ('solids','platforms','slopes'):
            self.assertEqual(after[key],before[key])


if __name__ == '__main__':
    unittest.main()
