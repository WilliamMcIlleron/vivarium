"""
The simulation itself. Deliberately pure Python with no dependency on Claude —
this is the part that runs for free, every tick, forever. `evolve` runs are what
change what's IN this file over time (new species, new mechanics, tuning).

Model: creatures live on a bounded 2D grid, move, eat, reproduce (with mutation)
above an energy threshold, and die at zero energy or old age.

Two species share the same grid:
  - grazer: seeks out Resources within sense_range, eats them for energy.
  - hunter: seeks out the nearest grazer within sense_range, eats it on contact
    for energy. Hunters do not eat Resources - they depend entirely on grazers,
    which is what makes this a real predator/prey pressure rather than two
    populations that happen to coexist.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field, asdict

GRID_SIZE = 40
STARTING_GRAZERS = 14
STARTING_HUNTERS = 3
RESOURCE_SPAWN_RATE = 0.6           # probability per tick of a new resource appearing
RESOURCE_ENERGY = 30
HUNT_ENERGY = 40                    # energy a hunter gains from eating a grazer
MOVE_COST = 1
MUTATION_RATE = 0.1                 # chance any given gene mutates on reproduction
MAX_AGE = 400

# Hunters are deliberately a K-strategist relative to grazers: much costlier
# to reproduce, so a single lucky kill doesn't immediately mint a new hunter
# and spiral into a hunter population that outstrips its own food supply.
REPRODUCE = {
    "grazer": {"threshold": 60, "cost": 40},
    "hunter": {"threshold": 110, "cost": 55},
}

# If hunters die out entirely, a small per-tick chance of one migrating back
# in - otherwise a single bad early run permanently turns this into a
# single-species world, which defeats the point of having two.
HUNTER_MIGRATION_RATE = 0.02

SPECIES = ("grazer", "hunter")


@dataclass
class Creature:
    id: str
    x: int
    y: int
    energy: int
    speed: int          # tiles moved per tick
    sense_range: int     # how far it can "see" food (grazer) or prey (hunter)
    species: str = "grazer"
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
        for _ in range(STARTING_GRAZERS):
            w.creatures.append(_spawn_creature("grazer"))
        for _ in range(STARTING_HUNTERS):
            w.creatures.append(_spawn_creature("hunter"))
        return w

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        w = cls(tick=data.get("tick", 0))
        w.creatures = [Creature(**c) for c in data.get("creatures", [])]
        w.resources = [Resource(**r) for r in data.get("resources", [])]
        return w

    def to_dict(self) -> dict:
        grazers = sum(1 for c in self.creatures if c.species == "grazer")
        hunters = sum(1 for c in self.creatures if c.species == "hunter")
        return {
            "tick": self.tick,
            "creatures": [asdict(c) for c in self.creatures],
            "resources": [asdict(r) for r in self.resources],
            "population": len(self.creatures),
            "grazers": grazers,
            "hunters": hunters,
        }

    def step(self) -> None:
        """Advance the world by exactly one tick."""
        self.events = []
        self.tick += 1

        if random.random() < RESOURCE_SPAWN_RATE:
            self.resources.append(
                Resource(x=random.randrange(GRID_SIZE), y=random.randrange(GRID_SIZE))
            )

        if (
            not any(c.species == "hunter" for c in self.creatures)
            and random.random() < HUNTER_MIGRATION_RATE
        ):
            self.creatures.append(_spawn_creature("hunter"))
            self.events.append("a hunter migrates into the world")

        grazers = [c for c in self.creatures if c.species == "grazer"]
        hunters = [c for c in self.creatures if c.species == "hunter"]

        # movement: hunters head for the nearest grazer. Grazers flee the
        # nearest hunter in sense range if one is close; otherwise they head
        # for the nearest resource. Either falls back to a random walk if
        # nothing relevant is in sense range. Grazers reusing sense_range for
        # threat detection means the same mutating gene trades off "finds
        # food better" against "spots predators better" - no separate dial.
        for creature in self.creatures:
            creature.age += 1
            if creature.species == "hunter":
                target = _nearest_creature(creature, grazers)
                if target is not None:
                    _move_toward(creature, target)
                else:
                    _move_random(creature)
            else:
                threat = _nearest_creature(creature, hunters)
                if threat is not None:
                    _move_away(creature, threat)
                else:
                    target = _nearest_resource(creature, self.resources)
                    if target is not None:
                        _move_toward(creature, target)
                    else:
                        _move_random(creature)
            creature.energy -= MOVE_COST

        # hunting: a hunter co-located with a still-living grazer eats it.
        # Checked after all movement resolves, so this reflects end-of-tick
        # positions for every creature, not just the ones processed first.
        killed_ids: set[str] = set()
        for hunter in hunters:
            prey = next(
                (g for g in grazers
                 if g.id not in killed_ids and g.x == hunter.x and g.y == hunter.y),
                None,
            )
            if prey is not None:
                killed_ids.add(prey.id)
                hunter.energy += HUNT_ENERGY
                self.events.append(f"hunt: grazer {prey.id[:8]} eaten at ({hunter.x},{hunter.y})")

        # grazing: a surviving grazer co-located with a resource eats it.
        for grazer in grazers:
            if grazer.id in killed_ids:
                continue
            eaten = _resource_at(self.resources, grazer.x, grazer.y)
            if eaten is not None:
                self.resources.remove(eaten)
                grazer.energy += RESOURCE_ENERGY

        # reproduction, aging, death
        newborns: list[Creature] = []
        survivors: list[Creature] = []
        for creature in self.creatures:
            if creature.id in killed_ids:
                self.events.append(f"death: {creature.id[:8]} at age {creature.age} (hunted)")
                continue

            repro = REPRODUCE[creature.species]
            if creature.energy >= repro["threshold"]:
                creature.energy -= repro["cost"]
                newborns.append(_reproduce(creature))
                self.events.append(f"birth ({creature.species}) at ({creature.x},{creature.y})")

            if creature.energy > 0 and creature.age < MAX_AGE:
                survivors.append(creature)
            else:
                self.events.append(f"death: {creature.id[:8]} at age {creature.age}")

        self.creatures = survivors + newborns

        if not any(c.species == "grazer" for c in self.creatures):
            self.events.append("GRAZERS EXTINCT")
        if not any(c.species == "hunter" for c in self.creatures):
            self.events.append("HUNTERS EXTINCT")
        if len(self.creatures) == 0:
            self.events.append("EXTINCTION")


def _spawn_creature(species: str = "grazer") -> Creature:
    speed = 2 if species == "hunter" else 1
    return Creature(
        id=str(uuid.uuid4()),
        x=random.randrange(GRID_SIZE),
        y=random.randrange(GRID_SIZE),
        energy=50,
        speed=speed,
        sense_range=5,
        species=species,
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


def _nearest_creature(creature: Creature, others: list[Creature]) -> Creature | None:
    in_range = [
        o for o in others
        if o.id != creature.id
        and abs(o.x - creature.x) <= creature.sense_range
        and abs(o.y - creature.y) <= creature.sense_range
    ]
    if not in_range:
        return None
    return min(in_range, key=lambda o: abs(o.x - creature.x) + abs(o.y - creature.y))


def _move_toward(creature: Creature, target: "Resource | Creature") -> None:
    dx = _clamp(target.x - creature.x, -creature.speed, creature.speed)
    dy = _clamp(target.y - creature.y, -creature.speed, creature.speed)
    creature.x = _wrap(creature.x + dx)
    creature.y = _wrap(creature.y + dy)


def _move_away(creature: Creature, threat: "Creature") -> None:
    dx = _clamp(creature.x - threat.x, -creature.speed, creature.speed)
    dy = _clamp(creature.y - threat.y, -creature.speed, creature.speed)
    if dx == 0 and dy == 0:
        # standing on the threat's exact tile - flee in a random direction
        # rather than freezing in place.
        dx = random.randint(-creature.speed, creature.speed)
        dy = random.randint(-creature.speed, creature.speed)
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
    cost = REPRODUCE[parent.species]["cost"]
    return Creature(
        id=str(uuid.uuid4()),
        x=parent.x,
        y=parent.y,
        energy=cost // 2,
        speed=speed,
        sense_range=sense_range,
        species=parent.species,
    )


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _wrap(v: int) -> int:
    return v % GRID_SIZE
