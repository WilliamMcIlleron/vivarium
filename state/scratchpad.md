# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-16, tick 7282 - the lineage trap, sprung exactly as predicted

Grid: 1 grazer, 0 hunters, 18 resources. Genome: speed 8.0, sense 8.0, nerve
STILL 3.0, camo 1.0, acuity 2.5, greg 1.0, provisioning 0.5. Ticks 7265-7281
are HUNTERS EXTINCT every single tick, with a total EXTINCTION at 7269 and a
re-founding grazer migrant at 7270 - which arrived at speed 8.0, i.e. the
failure mode last run's watch list named verbatim:

  "If grazers go extinct and every refounding migrant is a doomed speed-8 body
  while the trickle (which only fires when the species is ALIVE at <=3) never
  gets a chance to inject a cheap one, the world can lock."

It locked. Two runs of evidence was the bar I set; I got it in one, because
the migrant at 7270 is visibly the old stock (speed 8.0 in this run's
snapshot, twelve ticks after it walked in). So I took the queued fix.

Shipped: `_world_income()` (= RESOURCE_SPAWN_RATE * RESOURCE_ENERGY = 18/tick,
the first time this file has ever compared a genome against the world's
budget), `_founding_reset_chance()` and `_refounding_migrant()`, wired into
BOTH extinction-migration branches in step(). Affordable upkeep is income /
FOUNDING_CAPACITY(3) = 6. The reset share ramps 0 -> 1 across one more
affordable-upkeep above that (FOUNDING_RESET_SPAN 1.0):

  upkeep  6 -> 0%     (speed 5 sense 5: drawn from lineage as always)
  upkeep  7 -> 17%
  upkeep 10 -> 67%    (speed 7 sense 8)
  upkeep 11 -> 83%    (speed 8 sense 8 - the current bloodline)
  upkeep 12 -> 100%

Deliberately NOT a flat share like GRAZER_TRICKLE_FRESH_SHARE: this one is
self-clearing (only a cheap breeder can close it, and `remember()` closes it
automatically) and it is bit-for-bit inert for an affordable bloodline - the
`chance > 0` short-circuit means no extra random.random() is consumed in that
case, so cheap-lineage arrivals are identical down to the seed and tests that
seed random are safe. Hunters get the identical rule; their default (upkeep 2)
and any plausible remembered hunter sit far inside the band.

The interlock with last run: the sprint charge made the resident bloodline
expensive (9 -> 11) and the flat default cheap (1). This run is what lets the
world actually REACH the cheap one. Those two changes only work together.

## What to watch next run

- **Does a fresh-default grazer actually establish?** Viewer prints "founder
  reset" per species and the door's inner shape fades violet -> pale blue.
  Expect ~83% on the grazer line right now. If the next extinction re-founds
  at speed 1 / sense 5 / nerve 0 / upkeep 1 / bar 60, that animal has an
  eighteen-per-tick world to itself and SHOULD compound. If it breeds,
  `remember()` writes a cheap genome, founder reset falls toward 0, and the
  memory is repaired permanently.
- **Watch the memory line, not just avg speed.** lineage is a rolling window
  of 8; one cheap breeder only moves the average by an eighth. Judge by the
  "grazer ... speed" figure in the remembered-bloodline readout.
- If founder reset stays high for 300+ ticks AND no fresh migrant ever
  establishes, the problem is no longer the genome - it is that 50 starting
  energy plus an 18/tick income cannot get ANY body to a bar in time, and the
  next lever is the spatial one (groves / arrival near food), not another
  price.

## Still queued, in the order I would take it

- **Unify the two fresh-stock rules.** GRAZER_TRICKLE_FRESH_SHARE (flat 0.3,
  grazer-only, fires while ALIVE and thin) and `_founding_reset_chance`
  (computed, both species, fires on extinction) now do the same job by two
  different mechanisms. If the computed one proves out, the trickle should
  just call it and the flat constant should go. Deliberately left for a later
  run - one change per run.
- `remember()` de-duplication (don't append a genome identical to one already
  in the window). Less urgent now: the income check attacks the same
  monoculture from the draw side.
- Per-species TRAIT_REGISTRY: still not worth the refactor risk. Leave it.
- Performance guard (herd-cover O(n^2), viewer's arrivalField 1600-tile sweep,
  _open_ground, viewer's forageChoice): untouched, still queued.

## Standing lesson, now eleven times confirmed

CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A MECHANIC.
This run adds and removes no energy either; it makes the world compare a
genome's per-tick cost against the income for the first time. Corollary added
this run: **a memory that only records successes cannot correct itself once
the only remaining success is a failure by another name.** World.lineage
records breeders; when the sole surviving bloodline breeds once and then dies
out every time, the memory is a record of a death sentence and it is sealed
against update. Any future "the world remembers X" mechanic needs an outside
channel that does not depend on X succeeding.
