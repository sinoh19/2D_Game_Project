"""Item definitions shared by the bag, loot panel and field drops."""
from dataclasses import dataclass
from typing import Callable

from game.config import SCALE, WINDOW_HEIGHT
from game.terrain import slope_surfaces

POTION = 'health-potion'
BAG_SIZE = 10


@dataclass(frozen=True)
class Item:
    name: str
    icon: str
    use: Callable[[object], tuple[bool, str]]


def heal(player):
    amount = min(10, player.max_hp - player.hp)
    if amount <= 0:
        return False, '이미 체력이 가득 찼습니다.'
    player.hp += amount
    return True, f'회복 포션 사용  ·  HP +{amount}'


ITEMS = {POTION: Item('회복 포션', 'health-potion.png', heal)}


@dataclass
class DroppedItem:
    item_id: str
    x: float
    feet: float
    velocity: float = 0.0

    def update(self, dt, field):
        self.velocity = min(350.0, self.velocity + 640 * dt)
        next_feet = self.feet + self.velocity * dt
        surfaces = [top for left, top, right, bottom in field.solids + field.platforms
                    if left <= self.x <= right]
        surfaces.extend(slope_surfaces(field, self.x, 0))
        landing = min((y for y in surfaces if self.feet <= y <= next_feet), default=None)
        if landing is not None:
            self.feet = landing
            self.velocity = 0.0
        else:
            self.feet = next_feet

    def draw(self, icon, camera):
        icon.draw((self.x - camera) * SCALE, WINDOW_HEIGHT - (self.feet - 7) * SCALE,
                  16 * SCALE, 16 * SCALE)
