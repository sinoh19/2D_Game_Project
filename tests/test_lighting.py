"""Light falloff stays gentle; sources follow editor positions and sizes."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from game.lighting import glow_pixels,light_sources,flicker


class FireLightTests(unittest.TestCase):
    def test_light_fades_to_transparent_edge(self):
        pixels=glow_pixels(96)
        alpha=lambda x,y:pixels[(y*96+x)*4+3]
        self.assertEqual(alpha(0,0),0)
        self.assertEqual(alpha(0,48),0)
        self.assertGreater(alpha(48,48),alpha(70,48))
        self.assertGreater(alpha(70,48),alpha(85,48))
        self.assertLessEqual(max(pixels[3::4]),54)

    def test_moving_and_scaling_chandelier_moves_all_lights(self):
        item=dict(light='chandelier',x=100,y=32,width=48,height=64,opacity=1)
        layout=dict(props=[],tiledVisuals=[item])
        first=light_sources(layout)
        item.update(x=180,y=64,width=96,height=128,opacity=.5)
        second=light_sources(layout)
        self.assertEqual(len(second),4)
        for a,b in zip(first,second):
            self.assertAlmostEqual(b[0],180+(a[0]-100)*2)
            self.assertAlmostEqual(b[1],64+(a[1]-32)*2)
            self.assertAlmostEqual(b[2],a[2]*2)
            self.assertAlmostEqual(b[3],a[3]*.5)
        del item['light']
        self.assertEqual(light_sources(layout),[])

    def test_flicker_is_small_and_continuous(self):
        values=[flicker(i/60,1) for i in range(120)]
        self.assertGreater(min(values),.94)
        self.assertLess(max(values),1.06)
        self.assertLess(max(abs(a-b) for a,b in zip(values,values[1:])),.01)


if __name__=='__main__':unittest.main()
