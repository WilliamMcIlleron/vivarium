# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-13, tick 5522 - the post-mortem on ripening, and the leak I found

First: LAST RUN'S CHANGE LOOKS NEARLY INERT, and I should say so plainly
rather than wait another thousand ticks to admit it.

The prediction was "a long absence banks a feast". The world at tick 5522
holds 12 resources. Twelve. Not sixty. Here is why, and it is arithmetic I
should have done before shipping it:

  GRAZER_MIGRATION_RATE = 0.05  ->  a grazer extinction lasts ~20 ticks on
  average, and the log bears this out exactly: extinct 5464, migrant 5465.
  ONE TICK. Extinct 5505, migrant 5507. Two ticks.
  20 ticks x 0.6 spawn = 12 extra plants, each ~10 energy above baseline.

The ripening mechanism is gated on the length of an absence, and this world's
absences are a coin-flip long because the migration rate makes them so. The
mechanism cannot fire. It is not wrong, it is unreachable. If a future run
wants it to matter the lever is GRAZER_MIGRATION_RATE (longer, rarer
absences) or RESOURCE_RIPEN_TICKS (faster ripening), NOT a bigger
RESOURCE_MAX_ENERGY. Do not touch either in the same run as something else.

Second, and the actual change this run: predation was minting energy. A
hunter got a flat 40 for a grazer regardless of what that grazer was
carrying, so a starveling and a fat animal were the same meal. Consequences I
can now see written all over the history:

  - tick 1728: 2 grazers, 6 HUNTERS. A predator population three times its
    prey population is thermodynamically impossible unless the kill is a
    source rather than a transfer. It was a source.
  - hunters were coupled to prey HEAD COUNT and to nothing else about the
    prey. Every mechanic I have added on the grazer side for two thousand
    ticks - ripening plants, the breeding bar, provisioning - moves grazer
    CONDITION, and not one point of it reached the hunters.

Now: kill = int(0.7 * (12 + prey.energy)), capped at 70. 8 for a starveling,
~39 at the condition grazers here are typically caught in (so roughly neutral
on the mean, deliberately), 70 for an animal that has been feeding.

What I expect, in priority order, and what to do if I am wrong:

- "prey on the hoof" in the stats line is the new number. Read it against
  "larder". If larder rises and hoof follows it a few dozen ticks later, the
  food chain is one budget and this worked.
- Hunters should stop outnumbering grazers. If the history still shows
  hunters > grazers a thousand ticks from now, the leak is elsewhere and I
  should look at CARRION_ENERGY (still a flat 30, still the one payout in
  this world not tied to anything - I left it alone ON PURPOSE because it is
  the lifeline that ended the chronic hunter extinctions, but it IS the next
  flat number in line).
- The prediction I am least sure of: hunter speed should now be
  self-limiting. A fast hunter's menace radius keeps grazers off their food,
  which makes its own prey worth 8 instead of 50. Watch avg_speed in the
  hunter genome snapshot. If it keeps climbing, that feedback is too weak to
  see at this population size and I should stop claiming it.
- If hunters go extinct MORE and stay extinct: the efficiency factor is the
  knob (0.7 -> 0.85), nothing else. Do not raise HUNT_FLESH; the flesh floor
  is what makes a starveling worthless, and that is the mechanism.

The standing lesson from the last two runs, now twice confirmed: CHECK WHERE
THE ENERGY COMES FROM AND WHERE IT LEAKS BEFORE ADDING A MECHANIC. Income was
18/tick and nothing I built downstream could raise the ceiling; predation was
minting energy and nothing I built on the prey side could reach the predator.
Both were one multiplication I could have done in thirty seconds.

Still queued, in the order I would take them:

- Per-species TRAIT_REGISTRY, its own run, nothing else in the diff. The
  snapshot at 5522 is the argument now made concrete: grazers carry acuity
  2.5 - a gene ONLY hunters read and ONLY hunters pay for - while carrying
  camouflage 0.0, the gene that is actually theirs. Hunters carry acuity 0.0.
  Inert genes are drifting to the top of the wrong species and filling
  lineage memory with noise. provisioning is the shared counter-example that
  has to keep working afterwards.
- Extinction length (see the ripening post-mortem above). Probably the single
  highest-leverage number left in the file.
- The day/night cycle is still purely cosmetic and still the biggest unused
  surface. A temporal refuge would be this world's first mechanic about WHEN
  rather than WHERE. Not until a population exists to experience it.
- Performance guard, unchanged: `_update_herd_cover` and the viewer's
  herd-bond loop are both O(n^2). Fine at 40, watch at 200.