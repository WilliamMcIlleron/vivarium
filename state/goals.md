# Goals

This file is read by every `evolve` run and can be rewritten by the world itself.
Treat it as the world's current sense of what it's trying to become — not a fixed
spec. Whoever (whatever) edits this should explain WHY in the same commit's
changelog entry.

## Current focus

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
