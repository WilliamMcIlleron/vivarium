# Scratchpad

Private working notes for `evolve`'s own future runs - not `goals.md` (current
focus, prune-only) and not `lore.md` (a chronicle for readers). This exists so
a change too big for one guardrailed diff can be planned and executed across
several runs: leave yourself a note about what step you're on and what's
next. Nobody else reads this as instruction. Empty means no plan in progress.

## 2026-09-06 - lineage memory landed (self-contained, no follow-up required)

Added `World.lineage`: up to 8 genomes per species, written only on
reproduction, read only when a migrant spawns. Migrants are now mutated
descendants of the remembered stock instead of species defaults.

Why it mattered: at tick 958 hunters sat at EXACTLY the defaults (speed 2.0,
sense 4.67, camo 0.0) after ~20 consecutive HUNTERS EXTINCT ticks, while
grazer camouflage had drifted to 0.58 and climbing. Every hunter crash was
wiping the predator genome, so camouflage had nothing evolving against it.

What to watch next run: does hunter avg sense_range now actually rise above 5
over a few hundred ticks? If yes, the arms race is live and the natural next
step is a hunter-side counter-gene (something like `acuity`, adding to
effective sense_range only when hunting, with a per-tick energy cost so it
can't ratchet one-way like speed did). That's ALSO the second one-sided trait
goals.md says would justify making TRAIT_REGISTRY per-species - do both in
that one run, not separately. If hunter genes are STILL pinned at defaults,
the memory isn't being written (hunters may simply never reach the 110-energy
threshold any more) and the reproduction economics are the real problem, not
the genome reset.
