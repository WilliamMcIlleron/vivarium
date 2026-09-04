# Changelog

Append-only. Every `evolve` run adds one entry here before committing, whether
it succeeded, failed tests, or was reverted. This is the human-readable trail
of everything the world has decided about itself.

## Genesis

World created. Single species, single resource type, 40x40 grid, mutation on
speed and sense_range. See `state/goals.md` for what happens next.

## 2026-09-03T20:16:59

evolve run REJECTED: 229 lines changed, max is 150

## 2026-09-03T20:18:36

evolve run REJECTED: 224 lines changed, max is 150

## 2026-09-03T20:39:52

evolve run REJECTED: 409 lines changed, max is 350

## 2026-09-04T10:12:06

evolve run REJECTED: 449 lines changed, max is 350

## 2026-09-04 (manual dev session, not an evolve run)

All 4 evolve attempts above had been rejected by a guardrail bug: the diff-size
check counted each proposed file's full length instead of the actual changed
lines, so any proposal touching both `rules/ecosystem.py` and `viewer/index.html`
(351 lines combined) exceeded the 350-line cap regardless of how small the real
edit was - evolve could never succeed. Fixed `_validate_proposal` in `driver.py`
to diff against the file on disk. Also replaced the protected-path denylist with
an allowlist (evolve may only write `rules/`, `viewer/`, `state/goals.md`) and
added `tests/`, `state/world.json`, `state/changelog.md` to `PROTECTED.md` so
evolve can no longer legally rewrite its own tests or history to force a pass.

Separately, hand-built a predator/prey split since the world was still one
species and the daily evolve budget makes organic growth very slow: grazers
(unchanged food-seeking, now flee any hunter within sense_range) and hunters
(faster, seek out grazers, eat them on contact, costlier to reproduce so one
lucky kill doesn't spiral into a hunter population that outstrips its own food
supply). Also fixed `RESOURCE_SPAWN_RATE` (0.08 -> 0.6): at the old rate the
original single-species world was already headed for starvation-driven
extinction within a few hundred ticks, independent of anything predator-related.
`viewer/index.html` now renders hunters as a distinct red/orange triangle
against the grazer's green circle, per the visual parity rule. See
`state/goals.md` for the known remaining balance risk (grazers going fully
extinct in a minority of long runs) and what's next.
