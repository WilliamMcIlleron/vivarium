# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-07 (later) - nerve (fleeing is now a decision)

Read the tick-1728 snapshot carefully before touching anything, and it says
something different from what I assumed last run. Grazers: speed 5.0, sense
7.0. Hunters: speed 1.0, and there are SIX of them against 2 grazers. A
speed-1 hunter cannot catch a speed-5 grazer, ever. So the hunters are not
predators any more - they are a carrion economy living off grazers that
starve. And the grazers starve because flight was a reflex: any hunter inside
a 15x15 sense box and they bolt, six hunters means that box is nearly always
occupied, so they run permanently at 5 energy/tick and never stand on a
resource. GRAZERS EXTINCT over and over from STARVATION, not predation. The
herd cover I added last run never got a chance to matter for the same reason -
fleeing grazers can't clump.

So: gene #4, `nerve` (0-3, step 0.5). It subtracts from the distance at which
a grazer panics (`_panic_radius`), not from what it perceives - the grazer
sees the hunter fine and keeps eating. Hunger (energy < 25) multiplies nerve
by 1.5, so desperation shows up in exactly the animals about to die anyway.
Floor of 1 tile, so nerve is patience, not suicide.

Safety note for the revert streak (two so far, both hunter-side): this diff
touches NO hunter code, no energy accounting, and no existing function
signature. Critically, at nerve 0 the panic radius is EXACTLY sense_range at
any energy level, so a default-genome creature behaves bit-for-bit as before -
there is no case where an old test's expectation changes. I made the hunger
effect a multiplier on nerve rather than a flat subtraction specifically to
get that property.

What to watch next run:

- Does grazer avg nerve climb off 0.0? It should, fast, while hunters are at
  speed 1 - there is almost no downside right now. If it climbs and grazers
  stop going extinct, the next thing to watch is whether HUNTER speed climbs
  in response (lingering grazers are finally catchable) - that would be the
  first real two-sided arms race this world has run.
- `holding nerve` in the viewer stats line is the direct read: grazers that
  can see a hunter and are eating anyway.
- If nerve saturates at 3.0 and grazers then get farmed, the counter is
  hunter-side and already obvious: speed. Don't add a gene for it.
- Gregariousness/camouflage still read 0.0, but grazer population has been
  1-2 for hundreds of ticks - that's a blank lone genome, not selection.
  Don't read the snapshot as a trend below ~4 individuals.
- TRAIT_REGISTRY now holds FOUR one-sided genes (grazers carry inert acuity;
  hunters carry inert camouflage, gregariousness, nerve). The per-species
  registry refactor is overdue. Do it as its own run, nothing else in the
  diff, so a revert costs only the refactor.
