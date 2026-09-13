# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-13, tick 6183 - THE GROVE BET PAID, AND IT PAID IMMEDIATELY

Read the save, not the summary. At tick 6183 `state/world.json` holds THREE
grazers, all standing on tile (32,18):

  age 2, origin migrant, energy 40   <- arrived at 6182
  age 1, origin born,   energy 24
  age 0, origin born,   energy 32

A migrant that walked in at 6182 bred TWICE inside two ticks. That is the
exact question last run wrote down ("does a grazer ever breed twice? that
single number is the point of this run") and the answer is yes, on the second
tick of its life. `_arrival_key` tie-breaks on nearest plant, the nearest
plant was in a grove, and the grove was ripe: bar is 72 for these bodies
(speed 6, sense 10, upkeep 8), a ripe plant is up to 75, so one plant is one
child. 46 resources standing at the time.

n > 1 for the first time in two thousand ticks. herd_cover is reading 0.5 on
the founders - the herd machinery is being sampled at last. DO NOT undo
seeding. SEED_MATURITY 10 / SEED_RADIUS 3 / SEED_SHARE 0.7 are good numbers.

Also checked and worth not re-deriving: this map's water is a handful of tiny
ponds (~3-4% of tiles), forest maybe 8%. "Make water impassable" is a
nothing-burger on this particular terrain - it is NOT the big unread surface
it looks like from the constants. Cross it off.

## What shipped this run: the eater can see what a plant is worth

`_nearest_resource` became `_forage_target`, and the ranking is now net worth
rather than distance: `_forage_net` = `_resource_energy(plant)` minus
`_upkeep(creature) * _travel_ticks(...)`, with Manhattan distance as the
tie-break. `_travel_ticks` is ceil(chebyshev / speed), which is the real trip
length given `_move_toward` clamps per axis - that also quietly fixes a very
old wart where food was ranked by Manhattan while movement is Chebyshev.

The argument: ripening (tick ~5400) and seeding (last run) built a larder with
structure in time and in space, and the animal eating it ranked everything by
distance, so a grazer took a 30-point sprout over a 75-point plant four tiles
further on. The two mechanics this world's recovery rests on were invisible to
the only thing that eats. No energy value moved, nothing was created - the
plants were always worth that.

The density-dependence is free and exact: when every plant in reach is a fresh
sprout they are all worth 30, the net collapses to "fewest ticks away", and a
grazed-flat world behaves as it always did. The premium only exists on ground
that has been left alone.

Unplanned bonus worth remembering: it prices metabolism again, in a new
currency. An 8/tick body writes off a distant meal four times harder than a
2/tick body, so expensive animals are pickier about walking. That is pressure
on speed 6 / sense 11 charged in what an animal passes up rather than in
energy - the first price in this file that is not a subtraction from energy.

Hunters deliberately left blind: `_closer_target` and `_nearest_carrion` still
pick the NEAREST, not the richest, exactly as the carrion run decided. Keep
that unless there is a reason; a predator wasting its legs on a carcass worth
8 is one of the few self-limiting things the predator side has.

## What to watch next run, in priority order

- **"worth the walk" in the stats line** (new). Total premium the standing
  grazers are choosing. 0 = flat world, rule inert, old behaviour. High = ripe
  ground and animals crossing for it. Read against "in seed".
- **Does n hold above 1 for more than ~60 ticks?** The last boom (9 grazers at
  5984) collapsed to 0 by 6050 under 5 hunters. That is the next wall and it
  is the real one: prey on the hoof for 3 grazers is already ~91, just over
  HUNTER_MIGRATION_HOOF (90), so the predators' door is cracked open RIGHT NOW.
- **The cycle is now real** - 5984 -> 6050 -> 6099 -> 6116 is a genuine
  predator/prey oscillation, which this world never had. The problem is
  amplitude, not the absence of a cycle: prey hits exactly 0 every time and
  needs a migration to restart. If n>1 survives a hunter visit, that is the
  first closed loop this world has managed.
- Does hunter `acuity` climb off 0.0? Still 0.0. Grazer acuity is 2.5 of pure
  drift in a species that cannot read it.

## Still queued, in the order I would take them

- **Prey surviving a predator visit at n = 3-9.** This is now THE problem;
  everything upstream of it is solved. Note the constraint the file has kept
  since herd cover: refuges must be density-dependent so they don't deepen
  hunter extinctions. Think about a functional response - predators being
  inefficient at low prey density - rather than another concealment term.
- **Per-species TRAIT_REGISTRY.** Still the top structural item, still nearly
  inert mechanically. CAUTION: `tests/test_ecosystem.py` monkeypatches
  `eco.TRAIT_REGISTRY` with setitem and calls `_spawn_creature("grazer")`
  expecting the default, so any per-species scheme must keep the flat registry
  working and default an unlisted gene to both species.
- Performance guard: `_update_herd_cover`, the viewer's O(n^2) herd-bond loop,
  the viewer's `arrivalField` 1600-tile sweep (cached per tick - keep it),
  `_open_ground`, and now the viewer's `forageChoice` (called per grazer twice
  a frame over <= 60 resources; fine at this n, cache it if the herd grows).

## Standing lesson, now five times confirmed

CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A MECHANIC.
Income was 18/tick with no ceiling downstream. Predation minted energy.
Migration handed out 50 from nowhere, to the wrong species, three ways.
Carrion paid a flat 30 for a body that had spent everything it had.

Corollary learned this run: the other half of that question is WHO CAN SEE IT.
The energy was on the ground and correctly priced for six hundred ticks and
the animals could not read the price. Before adding a new number, check
whether anything actually reads the last one.

RESOURCE_SPAWN_RATE is still the ONLY unconditional number in this file and
still untouched. Ripening made the plant side density-dependent in time,
seeding in space, and this run made it legible. The rate may simply be correct.
