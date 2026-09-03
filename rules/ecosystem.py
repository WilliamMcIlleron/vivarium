"""
The simulation itself. Deliberately pure Python with no dependency on Claude —
this is the part that runs for free, every tick, forever. `evolve` runs are what
change what's IN this file over time (new species, new mechanics, tuning).

Model: creatures live on a bounded 2D grid, move, eat resources for energy,
reproduce (with mutation) above an energy threshold, and die at zero energy.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field, asdict

GRID_SIZE = 40
STARTING_CREATURES = 12
RESOURCE_SPAWN_RATE = 0.08          # probability per tick of a new resource appearing
RESOURCE_ENERGY = 30
MOVE_COST = 1
REPRODUCE_THRESHOLD = 60
REPRODUCE_COST = 40
MUTATION_RATE = 0.1                 # chance any given gene mutates on reproduction
MAX_AGE = 400


@dataclass
class Creature:
    id: str
    x: int
    y: int
    energy: int
    speed: int          # tiles moved per tick
    sense_range: int     # how far it can "see" food
    age: int = 0

    def genes(self) -> dict:
        return {"speed": self.speed, "sense_range": self.sense_range}


@dataclass
class Resource:
    x: int
    y: int


@dataclass
class World:
    tick: int = 0
    creatures: list[Creature] = field(default_factory=list)
    resources: list[Resource] = field(default_factory=list)
    events: list[str] = field(default_factory=list)  # notable happenings this tick

    @classmethod
    def new(cls) -> "World":
        w = cls()
        for _ in range(STARTING_CREATURES):
            w.creatures.append(_spawn_creature())
        return w

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        w = cls(tick=data.get("tick", 0))
        w.creatures = [Creature(**c) for c in data.get("creatures", [])]
        w.resources = [Resource(**r) for r in data.get("resources", [])]
        return w

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "creatures": [asdict(c) for c in self.creatures],
            "resources": [asdict(r) for r in self.resources],
            "population": len(self.creatures),
        }

    def step(self) -> None:
        """Advance the world by exactly one tick."""
        self.events = []
        self.tick += 1

        if random.random() < RESOURCE_SPAWN_RATE:
            self.resources.append(
                Resource(x=random.randrange(GRID_SIZE), y=random.randrange(GRID_SIZE))
            )

        newborns: list[Creature] = []
        survivors: list[Creature] = []

        for creature in self.creatures:
            creature.age += 1

            target = _nearest_resource(creature, self.resources)
            if target is not None:
                _move_toward(creature, target)
            else:
                _move_random(creature)
            creature.energy -= MOVE_COST

            eaten = _resource_at(self.resources, creature.x, creature.y)
            if eaten is not None:
                self.resources.remove(eaten)
                creature.energy += RESOURCE_ENERGY

            if creature.energy >= REPRODUCE_THRESHOLD:
                creature.energy -= REPRODUCE_COST
                newborns.append(_reproduce(creature))
                self.events.append(f"birth at ({creature.x},{creature.y})")

            if creature.energy > 0 and creature.age < MAX_AGE:
                survivors.append(creature)
            else:
                self.events.append(f"death: {creature.id[:8]} at age {creature.age}")

        self.creatures = survivors + newborns

        if len(self.creatures) == 0:
            self.events.append("EXTINCTION")


def _spawn_creature() -> Creature:
    return Creature(
        id=str(uuid.uuid4()),
        x=random.randrange(GRID_SIZE),
        y=random.randrange(GRID_SIZE),
        energy=50,
        speed=1,
        sense_range=5,
    )


def _nearest_resource(creature: Creature, resources: list[Resource]) -> Resource | None:
    in_range = [
        r for r in resources
        if abs(r.x - creature.x) <= creature.sense_range
        and abs(r.y - creature.y) <= creature.sense_range
    ]
    if not in_range:
        return None
    return min(in_range, key=lambda r: abs(r.x - creature.x) + abs(r.y - creature.y))


def _move_toward(creature: Creature, target: Resource) -> None:
    dx = _clamp(target.x - creature.x, -creature.speed, creature.speed)
    dy = _clamp(target.y - creature.y, -creature.speed, creature.speed)
    creature.x = _wrap(creature.x + dx)
    creature.y = _wrap(creature.y + dy)


def _move_random(creature: Creature) -> None:
    creature.x = _wrap(creature.x + random.randint(-creature.speed, creature.speed))
    creature.y = _wrap(creature.y + random.randint(-creature.speed, creature.speed))


def _resource_at(resources: list[Resource], x: int, y: int) -> Resource | None:
    for r in resources:
        if r.x == x and r.y == y:
            return r
    return None


def _reproduce(parent: Creature) -> Creature:
    speed = parent.speed
    sense_range = parent.sense_range
    if random.random() < MUTATION_RATE:
        speed = max(1, speed + random.choice([-1, 1]))
    if random.random() < MUTATION_RATE:
        sense_range = max(1, sense_range + random.choice([-1, 1]))
    return Creature(
        id=str(uuid.uuid4()),
        x=parent.x,
        y=parent.y,
        energy=REPRODUCE_COST // 2,
        speed=speed,
        sense_range=sense_range,
    )


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _wrap(v: int) -> int:
    return v % GRID_SIZE
