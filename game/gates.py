"""Side passages with persistent, mechanically rising lift gates."""
import math
from pathlib import Path
import pico2d as p2d
from game import drawing
from game.config import ASSETS, SCALE, WINDOW_HEIGHT


class LiftGate:
    def __init__(self, spec, opened=False):
        self.spec=spec
        self.state='open' if opened else 'closed'
        self.clock=1.52 if opened else 0.0

    @property
    def height(self):return self.spec['bottom']-self.spec['openingTop']

    @property
    def lift(self):
        if self.state=='open':return self.height
        if self.state=='closed':return 0
        t=max(0.0,min(1.0,(self.clock-.12)/1.4))
        return min(self.height,math.floor(self.height*(t*t*(3-2*t))/2)*2)

    @property
    def rect(self):
        s=self.spec;bottom=s['bottom']-self.lift
        if bottom<=s['openingTop']:return None
        return (s['gateX'],s['openingTop'],s['gateX']+s['gateWidth'],bottom)

    def begin(self):
        if self.state!='closed':return False
        self.state='opening';self.clock=0.0
        return True

    def update(self,dt):
        if self.state=='opening':
            self.clock=min(1.52,self.clock+dt)
            if self.clock>=1.52:self.state='open'


class SidePassages:
    def __init__(self,scene,restore=True):
        self.scene=scene
        data=scene.app.storage.read('gates.json',{}) if restore else {}
        opened=data.get('opened',[]) if data.get('scene')=='dungeon_01' else []
        if not isinstance(opened,list):opened=[]
        self.gates=[LiftGate(s,s['id'] in opened) for s in scene.layout.get('sidePassages',[])]
        self.base_solids=list(scene.layout['solids'])
        self.base_solids += [(g.spec['left'],0,g.spec['right'],g.spec['openingTop']) for g in self.gates]
        assets=scene.assets
        if not hasattr(assets,'gate_sound'):
            assets.gate_sound=None
            try:
                assets.gate_sound=p2d.load_wav(str(ASSETS/'dungeon/side_passages/gate-ratchet.wav'))
                assets.gate_sound.set_volume(38)
            except (OSError,IOError):
                pass
        self.sound=assets.gate_sound
        self.sync()

    def sync(self):
        self.scene.solids[:]=self.base_solids+[g.rect for g in self.gates if g.rect is not None]

    def nearby(self):
        player=self.scene.player
        candidates=[g for g in self.gates if abs(player.x-(g.spec['gateX']+g.spec['gateWidth']/2))<=76
                    and abs(player.y-g.spec['bottom'])<=24]
        return min(candidates,key=lambda g:abs(player.x-g.spec['gateX'])) if candidates else None

    def interact(self):
        gate=self.nearby()
        if gate and self.scene.player.grounded and gate.begin():
            if self.sound is not None:self.sound.play()
            return True
        return False

    def update(self,dt):
        for gate in self.gates:gate.update(dt)
        self.sync()

    def save(self):
        # A gate already being opened resumes fully open, rather than trapping
        # a player who saved while standing in its opening.
        opened=[g.spec['id'] for g in self.gates if g.state!='closed']
        self.scene.app.storage.write('gates.json',{'version':1,'scene':'dungeon_01','opened':opened})

    def draw(self,camera):
        assets=self.scene.assets
        for gate in self.gates:
            s=gate.spec
            if s['right']<camera or s['left']>camera+assets.view_width:continue
            # Keep the shared dungeon panorama visible through the passage.
            # Draw the gate behind the stone. A four-pixel continuation
            # enters the header pocket, closing the tiny alpha-edge gap
            # without shifting the panel's floor contact or collider.
            gx=s['gateX']-camera;w=s['gateWidth']
            remaining=max(0,gate.height-gate.lift)
            if remaining:
                jitter=1 if gate.state=='opening' and int(gate.clock*24)%3==1 else 0
                panel=assets.images['lift_gate']
                panel.clip_draw(0,0,w,remaining,(gx+w/2+jitter)*SCALE,
                    WINDOW_HEIGHT-(s['openingTop']+remaining/2)*SCALE,w*SCALE,remaining*SCALE)
                panel.clip_draw(0,min(panel.h-4,remaining),w,4,(gx+w/2+jitter)*SCALE,
                    WINDOW_HEIGHT-(s['openingTop']-2)*SCALE,w*SCALE,4*SCALE)
            cap_top=s['openingTop']-32
            for x in range(s['left'],s['right'],32):
                edge=None
                if s['side']=='left' and x==s['right']-32:edge='right'
                if s['side']=='right' and x==s['left']:edge='left'
                for y in range(0,cap_top,32):
                    key='passage_wall_'+edge if edge else 'Fill'
                    assets.tile(key,x,y,32,min(32,cap_top-y),camera)
                # The underside and exposed side share the original rock
                # material and an actual bottom corner, without an overhang.
                cap='passage_corner_b'+('r' if edge=='right' else 'l') if edge else 'passage_ceiling'
                assets.tile(cap,x,cap_top,32,32,camera)

    def draw_hint(self):
        gate=self.nearby()
        if gate is None or gate.state=='open':return
        text={'closed':'E  철문 열기','opening':'철문 개방 중…','open':'통로 열림'}[gate.state]
        x=max(10,min(540,self.scene.x-self.scene.camera_x-30))
        y=max(34,self.scene.y-68)
        drawing.rectangle((x-4,y-13,x+92,y+4),(18,19,25),filled=True)
        drawing.text(self.scene.app.resources.small,x,y,text,(210,205,183))
