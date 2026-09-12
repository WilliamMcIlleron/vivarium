# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-12 - flight was measured in the wrong unit

Provisioning verdict, ~900 ticks in: avg_provisioning is still 0.0 in BOTH
species. Per my own note last run, that means the gene isn't being sampled
because almost nothing is breeding, and the problem is upstream of life
history. It is. Do not touch PROVISION_ENERGY; the gene is fine, it just has
no population to be expressed in. Same for `nerve`, which has now gone six
runs without ever being selected in.

The upstream problem, finally pinned down at tick 4147:

  grazer: speed 7 (7/tick) + sense_range 12 (3/tick vision) = 10 energy/tick
  hunters: speed 2, i.e. they physically cannot catch a speed-7 grazer
  old panic radius: sense_range - nerve = 11.5 tiles
  P(a 23x23 box on a 40x40 grid contains one of 3 hunters) = ~70%

So seven ticks in ten the grazer was running at 7 energy a tick from things
that could never have caught it, on a map with 18 uneaten resources. The
animals were not being eaten and they were not short of food; they were
sprinting themselves to death out of a rule that said "anything you can see is
a thing you run from". Total resource inflow is 0.6*30 = 18 energy/tick, which
at 10/tick per grazer supports under two of them - the population sitting at 2
for a thousand ticks is not a coincidence, it is that number.

Fix shipped this run: flight is now measured in TICKS OF WARNING, not tiles.
`_warning_ticks` (FLIGHT_WARNING_TICKS 3.0, minus nerve, min 0.5) times the
threat's own speed = `_panic_radius(grazer, threat)`. New `_flight_threat`
picks the most urgent visible hunter rather than the nearest, since those can
now differ. `_flees` kept, same name, now takes the pair.

Why this and not a metabolic tweak: it fixes the STRUCTURAL complaint I wrote
down twice and called unfixable - nerve caps at 3.0 while sense_range caps at
nothing, so the brake could never catch the thing it was braking. A warning
measured in ticks is bounded by the tick, so a 0-3 gene now spans the whole
decision. It also decouples perception from panic, which means sense_range can
finally be selected on what it's for (finding food) with only vision upkeep
pricing it.

Revert-safety: no Creature field, no save format change, no new gene, no
TRAIT_REGISTRY entry. `tests/test_ecosystem.py` touches none of
`_panic_radius` / `_flees` / `_flight_threat` (checked, all 16 tests).

What to watch next run, in priority order:

- "holding nerve" in the viewer stats. Under the old rule it was structurally
  pinned near zero. If it is still zero with hunters alive, the new radius is
  still too wide and FLIGHT_WARNING_TICKS 3.0 -> 2.0 is the single knob to
  turn, nothing else.
- Grazer population. Expected: grazers stop starving-while-fleeing and climb
  past 5 for the first time since tick 1147. If they climb past ~12 and THEN
  crash, that's the old hunter-boom crash and herd cover / gregariousness
  finally have a population to work in - let it run, don't pre-empt it.
- Predation should come back. Grazers that ignore a slow hunter will sometimes
  be walked onto. That is the point and it is not a bug; only worry if grazers
  crash to 0 WITH hunters fat, which would mean the radius is now too small.
- Second-order effect worth watching: fewer grazers starving = fewer carcasses
  = hunters lose the scavenging crutch they have been living on since 1889.
  Hunters may thin out before they adapt. Do not rescue them with carrion;
  the adaptation available to them is SPEED, which now buys both the chase and
  the fear radius ("menace" ring in the viewer), and lineage memory means they
  can keep it across a crash. Give it several hundred ticks.
- If hunter avg_speed starts climbing, this worked exactly as designed and the
  arms race is speed-vs-nerve for the first time. If hunters instead go
  extinct for 500+ ticks with grazers stable, forest cover 1.5 -> 1.0 is still
  the first lever, as before. Do NOT reopen cannibalism.
- Vision upkeep: grazer avg sense went 11 -> 12 again, still UP, still only 2
  animals. FREE_SENSE_RANGE stays untouched until there are >6 grazers to read
  a trend from - and note the pressure has changed shape now, since a big
  sense_range is no longer self-punishing via panic. Vision upkeep is the ONLY
  price on it now. Re-read this deliberately at the next snapshot.
- Still overdue and still worth its own run with nothing else in the diff:
  per-species TRAIT_REGISTRY. Five genes, four one-sided, one (provisioning)
  genuinely shared - that shared one is the counter-example that has to keep
  working afterwards.
