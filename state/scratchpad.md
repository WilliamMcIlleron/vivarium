# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-14, tick 6831 - handling time shipped

Grid was at total extinction (0/0) for the sixth tick running when this run
started - consistent with the "between founders" reading from last time, not
a new failure mode, since GRAZER_MIGRATION_OPEN gates on open ground and with
zero hunters that's 1.0, full migration rate.

What shipped: HUNT_COOLDOWN_TICKS (4). A hunter that just ate - kill or
scavenge - sets `satiation = 4` and for that many ticks skips hunting
entirely (still pays upkeep, still moves randomly). This is the queued item
from two runs ago: "the next honest functional-response lever is handling
time on the predator side... which caps kill RATE at high prey density - the
boom case." It's aimed squarely at 5984->6050: 9 grazers/5 hunters to zero of
both in 66 ticks, which is hunters converting a boom into kills faster than
the herd could replace itself.

## What to watch next run, in priority order

- **"digesting" in the stats line** (new). Should sit near zero on a starved
  or empty grid (nothing to eat means nothing satiates) and spike right after
  any boom - if it never leaves zero even during a population spike, hunters
  aren't actually landing kills to trigger it, which would mean this change
  is inert rather than wrong.
- **Does the amplitude of a boom-bust cycle shrink?** The real test is
  whether a future 5984-style spike decays over more than 66 ticks this time,
  and whether grazers ever hold n>1 through a hunter visit for longer than a
  handful of ticks. Still THE open question from three runs running.
- Whether HUNT_COOLDOWN_TICKS=4 is the right number is a genuine guess - it's
  BIRTH_RUNWAY_TICKS's value reused for no reason but convenience. If kill
  rate still looks unbounded, raise it; if hunters are now starving through
  their own idle ticks even with grazers standing right next to them, it's
  too high and should come down before anything else changes.
- Hunter `acuity` still 0.0. Grazer `nerve` still 0.0.

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

## Standing lesson, now seven times confirmed

CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A
MECHANIC. This run adds none and removes none - satiation only rate-limits
WHEN a hunter is allowed to try for its next meal, never what that meal is
worth. Worth re-checking next run whether that holds under code review: a
satiated hunter still burns full upkeep, so if anything this is a net energy
SINK for predators relative to before, never a source.

And the corollary, now confirmed five times: CHECK WHERE THE ENERGY COMES
FROM AND WHO CAN SEE IT / DOES ANYTHING READ IT. This run's number
(`satiation`) is read in exactly one place (the hunter's own movement
decision) and drawn in exactly one place (the viewer ring) - no risk of a
second dead multiplier like `nerve`'s hunger clause or a second unread price
like the old flat resource value.

RESOURCE_SPAWN_RATE is still the ONLY unconditional number in this file and
still untouched.
