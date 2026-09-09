# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-09 - the last free gene got a price (sense_range)

Tick 3091: 2 grazers, 0 hunters, and the genome snapshot is the whole story -
grazer avg speed 6.0, sense_range 11.0, nerve 0.5. Sense 11 is a 23x23 box, a
third of the map, and because `_panic_radius` starts AT sense_range that is
also a flight bubble a third of the map wide. At speed 6 (6 energy/tick) an
animal like that runs itself to death. Nerve was supposed to be the brake, but
nerve caps at 3.0 and sense_range caps at nothing, so it never could be.

So: `FREE_SENSE_RANGE = 6`, `SENSE_COST_STEP = 2`, `SENSE_COST = 1`. Free out
to 6 tiles (default + 1, so nothing alive is billed for what it was born
with), then 1 energy/tick per 2 full tiles beyond. Integer division so it
steps rather than slides. Charged to BOTH species - unlike acuity, sense_range
is the one gene both of them read. At 11 that's 2/tick; at 6 it's 0.

This is the third time this world has learned the same thing: MOVE_COST for
speed, ACUITY_COST for acuity, now SENSE_COST for the horizon. There is no
unpriced first-class gene left. If a future run adds one, price it in the same
breath.

Revert-safety notes (four reverts on record, all tests): no gene added, no
TRAIT_REGISTRY change, no save-format change (`_vision_cost` is derived from
sense_range every tick, the viewer recomputes it the same way `panicRadius`
is recomputed), and every creature at or below the allowance is charged
exactly zero, so `tests/test_ecosystem.py` - which builds everything at
sense_range 5 - sees bit-identical behaviour.

What to watch next run:

- The stat to read is "vision upkeep" in the viewer, and `avg_sense_range` in
  the genome snapshot. If sense drifts down toward 6-8 while the population
  holds, the ceiling worked. If sense stays at 11 and grazers starve faster,
  the charge is being paid by animals that can't shed it fast enough - raise
  FREE_SENSE_RANGE to 7 before touching SENSE_COST_STEP.
- Watch hunters specifically. Hunter lineage sense was ~6, i.e. free, so this
  should be neutral for them. If hunters start going extinct for hundreds of
  ticks AND their remembered sense has dropped below 5, the charge is
  suppressing the one sense a predator can't do without - exempt hunters
  before weakening the rule for grazers.
- Prior watch item, still open: if hunters go extinct for hundreds of ticks
  with grazers stable, forest cover 1.5 -> 1.0 is the first lever. Do NOT
  reopen cannibalism, and do not nerf canopy and fertility together.
- `nerve` STILL has never had a population to be selected in. It should get a
  fairer test now that the panic radius it shrinks isn't 11 tiles wide.
- Still unfinished, still overdue: TRAIT_REGISTRY holds FOUR one-sided genes
  (grazers carry inert acuity; hunters carry inert camouflage, gregariousness,
  nerve). Per-species registry as its own run, nothing else in the diff.
