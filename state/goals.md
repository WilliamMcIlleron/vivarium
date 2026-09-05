# Goals

This file is read by every `evolve` run and can be rewritten by the world itself.
Treat it as the world's current sense of what it's trying to become — not a fixed
spec. Whoever (whatever) edits this should explain WHY in the same commit's
changelog entry.

**Standing rule:** an edit to this file should be pruning (removing something
stale, contradictory, or that's a backlog dressed as documentation), not adding
a new aspiration or direction. If you're not sure which one an edit is, it's
probably the one not to make.

## Current focus

- **Genome framework** (2026-09-04): `rules/ecosystem.py` has `TRAIT_REGISTRY`
  (name -> (default, mutation_step, min, max)) and `Creature.traits` - a
  generic, extensible genome. `speed` and `sense_range` stay first-class
  fields since movement code reads them directly everywhere, but any NEW
  mutating trait only needs one entry in `TRAIT_REGISTRY` plus behavior code
  that reads `creature.trait("name")` - inheritance and mutation happen
  automatically. First trait added (tick 298): `camouflage`, a grazer-relevant
  gene (0-3, mutation step 0.5) that shrinks a hunter's effective sense_range
  specifically when that hunter is hunting that grazer (`_nearest_creature`'s
  new `camouflage_aware` flag). Because the registry isn't species-scoped,
  hunters silently inherit the gene too - it's inert for them since nothing on
  the hunter side reads it. Worth a real per-species registry if a second
  trait that should be one-sided like this shows up; not worth building for
  just one.
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
  regenerate or redesign the terrain itself.
- The ecosystem now has two species (`rules/ecosystem.py`): grazers (eat resources)
  and hunters (eat grazers, flee-and-chase movement, faster but harder to reproduce).
  Grazers detect hunters using the same `sense_range` gene they use to find food -
  spotting predators and finding food are the same stat. Look for the most
  interesting single next step, not a laundry list.
- Prefer changes that create *emergent* behavior (a new pressure the population has
  to adapt to) over changes that just add content for its own sake.
- Known balance risk, worth watching and worth fixing if you see it happening: in
  hand-testing (2026-09-04), roughly a quarter of long runs ended with grazers
  fully extinct and only an occasional migrant hunter left. A fix that reduces this
  without re-introducing hunter-driven total extinction is a legitimate "tuning
  change" - don't feel obligated to solve it in one run, but don't ignore it either
  if `state/world.json` shows grazers trending toward zero.

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
