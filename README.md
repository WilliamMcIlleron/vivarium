# Vivarium

A working pattern for letting an LLM modify its own codebase without needing to trust
it: every constraint enforced in code, not prompted.

A small artificial-life ecosystem that runs itself and rewrites its own rules over time,
named for the enclosures built to keep and observe living things.

Two separate loops, deliberately kept apart:

- **`simulate`**: pure Python, no LLM call, free, cheap enough to run every few minutes.
  Advances the ecosystem one tick: movement, feeding, reproduction, death.
- **`evolve`**: calls Claude once per run to look at the world's state and goals, then
  write ONE actual code change to the simulation rules (a new species, a new mechanic, a
  tuning change, or a rewrite of its own goals). Costs usage, so it runs rarely (default:
  once a day).

This split exists so the world can "live" continuously for free, while the part that
costs money/quota (the self-modification) stays deliberately infrequent and controlled.

Current model: two species share the grid - **grazers** (eat resources) and **hunters**
(eat grazers). It's a real predator/prey system, not just two populations that happen to
coexist; see `state/goals.md` for the world's current focus.

## Current state (2026-09-04)

Evolve hasn't landed a real committed change on its own yet. Every real attempt so far
has been one of: rejected by a guardrail bug that made success mathematically
impossible (fixed, see below), failed to parse as JSON, or reverted after its tests
failed. The predator/prey split, terrain, genome framework, and reflection runs in the
code today were hand-built to bootstrap the world past its first, very slow evolve runs.
The guardrails below exist so the next real change is evolve's, not a human's.

## Quick start

```bash
pip install -r requirements.txt
python driver.py simulate      # one free tick, no LLM
python driver.py evolve        # one LLM-driven evolution step
```

## Running it unattended (local schedule, Pro plan)

Uses the official Claude Code CLI (`claude -p`) authenticated with your Pro/Max
subscription login: no API key needed, no extra cost beyond your existing plan. Runs
locally on your own machine (see `config.py` for why not GitHub Actions on this backend).

- Linux / macOS / WSL: see `crontab.example`.
- Plain Windows (no WSL): Windows has no `cron` - see `SCHEDULING_WINDOWS.md` for the
  Task Scheduler equivalent.

## Upgrading to the API later

Swapping to pay-per-token billing (for reliability, higher frequency, or to move `evolve`
onto GitHub Actions / a server) is a one-line change:

```bash
export WORLD_BACKEND=api
export ANTHROPIC_API_KEY=sk-...
```

`config.py` is the only file that knows about backends. Nothing else in the codebase
changes. See `.github/workflows/evolve.yml.disabled` for the ready-to-enable Actions
workflow once you're on the API backend.

## Structure

```
driver.py              entry point: simulate | evolve
config.py               backend abstraction (CLI subscription vs API key)
rules/ecosystem.py      the simulation itself (pure Python, no LLM)
state/world.json        current world state (species, resources, tick count)
state/goals.md          what the world is currently trying to become (Claude edits this)
state/changelog.md      append-only log of every evolve run and what it changed
state/budget.json       spend/run tracking, used by the guardrails
PROTECTED.md            paths evolve is not allowed to touch
tests/                  must pass before an evolve change is committed
viewer/index.html       open this to watch the world (reads state/world.json)
PAUSED                  create this empty file to freeze evolve immediately
crontab.example         unattended scheduling on Linux/macOS/WSL
SCHEDULING_WINDOWS.md   unattended scheduling on plain Windows (Task Scheduler)
```

## Guardrails (enforced in code, not just prompted)

1. An allowlist: evolve may only write under `rules/`, `viewer/`, and `state/goals.md` -
   everything else is rejected even before the `PROTECTED.md` check runs.
2. `PROTECTED.md` paths are diffed against every evolve change; touching one fails the run.
3. `state/budget.json` caps runs per day / diff size per run; evolve refuses to start over
   cap. Diff size is measured as actual added/removed lines against the file on disk, not
   the file's full length - a small edit to a big file doesn't cost the whole file.
4. `tests/` must pass or the change is reverted, never committed. `tests/` is itself
   protected, so evolve can't loosen its own tests to force a pass. A proposal that fails
   tests gets one retry with the failure shown to it before it's reverted, the same way a
   normal coding loop gets to see an error and fix it.
5. `PAUSED` file, checked first, halts everything.
6. Every evolve run writes a changelog entry before committing: a human-readable trail.

## Real bugs found and fixed (2026-09-04)

- The diff-size guardrail measured a proposed file's full length instead of the actual
  changed lines, so any proposal touching both `rules/ecosystem.py` and
  `viewer/index.html` (351 lines combined) exceeded the 350-line cap regardless of how
  small the real edit was. Four straight evolve attempts were rejected before this was
  caught. Fixed: diff size is now measured with `difflib` against the file on disk.
- The CLI backend passed the whole prompt as a Windows command-line argument, which
  silently breaks once the codebase grows past Windows' roughly 32,000-character
  command-line limit. Fixed by sending the prompt over stdin instead.

Both failed loudly and left a changelog entry rather than quietly doing nothing, which
is the actual point of building the guardrails this way.
