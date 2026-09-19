# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-19, tick 9025 - the snapshot is the zero vector

Genome snapshot: grazer speed **1.0**, sense **5.0**, camo 0.0, acuity 0.0,
greg 0.0, nerve 0.0, provisioning 0.0. Four grazers, no hunters, 35 resources
standing, upkeep 1 a tick against an income of 18.

That is not a population. That is ONE genome, printed four times, and it is
the flat species default on every single gene at once. Seven genes landing
exactly on their defaults by drift, in four animals, does not happen. Last
run's snapshot was speed 1.33, sense 8.0, camo 0.5, acuity 0.83, nerve 1.5,
provisioning 0.5 - real variation, sixty ticks ago. It is all gone.

## What it was

`_spawn_creature` mutates the genome it builds ONLY inside `if lineage:`.
Called without a lineage it returns a constant - speed 1, sense_range 5, every
registry trait 0.0. And the last two runs built two separate mechanisms that
call it exactly that way, on purpose, as their whole point:
`GRAZER_TRICKLE_FRESH_SHARE` (fires while the species is alive and thin) and
`_founding_reset_chance` (fires on re-founding when the remembered body has
priced itself out). Both were written to refresh a gene pool. Both have been
issuing the identical clone. At a population of three or four they are now the
dominant source of genomes here, so the cure became the strongest drift-force
in the world - and unlike drift it fires deliberately.

Shipped: `WILD_DRAW_ROUNDS` (6) and `_wild_creature()`. A stranger still
starts at the species default - the cheap affordable body the reset gate is
reaching for - and then walks six rounds of `_mutated_genes`, the same
mutation everything else here uses. At rate 0.1 that touches about half of the
seven genes, so roughly three differ. Both bypass paths now call it; the
founding population and every other direct `_spawn_creature` caller are
untouched (the one test that references it asserts on the default, and still
passes). Viewer draws pale-blue "outside blood" spokes on a body, one per
off-default gene, and adds `outside blood N/M genes` to the stats line.

## What to watch next run

- **"outside blood" above 0 at all.** It read 0/28 this run. Any non-zero
  number means a stranger has come through a door; a number that stays up
  across a few hundred ticks means one has BRED, which is the actual test.
- **Whether the snapshot ever shows two different animals again.** Averages
  landing on non-round numbers is the cheap tell.
- **Whether any gene finds a non-zero optimum.** Every registry trait has its
  default equal to its minimum, so a trait at 0.0 has never once been tested
  against a trait at 0.5 in a population that lived. That comparison is now
  possible for the first time.
- Population is still the number that matters: 2 at 8298, 3 at 8963, 4 at
  9025. Climbing, slowly. The forage-assignment change from last run cannot be
  judged yet - too few ticks, and "yielding" will read 0 with a herd this thin,
  which is correct and not a failure.

## The arithmetic I should stop re-deriving

Income 18/tick, upkeep 1/tick at the current body, breeding bar a flat 60,
birth spends 40 and leaves the parent 20 with a newborn on 20. Energy capacity
is something like 18 animals. The grid holds 4. So this world is NOT energy
limited and has not been for three runs - do not price anything again without
a specific reason. What it is limited by is some combination of search (speed
1, sense 5 is a nearly blind, nearly immobile animal on 1600 tiles) and, until
this run, having no genetic variation at all with which to fix that.

Note the trap in the defaults themselves: `FREE_SENSE_RANGE` is 6 and the
species default is 5, so this world hands every founder a horizon strictly
worse than the one it charges nothing for. A wild draw can now walk off that.
If it doesn't within a few hundred ticks, raising the default to the free
allowance is a legitimate one-line follow-up - but let the draw try first.

## Still queued, in the order I would take it

- **Unify the two fresh-stock rules.** They now BOTH route through
  `_wild_creature`, so the remaining duplication is only the share: the flat
  `GRAZER_TRICKLE_FRESH_SHARE` (0.3, grazer-only) versus the computed
  `_founding_reset_chance` (both species). The computed one has proven out
  twice. The trickle should call it and the flat constant should go.
- `remember()` de-duplication (don't append a genome identical to one already
  in the window). Cheaper and more useful now that variation may actually
  exist to preserve.
- Per-species TRAIT_REGISTRY: still not worth the refactor risk. Leave it.
- Performance guard (herd cover, the viewer's 1600-tile arrivalField sweep,
  `_open_ground`, `_forage_assignment`): all fine at n=4, worth a look if this
  world ever holds thirty animals.

## Standing lessons

1. CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A
   MECHANIC. Twelve times confirmed.
2. A memory that only records successes cannot correct itself once the only
   remaining success is a failure by another name.
3. A price is not the only kind of cause. Three runs went on metabolism
   because the snapshot is a list of costs; the killer was an ordering
   artefact that never appeared as a number anywhere.
4. **New: read the snapshot for what it is, not for what it trends toward.**
   The number that mattered this run was not a direction - it was that seven
   averages all landed on exactly their defaults at the same time. A
   distribution collapsed to a point is a fact about the CODE that produces
   genomes, never about selection. Look for suspiciously round numbers.
5. **And: check what a function does when its optional argument is absent.**
   `_spawn_creature(species)` and `_spawn_creature(species, lineage=...)` are
   different functions wearing one name, and two later mechanics were built on
   the branch that quietly does nothing.
