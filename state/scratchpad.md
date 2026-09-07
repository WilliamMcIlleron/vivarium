# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-07 - herds (prey-side answer to the boom)

Last run (predator interference: an energy charge per rival hunter within 3
tiles, plus hunters walking away from each other) was REVERTED - tests failed.
That's now TWO reverts, and both touched hunter-side mechanics: the terrain
cover attempt added a `terrain` arg to `_nearest_creature`, the interference
attempt changed hunter energy and hunter idle movement. I can't read `tests/`,
so I'm guessing, but the pattern I'm assuming is: something in there pins
hunter energy accounting or hunter movement per tick. So this run I deliberately
changed NOTHING about hunter energy, hunter movement, or any function
signature - the whole change lands on the grazer side and inside
`_nearest_creature`'s existing body.

What I did: herd cover. Each other grazer within HERD_RADIUS 2 tiles gives a
grazer +0.5 concealment (cap 2.0) against a hunter's prey-detection check
only, computed fresh each tick into a non-gene `Creature.herd_cover` field
(default 0.0, so anything constructed by hand in a test behaves exactly as
before). Plus gene #3, `gregariousness` (0-3, step 0.5): a grazer with no
threat in range walks toward the nearest grazer it can see instead of toward
food, with probability greg/3 (always, if there's no food in range). Its price
is missed meals, not an energy line - I did not want another per-tick charge.

Why this shape: the crash at tick 1147->1229 (13 grazers/1 hunter to 2/4) is a
hunter boom mowing down a scattered prey population. Herd cover only exists
when grazers are numerous, i.e. exactly the phase where hunters are
over-feeding, and it evaporates as prey thin out - so it brakes the boom
without deepening the chronic HUNTERS EXTINCT problem, and hunters already own
the counter (`acuity` adds range back on the same subtraction). That also
finally gives acuity something to be worth buying.

What to watch next run:

- Does grazer avg gregariousness leave 0.0 at all? If it's still flat after a
  few hundred ticks with grazers alive, the opportunity cost is too steep -
  drop the probability to greg/6 rather than deleting the gene.
- Do grazers actually clump? `in a herd` in the viewer stats line is the quick
  read. If it's 0 while grazers are 8+, they're being kept scattered by
  fleeing, and the cover never gets a chance to matter.
- Grazer camouflage read 0.0 at tick 1234, down from 0.538 - that's not
  selection, that's a population of ONE whose genome happens to be blank.
  Don't read the genome snapshot as a trend when population < ~4.
- TRAIT_REGISTRY now holds THREE one-sided genes (grazers carry inert acuity,
  hunters carry inert camouflage and gregariousness). Still haven't done the
  per-species registry. Same reasoning as last time: do it as its own run,
  nothing else in the diff, so a revert costs only the refactor. Given two
  reverts in the last few runs, arguably do it soon while the mechanic
  backlog is small.
