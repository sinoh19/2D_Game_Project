"""Temporary text-only scene for validating melee encounter transitions."""
import pico2d as p2d
from game import drawing


class MeleeScene:
    def __init__(self, app, field, enemy, cause):
        self.app = app
        self.field = field
        self.player = field.player
        self.enemy = enemy
        self.cause = cause

    def update(self, dt):
        pass

    def save(self):
        self.field.save()

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN and event.key == p2d.SDLK_ESCAPE:
            self.save()
            self.app.show_title()

    def draw(self):
        drawing.rectangle((0,0,639,359),(0,0,0),filled=True)
        drawing.text(self.app.resources.dialogue,270,130,'근접 전투')
        message = '선제공격: 슬라임에게 10 피해' if self.cause == 'player_attack' else '슬라임 접촉: 플레이어에게 10 피해'
        drawing.text(self.app.resources.small,210,180,message)
        drawing.text(self.app.resources.small,220,212,
                     f'플레이어 HP {self.player.hp} / {self.player.max_hp}     슬라임 HP {self.enemy.hp} / {self.enemy.max_hp}')
        drawing.text(self.app.resources.small,244,280,'전투 진입 확인용 화면 · ESC 메인')
