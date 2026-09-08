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

Three genes fight over the same number - the hunter's effective sense_range
when it is looking for live prey. A grazer's `camouflage` shrinks it (hiding as
an individual); a grazer's herd cover shrinks it further (hiding as a crowd -
see HERD_RADIUS); a hunter's `acuity` adds back to it, at a per-tick energy
cost. Concealment is something prey can buy two different ways, and seeing
through either is something a predator has to be able to afford.

Fleeing, meanwhile, is not a reflex. A grazer that spots a hunter compares the
distance to its own flight distance - its sense_range, shrunk by the `nerve`
gene and shrunk further when it is hungry - and only bolts if the hunter is
inside it. Nerve is what lets an animal finish a meal with a predator in view,
which in a world this crowded with hunters is the difference between eating and
starving; it is paid for in the risk of being caught.

Anything that dies of starvation or old age leaves a Carrion behind: a static,
rotting carcass. It is the only food a hunter can get without catching
something that is actively fleeing it - but only a grazer's body counts. A
hunter's corpse is inedible to other hunters (see SCAVENGEABLE_CARRION), so
the entire scavenging supply is tied to the prey population and a predator can
never live off its own dead.

The world also keeps a genetic memory (`World.lineage`): the genomes of the
creatures that actually managed to reproduce here. When a species dies out and
a migrant wanders back in, that migrant arrives as a mutated descendant of the
remembered stock instead of a blank species default - so an extinction is a
bottleneck, not a factory reset.
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

# Carrion: every death that ISN'T a kill (starvation, old age) drops a carcass
# on that tile. Hunters can scavenge it. Deliberately worth less than a fresh
# kill and gone after CARRION_DECAY ticks, so it's a lifeline, not a living:
# a hunter burns ~2 energy/tick, so CARRION_ENERGY covers about 15 ticks of
# upkeep and can't on its own carry a hunter to its 110-energy reproduction
# threshold. Reproducing still takes live prey.
#
# Why this should stabilise rather than tip the balance: the carcass supply is
# set by how many creatures die of NON-predation causes, which scales with the
# grazer population - and predation itself produces no carcasses. So a hunter
# boom eats its own scavenging supply (kills replace natural deaths), while a
# hunter crash leaves the carcasses of a large, unhunted grazer population
# lying around for the next migrant to find. Negative feedback in both
# directions, which is exactly what the last ~20 straight ticks of
# "HUNTERS EXTINCT" say this world was missing.
CARRION_ENERGY = 30
CARRION_DECAY = 40                  # ticks a carcass lasts before it rots away

# Whose bodies a hunter will actually eat.
#
# The paragraph above claims the carcass supply "scales with the grazer
# population". That was only ever half true, because nothing checked whose
# body it was: hunters have been eating hunters. Tick 1870 is what that looks
# like - zero grazers, five hunters, and GRAZERS EXTINCT in nearly every tick
# since 1813. With no prey anywhere on the grid the only deaths are hunter
# deaths, and each one drops CARRION_ENERGY straight back into the hunter
# population. That closed cannibal loop doesn't really feed the predators; it
# lets them die very slowly, five at a time, and it means a lone grazer
# migrating in at tick 1824 walks onto a grid that still has five hunters
# standing on it and is gone before it can breed. The predator population had
# stopped depending on prey at all, which is the one thing it was never
# supposed to be able to do.
#
# So a carcass now remembers what it was, and only a grazer's body is food. A
# hunter's corpse is scenery: it rots where it fell, unwalked-to and uneaten.
# That restores the negative feedback carrion was designed to have - no
# grazers means no carrion means the hunters genuinely starve out, which is
# exactly the window a re-migrating grazer needs - without touching predation,
# energy values, or any gene.
SCAVENGEABLE_CARRION = ("grazer",)

# Safety in numbers. Every other grazer within HERD_RADIUS tiles (Chebyshev,
# the same box shape sense_range uses) gives a grazer HERD_COVER_PER_NEIGHBOR
# of extra concealment against a hunter's prey-detection check, capped at
# HERD_COVER_MAX - the predator-confusion effect: a single animal in the open
# is easy to fix on, a mass of them is not.
#
# This is aimed squarely at the crash this world keeps having. Between tick
# 1147 and tick 1229 it went from 13 grazers and 1 hunter to 2 grazers and 4
# hunters: a hunter boom converting a whole prey population into predators
# faster than it could breed, which ends in GRAZERS EXTINCT and then the
# hunters starving behind them. The important property is that it is
# DENSITY-DEPENDENT and prey-side: cover exists only while grazers are
# numerous, which is exactly the phase where hunters are over-feeding, and it
# evaporates as the population thins - so a lone straggler is as catchable as
# it ever was and this does nothing to deepen the chronic hunter extinctions.
# It brakes the boom without being a flat nerf, and hunters already have the
# counter: `acuity` adds range back on the same subtraction.
HERD_RADIUS = 2
HERD_COVER_PER_NEIGHBOR = 0.5
HERD_COVER_MAX = 2.0

# Nerve: how close a hunter has to get before a grazer abandons what it is
# doing and runs.
#
# Fleeing used to be a pure reflex - any hunter anywhere inside sense_range and
# the grazer bolted - and by tick 1728 that reflex was killing the species.
# Grazers had evolved sense_range 7 and speed 5 against six hunters, so the
# 15x15 box around every grazer nearly always contained a predator: the animal
# spent its entire life running, burning 5 energy a tick (MOVE_COST scales with
# speed) and never standing on a resource long enough to eat one. GRAZERS
# EXTINCT, over and over, from starvation rather than from predation - while
# the hunters, who had drifted down to speed 1 and could not have caught a
# fleeing grazer at all, lived comfortably off the carcasses.
#
# `nerve` makes flight a decision instead of a reflex. It subtracts from the
# distance at which a grazer panics, so a nervy animal keeps feeding while a
# predator is still a few tiles off, and it costs exactly what you would
# expect: the hunter gets closer. Hunger multiplies it by NERVE_HUNGER_BOOST,
# because a grazer that is about to starve is risking very little by staying -
# desperation is its own pressure, and it shows up precisely in the animals
# that were going to die anyway. The panic radius never drops below one tile
# (nerve buys patience, not suicide), and at nerve 0 it is exactly sense_range,
# i.e. bit-for-bit the world's original reflex.
NERVE_HUNGER_LEVEL = 25   # energy below which a grazer accepts the extra risk
NERVE_HUNGER_BOOST = 1.5  # multiplier applied to nerve while hungry

# How many genomes the world remembers per species (see World.lineage and
# _spawn_creature's `lineage` argument). Only creatures that actually
# reproduced get recorded: the memory is of what WORKED here, not of
# everything that happened to die here.
#
# Hunters are why this exists. The event log shows them going extinct and
# re-migrating over and over, and every single migrant was arriving at the
# flat species default - speed 2, sense_range 5, camouflage 0 - while grazers,
# who never fully crashed, kept ratcheting camouflage upward across hundreds
# of ticks (0.58 average and climbing at tick 958). That isn't an arms race,
# it's a one-way escalation: the predator side was structurally incapable of
# ever keeping an adaptation, because its genome was reset by every crash.
# With a lineage memory, a migrant descends from the last stock that bred
# here, so both species can accumulate across crashes and camouflage finally
# has something evolving against it. It's a bottleneck (memory is small, and
# the migrant is a single mutated draw from it), not a save file.
LINEAGE_MEMORY = 8

# Cost per point of speed, charged every tick regardless of how far a creature
# actually moved that tick. Speed used to be a free stat: a first-class
# mutating gene with zero energy price, so it could only ever ratchet upward
# with no downside. That's exactly what was happening - grazers had drifted to
# a higher average speed than hunters, who get reset to the species default
# every time they go extinct and migrate back in, so they could never catch
# up. Pricing speed in energy gives it a real tradeoff against food-finding
# for both species instead of a one-way escalation that only ever favored
# whichever species last avoided a population crash.
MOVE_COST = 1

# Energy a hunter pays every tick per FULL point of its acuity gene (see
# TRAIT_REGISTRY below). Charged with int() truncation, so half-points are
# free: acuity 0.5 is a free edge, 1.0 costs 1/tick, 2.0 costs 2/tick. That's
# deliberate - it gives a cheap first rung onto the ladder (a hunter that has
# just migrated in and is one bad tick from starving can still afford to look
# harder) while making a genuinely keen-eyed predator an expensive animal that
# has to convert its sight into kills. Same lesson as MOVE_COST: a gene with
# no price can only ratchet upward, and this world already has one of those in
# camouflage.
ACUITY_COST = 1

MUTATION_RATE = 0.1                 # chance any given gene mutates on reproduction
MAX_AGE = 400

# Hunters are deliberately a K-strategist relative to grazers: much costlier
# to reproduce, so a single lucky kill doesn't immediately mint a new hunter
# and spiral into a hunter population that outstrips its own food supply.
REPRODUCE = {
    "grazer": {"threshold": 60, "cost": 40},
    "hunter": {"threshold": 110, "cost": 55},
}

# If either species dies out entirely, a small per-tick chance of one
# migrating back in. Without this, grazer extinction was a PERMANENT dead
# world: hunters only eat grazers, never resources, so a wiped-out grazer
# population starves the hunters out too with nothing left to bring either
# species back. Grazer migration is higher since they're the base of the
# food chain - a lone re-migrated grazer with nothing hunting it yet has a
# real chance to reproduce before a hunter shows up; a lone re-migrated
# hunter is much more exposed (no fallback food source at all).
HUNTER_MIGRATION_RATE = 0.02
GRAZER_MIGRATION_RATE = 0.05

SPECIES = ("grazer", "hunter")

# Terrain is a fixed, cosmetic layer generated once at world creation - it's
# the "engine" the viewer renders onto, not something evolve runs are meant
# to regenerate or read. step() never touches it.
TERRAIN_CODES = "wsgf"  # water, sand, grass, forest

# Extensible genome: name -> (default, mutation_step, min, max). speed and
# sense_range stay first-class Creature fields since core movement code
# reads them directly everywhere - this registry is for ADDITIONAL traits,
# so adding a new mutating gene is one line here plus whatever behavior code
# actually uses it, instead of editing Creature/_spawn_creature/_reproduce
# separately for each one.
#
# camouflage: how much a grazer shrinks a hunter's *effective* sense_range
# specifically when that hunter is looking for it (see _nearest_creature's
# camouflage_aware path below).
#
# acuity: the hunter's half of that same subtraction. It ADDS to a hunter's
# effective sense_range, but only when the hunter is looking for live prey -
# never for carrion, never for anything else - so it is precisely a counter to
# camouflage rather than a general-purpose senses upgrade. Unlike camouflage
# it is not free: see ACUITY_COST.
#
# gregariousness: how strongly a grazer with nothing chasing it will walk
# toward the nearest grazer it can see instead of toward food. That's what
# makes herd cover (HERD_RADIUS) an evolvable strategy rather than an accident
# of where creatures happen to stand - and it pays for itself in missed meals
# rather than in a flat energy charge, since a grazer standing in the herd is
# a grazer not standing on a resource.
#
# nerve: how close a hunter has to get before a grazer stops feeding and runs
# (see NERVE_HUNGER_LEVEL). It shrinks the panic radius, never the grazer's
# perception - a nervy grazer sees the predator perfectly well and keeps
# eating anyway - and its price is the shorter head start it leaves itself.
#
# None of the four is species-scoped - the registry has no concept of
# "grazer-only", so each species carries the other's genes inertly, since
# nothing on that side ever reads them.
TRAIT_REGISTRY: dict[str, tuple[float, float, float, float]] = {
    "camouflage": (0.0, 0.5, 0.0, 3.0),
    "acuity": (0.0, 0.5, 0.0, 3.0),
    "gregariousness": (0.0, 0.5, 0.0, 3.0),
    "nerve": (0.0, 0.5, 0.0, 3.0),
}


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
    traits: dict = field(default_factory=dict)  # extra genome, see TRAIT_REGISTRY
    # "born" for anything that hatched here (including the founding
    # population), "migrant" for something that walked in from outside after
    # its species had died out. Purely descriptive - no behavior reads it -
    # but the viewer marks recent migrants, since "where this bloodline came
    # from" is now a real fact about a creature rather than a formality.
    origin: str = "born"
    # NOT a gene: recomputed from scratch every tick for grazers from how many
    # other grazers are standing nearby (see _update_herd_cover). Persisted
    # only so the viewer can draw the herd without recomputing it.
    herd_cover: float = 0.0

    def trait(self, name: str) -> float:
        default = TRAIT_REGISTRY[name][0] if name in TRAIT_REGISTRY else 0.0
        return self.traits.get(name, default)

    def genes(self) -> dict:
        return {"speed": self.speed, "sense_range": self.sense_range, **self.traits}


@dataclass
class Resource:
    x: int
    y: int


@dataclass
class Carrion:
    """A carcass left behind by a non-predation death. Static, rots away
    after CARRION_DECAY ticks. `species` is whose body it is, and it decides
    whether the carcass is food at all: only the species listed in
    SCAVENGEABLE_CARRION can be eaten, so a hunter's remains are inert
    scenery rather than a meal for the next hunter along."""
    x: int
    y: int
    age: int = 0
    species: str = "grazer"


@dataclass
class World:
    tick: int = 0
    creatures: list[Creature] = field(default_factory=list)
    resources: list[Resource] = field(default_factory=list)
    terrain: list[str] = field(default_factory=list)  # GRID_SIZE rows, one char/cell
    events: list[str] = field(default_factory=list)  # notable happenings this tick
    carrion: list[Carrion] = field(default_factory=list)
    # species -> list of remembered genomes (oldest first, capped at
    # LINEAGE_MEMORY). Written only when a creature reproduces; read only when
    # a migrant arrives.
    lineage: dict = field(default_factory=lambda: {s: [] for s in SPECIES})

    @classmethod
    def new(cls) -> "World":
        w = cls()
        w.terrain = _generate_terrain()
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
        # Saves from before carrion existed simply start with none on the
        # ground - the first natural death repopulates it. Carcasses saved
        # before bodies had a species default to "grazer", i.e. edible, which
        # is how they behaved when they were written; they rot away within
        # CARRION_DECAY ticks either way.
        w.carrion = [Carrion(**k) for k in data.get("carrion", [])]
        # Same for lineage: a save from before the world remembered anything
        # starts blank, and the first birth of each species fills it in.
        remembered = data.get("lineage") or {}
        w.lineage = {s: list(remembered.get(s, [])) for s in SPECIES}
        # Saves from before terrain existed have no "terrain" key - generate
        # one rather than fail, since terrain is cosmetic and has no bearing
        # on anything the simulation itself depends on.
        w.terrain = data.get("terrain") or _generate_terrain()
        return w

    def to_dict(self) -> dict:
        grazers = sum(1 for c in self.creatures if c.species == "grazer")
        hunters = sum(1 for c in self.creatures if c.species == "hunter")
        return {
            "tick": self.tick,
            "creatures": [asdict(c) for c in self.creatures],
            "resources": [asdict(r) for r in self.resources],
            "carrion": [asdict(k) for k in self.carrion],
            "lineage": {s: list(self.lineage.get(s, [])) for s in SPECIES},
            "terrain": self.terrain,
            "population": len(self.creatures),
            "grazers": grazers,
            "hunters": hunters,
        }

    def remember(self, creature: Creature) -> None:
        """Record a genome that successfully reproduced here. Rolling window:
        only the last LINEAGE_MEMORY are kept, so the memory tracks what the
        population looks like NOW rather than averaging its whole history.
        A species that hasn't bred in a long time keeps whatever it last
        managed - which is the point, since that's exactly the species that
        keeps going extinct."""
        record = self.lineage.setdefault(creature.species, [])
        record.append(creature.genes())
        del record[:-LINEAGE_MEMORY]

    def step(self) -> None:
        """Advance the world by exactly one tick."""
        self.events = []
        self.tick += 1

        # carcasses rot. Done first so a carcass created at the end of tick N
        # is scavengable for the whole of tick N+1.
        for carcass in self.carrion:
            carcass.age += 1
        self.carrion = [k for k in self.carrion if k.age < CARRION_DECAY]

        if random.random() < RESOURCE_SPAWN_RATE:
            self.resources.append(
                Resource(x=random.randrange(GRID_SIZE), y=random.randrange(GRID_SIZE))
            )

        # Migrants are drawn from the world's genetic memory (see
        # LINEAGE_MEMORY): a descendant of the last stock that bred here,
        # mutated once on arrival, rather than a fresh default-statted
        # creature. Falls back to the species default when nothing of that
        # species ever reproduced here.
        if (
            not any(c.species == "hunter" for c in self.creatures)
            and random.random() < HUNTER_MIGRATION_RATE
        ):
            self.creatures.append(
                _spawn_creature(
                    "hunter", lineage=self.lineage.get("hunter"), origin="migrant"
                )
            )
            self.events.append("a hunter migrates into the world")

        if (
            not any(c.species == "grazer" for c in self.creatures)
            and random.random() < GRAZER_MIGRATION_RATE
        ):
            self.creatures.append(
                _spawn_creature(
                    "grazer", lineage=self.lineage.get("grazer"), origin="migrant"
                )
            )
            self.events.append("a grazer migrates into the world")

        grazers = [c for c in self.creatures if c.species == "grazer"]
        hunters = [c for c in self.creatures if c.species == "hunter"]

        # Who is standing with whom, from start-of-tick positions, before
        # anything moves - so a hunter's detection check this tick reads the
        # herd as it was when the tick began rather than half-updated.
        _update_herd_cover(grazers)

        # movement: hunters head for whichever is closer, the nearest grazer
        # or the nearest carcass they can actually eat - live prey is worth
        # more but runs away, carrion is worth less but holds still. A dead
        # hunter is neither: it isn't food (SCAVENGEABLE_CARRION), so nothing
        # ever walks toward one. Grazers flee the nearest hunter in sense
        # range if it is inside their flight distance (see _panic_radius - a
        # grazer with nerve lets a predator come closer before it gives up on
        # eating); otherwise they either drift toward company (gregariousness)
        # or head for the nearest resource, falling back to a random walk if
        # nothing relevant is in sense range.
        # Grazers reusing sense_range for threat detection means the same
        # mutating gene trades off "finds food better" against "spots
        # predators better" - no separate dial.
        # Layered on top of that, three things pull on the hunter's
        # prey-detection number and nothing else: a grazer's `camouflage` and
        # its herd cover subtract from the hunter's effective sense_range, and
        # the hunter's `acuity` adds back to it. None of them does anything
        # for a carcass: hiding is a behaviour of the living, and a body in
        # the open takes no special eye to find.
        for creature in self.creatures:
            creature.age += 1
            if creature.species == "hunter":
                prey = _nearest_creature(creature, grazers, camouflage_aware=True)
                carcass = _nearest_carrion(creature, self.carrion)
                target = _closer_target(creature, prey, carcass)
                if target is not None:
                    _move_toward(creature, target)
                else:
                    _move_random(creature)
            else:
                threat = _nearest_creature(creature, hunters)
                if threat is not None and _flees(creature, threat):
                    _move_away(creature, threat)
                else:
                    target = _nearest_resource(creature, self.resources)
                    companion = _herd_target(creature, grazers, target)
                    if companion is not None:
                        _move_toward(creature, companion)
                    elif target is not None:
                        _move_toward(creature, target)
                    else:
                        _move_random(creature)
            # Cost scales with the creature's own speed gene (see MOVE_COST
            # above) - being fast is a real metabolic expense now, not a
            # stat with only upside.
            creature.energy -= MOVE_COST * creature.speed
            # And a hunter pays for its eyes every tick whether or not they
            # found anything (see ACUITY_COST). Charged only to hunters, since
            # a grazer's inherited acuity is inert - it should not be billed
            # for a sense it never uses.
            if creature.species == "hunter":
                creature.energy -= int(ACUITY_COST * creature.trait("acuity"))

        # hunting: a hunter co-located with a still-living grazer eats it.
        # Checked after all movement resolves, so this reflects end-of-tick
        # positions for every creature, not just the ones processed first.
        killed_ids: set[str] = set()
        fed_hunter_ids: set[str] = set()
        for hunter in hunters:
            prey = next(
                (g for g in grazers
                 if g.id not in killed_ids and g.x == hunter.x and g.y == hunter.y),
                None,
            )
            if prey is not None:
                killed_ids.add(prey.id)
                fed_hunter_ids.add(hunter.id)
                hunter.energy += HUNT_ENERGY
                self.events.append(f"hunt: grazer {prey.id[:8]} eaten at ({hunter.x},{hunter.y})")

        # scavenging: a hunter that made no kill this tick eats a carcass it's
        # standing on - if that carcass is prey. A hunter never gets both a
        # kill and a scavenge in one tick (a kill is the better meal and
        # taking both would double-dip a single tile), and it never gets a
        # meal out of another hunter at all.
        for hunter in hunters:
            if hunter.id in fed_hunter_ids:
                continue
            carcass = _carrion_at(self.carrion, hunter.x, hunter.y)
            if carcass is not None:
                self.carrion.remove(carcass)
                hunter.energy += CARRION_ENERGY
                self.events.append(f"scavenge: carcass eaten at ({hunter.x},{hunter.y})")

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
                # Breeding is the only thing that writes to the world's
                # genetic memory - reaching the threshold is the world's own
                # definition of a genome that works here.
                self.remember(creature)
                self.events.append(f"birth ({creature.species}) at ({creature.x},{creature.y})")

            if creature.energy > 0 and creature.age < MAX_AGE:
                survivors.append(creature)
            else:
                # Starvation and old age leave a body; being eaten does not,
                # since the hunter already took the energy. The body remembers
                # what it was, because only a grazer's is edible.
                self.events.append(f"death: {creature.id[:8]} at age {creature.age}")
                self.carrion.append(
                    Carrion(x=creature.x, y=creature.y, species=creature.species)
                )

        self.creatures = survivors + newborns

        if not any(c.species == "grazer" for c in self.creatures):
            self.events.append("GRAZERS EXTINCT")
        if not any(c.species == "hunter" for c in self.creatures):
            self.events.append("HUNTERS EXTINCT")
        if len(self.creatures) == 0:
            self.events.append("EXTINCTION")


def _generate_terrain() -> list[str]:
    """Hand-rolled value noise, no numpy: random per-cell values, smoothed by
    a few passes of neighbor-averaging so terrain forms contiguous patches
    instead of single-cell salt-and-pepper static, then normalized and cut
    into four biome bands. Generated once and saved - not regenerated on
    later loads, so it's a stable landscape rather than a different one
    every tick.
    """
    grid = [[random.random() for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

    for _ in range(4):
        smoothed = [[0.0] * GRID_SIZE for _ in range(GRID_SIZE)]
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                total = 0.0
                count = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < GRID_SIZE and 0 <= nx < GRID_SIZE:
                            total += grid[ny][nx]
                            count += 1
                smoothed[y][x] = total / count
        grid = smoothed

    flat = [v for row in grid for v in row]
    lo, hi = min(flat), max(flat)
    span = hi - lo or 1.0

    rows = []
    for y in range(GRID_SIZE):
        chars = []
        for x in range(GRID_SIZE):
            norm = (grid[y][x] - lo) / span
            if norm < 0.22:
                chars.append("w")
            elif norm < 0.30:
                chars.append("s")
            elif norm < 0.75:
                chars.append("g")
            else:
                chars.append("f")
        rows.append("".join(chars))
    return rows


def _spawn_creature(
    species: str = "grazer",
    lineage: list[dict] | None = None,
    origin: str = "born",
) -> Creature:
    """A fresh creature. With no `lineage`, it gets the flat species default -
    that's the founding population. With one, it's a descendant of the
    remembered stock: one genome picked at random from the world's memory,
    then mutated exactly as if it had been born to that ancestor.
    """
    speed = 2 if species == "hunter" else 1
    sense_range = 5
    traits = {name: default for name, (default, _step, _lo, _hi) in TRAIT_REGISTRY.items()}

    if lineage:
        ancestor = random.choice(lineage)
        speed = int(ancestor.get("speed", speed))
        sense_range = int(ancestor.get("sense_range", sense_range))
        traits = {
            name: ancestor.get(name, default)
            for name, (default, _step, _lo, _hi) in TRAIT_REGISTRY.items()
        }
        speed, sense_range, traits = _mutated_genes(speed, sense_range, traits)

    return Creature(
        id=str(uuid.uuid4()),
        x=random.randrange(GRID_SIZE),
        y=random.randrange(GRID_SIZE),
        energy=50,
        speed=speed,
        sense_range=sense_range,
        species=species,
        traits=traits,
        origin=origin,
    )


def _update_herd_cover(grazers: list[Creature]) -> None:
    """Recompute every grazer's herd cover from how many other grazers are
    within HERD_RADIUS tiles. Not a gene and not inherited - it's a fact
    about where an animal is standing this tick, so it's rebuilt from
    scratch each time and never carried over.
    """
    for grazer in grazers:
        neighbors = sum(
            1 for other in grazers
            if other.id != grazer.id
            and abs(other.x - grazer.x) <= HERD_RADIUS
            and abs(other.y - grazer.y) <= HERD_RADIUS
        )
        grazer.herd_cover = min(HERD_COVER_MAX, HERD_COVER_PER_NEIGHBOR * neighbors)


def _panic_radius(grazer: Creature) -> float:
    """How close a hunter has to get before this grazer drops what it's doing
    and runs. Starts at its full sense_range - so a grazer with nerve 0 bolts
    at the first predator it can see, exactly as this world has always
    worked - and shrinks by the nerve gene, amplified while the animal is
    hungry enough that a missed meal is its own kind of death. Never below
    one tile: nerve buys patience, not suicide.
    """
    nerve = grazer.trait("nerve")
    if grazer.energy < NERVE_HUNGER_LEVEL:
        nerve *= NERVE_HUNGER_BOOST
    return max(1.0, grazer.sense_range - nerve)


def _flees(grazer: Creature, threat: Creature) -> bool:
    """Whether a spotted hunter is close enough to be worth running from.
    Chebyshev distance, the same box shape sense_range uses, so the flight
    bubble and the sense box are the same shape and differ only in size.
    """
    distance = max(abs(threat.x - grazer.x), abs(threat.y - grazer.y))
    return distance <= _panic_radius(grazer)


def _herd_target(
    creature: Creature, grazers: list[Creature], food: "Resource | None"
) -> "Creature | None":
    """The grazer this one wants to go stand next to, or None if it would
    rather eat. Only consulted when nothing is chasing it - a threat always
    wins. With no food in sense range, joining the herd beats wandering at
    random, so it always goes; with food in range it's a coin weighted by
    the gregariousness gene, so the gene's real price is the meals it skips
    rather than an energy charge bolted on the side.
    """
    gregariousness = creature.trait("gregariousness")
    if gregariousness <= 0:
        return None
    companion = _nearest_creature(creature, grazers)
    if companion is None:
        return None
    if food is None:
        return companion
    _default, _step, _lo, hi = TRAIT_REGISTRY["gregariousness"]
    return companion if random.random() < gregariousness / hi else None


def _nearest_resource(creature: Creature, resources: list[Resource]) -> Resource | None:
    in_range = [
        r for r in resources
        if abs(r.x - creature.x) <= creature.sense_range
        and abs(r.y - creature.y) <= creature.sense_range
    ]
    if not in_range:
        return None
    return min(in_range, key=lambda r: abs(r.x - creature.x) + abs(r.y - creature.y))


def _edible(carcass: Carrion) -> bool:
    """Whether this body is food. Only prey species are (see
    SCAVENGEABLE_CARRION) - a hunter's remains are inert, so hunters neither
    walk toward them nor gain anything from standing on them."""
    return carcass.species in SCAVENGEABLE_CARRION


def _nearest_carrion(creature: Creature, carrion: list[Carrion]) -> Carrion | None:
    # Only ever called for a hunter looking for something to scavenge, so the
    # edibility filter belongs here rather than at the call site: an inedible
    # carcass is not a target, and a hunter should not spend its movement
    # walking to one.
    in_range = [
        k for k in carrion
        if _edible(k)
        and abs(k.x - creature.x) <= creature.sense_range
        and abs(k.y - creature.y) <= creature.sense_range
    ]
    if not in_range:
        return None
    return min(in_range, key=lambda k: abs(k.x - creature.x) + abs(k.y - creature.y))


def _closer_target(
    creature: Creature, prey: "Creature | None", carcass: "Carrion | None"
) -> "Creature | Carrion | None":
    """Which meal a hunter walks toward. Ties go to live prey - it's worth
    more energy, so when the trip is the same length it's the better bet."""
    if carcass is None:
        return prey
    if prey is None:
        return carcass

    def distance(target) -> int:
        return abs(target.x - creature.x) + abs(target.y - creature.y)

    return carcass if distance(carcass) < distance(prey) else prey


def _nearest_creature(
    creature: Creature, others: list[Creature], camouflage_aware: bool = False
) -> Creature | None:
    # camouflage_aware is only passed True for a hunter scanning for grazers.
    # It's the predator/prey detection path, and three things pull on the same
    # number there: each candidate's own camouflage AND its herd cover shrink
    # the searching creature's effective sense_range just for that candidate,
    # and the searcher's own acuity adds back to it. So a well-hidden grazer -
    # by pigment, by company, or both - can be standing well inside a hunter's
    # nominal sense_range and still go undetected, unless that hunter is
    # paying (in energy every tick, see ACUITY_COST) to see through it.
    # Grazers scanning for hunter threats, and grazers looking for each other,
    # are unaffected (camouflage_aware defaults to False), so none of this
    # ever helps the side it wasn't meant for. Note that a grazer's `nerve`
    # doesn't belong here either: it changes what a grazer DOES about a
    # hunter it has seen, never whether it sees it.
    def _effective_range(other: Creature) -> float:
        if not camouflage_aware:
            return creature.sense_range
        return max(
            0.0,
            creature.sense_range
            - other.trait("camouflage")
            - other.herd_cover
            + creature.trait("acuity"),
        )

    in_range = [
        o for o in others
        if o.id != creature.id
        and abs(o.x - creature.x) <= _effective_range(o)
        and abs(o.y - creature.y) <= _effective_range(o)
    ]
    if not in_range:
        return None
    return min(in_range, key=lambda o: abs(o.x - creature.x) + abs(o.y - creature.y))


def _move_toward(creature: Creature, target: "Resource | Creature | Carrion") -> None:
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


def _carrion_at(carrion: list[Carrion], x: int, y: int) -> Carrion | None:
    # Same as _nearest_carrion: this is the hunter's scavenging path, so an
    # inedible body on the tile is simply not there as far as it's concerned.
    for k in carrion:
        if k.x == x and k.y == y and _edible(k):
            return k
    return None


def _mutated_genes(
    speed: int, sense_range: int, traits: dict
) -> tuple[int, int, dict]:
    """One round of mutation over a whole genome. Shared by ordinary birth
    and by migrant arrival so a migrant drawn from lineage memory is exactly
    'a child of the remembered stock', with no second, divergent copy of the
    mutation rules to keep in sync.
    """
    if random.random() < MUTATION_RATE:
        speed = max(1, speed + random.choice([-1, 1]))
    if random.random() < MUTATION_RATE:
        sense_range = max(1, sense_range + random.choice([-1, 1]))

    # Generic mutation for whatever's in TRAIT_REGISTRY - adding a new gene
    # there is enough to make it inherit and mutate correctly, no extra code
    # needed here.
    new_traits = dict(traits)
    for name, (default, step, lo, hi) in TRAIT_REGISTRY.items():
        value = new_traits.get(name, default)
        if random.random() < MUTATION_RATE:
            value = _clamp(value + random.choice([-step, step]), lo, hi)
        new_traits[name] = value

    return speed, sense_range, new_traits


def _reproduce(parent: Creature) -> Creature:
    speed, sense_range, new_traits = _mutated_genes(
        parent.speed, parent.sense_range, parent.traits
    )

    cost = REPRODUCE[parent.species]["cost"]
    return Creature(
        id=str(uuid.uuid4()),
        x=parent.x,
        y=parent.y,
        energy=cost // 2,
        speed=speed,
        sense_range=sense_range,
        species=parent.species,
        traits=new_traits,
    )


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _wrap(v: int) -> int:
    return v % GRID_SIZE
