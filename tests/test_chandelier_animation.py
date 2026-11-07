"""Flame-only pixel motion remains anchored and loops without body drift."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from game.chandelier import flame_frames,frame_index


class FlameAnimationTests(unittest.TestCase):
    def test_each_flame_moves_but_the_wicks_and_body_do_not(self):
        raw=bytearray(48*64*4)
        for x in (5,24,42):
            for y in range(46,51):
                i=(y*48+x)*4;raw[i:i+4]=bytes((240,150,20,255))
            i=(51*48+x)*4;raw[i:i+4]=bytes((60,60,65,255))
        frames=flame_frames(raw,48,64)
        self.assertEqual(len(frames),6)
        for left,right in ((0,16),(16,32),(32,48)):
            regions=[b''.join(f[(y*48+left)*4:(y*48+right)*4] for y in range(44,51)) for f in frames]
            self.assertGreater(len(set(regions)),1)
        for frame in frames:
            self.assertEqual(frame[:44*48*4],raw[:44*48*4])
            self.assertEqual(frame[51*48*4:],raw[51*48*4:])
            # Every occupied flame row touches the next, with no flying debris.
            for left,right in ((0,16),(16,32),(32,48)):
                rows=[y for y in range(44,51) if any(frame[(y*48+x)*4+3] for x in range(left,right))]
                self.assertEqual(rows,list(range(min(rows),51)))

    def test_loop_has_six_frames_at_eight_fps(self):
        self.assertEqual([frame_index(n/8) for n in range(12)],list(range(6))*2)


if __name__=='__main__':unittest.main()
