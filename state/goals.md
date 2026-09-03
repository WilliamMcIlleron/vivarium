# Goals

This file is read by every `evolve` run and can be rewritten by the world itself.
Treat it as the world's current sense of what it's trying to become — not a fixed
spec. Whoever (whatever) edits this should explain WHY in the same commit's
changelog entry.

## Current focus

- The ecosystem is brand new (`rules/ecosystem.py`): one species, one resource type,
  a fixed grid. It works, but it's simple. Look for the most interesting single
  next step, not a laundry list.
- Prefer changes that create *emergent* behavior (a new pressure the population has
  to adapt to) over changes that just add content for its own sake.
- Good candidate directions, roughly in order of interesting-to-least:
  - A second resource type with different nutritional value, forcing tradeoffs.
  - A predator/prey split (a second creature species that eats the first).
  - Seasons or cycles that change resource spawn rate over time.
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
