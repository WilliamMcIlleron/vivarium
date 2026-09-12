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

Three genes and the ground itself fight over the same number - the hunter's
effective sense_range when it is looking for live prey. A grazer's `camouflage`
shrinks it (hiding as an individual); a grazer's herd cover shrinks it further
(hiding as a crowd - see HERD_RADIUS); forest canopy shrinks it again for any
grazer standing under it (see TERRAIN_COVER); a hunter's `acuity` adds back to
it, at a per-tick energy cost. Concealment is something prey can buy three
different ways, and seeing through any of them is something a predator has to
be able to afford.

The map is therefore no longer scenery. Its counterweight is food: resources
grow according to how much light reaches the ground (TERRAIN_FERTILITY), so
the safest tiles on the grid are also the emptiest ones. Cover and food are in
different places, and a grazer that wants to eat has to leave the trees.

Fleeing, meanwhile, is not a reflex, and as of this run it is not measured in
tiles either. A grazer judges a predator by how long it would take to arrive:
it demands a few ticks of clearance (FLIGHT_WARNING_TICKS, cut by the `nerve`
gene and cut further when it is hungry) and multiplies that by the hunter's
own speed, so a shambling scavenger can be ignored at four tiles while a
sprinter is worth running from at fifteen. Seeing far and fleeing early are
therefore separate decisions now, which they were not back when flight
distance was simply sense_range. When it does run, it runs for the trees
rather than in a straight line (see _move_away).

Nothing about a body here is free. Speed costs energy every tick (MOVE_COST),
a hunter's acuity costs energy every tick (ACUITY_COST), and so does the
horizon itself (see FREE_SENSE_RANGE): eyes out to the species baseline are
part of the animal, and every couple of tiles of sight beyond that is paid for
forever, whether or not they ever find anything. An unpriced gene does not
find an optimum - it only ratchets. The whole of that per-tick bill lives in
one place, `_upkeep`.

Bodies are not the only thing a genome decides here. `provisioning` is this
world's first life-history gene: it sets how much of a parent's own energy
goes into each newborn instead of into staying alive to breed again (see
PROVISION_ENERGY). It creates nothing - every point the child starts with is a
point the parent no longer has - and it is the only gene in the registry that
both species read for the same reason, because "many cheap offspring or few
expensive ones" is a question a predator faces exactly as squarely as its prey.

Reproduction, as of this run, is priced by the body too. A newborn used to be
handed a flat `cost // 2` whatever it was going to be, so breeding a speed-7
grazer with a twelve-tile horizon cost precisely what breeding a speed-1 one
did - even though the first child burns its whole endowment in two ticks and
the second lives twenty on it. A newborn is now sent out with
BIRTH_RUNWAY_TICKS ticks of its own upkeep (`_birth_weight`), floored at that
old flat number, and the difference is raised by the parent BEFORE it is
allowed to breed at all (`_breeding_bar`). An expensive genome therefore has a
higher bar to clear every single generation, which puts selection on
metabolism at the reproductive bottleneck instead of only in slow attrition -
the one place it can still act in a population of two.

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

# Nerve: how much warning a grazer insists on having before it abandons what
# it is doing and runs.
#
# Flight used to be measured in tiles, and the tiles were the grazer's own
# sense_range: anything it could see, it ran from, minus a flat `nerve`. That
# made the two most important numbers on a prey animal the same number, and
# tick 4147 is the bill. Grazers had drifted to sense_range 12 and so panicked
# at 11.5 tiles - a 23x23 box, a third of the entire grid - at three hunters
# whose top speed is 2. Something was inside that box roughly seven ticks out
# of ten, so the animal spent its whole life sprinting at 7 energy a tick away
# from predators that could never physically have caught it, and starved on a
# map with eighteen uneaten resources lying on the ground. `nerve` was added
# at tick 1728 to be the counterweight to exactly this and structurally could
# not be: nerve is capped at 3.0 and sense_range is capped at nothing, so the
# brake was always going to be outrun by the thing it was braking.
#
# So a grazer now judges a predator the way a real prey animal does - by how
# long it would take to arrive, not by how far away it is. It demands
# FLIGHT_WARNING_TICKS ticks of clearance, and the number of tiles that buys
# depends entirely on the hunter in front of it: a shambling speed-1 scavenger
# has to be within three tiles to be worth interrupting a meal for, while a
# speed-6 sprinter is worth running from at eighteen. `nerve` subtracts from
# the warning itself, so for the first time it is measured on the same scale
# as the thing it counters and its 0-3 range spans the entire useful range of
# the decision instead of chasing an unbounded gene. Hunger still multiplies
# it, because an animal that is about to starve is risking very little by
# staying.
#
# The consequences are meant to run both ways. Prey can finally buy a long
# horizon (which still costs energy, see FREE_SENSE_RANGE) without buying
# paranoia along with it - seeing far and fleeing early are separate decisions
# at last. And a hunter's speed is no longer only about the chase: it is the
# radius of its own reputation, ground that prey will not stand and feed on
# while it is there. A fast enough predator can starve a grazer without ever
# touching it.
NERVE_HUNGER_LEVEL = 25       # energy below which a grazer accepts the extra risk
NERVE_HUNGER_BOOST = 1.5      # multiplier applied to nerve while hungry
FLIGHT_WARNING_TICKS = 3.0    # ticks of clearance a nerveless grazer demands
FLIGHT_MIN_WARNING = 0.5      # even the bravest won't let one arrive unannounced

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

# The price of a horizon.
#
# sense_range was the last first-class gene in this world with no cost on it
# at all, and by tick 3091 the grazers had drifted to an average sense_range
# of 11 - more than double the species default. That is a 23x23 box, a third
# of the entire map, and it is not the harmless "finds food better" upgrade it
# looks like, because a grazer's flight distance IS its sense_range (see
# _panic_radius). An animal that can see a third of the world panics at a
# hunter a third of the world away, and at the speed 6 those same grazers had
# drifted to it burns 6 energy every tick doing it - which is the exact
# starvation-while-fleeing death spiral `nerve` was added at tick 1728 to
# stop. Nerve could never stop it: nerve is capped at 3.0 and sense_range is
# capped at nothing, so the counterweight was structurally unable to catch up
# with the thing it was counterweighting. Third time this world has learned
# the same lesson, after MOVE_COST and ACUITY_COST: an unpriced gene doesn't
# find an optimum, it just ratchets.
#
# One correction, from tick 4147: the middle of that argument is no longer
# true. Flight distance is not sense_range any more - it is ticks of warning
# against a particular hunter's speed (see FLIGHT_WARNING_TICKS) - so a long
# horizon has stopped being a paranoia radius. The first and last sentences
# stand exactly as written, and this charge is now the ONLY thing keeping
# sense_range honest, which is a reason to leave it alone rather than a reason
# to relax it.
#
# It is meant as a soft ceiling, not a nerf. At sense_range 6 a creature pays
# nothing at all; at 11, where the grazers actually are, it pays 2 a tick -
# enough to be a real reason to come back down, not enough to be a death
# sentence for the two animals currently holding this world open.
FREE_SENSE_RANGE = 6
SENSE_COST_STEP = 2
SENSE_COST = 1

MUTATION_RATE = 0.1                 # chance any given gene mutates on reproduction
MAX_AGE = 400

# Hunters are deliberately a K-strategist relative to grazers: much costlier
# to reproduce, so a single lucky kill doesn't immediately mint a new hunter
# and spiral into a hunter population that outstrips its own food supply.
REPRODUCE = {
    "grazer": {"threshold": 60, "cost": 40},
    "hunter": {"threshold": 110, "cost": 55},
}

# How many ticks of its own upkeep a newborn is sent into the world with.
#
# The flat `cost // 2` endowment was written when a grazer cost 1 energy a
# tick, and 20 energy was a twenty-tick childhood. The grazers this world
# actually produces now run at speed 6 with a twelve-tile horizon - 9 energy a
# tick - so the same 20 is a two-tick childhood on a 1600-tile grid. Tick 4209
# is roughly the thousandth in a row where a population sitting on twenty
# uneaten resources could not put a child far enough to reach one.
# PROVISION_ENERGY was added at tick 3240 to let a parent fix that
# voluntarily, and nine hundred ticks later `provisioning` is still 0.0 in
# both species: a gene needs a population to be sampled in, and there isn't
# one.
#
# So the endowment is no longer a constant, it is a runway: a newborn starts
# with BIRTH_RUNWAY_TICKS ticks of whatever body it inherited, floored at the
# old `cost // 2` so nothing cheap changes at all. The important half is who
# pays for it. The parent raises the difference BEFORE it is allowed to breed
# (see _breeding_bar), so an expensive animal's threshold rises with its own
# metabolism - a speed-6, sense-12 grazer must reach 76 instead of 60, while a
# speed-1 grazer breeds at 60 exactly as it always did - and what the parent
# is left holding afterwards is identical either way.
#
# That is the whole point. Every price this world has put on a gene so far has
# been charged per tick, and a per-tick charge only selects through attrition;
# attrition needs a population large enough that the merely inefficient
# outnumber the unlucky. This one is charged at the reproductive bottleneck,
# where it bites within a single generation, which is the only timescale a
# world holding two animals has. It creates no energy and destroys none: a
# cheap lineage is bit-for-bit unaffected, and an expensive one simply has to
# be fatter before it may have a child.
#
# The feedback it sets up is density-dependent, which is what makes it an
# ecology rather than a nerf. After a crash, uneaten resources pile up, and
# even an expensive migrant can clear the higher bar - so the remembered
# bloodline still gets its chance to breed. As the population recovers and the
# larder thins, the bar is what decides who keeps breeding, and that is the
# cheap animal every time.
BIRTH_RUNWAY_TICKS = 4

# Parental provisioning: extra energy a parent hands to its newborn, on top of
# the standard endowment, per point of the `provisioning` gene.
#
# Tick 3240 is the argument for this. The world holds 3 grazers, 2 hunters and
# twenty uneaten resources lying on the ground - food is not what is missing.
# What is missing is children that live long enough to walk to one. Grazers
# have drifted to speed 5.67 and sense_range 12, which is about 5 energy a
# tick of movement plus 3 of vision upkeep: roughly 9 a tick, every tick, for
# an animal that starts life with `cost // 2` = 20 energy. That is a two-tick
# lifespan for a newborn on a 1600-tile grid. The adults are superbly equipped
# and their offspring are born starving, which is why a population sitting on
# a full larder has not grown past five animals in a thousand ticks.
#
# Every gene in this world so far has been about detection or movement - what
# an animal can see, what can see it, how fast it runs. None of them touches
# the one decision every real organism has to make: many cheap offspring or
# few expensive ones. `provisioning` is that decision, and nothing else in the
# tick has to change for it to matter.
#
# The property that makes it safe: it creates no energy. Every point the child
# starts with is a point the parent no longer has, so the ecosystem's total
# budget is exactly what it was - this only moves energy along the life cycle,
# from an animal that has already proved it can feed itself to one that hasn't.
# And it can only be afforded by a fat parent: a grazer breeding at exactly its
# threshold of 60 has 20 left after the cost, so maximum generosity leaves it
# with 2 and almost certainly dead before its next meal. A parent never pays
# itself below 1 energy (see _provision), so the gene buys a child's head start
# out of the parent's future, never out of an instant suicide. Whether this
# world chooses a few well-stocked young or a great many doomed ones is the
# entire point of adding it.
#
# Note how it now relates to BIRTH_RUNWAY_TICKS above: the runway is the
# minimum every child is owed and the parent must have saved up for, while
# provisioning is what a parent chooses to add on top of that floor. One is
# the law, the other is generosity.
PROVISION_ENERGY = 6

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

# Terrain is a fixed landscape generated once at world creation. Nothing here
# ever regenerates or redesigns it - the map you get is the map the world
# keeps - but as of this run it is no longer inert decoration: step() reads it
# through the two tables below.
TERRAIN_CODES = "wsgf"  # water, sand, grass, forest

# What the ground is worth to whatever is standing on it.
#
# TERRAIN_COVER is concealment, and it enters the world at exactly the same
# place camouflage and herd cover do: it subtracts from a hunter's effective
# sense_range when that hunter is looking for a grazer standing on that tile
# (see _nearest_creature). Only the canopy hides anything; grass, sand and
# open water are all the same bare ground they always were. It is prey-side
# only - a hunter in the trees is as visible as it ever was, because grazers
# never use the camouflage_aware path - and `acuity` already cancels it point
# for point, the same counter that exists for the other two.
#
# Why now: this world has held 0 grazers with GRAZERS EXTINCT in nearly every
# tick since 1813, and the reason a re-migrating grazer never establishes is
# that on 1600 identical tiles there is nowhere to be that is safer than
# anywhere else. A refuge is a different kind of fix from a gene - it's a
# place, not a stat, so it helps the animal that has not had time to evolve
# anything yet.
#
# TERRAIN_FERTILITY is the price of that refuge. Resources are drawn toward
# ground that gets light, so the canopy grows almost nothing: the safest tiles
# on the map are also the emptiest. The total spawn rate is untouched
# (RESOURCE_SPAWN_RATE still decides IF a resource appears, this only decides
# WHERE), so this moves food around rather than adding or removing any - it
# buys the hiding place with hunger instead of with an energy charge bolted on
# the side, the same way gregariousness is paid for in missed meals.
TERRAIN_COVER = {"f": 1.5, "g": 0.0, "s": 0.0, "w": 0.0}
TERRAIN_FERTILITY = {"g": 1.0, "s": 0.8, "w": 0.6, "f": 0.25}
FERTILITY_ATTEMPTS = 12   # rejection-sampling tries before a resource lands anywhere

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
# camouflage, herd cover and canopy rather than a general-purpose senses
# upgrade. Unlike camouflage it is not free: see ACUITY_COST.
#
# gregariousness: how strongly a grazer with nothing chasing it will walk
# toward the nearest grazer it can see instead of toward food. That's what
# makes herd cover (HERD_RADIUS) an evolvable strategy rather than an accident
# of where creatures happen to stand - and it pays for itself in missed meals
# rather than in a flat energy charge, since a grazer standing in the herd is
# a grazer not standing on a resource.
#
# nerve: how much warning a grazer insists on having before it stops feeding
# and runs (see FLIGHT_WARNING_TICKS). It shrinks that warning, measured in
# ticks, never the grazer's perception - a nervy grazer sees the predator
# perfectly well and keeps eating anyway - and its price is the shorter head
# start it leaves itself. Because the warning is a small fixed number of ticks
# rather than an unbounded sense_range, this gene's 0-3 range finally spans
# the whole decision it is supposed to govern.
#
# provisioning: how much of its own remaining energy a parent pours into each
# newborn instead of keeping it to survive and breed again (see
# PROVISION_ENERGY). The first four genes above are all about detection or
# movement, and all four are one-sided - each species carries the other's
# inertly. This one is neither: it is a life-history trait, it moves no
# energy into or out of the world, and BOTH species read it, because "many
# cheap offspring or few expensive ones" is a question a predator faces
# exactly as squarely as its prey.
TRAIT_REGISTRY: dict[str, tuple[float, float, float, float]] = {
    "camouflage": (0.0, 0.5, 0.0, 3.0),
    "acuity": (0.0, 0.5, 0.0, 3.0),
    "gregariousness": (0.0, 0.5, 0.0, 3.0),
    "nerve": (0.0, 0.5, 0.0, 3.0),
    "provisioning": (0.0, 0.5, 0.0, 3.0),
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
        # one rather than fail. A world with no terrain at all still runs:
        # every lookup falls back to open grass (see _terrain_at), i.e. no
        # cover anywhere and uniform fertility, exactly how this world
        # behaved before the ground meant anything.
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

        # Food grows where light reaches the ground: same per-tick chance of a
        # resource as always, but WHERE it lands is weighted by biome (see
        # TERRAIN_FERTILITY). Open grass is the larder, the canopy is nearly
        # bare - which is what makes the forest a refuge you have to leave.
        if random.random() < RESOURCE_SPAWN_RATE:
            x, y = _forage_location(self.terrain)
            self.resources.append(Resource(x=x, y=y))

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
        # ever walks toward one. Grazers run from whichever visible hunter is
        # most URGENT - not necessarily the nearest one any more, since a
        # grazer's flight distance is now ticks of warning multiplied by that
        # particular predator's speed (see _flight_threat), so a distant
        # sprinter can matter more than a slow scavenger two tiles away - and
        # they flee toward the best cover they can reach rather than in a
        # straight line; otherwise they either drift toward company
        # (gregariousness) or head for the nearest resource, falling back to a
        # random walk if nothing relevant is in sense range.
        # Grazers reusing sense_range for threat detection means the same
        # mutating gene trades off "finds food better" against "spots
        # predators better" - no separate dial. What it no longer trades off
        # against is the animal's own nerve: perceiving a hunter and running
        # from it are two different questions now.
        # Layered on top of that, four things pull on the hunter's
        # prey-detection number and nothing else: a grazer's `camouflage`, its
        # herd cover and the canopy over the tile it's standing on all
        # subtract from the hunter's effective sense_range, and the hunter's
        # `acuity` adds back to it. None of them does anything for a carcass:
        # hiding is a behaviour of the living, and a body in the open takes no
        # special eye to find.
        for creature in self.creatures:
            creature.age += 1
            if creature.species == "hunter":
                prey = _nearest_creature(
                    creature, grazers, camouflage_aware=True, terrain=self.terrain
                )
                carcass = _nearest_carrion(creature, self.carrion)
                target = _closer_target(creature, prey, carcass)
                if target is not None:
                    _move_toward(creature, target)
                else:
                    _move_random(creature)
            else:
                threat = _flight_threat(creature, hunters)
                if threat is not None:
                    _move_away(creature, threat, self.terrain)
                else:
                    target = _nearest_resource(creature, self.resources)
                    companion = _herd_target(creature, grazers, target)
                    if companion is not None:
                        _move_toward(creature, companion)
                    elif target is not None:
                        _move_toward(creature, target)
                    else:
                        _move_random(creature)
            # The entire per-tick bill for being this animal - its speed
            # (MOVE_COST), its horizon (FREE_SENSE_RANGE) and, for a hunter,
            # its acuity (ACUITY_COST) - charged in one place and
            # arithmetically identical to the three separate deductions it
            # replaces. It lives in _upkeep now because reproduction reads the
            # same number: what a body costs to run is what it costs to start
            # (see _birth_weight).
            creature.energy -= _upkeep(creature)

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
            # The bar is no longer the same for everybody. An animal has to be
            # able to afford the runway its child will need (see
            # BIRTH_RUNWAY_TICKS), which for an expensive body means reaching a
            # higher number before it may breed at all - and for a cheap one
            # means exactly the species threshold it always was.
            if creature.energy >= _breeding_bar(creature):
                endowment = _birth_weight(creature)
                creature.energy -= repro["cost"] + endowment - repro["cost"] // 2
                # Life history: on top of the cost of breeding, the parent
                # decides how much of what's left it hands straight to the
                # newborn (see PROVISION_ENERGY). Nothing is created here -
                # every point the child starts with is a point the parent is
                # now short, and it comes out of the parent's own chances of
                # surviving to breed again. At provisioning 0, which is what
                # every creature in this world carries today, the gift is zero.
                gift = _provision(creature)
                creature.energy -= gift
                newborns.append(_reproduce(creature, gift, endowment))
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
    every tick. The smoothing matters more than it used to: contiguous
    forest is a refuge a grazer can run into, single scattered cells would
    only be noise.
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


def _terrain_at(terrain: list[str] | None, x: int, y: int) -> str:
    """The biome code of one tile, defaulting to open grass for anything the
    map doesn't cover - a world loaded from a save with no terrain, or a
    lookup off the end of a short row. Grass is the neutral choice: no cover,
    full fertility, i.e. exactly how this world behaved before the ground
    meant anything.
    """
    if not terrain:
        return "g"
    if not (0 <= y < len(terrain)):
        return "g"
    row = terrain[y]
    if not (0 <= x < len(row)):
        return "g"
    return row[x]


def _cover_at(terrain: list[str] | None, x: int, y: int) -> float:
    """How much this tile hides whatever is standing on it (TERRAIN_COVER)."""
    return TERRAIN_COVER.get(_terrain_at(terrain, x, y), 0.0)


def _forage_location(terrain: list[str] | None) -> tuple[int, int]:
    """Where a new resource lands. Rejection sampling against
    TERRAIN_FERTILITY - pick a tile, keep it with that biome's probability,
    try again otherwise - so no per-tile weight table has to be built or kept
    in sync with the map. After FERTILITY_ATTEMPTS the last draw is taken
    regardless, which keeps the total spawn RATE exactly what
    RESOURCE_SPAWN_RATE says it is: this decides where food grows, never how
    much of it there is.
    """
    x = random.randrange(GRID_SIZE)
    y = random.randrange(GRID_SIZE)
    for _ in range(FERTILITY_ATTEMPTS):
        if random.random() < TERRAIN_FERTILITY.get(_terrain_at(terrain, x, y), 1.0):
            return x, y
        x = random.randrange(GRID_SIZE)
        y = random.randrange(GRID_SIZE)
    return x, y


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


def _vision_cost(creature: Creature) -> int:
    """Energy per tick this creature pays simply for being able to see as far
    as it does (see FREE_SENSE_RANGE). Whole tiles only: the first
    FREE_SENSE_RANGE tiles of horizon are part of the body and free, and past
    that the charge steps up once every SENSE_COST_STEP tiles rather than
    sliding - so a single point of drift is never immediately expensive, and
    the bill only really lands on a lineage that has committed to seeing a
    long way. Not a gene of its own and not stored on the creature: it is
    derived from sense_range every tick, so the save format is untouched and
    a creature at or below the allowance is charged nothing at all.
    """
    excess = creature.sense_range - FREE_SENSE_RANGE
    if excess <= 0:
        return 0
    return int(SENSE_COST * (excess // SENSE_COST_STEP))


def _upkeep(creature: Creature) -> int:
    """Everything this creature pays every single tick simply for being the
    animal it is: its speed (MOVE_COST), its horizon (see _vision_cost) and,
    for a hunter, its acuity (ACUITY_COST). A grazer's inherited acuity is
    inert and is not billed, exactly as before.

    This is the precise charge step() applies. It is factored out here because
    reproduction now reads the same number - the cost of running a body and
    the cost of starting one must not be able to drift apart (see
    _birth_weight).
    """
    cost = MOVE_COST * creature.speed + _vision_cost(creature)
    if creature.species == "hunter":
        cost += int(ACUITY_COST * creature.trait("acuity"))
    return cost


def _birth_weight(parent: Creature) -> int:
    """The energy a newborn of this parent is sent out with: BIRTH_RUNWAY_TICKS
    ticks of the body it is about to inherit, and never less than the flat
    `cost // 2` every child in this world used to get regardless of what it
    was. A cheap animal is therefore completely unaffected; an expensive one
    produces a child that is correspondingly expensive to launch.

    Measured on the PARENT, since the child's genome doesn't exist until
    _reproduce mutates one - which is honest enough, because a mutation moves
    speed by one and sense_range by one at most, and provisioning for the body
    you know is exactly what a real parent does.
    """
    cost = REPRODUCE[parent.species]["cost"]
    return max(cost // 2, BIRTH_RUNWAY_TICKS * _upkeep(parent))


def _breeding_bar(parent: Creature) -> int:
    """The energy THIS animal has to reach before it may reproduce: the species
    threshold, plus whatever its newborn's runway costs above the old flat
    endowment. A creature living inside that flat floor breeds at exactly the
    number it always did.

    Note what does NOT change: the parent is left holding `threshold - cost`
    when it breeds at its own bar, whatever that bar is, so this moves the
    price of admission and never the aftermath. The bar is the only new
    pressure here, and it is a pressure on metabolism at the one moment
    metabolism has never yet been priced.
    """
    repro = REPRODUCE[parent.species]
    return repro["threshold"] + _birth_weight(parent) - repro["cost"] // 2


def _provision(parent: Creature) -> int:
    """Energy this parent hands to its newborn on top of the endowment it was
    already required to save up for (see PROVISION_ENERGY and _birth_weight).
    Whole points only, and never more than the parent can give while still
    ending the tick alive: a generous animal buys its child a head start out of
    its own future, not out of an immediate suicide, so the cause of death here
    is always the ordinary metabolic one a tick or two later.

    At provisioning 0 - which is what every creature currently alive in this
    world carries, and what every creature in tests/ carries - this is exactly
    zero and reproduction behaves as it always has.
    """
    invest = parent.trait("provisioning")
    if invest <= 0:
        return 0
    return max(0, min(int(PROVISION_ENERGY * invest), parent.energy - 1))


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


def _warning_ticks(grazer: Creature) -> float:
    """How many ticks of clearance this grazer insists on having between
    itself and an approaching hunter before it gives up on whatever it was
    doing. Starts at FLIGHT_WARNING_TICKS - the nerveless default - and is cut
    by the nerve gene, amplified while the animal is hungry enough that a
    missed meal is its own kind of death. Never reaches zero: nerve buys
    patience, not blindness.

    This is the number that used to be a distance, and the change is the whole
    point. A warning measured in ticks is bounded by the tick, so a gene that
    caps at 3.0 can actually span it; a warning measured in tiles was bounded
    by sense_range, which caps at nothing at all.
    """
    nerve = grazer.trait("nerve")
    if grazer.energy < NERVE_HUNGER_LEVEL:
        nerve *= NERVE_HUNGER_BOOST
    return max(FLIGHT_MIN_WARNING, FLIGHT_WARNING_TICKS - nerve)


def _panic_radius(grazer: Creature, threat: Creature) -> float:
    """How close THIS hunter has to get before this grazer drops what it is
    doing and runs: the ground that particular predator covers in the warning
    the grazer demands. It is a property of the pair, not of the prey alone -
    the same grazer will ignore a shambling scavenger at four tiles and bolt
    from a sprinter at fifteen - which is what turns a hunter's speed into
    something prey react to rather than only something that catches them.

    Never below one tile, since anything standing next to you is worth running
    from however slowly it moves.
    """
    closing = max(1, threat.speed)
    return max(1.0, closing * _warning_ticks(grazer))


def _flees(grazer: Creature, threat: Creature) -> bool:
    """Whether a spotted hunter is close enough to be worth running from.
    Chebyshev distance, the same box shape sense_range uses, measured against
    a radius that belongs to this particular predator (see _panic_radius).
    """
    distance = max(abs(threat.x - grazer.x), abs(threat.y - grazer.y))
    return distance <= _panic_radius(grazer, threat)


def _flight_threat(grazer: Creature, hunters: list[Creature]) -> "Creature | None":
    """The hunter this grazer actually runs from, or None if it can hold its
    ground and keep feeding.

    Not necessarily the nearest one. Now that flight distance scales with a
    predator's own speed, the nearest hunter and the most dangerous hunter can
    be different animals - a speed-1 scavenger three tiles away may be beneath
    notice while a speed-6 sprinter ten tiles off is not - so every hunter
    inside sense_range is judged on its own terms and the worst of them, the
    one furthest inside the panic radius it personally earns, is what the
    grazer flees. Perception is unchanged: a hunter it cannot see cannot
    frighten it.
    """
    worst: Creature | None = None
    worst_urgency = 0.0
    for hunter in hunters:
        if hunter.id == grazer.id:
            continue
        if (
            abs(hunter.x - grazer.x) > grazer.sense_range
            or abs(hunter.y - grazer.y) > grazer.sense_range
        ):
            continue
        if not _flees(grazer, hunter):
            continue
        distance = max(abs(hunter.x - grazer.x), abs(hunter.y - grazer.y))
        urgency = _panic_radius(grazer, hunter) - distance
        if worst is None or urgency > worst_urgency:
            worst = hunter
            worst_urgency = urgency
    return worst


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
    # walking to one. Terrain doesn't enter into it - a body in the trees is
    # still a body, and hiding is a behaviour of the living.
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
    creature: Creature,
    others: list[Creature],
    camouflage_aware: bool = False,
    terrain: list[str] | None = None,
) -> Creature | None:
    # camouflage_aware is only passed True for a hunter scanning for grazers.
    # It's the predator/prey detection path, and four things pull on the same
    # number there: each candidate's own camouflage, its herd cover AND the
    # canopy over the tile it's standing on shrink the searching creature's
    # effective sense_range just for that candidate, and the searcher's own
    # acuity adds back to it. So a well-hidden grazer - by pigment, by
    # company, by standing in the trees, or all three - can be well inside a
    # hunter's nominal sense_range and still go undetected, unless that hunter
    # is paying (in energy every tick, see ACUITY_COST) to see through it.
    # Grazers scanning for hunter threats, and grazers looking for each other,
    # are unaffected (camouflage_aware defaults to False), so none of this
    # ever helps the side it wasn't meant for - a hunter in the forest is as
    # visible to its prey as it ever was. Note that a grazer's `nerve` doesn't
    # belong here either: it changes what a grazer DOES about a hunter it has
    # seen, never whether it sees it.
    def _effective_range(other: Creature) -> float:
        if not camouflage_aware:
            return creature.sense_range
        return max(
            0.0,
            creature.sense_range
            - other.trait("camouflage")
            - other.herd_cover
            - _cover_at(terrain, other.x, other.y)
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


def _move_away(
    creature: Creature, threat: "Creature", terrain: list[str] | None = None
) -> None:
    """Flight - toward the trees where there are any.

    A fleeing grazer used to move the full length of its speed in a straight
    line directly away from the hunter, which on a featureless grid was the
    only sensible thing to do. Now that the canopy actually conceals
    (TERRAIN_COVER), running in a straight line is often the WORSE move: a
    tile of forest one step off the escape vector takes 1.5 off the hunter's
    effective sense_range, which can drop the grazer out of its detection box
    entirely, while another two tiles of open ground only buys distance from a
    predator that can still see exactly where it went.

    So the grazer looks at every tile it could reach this tick, keeps the ones
    that actually open the gap (strictly greater Chebyshev distance, measured
    before wrapping so the map seam can't be mistaken for a head start), and
    takes the best cover among them, breaking ties on distance. That's the
    tradeoff in one line: cover first, ground second. If nothing increases the
    distance the animal is cornered, and it falls back to exactly the old
    behaviour - a straight-line shove away, or a random scramble if it's
    standing on the hunter's own tile.
    """
    here = max(abs(creature.x - threat.x), abs(creature.y - threat.y))
    best_key = None
    best_tile = None
    for dx in range(-creature.speed, creature.speed + 1):
        for dy in range(-creature.speed, creature.speed + 1):
            gap = max(abs(creature.x + dx - threat.x), abs(creature.y + dy - threat.y))
            if gap <= here:
                continue
            nx, ny = _wrap(creature.x + dx), _wrap(creature.y + dy)
            key = (
                _cover_at(terrain, nx, ny),
                gap,
                abs(creature.x + dx - threat.x) + abs(creature.y + dy - threat.y),
            )
            if best_key is None or key > best_key:
                best_key = key
                best_tile = (nx, ny)

    if best_tile is not None:
        creature.x, creature.y = best_tile
        return

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


def _reproduce(
    parent: Creature, gift: int = 0, endowment: "int | None" = None
) -> Creature:
    """One offspring of `parent`, with a mutated copy of its genome, starting
    on `endowment` (see _birth_weight) plus whatever the parent chose to hand
    over on top of it (see _provision). Both arguments fall back to the
    behaviour that existed before either idea did - a flat `cost // 2` and no
    gift - so calling this with a parent alone, as tests/ does, produces
    exactly the newborn it always did.
    """
    speed, sense_range, new_traits = _mutated_genes(
        parent.speed, parent.sense_range, parent.traits
    )

    cost = REPRODUCE[parent.species]["cost"]
    if endowment is None:
        endowment = cost // 2
    return Creature(
        id=str(uuid.uuid4()),
        x=parent.x,
        y=parent.y,
        energy=endowment + gift,
        speed=speed,
        sense_range=sense_range,
        species=parent.species,
        traits=new_traits,
    )


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _wrap(v: int) -> int:
    return v % GRID_SIZE
