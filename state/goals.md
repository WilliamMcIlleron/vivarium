# Goals

This file is read by every `evolve` run and can be rewritten by the world itself.
Treat it as the world's current sense of what it's trying to become — not a fixed
spec. Whoever (whatever) edits this should explain WHY in the same commit's
changelog entry.

## Current focus

- **Genome framework** (2026-09-04): `rules/ecosystem.py` has `TRAIT_REGISTRY`
  (name -> (default, mutation_step, min, max)) and `Creature.traits` - a
  generic, extensible genome. `speed` and `sense_range` stay first-class
  fields since movement code reads them directly everywhere, but any NEW
  mutating trait only needs one entry in `TRAIT_REGISTRY` plus behavior code
  that reads `creature.trait("name")` - inheritance and mutation happen
  automatically, no need to touch `_reproduce`/`_spawn_creature` by hand.
  `TRAIT_REGISTRY` is deliberately empty - this is the framework, not the
  content. The first real trait you add here (tied to real behavior, not
  just existing for its own sake) is a legitimate "one meaningful change."
- **You now see more than population counts**: the prompt includes a genome
  snapshot (per-species trait averages), recent notable events (extinctions,
  migrations), and recent population history. Use them - if grazers have
  been trending toward zero for several runs, that's a more urgent signal
  than anything else in this file.
- **Reflection runs**: roughly once a week, instead of a code change, you'll
  be asked to write a short chronicle entry into `state/lore.md` instead -
  a first-person field-journal reflection on what this world has actually
  become, distinct from the engineering `changelog.md`. Shown in the viewer
  as "latest chronicle." Write it like you're actually looking at this
  specific world's specific state, not a generic template.
- The world now has a terrain layer (water/sand/grass/forest, generated once at
  world creation, rendered in `viewer/index.html`) plus a day/night cycle and
  drifting fog for atmosphere. This is fixed "engine" scaffolding, not content -
  it's currently purely cosmetic (creatures ignore it completely). Don't
  regenerate or redesign the terrain itself; DO feel free to make creature
  behavior actually respond to it (see "terrain-aware behavior" below) - that's
  content, and content is what evolve is for.
- The ecosystem now has two species (`rules/ecosystem.py`): grazers (eat resources)
  and hunters (eat grazers, flee-and-chase movement, faster but harder to reproduce).
  Grazers detect hunters using the same `sense_range` gene they use to find food -
  spotting predators and finding food are the same stat, which is the interesting
  tension to build on. Look for the most interesting single next step, not a
  laundry list.
- Prefer changes that create *emergent* behavior (a new pressure the population has
  to adapt to) over changes that just add content for its own sake.
- Known balance risk, worth watching and worth fixing if you see it happening: in
  hand-testing (2026-09-04), roughly a quarter of long runs ended with grazers
  fully extinct and only an occasional migrant hunter left. A fix that reduces this
  without re-introducing hunter-driven total extinction is a legitimate "tuning
  change" - don't feel obligated to solve it in one run, but don't ignore it either
  if `state/world.json` shows grazers trending toward zero.
- Good candidate directions, roughly in order of interesting-to-least:
  - Terrain-aware behavior: `World.terrain` (a 40-row grid of "w"/"s"/"g"/"f"
    characters, same coordinates as creatures/resources) exists but nothing
    reads it yet. Real options: water blocks movement, resources only spawn on
    grass/forest, hunters or grazers move slower on sand, forest tiles reduce a
    hunter's effective sense_range (cover for grazers to hide in). Pick one, not
    all of them.
  - A second resource type with different nutritional value, forcing tradeoffs
    (e.g. a rare high-energy resource hunters could also eat as a fallback, taking
    some pressure off grazers when hunting is going too well).
  - Grazer herd behavior: grazers that cluster tend to spot hunters sooner (more
    eyes) at the cost of competing with each other for the same resources.
  - Seasons or cycles that change resource spawn rate over time (could also tie
    to the day/night cycle already in the viewer, e.g. resources spawn faster
    in daylight).
  - A cost/benefit tradeoff gene beyond speed/sense_range (e.g. size vs. energy
    efficiency).
  - Environmental hazards (regions of the grid that drain energy faster).
  - Lineage tracking: give Creature a `parent_id`, so a family tree exists even
    if nothing reads it yet. Once it does, worth surfacing which lineage is
    currently dominant, or how many generations deep the oldest living line
    goes - that's a much more interesting fact about the world than "12
    grazers" is on its own.
  - A "notable creature" callout in the viewer stats bar: the oldest living
    creature, or the one with the most descendants (needs lineage tracking
    above first). Turns the population count into an actual story about a
    specific creature, not just a number that goes up and down.
- Longer-term, speculative idea, only worth picking up once the above feels
  exhausted: connect resource spawn rate to a real weather API for a real city,
  so the world has an actual tether to reality instead of pure randomness. Only
  do this if you can articulate what interesting behavior it would cause — don't
  add it just because it's in this file.

## Constraints (always true, not up for revision by evolve)

- One meaningful change per run. Resist the urge to do several things at once.
- Every change must keep `tests/` passing.
- Respect `PROTECTED.md`.
- If you rewrite this file, keep this "Constraints" section unchanged.
- **Visual parity rule:** if a change introduces something a viewer could show
  (a new species, a visible environmental effect, a new creature attribute
  worth seeing), `viewer/index.html` must be updated in the same run to
  represent it distinctly — a new color, shape, or size mapping, not just a
  reused dot. A change that adds something invisible to the viewer is
  incomplete. Changes that are purely internal (tuning a constant, refactoring)
  don't require a viewer update — use judgment, but default to updating it.
