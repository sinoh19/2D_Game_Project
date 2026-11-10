"""Freeze the hit frame, then sweep pixel tiles into the melee scene."""
import math
import pico2d as p2d
from game import drawing

FREEZE_SECONDS = .16
COVER_SECONDS = .28
BLACK_SECONDS = .04
REVEAL_SECONDS = .24
TILE_SIZE = 32


class MeleeTransitionScene:
    def __init__(self, app, source, destination):
        self.app = app
        self.source = source
        self.destination = destination
        self.elapsed = 0.0
        self.finished = False
        self.slime_hit = destination.cause == 'player_attack'
        self.hold_seconds = FREEZE_SECONDS
        self.cover_end = self.hold_seconds + COVER_SECONDS
        self.reveal_start = self.cover_end + BLACK_SECONDS
        self.duration = self.reveal_start + REVEAL_SECONDS
        self.focus = (max(0,min(639,destination.enemy.x-source.camera_x)),
                      max(0,min(359,destination.enemy.y-12)))

    @property
    def phase(self):
        if self.elapsed < self.hold_seconds:return 'freeze'
        if self.elapsed < self.cover_end:return 'cover'
        if self.elapsed < self.reveal_start:return 'black'
        if self.elapsed < self.duration:return 'reveal'
        return 'done'

    def update(self, dt):
        if self.finished:return
        self.elapsed = min(self.duration,self.elapsed+max(0.0,dt))
        # Neither the frozen field nor the battle advances during the effect.
        if self.elapsed >= self.duration:
            self.finished = True
            self.app.scene = self.destination

    def save(self):
        self.source.save()

    def handle_event(self, event):
        if event.type == p2d.SDL_KEYDOWN and event.key == p2d.SDLK_ESCAPE:
            self.save()
            self.finished = True
            self.app.show_title()

    def tile_amount(self, column, row):
        phase=self.phase
        if phase=='freeze':return 0.0
        if phase=='black':return 1.0
        if phase=='done':return 0.0
        distance=math.hypot(column*TILE_SIZE+16-self.focus[0],row*TILE_SIZE+16-self.focus[1])
        farthest=max(math.hypot(x-self.focus[0],y-self.focus[1])
                     for x in (0,640) for y in (0,360))
        delay=min(1.0,distance/max(1,farthest))*.45
        if phase=='cover':
            progress=(self.elapsed-self.hold_seconds)/COVER_SECONDS
            return max(0.0,min(1.0,(progress-delay)/.55))
        progress=(self.elapsed-self.reveal_start)/REVEAL_SECONDS
        return 1-max(0.0,min(1.0,(progress-delay)/.55))

    def draw(self):
        phase=self.phase
        if phase=='black':
            drawing.rectangle((0,0,639,359),(0,0,0),filled=True)
            return
        if phase in ('freeze','cover'):
            if self.slime_hit:
                self.source.draw(hit_enemy=self.destination.enemy,
                                 hit_elapsed=max(0.0, self.elapsed - self.hold_seconds))
            else:
                self.source.draw(hit_by=self.destination.enemy, hit_elapsed=self.elapsed)
        else:
            self.destination.draw()
        if phase in ('freeze','done'):return
        for row in range(math.ceil(360/TILE_SIZE)):
            for column in range(640//TILE_SIZE):
                amount=self.tile_amount(column,row)
                width=round(TILE_SIZE*amount)
                if width:
                    left=column*TILE_SIZE+(TILE_SIZE-width)//2
                    drawing.rectangle((left,row*TILE_SIZE,left+width-1,min(359,(row+1)*TILE_SIZE-1)),
                                      (0,0,0),filled=True)
