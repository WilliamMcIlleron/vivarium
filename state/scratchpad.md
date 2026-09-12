# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-12 (second run today) - every price in this world was a per-tick price

Flight-in-ticks shipped at 4147 and grazers were extinct again by 4190. That
is 43 ticks of data and it proves nothing either way - do NOT conclude the
flight change failed, and do NOT touch FLIGHT_WARNING_TICKS until there has
been a stretch with >3 grazers and hunters alive at the same time to read
"holding nerve" from. It is still the right first knob if that reading comes
back zero.

What I actually did this run, and why it is upstream of all of that:

Every price this world has ever put on a gene - MOVE_COST, ACUITY_COST,
FREE_SENSE_RANGE - is charged PER TICK. A per-tick price only selects through
attrition, and attrition needs a population big enough that the merely
inefficient outnumber the unlucky. This world holds two animals. At N=2,
attrition is indistinguishable from noise, which is exactly why grazers have
been ratcheting to speed 6 / sense 12 for a thousand ticks while a per-tick
bill of 9 energy sat right there doing nothing about it. I have been writing
"unpriced genes only ratchet" in four separate comment blocks and missing that
the priced ones were ratcheting too, because the price was charged in the one
currency a tiny population cannot pay attention to.

So: `_birth_weight` / `_breeding_bar`. A newborn is launched with
BIRTH_RUNWAY_TICKS (4) ticks of the body it inherits, floored at the old flat
`cost // 2`, and the parent must reach threshold + (runway - flat) before it
may breed. Also factored the whole per-tick charge into `_upkeep` so the cost
of running a body and the cost of starting one can't drift apart.

The arithmetic, so future-me doesn't have to redo it:

  grazer speed 1, sense 5: upkeep 1 -> runway 4 -> floored to 20 -> bar 60.
    IDENTICAL to before. Nothing cheap changed at all.
  grazer speed 6, sense 12: upkeep 9 -> runway 36 -> bar 76.
  hunter speed 2, sense 5: upkeep 2 -> runway 8 -> floored to 27 -> bar 110.
    Also identical. cost//2 = 27 is a high floor, so hunters are barely
    touched until they get expensive. That is deliberate, not an oversight.

Invariant worth keeping: a parent that breeds at exactly its own bar is left
holding `threshold - cost` no matter what the bar is. The bar moves; the
aftermath does not. Don't break that if you tune this.

Why this should be density-dependent rather than a flat nerf: after a crash,
resources pile up uneaten, and even an expensive migrant clears 76 by eating
two or three of them - so the remembered bloodline still gets to breed and the
world doesn't lock. As the population recovers and the larder thins, the bar
is what decides who KEEPS breeding, and that is the cheap animal every time.
Boom on stored food, then selection for cheap bodies. That cycle is the thing
to look for.

What to watch next run, in priority order:

- The remembered grazer bloodline's SPEED and SENSE. This is the only number
  that matters. If it is still ~6 / ~12 after several hundred ticks with
  births happening, the bar is not biting and BIRTH_RUNWAY_TICKS 4 -> 6 is
  the one knob, nothing else. If it starts coming down, leave everything
  alone and let it run - that descent is worth more than any new mechanic.
- "breeding bar" and "birth weight" in the stats line. Bar at 60/110 means a
  cheap population; bar well above means the metabolism is the obstacle.
- Grazer population ceiling. Cheap grazers (upkeep 1-2) on 18 energy/tick of
  inflow could support 9-18 animals instead of under 2. If grazers finally
  climb into double figures, herd cover, gregariousness and camouflage all
  get a population to be selected in for the first time since tick 1147 -
  that is the payoff, and it is downstream of this, not of a new gene.
- DANGER SIGN, take seriously: no births at all for 300+ ticks with grazers
  alive. That means the bar is unreachable and the lineage is locked at an
  expensive genome it can never breed out of. The fix would be to floor the
  bar (cap the surcharge at ~12) rather than to revert. Check births in the
  event log before assuming it.
- provisioning is STILL 0.0 in both species and that is still not a reason to
  touch PROVISION_ENERGY. It now has a clear division of labour with the
  runway: the runway is the floor every parent must save for, provisioning is
  what a parent adds on top. It cannot be sampled without births.
- Do NOT re-diagnose the newborn-starvation problem again. It has now been
  attacked twice (provisioning at 3240, birth weight here). If it is still the
  binding constraint after this, the answer is upstream in RESOURCE_SPAWN_RATE
  or in grazer metabolism, not in a third life-history mechanic.
- Still overdue and still worth its own run with nothing else in the diff:
  per-species TRAIT_REGISTRY. Five genes, four one-sided, one (provisioning)
  genuinely shared - that shared one is the counter-example that has to keep
  working afterwards.
- Still untouched and still the biggest unused surface in the world: the
  day/night cycle is purely cosmetic. A temporal refuge would be the first
  mechanic here that is about WHEN rather than WHERE. Not now.
