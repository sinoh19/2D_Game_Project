"""Item definitions shared by the bag, loot panel and field drops."""
from dataclasses import dataclass
from math import sin, tau
from typing import Callable

import pico2d as p2d

from game.config import SCALE, WINDOW_HEIGHT
from game.terrain import slope_surfaces

POTION = 'health-potion'
SWORD = 'mercenary-sword'
LEATHER_ARMOR = 'mercenary-leather-armor'
RING_STRENGTH = 'starting-wood-ring-strength'
RING_AGILITY = 'starting-wood-ring-agility'
RING_INTELLIGENCE = 'starting-wood-ring-intelligence'
RING_LUCK = 'starting-wood-ring-luck'
RING_IDS = (RING_STRENGTH, RING_AGILITY, RING_INTELLIGENCE, RING_LUCK)
BAG_SIZE = 10


@dataclass(frozen=True)
class Item:
    name: str
    icon: str
    use: Callable[[object], tuple[bool, str]]


@dataclass(frozen=True)
class Equipment:
    id: str
    name: str
    icon: str
    description: str



@dataclass(frozen=True)
class Weapon(Equipment):
    base_attack: int
    slot = 'weapon'

    @property
    def stats(self):
        return (('기본 공격력', self.base_attack),)


@dataclass(frozen=True)
class Armor(Equipment):
    physical_defense: int
    magic_defense: int
    slot = 'armor'

    @property
    def stats(self):
        return (('물리 방어력', self.physical_defense), ('마법 방어력', self.magic_defense))


@dataclass(frozen=True)
class Accessory(Equipment):
    stat: str
    bonus: int = 2
    slot = 'accessory'

    @property
    def stats(self):
        return (({'strength': '힘', 'agility': '민첩',
                  'intelligence': '지능', 'luck': '행운'}[self.stat], self.bonus),)


STARTER_SWORD = Weapon(SWORD, '용병의 검', 'mercenary-sword.png', '용병이 처음부터 지닌 검.', 7)

STARTER_ARMOR = Armor(LEATHER_ARMOR, '용병의 가죽 갑옷', 'mercenary-leather-armor.png', '낡은 가죽으로 만든 기본 갑옷.', 0, 0)
STARTING_RINGS = {
    RING_STRENGTH: Accessory(RING_STRENGTH, '시작의 나무반지', 'starting-ring-strength.png',
                             '힘을 2 올려 주는 나무반지.', 'strength'),
    RING_AGILITY: Accessory(RING_AGILITY, '시작의 나무반지', 'starting-ring-agility.png',
                            '민첩을 2 올려 주는 나무반지.', 'agility'),
    RING_INTELLIGENCE: Accessory(RING_INTELLIGENCE, '시작의 나무반지', 'starting-ring-intelligence.png',
                                 '지능을 2 올려 주는 나무반지.', 'intelligence'),
    RING_LUCK: Accessory(RING_LUCK, '시작의 나무반지', 'starting-ring-luck.png',
                         '행운을 2 올려 주는 나무반지.', 'luck'),
}

def heal(player):
    amount = min(10, player.max_hp - player.hp)
    if amount <= 0:
        return False, '이미 체력이 가득 찼습니다.'
    player.hp += amount
    return True, f'회복 포션 사용  ·  HP +{amount}'


ITEMS = {POTION: Item('회복 포션', 'health-potion.png', heal), SWORD: STARTER_SWORD,
         LEATHER_ARMOR: STARTER_ARMOR, **STARTING_RINGS}


@dataclass(eq=False)
class DroppedItem:
    item_id: str
    x: float
    feet: float
    velocity: float = 0.0
    grounded: bool = False

    def update(self, dt, field):
        self.velocity = min(350.0, self.velocity + 640 * dt)
        next_feet = self.feet + self.velocity * dt
        surfaces = [top for left, top, right, bottom in field.solids + field.platforms
                    if left <= self.x <= right]
        surfaces.extend(slope_surfaces(field, self.x, 0))
        landing = min((y for y in surfaces if self.feet <= y <= next_feet), default=None)
        self.grounded = landing is not None
        if self.grounded:
            self.feet = landing
            self.velocity = 0.0
        else:
            self.feet = next_feet

    def draw(self, icon, camera, elapsed):
        size = 22 if isinstance(ITEMS[self.item_id], Equipment) else 14
        hover = 5 + round(2 * sin(tau * elapsed / 1.4)) if self.grounded else 0
        center_y = self.feet - (size / 2 - 1) - hover
        p2d.SDL_SetTextureColorMod(icon.texture, 176, 196, 202)
        try:
            icon.draw((self.x - camera) * SCALE, WINDOW_HEIGHT - center_y * SCALE,
                      size * SCALE, size * SCALE)
        finally:
            p2d.SDL_SetTextureColorMod(icon.texture, 255, 255, 255)
