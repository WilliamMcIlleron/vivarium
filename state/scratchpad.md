# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-09 (later) - the newborn was the thing that was dying

Tick 3240: 3 grazers, 2 hunters, and TWENTY uneaten resources on the ground.
That last number is the whole diagnosis. Food is not scarce here and has not
been for a thousand ticks. Do the arithmetic on a grazer instead: speed 5.67
(~5/tick) plus sense_range 12 (3/tick vision upkeep) is ~9 energy a tick, and
a newborn starts on `cost // 2` = 20. That is a two-tick life. The adults are
superbly equipped and their children are born starving, which is why the
population cannot climb off five no matter how much food is lying around.

So: `provisioning` (0-3, step 0.5, PROVISION_ENERGY = 6). A parent hands up to
18 energy straight to the newborn, out of its own pocket, after the flat
breeding cost. Nothing is created - this only moves energy along the life
cycle - and it can only be afforded by a fat parent, since a grazer breeding
at exactly threshold 60 keeps 20 after cost and maximum generosity leaves it
with 2. `_provision` clamps to `parent.energy - 1` so a parent never pays
itself to instant death; it dies the ordinary metabolic way a tick later if it
overspent.

This is deliberately NOT another detection/movement gene. All four existing
genes are about seeing or running and all four are one-sided. This one is a
life-history trait and BOTH species read it, which is also the first honest
reason the registry has had to not be species-scoped.

Revert-safety (five reverts on record, all tests): no Creature field, no save
format change, `_reproduce(parent)` still takes one argument (`gift=0`), and
every creature alive today carries provisioning 0 -> gift 0 -> bit-identical
reproduction. `tests/test_ecosystem.py` calls `eco._reproduce(creature)`
directly in the trait-registry test; that still works.

What to watch next run:

- "brood stake" in the viewer stats, and `avg_provisioning` in the genome
  snapshot. Above ~0.5 means the world has started choosing quality over
  quantity. Watch what happens to population at the same time: if brood stake
  climbs AND population climbs, this was the missing dial. If brood stake
  climbs and population falls, parents are killing themselves for children
  that die anyway - drop PROVISION_ENERGY to 4 before touching anything else.
- If it stays flat at 0.0 for several hundred ticks, the gene is not being
  sampled because almost nothing is breeding at all - in that case the problem
  is upstream of life history and the next lever is grazer metabolic load
  (speed 5.67 is 5/tick on its own), not this.
- Hunters: still going extinct in a loop (3163-3235). The structural reason is
  worth writing down, because it is not carrion and not cover this time -
  prey outclass predators on every axis at once. Grazers see 12 tiles and flee
  at ~11.7; hunters see 7, minus camo 0.83 and canopy 1.5 = ~4.7 against a
  hidden grazer; grazers run at 5.67, hunters chase at 3. A hunter physically
  cannot close on a grazer that has already seen it. If hunters are still
  flickering next run, the fix is predator-side and should be about CLOSING
  distance, not about seeing further - an ambush/stillness concealment (a
  motionless hunter becomes hard for grazers to see, paid for in ground not
  covered) is the design I'd reach for, and it mirrors herd cover as a
  density-dependent, prey-abundance-gated advantage.
- Vision upkeep verdict, one run in: grazer avg sense went 11.0 -> 12.0, i.e.
  UP, not down. Three animals is nowhere near enough to call it; do not touch
  FREE_SENSE_RANGE yet. Re-read at the next snapshot with >6 grazers.
- Prior watch item, still open: if hunters go extinct for hundreds of ticks
  with grazers stable, forest cover 1.5 -> 1.0 is the first lever. Do NOT
  reopen cannibalism, and do not nerf canopy and fertility together.
- `nerve` STILL has never had a population to be selected in.
- Overdue: TRAIT_REGISTRY now holds four one-sided genes plus one genuinely
  shared one (provisioning). Per-species registry as its own run, nothing else
  in the diff - and note that provisioning is the counter-example that has to
  keep working after it.
