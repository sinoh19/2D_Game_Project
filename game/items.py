"""Item definitions shared by the bag, loot panel and field drops."""
from dataclasses import dataclass
from typing import Callable

import pico2d as p2d

from game.config import SCALE, WINDOW_HEIGHT
from game.terrain import slope_surfaces

POTION = 'health-potion'
SWORD = 'mercenary-sword'
BAG_SIZE = 10


@dataclass(frozen=True)
class Item:
    name: str
    icon: str
    use: Callable[[object], tuple[bool, str]]


@dataclass(frozen=True)
class Weapon:
    id: str
    name: str
    icon: str
    description: str
    base_attack: int


STARTER_SWORD = Weapon(SWORD, '용병의 검', 'mercenary-sword.png', '용병이 처음부터 지닌 검.', 7)


def heal(player):
    amount = min(10, player.max_hp - player.hp)
    if amount <= 0:
        return False, '이미 체력이 가득 찼습니다.'
    player.hp += amount
    return True, f'회복 포션 사용  ·  HP +{amount}'


ITEMS = {POTION: Item('회복 포션', 'health-potion.png', heal), SWORD: STARTER_SWORD}


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

    def draw(self, icon, camera):
        size = 22 if self.item_id == SWORD else 14
        center_y = self.feet - (size / 2 - 1)
        p2d.SDL_SetTextureColorMod(icon.texture, 176, 196, 202)
        try:
            icon.draw((self.x - camera) * SCALE, WINDOW_HEIGHT - center_y * SCALE,
                      size * SCALE, size * SCALE)
        finally:
            p2d.SDL_SetTextureColorMod(icon.texture, 255, 255, 255)
