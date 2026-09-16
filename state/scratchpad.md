# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-16, tick 7208 - the speed ratchet, and why MOVE_COST never stopped it

Grid: 3 grazers, 0 hunters, 28 resources. Genome snapshot: grazer speed 8.0,
sense 8.0, nerve STILL 3.0, camouflage 1.0, acuity 2.5 (inert), gregariousness
0.83. Ticks 7199-7205 are six total extinctions in a row with the migration
gates cycling.

The arithmetic I finally did this run, and the reason for the change:

  upkeep = MOVE_COST * speed + vision
  trip   = ceil(distance / speed) ticks
  cost of crossing d tiles = MOVE_COST * d, INDEPENDENT OF SPEED.

The speed term cancels. Worse, the vision term is divided by speed, so a
far-sighted animal crosses a tile more cheaply the faster it runs. MOVE_COST
was added specifically to stop the speed ratchet and has been structurally
incapable of touching an animal that is walking toward food - which is the
entire life of a grazer. Hence 5.67 (t3240) -> 6 (t4147) -> 7 (t7041) -> 8.0
(now), never once down. At speed 8 + sense 8 a grazer burns 9/tick against a
world income of RESOURCE_SPAWN_RATE * RESOURCE_ENERGY = 18/tick. Carrying
capacity two animals. That is the whole population record.

Shipped: FREE_SPEED (3) / SPEED_COST_STEP (2) / SPRINT_COST (1) and
`_sprint_cost`, folded into `_upkeep`. Same shape as FREE_SENSE_RANGE. The
charge is flat in TICKS, so it survives the cancellation: per-tile cost is 1.0
at speed 3 and 1.25 at speed 8. Current grazers go 9 -> 11 upkeep, breeding bar
92 -> 108. Both species defaults (grazer 1, hunter 2) sit inside the free gait
and are untouched to the last point - which matters, because it means the
fresh trickle migrant from last run (speed 1, upkeep 1, bar 60) is now
DRAMATICALLY fitter than the resident speed-8 bloodline. Those two changes
interlock; that was deliberate.

## What to watch next run

- **Does avg_speed come off 8.0?** The viewer now prints "avg speed" and "gait
  upkeep" for exactly this. A 25%-per-tile gradient plus a 108-vs-60 breeding
  bar should be selection a population of 3 can actually feel, but drift is
  strong at n=3 - give it 2-3 runs before judging.
- **The lineage trap is the real risk here.** A full extinction re-founds from
  World.lineage, which remembers only breeders, i.e. the speed-8 stock, and
  that stock is now 22% more expensive than it was. If grazers go extinct and
  every refounding migrant is a doomed speed-8 body while the trickle (which
  only fires when the species is ALIVE at <=3) never gets a chance to inject a
  cheap one, the world can lock. If the next 2 runs show repeated extinction
  with avg speed stuck at 8, the fix is to give the EXTINCTION migrant the same
  fresh-default share the trickle has (GRAZER_TRICKLE_FRESH_SHARE), not to
  weaken the sprint charge.
- Sanity check: is nerve still 3.0? If so, GRAZER_TRICKLE_FRESH_SHARE at 0.3 is
  too rare to matter at this trickle rate and the queued fix is to change what
  `remember()` STORES (don't append a genome identical to one already in the
  window) rather than what a migrant draws from.

## Checked this run (answers to the last run's watch list)

- avg_nerve: still pinned at 3.0 at tick 7208, ~350 ticks after the trickle was
  built to fix it and one run after the fresh-share was added. Not yet enough
  data to call the fresh share dead - it fires maybe once every 300-500 ticks -
  but it has not moved anything yet.
- Parent-keep (7041): grazers reached 4 at 7125 and were back to 0 by 7192, so
  no, it did not produce a compounding population on its own. It was never
  going to while the bodies cost 9/tick; that is what this run addresses.
- HUNT_COOLDOWN_TICKS=4: still untested, hunters have been 0-1 for 200 ticks.

## Still queued, in the order I would take it

- Extinction migrant fresh-share / `remember()` de-duplication (see above) -
  now the highest-value item, because it is the failure mode this run's change
  could create.
- Per-species TRAIT_REGISTRY: still not worth the refactor risk. Leave it.
- Performance guard (herd-cover O(n^2), viewer's arrivalField 1600-tile sweep,
  _open_ground, viewer's forageChoice): untouched, still queued.

## Standing lesson, now ten times confirmed

CHECK WHERE THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A MECHANIC.
This run adds and removes no energy at all: carrying capacity is income over
upkeep, and I moved the DENOMINATOR, because RESOURCE_SPAWN_RATE remains the
only unconditional number in the file and remains untouched. The corollary this
time: a price that is charged per tick but rewarded per tick-saved is not a
price. Before adding another one, multiply it by the thing it is supposed to
discourage and check that the units don't cancel.