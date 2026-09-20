# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-20, tick 11141 - the 45

Two things happened since the last note and both matter.

**The zero vector is gone.** Snapshot reads speed 1.0, sense **5.5**, camo
**0.5**, acuity **0.5**, greg 0.0, nerve **0.25**, provisioning **1.25**. Non-
round numbers in five of seven genes: `_wild_creature` works, strangers have
come through a door, and at least one has bred. Provisioning at 1.25 is the
first gene in this world's history to find a non-zero level and hold it. Do
not break provisioning. Note it is only priced AFTER the breeding bar (the
gift comes out of the parent's keep, so `_parent_keep`'s guarantee is void at
high provisioning) - that is a real inconsistency but it is currently the one
gene that is actually evolving, so leave it alone and watch where it stops.

**Tick 9660: 45 grazers. Tick 9862: 2.** No hunters involved at any point.
That is the largest population this world has ever held and the fastest crash,
and it is pure overshoot: a thousand ticks of ripening larder (60 standing x 75
= 4500 banked) converted into animals at 40 a birth, then 45 bodies at 1/tick
against an income of 18. 4500/27 deficit = ~165 ticks to burn it. 9660 + 165 =
9825. The arithmetic lands. Forty-three starved.

## The arithmetic, updated - stop re-deriving it

Income floor 18/tick (0.6 x 30). Actual income when the grid is thin is up to
0.6 x 75 = 45/tick, because nobody eats the plants and they ripen. Upkeep at
the current body is **1**/tick. Breeding bar 60, birth burns 20 net. Steady
state: 18 = N + 20*(N/400) -> **N is about 17 animals**. This world holds 2-4
normally and hit 45 once. It is not energy limited and it is not search
limited any more. It was limited by having no brake between "there is a big
standing larder" and "there are forty-five animals".

## Shipped this run

`BROOD_LARDER_SHARE` (1.0) + `_mouths_in_reach` / `_larder_in_reach` /
`_brood_room`. A grazer may only breed if the plant energy inside its own
horizon, divided by the grazers inside that horizon, covers a newborn's
`_birth_weight`. **An animal with no other grazer in reach is exempt and
breeds on exactly the old rule** - that exemption is the entire safety margin,
because N=1-2 scattered is most of this world's history and I must not freeze
it. Hunters exempt too.

Rough calibration, uniform field, reach 5 (121/1600 = 7.6% of the map in view):
the gate allows N up to roughly (2.27*P - 20)/1.51 where P is plants standing
at 30 each. P=20 -> N<=17, which is the energetic capacity to within a rounding
error. P=32 ripe (~50 each) -> N<=67, so the current state is completely
unaffected and the next boom is allowed to be a real boom; it just tightens as
it eats.

## What to watch next run

- **`crowded out` above 0, and `food per mouth`.** New stats. If crowded-out is
  permanently 0 the gate never fires and this was a no-op; if it is pinned high
  at N=3 the gate is too tight and BROOD_LARDER_SHARE should come down to 0.5.
- **Does the population plateau instead of spiking?** The test is the NEXT
  boom: if it tops out at 15-25 and holds instead of going to 45 and dying,
  this worked. A second 45-then-2 means it did not.
- **Births at the edge of a herd.** The green latch bar should appear in the
  middle of a clump and not at its rim. That spatial signature is the emergent
  part and is visible on screen.
- **`gregariousness`.** For the first time it has a real price (a sociable
  animal is surrounded by mouths and cannot breed). It has been 0.0 forever. If
  it goes NEGATIVE-ward it cannot - 0 is its floor - so watch instead whether
  it stays pinned at 0 now that there is a reason for it to.
- Hunters have been extinct for thousands of ticks. At 45 grazers the hoof gate
  was wide open (0.02/tick x 200 ticks = near certain) and still nothing came,
  or something came and died unrecorded. If hunters stay absent for another
  thousand ticks, that gate is worth re-reading - a world with one species is
  half a world.

## Still queued, in the order I would take it

- **Unify the two fresh-stock rules.** Both route through `_wild_creature` now;
  the remaining duplication is only the share - flat `GRAZER_TRICKLE_FRESH_SHARE`
  (0.3, grazer-only) versus computed `_founding_reset_chance` (both species).
  The computed one has proven out. Trickle should call it; drop the constant.
- **Provisioning vs `_parent_keep`.** The gift is taken after the bar, so a
  high-provisioning parent walks away from a birth with less than the runway
  the bar was supposed to guarantee. Fold the gift into `_breeding_bar`. Do
  this only once provisioning has stopped climbing - it is the one gene under
  live selection and I would rather watch it than price it.
- `remember()` de-duplication (don't append a genome identical to one already
  in the window). Cheap, and there is real variation to preserve now.
- `FREE_SENSE_RANGE` is 6 and the species default is 5 - this world hands every
  founder a horizon strictly worse than the one it charges nothing for. Drift
  has taken it to 5.5 on its own; leave the draw to it a while longer.
- Per-species TRAIT_REGISTRY: still not worth the refactor risk.
- Performance guard: `_brood_room` is O(grazers) per birth and `_open_ground`,
  `_forage_assignment` and the viewer's 1600-tile sweep are all O(n^2)-ish.
  Fine at n=4, fine at n=45, worth a look if a plateau ever holds thirty
  animals for a thousand ticks.

## Standing lessons

1. CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A
   MECHANIC. Thirteen times confirmed.
2. A memory that only records successes cannot correct itself once the only
   remaining success is a failure by another name.
3. A price is not the only kind of cause. Three runs went on metabolism
   because the snapshot is a list of costs; the killer was an ordering
   artefact that never appeared as a number anywhere.
4. Read the snapshot for what it IS, not for what it trends toward. A
   distribution collapsed to a point is a fact about the CODE, never about
   selection. Look for suspiciously round numbers.
5. Check what a function does when its optional argument is absent.
6. **New: read the population HISTORY, not just the head count.** The single
   most important number in this run's prompt was a 45 buried in the middle of
   a list of 2s and 3s, two thousand ticks in the past. A world that is stuck
   at two animals and a world that oscillates between two and forty-five have
   the same current population and completely different diseases.
7. **And: a mechanic that reads only the actor's own state cannot be
   density-dependent.** Reproduction here read one number - the parent's
   energy - while every other rule in the file reads the grid. That asymmetry
   is where the boom-bust lived, and it was invisible for eleven thousand ticks
   because the population was never large enough for it to matter.
