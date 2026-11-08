from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pico2d as p2d
from game.app import App
from game.scenes.field import FieldScene
from game.scenes.melee import MeleeScene
from game.combat import Vitals, resolve_encounter, attack_regions, attack_connects


class MeleeEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.app=App(data_directory=Path(cls.tmp.name),hidden=True)

    @classmethod
    def tearDownClass(cls):
        cls.app.close();cls.tmp.cleanup()

    def setUp(self):
        self.field=FieldScene(self.app,new_game=True)
        self.app.scene=self.field
        self.player=self.field.player
        self.enemy=self.field.enemies[0]
        self.enemy.speed=0
        self.player.x=690;self.player.y=288;self.player.facing=1

    def attack(self):
        self.field.handle_event(SimpleNamespace(type=p2d.SDL_KEYDOWN,key=p2d.SDLK_c))
        for _ in range(66):
            self.app.scene.update(1/60)

    def test_contact_damages_player_and_enters_melee(self):
        self.player.x=710
        self.field.update(1/60)
        self.assertIsInstance(self.app.scene,MeleeScene)
        self.assertEqual((self.player.hp,self.enemy.hp),(90,100))
        self.assertEqual(self.app.scene.cause,'enemy_contact')
        self.assertIs(self.app.scene.player,self.player)
        self.assertIs(self.app.scene.enemy,self.enemy)

    def test_c_attack_damages_slime_and_enters_melee(self):
        self.assertEqual((self.player.hp,self.enemy.hp),(100,100))
        self.attack()
        self.assertIsInstance(self.app.scene,MeleeScene)
        self.assertEqual((self.player.hp,self.enemy.hp),(100,90))
        self.assertEqual(self.app.scene.cause,'player_attack')

    def test_one_hit_only_and_field_stops(self):
        self.attack();positions=(self.player.x,self.enemy.x,self.enemy.time)
        for _ in range(30):
            self.field.update(.1);self.app.scene.update(.1)
            resolve_encounter(self.field)
        self.assertEqual((self.player.hp,self.enemy.hp),(100,90))
        self.assertEqual(positions,(self.player.x,self.enemy.x,self.enemy.time))
        self.assertFalse(self.field.keys)

    def test_attack_misses_out_of_range_or_wrong_direction(self):
        self.player.x=650;self.attack()
        self.assertIs(self.app.scene,self.field)
        self.setUp();self.player.facing=-1;self.attack()
        self.assertIs(self.app.scene,self.field)
        self.assertEqual((self.player.hp,self.enemy.hp),(100,100))

    def test_attack_requires_active_swing(self):
        self.player.attack()
        self.field.update(.1)
        self.assertIs(self.app.scene,self.field)
        self.player.attack_time=.6
        self.field.update(.01)
        self.assertIs(self.app.scene,self.field)

    def test_active_sword_wins_simultaneous_contact(self):
        self.player.x=710;self.player.attack_time=.8
        self.field.update(1/60)
        self.assertEqual((self.player.hp,self.enemy.hp),(100,90))

    def test_wall_blocks_opening_attack(self):
        self.field.passages.base_solids.append([717,230,719,288])
        self.attack()
        self.assertIs(self.app.scene,self.field)
        self.assertEqual(self.enemy.hp,100)

    def test_vertical_separation_does_not_trigger(self):
        self.player.y=200;self.player.attack_time=.8;self.field.update(1/120)
        self.assertIs(self.app.scene,self.field)
        self.assertEqual(self.enemy.hp,100)

    def test_dead_enemy_does_not_trigger(self):
        self.enemy.hp=0;self.player.x=710
        self.field.update(.1)
        self.assertIs(self.app.scene,self.field)
        self.assertEqual(self.player.hp,100)

    def test_escape_returns_to_title(self):
        from game.scenes.title import TitleScene
        self.attack()
        self.app.scene.handle_event(SimpleNamespace(type=p2d.SDL_KEYDOWN,key=p2d.SDLK_ESCAPE))
        self.assertIsInstance(self.app.scene,TitleScene)

    def test_windup_has_no_sword_hitbox(self):
        for time in (0,.2,.5,.7,.79,1.0,1.4):
            self.player.attack_time=time
            self.assertEqual(attack_regions(self.field),[],time)
            self.assertFalse(attack_connects(self.field,self.enemy))

    def test_sword_hit_is_visible_before_transition(self):
        self.player.attack()
        for _ in range(47):self.field.update(1/60)
        self.assertIs(self.app.scene,self.field)
        self.assertEqual(self.enemy.hp,100)
        for _ in range(3):
            self.field.update(1/60)
            if self.field.encounter:break
        self.assertEqual(self.enemy.hp,90)
        self.assertIs(self.app.scene,self.field)
        self.assertTrue(.79<=self.player.attack_time<1)
        self.assertTrue(attack_regions(self.field))
        self.field.update(.11)
        self.assertIsInstance(self.app.scene,MeleeScene)

    def test_blade_shape_misses_inside_old_rectangle(self):
        self.player.attack_time=.8
        self.enemy.scale=.25
        self.enemy.y=268
        self.enemy.x=self.player.x+10
        self.assertFalse(attack_connects(self.field,self.enemy))

    def test_mirrored_swing(self):
        self.player.x=750;self.player.facing=-1;self.player.attack_time=.8
        self.assertTrue(attack_connects(self.field,self.enemy))
        self.player.facing=1
        self.assertFalse(attack_connects(self.field,self.enemy))

    def test_health_clamps_at_zero(self):
        actor=Vitals();actor.take_damage(150)
        self.assertEqual(actor.hp,0)


if __name__=='__main__':unittest.main()
