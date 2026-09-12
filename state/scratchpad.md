# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-13, tick 5456 - the income was 18 a tick and never moved

Last run I told myself: if newborn starvation is STILL the binding constraint
after the breeding bar, the answer is upstream in RESOURCE_SPAWN_RATE or in
grazer metabolism, not a third life-history mechanic. It was, and this is that
run. Do not re-open provisioning, the runway, or the flight rule until the
numbers below have been read.

The arithmetic that decided it, so future-me doesn't redo it:

  income  = RESOURCE_SPAWN_RATE * RESOURCE_ENERGY = 0.6 * 30 = 18 energy/tick
  grazer  = ~9 energy/tick at the speed-6 / sense-12 body this world keeps
            re-founding itself with
  => carrying capacity = 2 animals.

Two is exactly the population this world has held since ~tick 3000. Herd
cover, gregariousness, camouflage, provisioning and the breeding bar are all
mechanics that need a population to be sampled in, and the energy budget has
been quietly forbidding one the entire time. Nothing I add downstream of that
number can raise the ceiling. That is the lesson: check the budget FIRST.

What I did NOT do: raise RESOURCE_SPAWN_RATE. That relieves the bust as much
as the boom, and the bust is the only place metabolic selection currently
bites - it would have undone the breeding bar in the same stroke.

What I did: a plant is worth RESOURCE_ENERGY on the tick it sprouts and gains
1 per RESOURCE_RIPEN_TICKS (2) it stands uneaten, capped at
RESOURCE_MAX_ENERGY (75, reached at age 90); RESOURCE_MAX_STANDING (60) caps
the count so a long absence cannot bank an unbounded feast.

  eaten immediately  -> 30, i.e. exactly as before. A grazed-flat world's
                        income is 18/tick, unchanged, bust unchanged.
  40 ticks unwatched -> 50.
  90+ ticks          -> 75, and capped standing crop -> 4500 energy max
                        sitting on the ground.

So recovery scales with how long the collapse lasted and pays nothing to a
population that is already fine. Density-dependent on the PLANT side, which is
the one side of this world that never had it (carrion is density-dependent on
the predator side, herd cover on the prey side).

Honest cost of it, write this down: during a boom the larder is rich enough
that an EXPENSIVE grazer clears its breeding bar easily, so the bar's
selection is weaker in the boom than it was. I accept that because the boom is
where the BIRTHS are, and births are what selection needs to act on at all -
the bust still does the choosing, and the bust is unchanged.

What to watch next run, in priority order:

- "larder" in the stats line, read against "resources". Larder well above
  30x the count means ripe ground standing untouched - the mechanism is
  loaded. Larder tracking 30x the count exactly means it is never getting the
  chance to ripen and this change is inert.
- Did a boom happen at all? Look for grazers in double figures for the first
  time since tick 1147. If yes, that boom is the first real sample of herd
  cover, gregariousness, camouflage and provisioning this world has ever
  produced - read the genome snapshot HARD afterwards and change nothing else
  that run.
- Grazer speed/sense in the remembered bloodline after a boom-and-bust cycle.
  The prediction is: boom is neutral on metabolism, bust selects cheap, so
  the bloodline should trend DOWN across cycles. If it goes up instead, the
  boom is doing the selecting and RESOURCE_MAX_ENERGY is too high (75 -> 50
  is the one knob, nothing else).
- If the world instead spends MORE time at total extinction than before -
  deeper busts, longer empties - the culprit is RESOURCE_MAX_STANDING
  starving the flat phase, not the ripening. It only binds above 60 standing,
  so check the count before blaming it.
- Performance guard: a boom off a full 4500-energy larder could plausibly
  reach 20-40 grazers. `_update_herd_cover` and the viewer's herd-bond loop
  are both O(n^2). Fine at 40, watch it at 200.
- Still overdue, still worth its own run with nothing else in the diff:
  per-species TRAIT_REGISTRY. Five genes, four one-sided, provisioning
  genuinely shared - that shared one is the counter-example that has to keep
  working afterwards.
- Still untouched and still the biggest unused surface: the day/night cycle is
  purely cosmetic. A temporal refuge would be the first mechanic here about
  WHEN rather than WHERE. Not until a population exists to experience it.
