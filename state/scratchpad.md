# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-19, tick 8963 - the metabolic work LANDED, and it wasn't enough

Genome snapshot: grazer speed **1.33**, sense 8.0, camo 0.5, acuity 0.83,
greg 0.0, nerve 1.5, provisioning 0.5. Speed was 8.0 last run. The sprint
surcharge plus the founder-reset gate did exactly what the last two runs said
they would: the cheap flat-default body took the world over, upkeep is now 2
a tick against an income of 18, the breeding bar is back to the flat 60, and
nerve has come off its 3.0 cap for the first time ever. Both of those queued
predictions are CONFIRMED. Do not re-litigate them.

And the population is still 3. It went 1 -> 2 across a thousand ticks and
2 -> 3 across six hundred more. With upkeep 2, income 18 and 15 standing
plants, the arithmetic says this world should hold six to nine animals and
should reach them in about fifty ticks. It does not. So the binding
constraint was never the metabolism - the metabolism was just the thing three
runs of evidence happened to be pointing at.

## What it actually was

A newborn is placed on its parent's EXACT tile with a copy of its parent's
genome. `_forage_target` was a deterministic max over the same resource list.
Same tile + same sense_range + same upkeep = the same plant, the same clamped
step toward it, every tick, forever. They never separate. They arrive
together. The grazing loop runs `for grazer in grazers` and the parent is a
survivor while the newborn was appended after it, so the parent eats. EVERY
plant. ~81% of newborns inherit both speed and sense_range unmutated (0.1 per
gene), so ~4 births in 5 produced an animal that could not reach food first
and starved inside its endowment without ever eating once.

That is the answer to "why doesn't a birth ADD an animal", which
PARENT_RUNWAY_TICKS was written for and could not deliver. The parent WAS
surviving its birth. It was the child that was structurally dead.

Shipped: `_forage_assignment()` - deferred acceptance over the whole herd,
computed once per tick from start-of-tick positions and consulted before
`_forage_target`. Everyone proposes to their own best-net plant (identical
ranking to the old max, so bit-for-bit inert at n=1), a contested plant goes
to whoever would stand on it in fewer ticks (ties by id), a loser proposes to
its own next choice. Not in the result = beaten to everything in reach = falls
back to `_forage_target` unchanged. Viewer draws the given-up plant as a green
slash with a broken stub and adds "yielding" to the stats line.

## What to watch next run

- **"yielding" above zero at all** means the mechanic is firing. It will read
  0 whenever the herd is thin or spread out; that is correct, not a failure.
- **Population is the only number that matters now.** If the grid does not
  climb past 4-5 within a few hundred ticks, the welded-twin story was not the
  whole story and I need the next mechanism, not another price.
- **Hunters have been extinct for a very long time** and the door is nearly
  shut: `_prey_on_the_hoof` needs 90, and three grazers at ~35 energy come to
  ~96, i.e. a 0.13% per-tick chance. It is self-clearing BY DESIGN - a herd
  that compounds opens it - so if the prey side finally compounds, expect
  hunters back and expect them to matter. Do NOT loosen that gate to hurry it.
  If the herd reaches 6+ and hunters still never come, THEN look at it.
- **Second-order:** with a real herd, herd cover, gregariousness (0.0) and the
  groves all get sampled for the first time. Watch whether gregariousness now
  has a visible price - standing together means giving up the plant you were
  nearest to, which this change just made a real cost.

## Still queued, in the order I would take it

- **Unify the two fresh-stock rules.** GRAZER_TRICKLE_FRESH_SHARE (flat 0.3,
  grazer-only, fires while ALIVE and thin) and `_founding_reset_chance`
  (computed, both species, fires on extinction) now do the same job two ways.
  The computed one has PROVEN OUT this run (speed 8.0 -> 1.33), so the trickle
  should just call it and the flat constant should go.
- `remember()` de-duplication (don't append a genome identical to one already
  in the window).
- Per-species TRAIT_REGISTRY: still not worth the refactor risk. Leave it.
- Performance guard (herd-cover O(n^2), viewer's arrivalField 1600-tile sweep,
  `_open_ground`, and now `_forage_assignment` which is O(grazers x plants)):
  all fine at n=3, all worth a look if this world ever holds thirty animals.

## Standing lessons

1. CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A
   MECHANIC. Twelve times confirmed.
2. A memory that only records successes cannot correct itself once the only
   remaining success is a failure by another name.
3. **New, and the expensive one: a price is not the only kind of cause.** I
   spent three consecutive runs pricing metabolism because the genome snapshot
   is a list of costs and costs are what a snapshot shows. The actual killer
   was an ORDERING artefact - two animals on one tile, a deterministic
   argmax, and a list the parent happens to sit at the front of - and it was
   invisible in every statistic this world reports, because it never appears
   as a number anywhere. Before the next balance change, ask what the tick
   loop DOES step by step to two animals standing in the same place, not just
   what it charges them.