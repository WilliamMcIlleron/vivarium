# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-14, tick 6863 - grazer trickle immigration shipped

Grid was at 3 grazers, 0 hunters, hunters extinct for 19 straight logged
ticks. The genome snapshot handed to this run showed something new: avg_nerve
3.0 - the hard ceiling - across every grazer alive. Every previous mention of
nerve in this file's history says it "has sat at 0.0 in every grazer this
world has ever produced." It clearly isn't 0.0 any more.

Read as a small-population-genetics problem, not a bug: nerve has no per-tick
cost by design (its cost is meant to be predation risk, paid only once a
hunter exists to collect it), and with hunters extinct for the last twenty
ticks and only 2-3 grazers alive, a symmetric mutation step can walk the gene
to its cap by pure drift long before selection gets a vote. Whether this is
actually harmful depends entirely on what happens the next time a hunter
migrates back in and finds a herd with essentially no flight warning
(FLIGHT_WARNING_TICKS - 3.0, floored at FLIGHT_MIN_WARNING = 0.5).

What shipped: GRAZER_TRICKLE_POPULATION (3) / GRAZER_TRICKLE_RATE (0.01). A
small, separate chance of a grazer wandering in from outside even while the
species is NOT extinct, whenever the standing count is <=3 - drawing from the
same lineage memory as any other migrant, gated by the same open-ground check
the extinction migrant uses. This is deliberately NOT a rate bump on the
existing extinction-triggered GRAZER_MIGRATION_RATE - that one only ever
fires when grazers hit zero, which does nothing for a population that is
alive but too thin to keep its own gene pool honest.

## What to watch next run, in priority order

- **Does avg_nerve actually move off 3.0 once trickle immigrants start
  landing?** If it stays pinned at the ceiling even with occasional outside
  draws, either the trickle rate is too low to matter at this population size
  or the lineage memory itself is already saturated with maxed-nerve genomes
  (in which case the fix needs to happen further upstream, e.g. by not
  remembering every breeder indiscriminately).
- **Does a returning hunter cause a fast wipeout of a bold (low-nerve-warning)
  herd?** This was the concrete harm scenario motivating the change. If a
  hunter migrates in and the grazer population crashes hard within a handful
  of ticks, that's the nerve ceiling actually biting, and the trickle rate
  alone may not be enough - worth considering whether nerve's own mutation
  step or ceiling needs revisiting too.
- **"a grazer wanders in from outside" vs "a grazer migrates into the
  world"** in the event log - these are now two different code paths for two
  different reasons (thin population vs. total extinction). Worth checking
  they aren't both firing back-to-back in a way that looks like double
  immigration.
- Still carried over from last run: "digesting" in the stats line should sit
  near zero on a starved/empty grid and spike after a boom - not yet
  observable this run since hunters are extinct. HUNT_COOLDOWN_TICKS=4 is
  still an untested guess once hunters do return.
- Hunter `acuity` still 0.0 in remembered lineage (not visible in this run's
  snapshot since hunters are extinct - grazer sheet showed acuity 2.5, but
  that's the INERT copy grazers carry pointlessly, not the hunter one).

## Still queued, in the order I would take them

- **Per-species TRAIT_REGISTRY.** Still the top structural item, still
  nearly inert mechanically. CAUTION: `tests/test_ecosystem.py` monkeypatches
  `eco.TRAIT_REGISTRY` with setitem and calls `_spawn_creature("grazer")`
  expecting the default, so any per-species scheme must keep the flat
  registry working and default an unlisted gene to both species.
- Performance guard: `_update_herd_cover`, the viewer's O(n^2) herd-bond loop,
  the viewer's `arrivalField` 1600-tile sweep (cached per tick - keep it),
  `_open_ground`, and the viewer's `forageChoice` (per grazer, twice a frame).
- Water is ~3-4% of this map and forest ~8%: "make water impassable" is a
  nothing-burger on this terrain. Crossed off, don't re-derive it.

## Standing lesson, now eight times confirmed

CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A
MECHANIC. This run's trickle migrant is priced exactly like the existing
extinction migrant it's modeled on - fifty energy handed to one animal from
outside the budget - so it is not free, but it is bounded: GRAZER_TRICKLE_RATE
is a fifth of GRAZER_MIGRATION_RATE and only fires at all below
GRAZER_TRICKLE_POPULATION, so it cannot become a second unconditional income
stream the way plain migration once was.

And the corollary, now confirmed six times: CHECK WHERE THE ENERGY COMES FROM
AND WHO CAN SEE IT / DOES ANYTHING READ IT. `_grazer_trickle_chance` reuses
`_open_ground` and `_arrival_site`, both already read elsewhere, and the new
constants are read in exactly one function each - no second dead multiplier
risk like `nerve`'s hunger clause was for two thousand ticks.

RESOURCE_SPAWN_RATE is still the ONLY unconditional number in this file and
still untouched.
