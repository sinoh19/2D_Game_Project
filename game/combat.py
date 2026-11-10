"""Field encounter rules, independent of the eventual turn-based battle UI."""
from random import randint

DEFAULT_HP = 100
HIT_DAMAGE = 10
BASE_PHYSICAL_DAMAGE = 7


def apply_strength(base_damage, strength):
    # Strength adds 1/20 of base damage per point, rounding halves up.
    return (base_damage * (20 + strength) + 10) // 20


def roll_physical_damage(strength):
    return apply_strength(BASE_PHYSICAL_DAMAGE, strength) + randint(-2, 2)


class Vitals:
    def __init__(self):
        self.max_hp = DEFAULT_HP
        self.hp = self.max_hp

    def take_damage(self, damage=HIT_DAMAGE):
        self.hp = max(0, self.hp-max(0, damage))


def overlaps(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def enemy_bounds(enemy):
    frame = enemy.motion['frames'][enemy.frame]
    foot = enemy.y+(frame['footY']-enemy.motion['pivot'][1])*enemy.scale
    half = frame['bodyWidth']*enemy.scale/2
    return (enemy.x-half, foot-frame['bodyHeight']*enemy.scale, enemy.x+half, foot)


def player_bounds(player):
    return (player.x-player.HALF_WIDTH, player.y-player.HEIGHT,
            player.x+player.HALF_WIDTH, player.y)


def attack_regions(scene):
    """World-space strips following the visible blade/arc of this exact frame."""
    player = scene.player
    if player.attack_time is None:
        return []
    clip = scene.assets.animations['clips']['attack']
    index = 0
    for i, candidate in enumerate(clip['frames']):
        if candidate['time'] > player.attack_time+1e-8:
            break
        index = i
    frame = clip['frames'][index]
    px, py = frame['pivot']
    height = frame['rect'][3]
    scale = scene.assets.character_scale
    regions = []
    for x,y,w,h in scene.assets.attack_hitboxes['frames'].get(str(index),[]):
        left = player.x+(x-px)*scale*player.facing
        right = player.x+(x+w-px)*scale*player.facing
        top = player.y+(y-height+py)*scale
        regions.append((min(left,right),top,max(left,right),top+h*scale))
    return regions


def attack_connects(scene, enemy):
    target = enemy_bounds(enemy)
    for region in attack_regions(scene):
        if not overlaps(region,target):
            continue
        hit_y = (max(region[1],target[1])+min(region[3],target[3]))/2
        if not any(min(scene.player.x,enemy.x) < r and max(scene.player.x,enemy.x) > l
                   and t < hit_y < b for l,t,r,b in scene.solids):
            return True
    return False


def resolve_encounter(scene):
    """Choose exactly one opening hit, then hand the same actors to battle."""
    if scene.encounter is not None:
        return False
    living = [enemy for enemy in scene.enemies if enemy.hp > 0]
    # A valid sword hit wins over simultaneous body contact.
    attacked = [enemy for enemy in living if attack_connects(scene,enemy)]
    touched = [enemy for enemy in living
               if overlaps(player_bounds(scene.player),enemy_bounds(enemy))]
    targets = attacked or touched
    if not targets:
        return False
    enemy = min(targets,key=lambda e:abs(e.x-scene.player.x))
    cause = 'player_attack' if attacked else 'enemy_contact'
    if attacked:
        enemy.take_damage(roll_physical_damage(scene.player.strength))
    else:
        scene.player.take_damage(enemy.roll_damage())
    scene.encounter = (enemy,cause)
    scene.keys.clear()
    scene.app.start_melee(scene,enemy,cause)
    return True
