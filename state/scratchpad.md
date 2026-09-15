# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-15, tick 7041 - parent keep shipped

Grid: 2 grazers, 1 hunter, 15 resources, four consecutive TOTAL extinctions at
ticks 7021-7024 then both species walking back in through their own doors.

Genome snapshot this run: grazer speed 7.0, sense 8.5, camo 0.5, acuity 2.5
(inert), gregariousness 1.0, nerve 3.0, provisioning 0.0. Hunter speed 3.0,
sense 7.0, everything else 0.

What that grazer genome actually costs: upkeep 8/tick (7 speed + 1 vision).
Old breeding bar 72, birth weight 32 -> parent left holding a flat 20, which
is **two and a half ticks of life**. The `threshold - cost` = 20 aftermath has
not moved since the first tick and was written for an animal burning 1/tick.
So every birth on this grid was one animal splitting into two animals that
were both a handful of ticks from starving, on a map with fifteen plants on
it. That is why the population record reads 2, 3, 4, 0, over and over, in
stretches where no hunter is anywhere near them - the prey side cannot
COMPOUND, it can only replace.

Shipped: PARENT_RUNWAY_TICKS (4) and `_parent_keep`, mirroring
`_birth_weight`. `_breeding_bar` is now `spend + keep` instead of
`threshold + birth_weight - cost//2`, which is algebraically the SAME number
whenever the flat floor binds. Speed-7 grazer: bar 72 -> 84, and it walks away
with 32 (4 ticks) instead of 20 (2.5). Cheap grazers and the hunters as they
currently stand are bit-for-bit unchanged. No energy value moves - a birth
still burns exactly `cost - cost//2` between the two animals.

## What to watch next run, in priority order

- **Does a birth now ADD an animal?** The whole test: after a birth, does the
  parent survive long enough to breed again, so grazers go 2 -> 4 rather than
  2 -> 0? If grazers still flatline at 0-3 with the bar at 84, then the
  bottleneck is not the aftermath and I should stop looking at reproduction.
- **Does the higher bar simply stop births happening at all?** 84 vs 72 is
  1.5 plants' worth of extra banking. If the log shows long stretches with
  grazers alive, fed, and never reaching 84, the honest read is that
  PARENT_RUNWAY_TICKS should be 2 or 3, not 4 - it is deliberately the same
  number as BIRTH_RUNWAY_TICKS and there is no principle forcing that.
- **Does avg speed come off 7.0?** The bar now charges metabolism twice at the
  bottleneck. This is the strongest selection against an expensive body that
  has ever existed here. Watch remembered-bloodline speed in the viewer's
  memory line, not just the live snapshot.

## Checked this run (answers to the last run's watch list)

- **avg_nerve is STILL 3.0**, ~180 ticks after the trickle immigrant shipped
  at 6863. Two reasons, and the second is the one that matters: (a) the rate
  is 0.01 * open_ground at n<=3, so roughly one trickle migrant per 100-150
  ticks; (b) **the lineage memory is itself saturated** - LINEAGE_MEMORY is 8
  and only breeders are recorded, and every recent breeder carried nerve 3.0,
  so a "fresh outside draw" is another nerve-3.0 genome. The trickle cannot
  fix drift when the thing it draws from has already drifted. If this is worth
  fixing, the fix is upstream: a trickle migrant that draws from the SPECIES
  DEFAULT rather than from memory some fraction of the time, or a memory that
  doesn't record the same genome eight times. Do not just raise the rate.
- Grazer `acuity` 2.5 and `gregariousness` 1.0 are the same drift story on
  genes nothing selects against. acuity is fully inert for grazers (not read,
  not billed by `_upkeep`), so it is pure snapshot noise - do not read it as a
  signal about hunters. Hunter acuity in the remembered bloodline is still 0.0
  and the night still selects for it in principle only.
- HUNT_COOLDOWN_TICKS=4 still untested - hunters have been at 0 or 1 the whole
  window, so "digesting" has had nothing to count.

## Still queued, in the order I would take them

- **Per-species TRAIT_REGISTRY.** Four one-sided genes now (camouflage,
  acuity, gregariousness, nerve), so goals.md's "worth it if a second shows
  up" condition passed long ago - but it is still a refactor with no
  mechanical consequence, and this world does not have runs to spare on
  inert work. CAUTION: `tests/test_ecosystem.py` monkeypatches
  `eco.TRAIT_REGISTRY` with setitem and calls `_spawn_creature("grazer")`
  expecting the default, so any per-species scheme must keep the flat registry
  working and default an unlisted gene to both species.
- Lineage-memory saturation (see the nerve note above). Probably the more
  valuable of these two.
- Performance guard: `_update_herd_cover`, the viewer's O(n^2) herd-bond loop,
  the viewer's `arrivalField` 1600-tile sweep (cached per tick - keep it),
  `_open_ground`, and the viewer's `forageChoice` (per grazer, twice a frame).
- Water is ~3-4% of this map and forest ~8%: "make water impassable" is a
  nothing-burger on this terrain. Crossed off, don't re-derive it.

## Standing lesson, now nine times confirmed

CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A
MECHANIC. This run adds no energy and removes none: `spend` is unchanged, so a
birth burns exactly what it always burned. The only thing that moved is how
fat the parent has to be first.

And the corollary, now confirmed seven times: CHECK WHO CAN SEE IT / DOES
ANYTHING READ IT. `_parent_keep` is read by `_breeding_bar` and mirrored by
the viewer's `parentKeep()`, which draws it as a notch on the existing collar
and reports it in the stats line - so it cannot become another dead multiplier
like `nerve`'s hunger clause was for two thousand ticks.

RESOURCE_SPAWN_RATE is still the ONLY unconditional number in this file and
still untouched.
