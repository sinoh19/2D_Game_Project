"""Field encounter rules, independent of the eventual turn-based battle UI."""
DEFAULT_HP = 100
HIT_DAMAGE = 10
ATTACK_START = .2
ATTACK_END = .5
ATTACK_REACH = 30.0


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


def attack_bounds(player):
    start = player.x
    end = start+player.facing*(player.HALF_WIDTH+ATTACK_REACH)
    return (min(start,end), player.y-36, max(start,end), player.y+2)


def attack_connects(scene, enemy):
    player = scene.player
    if player.attack_time is None or not ATTACK_START <= player.attack_time < ATTACK_END:
        return False
    target = enemy_bounds(enemy)
    if not overlaps(attack_bounds(player),target):
        return False
    # Solid walls between the actors also block the opening strike.
    height = (max(target[1],player.y-36)+min(target[3],player.y))/2
    return not any(min(player.x,enemy.x) < r and max(player.x,enemy.x) > l
                   and t < height < b for l,t,r,b in scene.solids)


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
    victim = enemy if attacked else scene.player
    victim.take_damage()
    scene.encounter = (enemy,cause)
    scene.keys.clear()
    scene.app.start_melee(scene,enemy,cause)
    return True
