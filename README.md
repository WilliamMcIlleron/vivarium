# Self-Evolving World

A small artificial-life ecosystem that runs itself and rewrites its own rules over time.

Two separate loops, deliberately kept apart:

- **`simulate`** — pure Python, no LLM call, free, cheap enough to run every few minutes.
  Advances the ecosystem one tick: movement, feeding, reproduction, death.
- **`evolve`** — calls Claude once per run to look at the world's state and goals, then
  write ONE actual code change to the simulation rules (a new species, a new mechanic, a
  tuning change, or a rewrite of its own goals). Costs usage, so it runs rarely (default:
  once a day).

This split exists so the world can "live" continuously for free, while the part that
costs money/quota (the self-modification) stays deliberately infrequent and controlled.

## Quick start

```bash
pip install -r requirements.txt
python driver.py simulate      # one free tick, no LLM
python driver.py evolve        # one LLM-driven evolution step
```

## Running it unattended (local cron, Pro plan)

See `crontab.example`. This uses the official Claude Code CLI (`claude -p`) authenticated
with your Pro/Max subscription login — no API key needed, no extra cost beyond your
existing plan. Runs locally on your own machine (see `config.py` for why not GitHub
Actions on this backend).

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
```

## Guardrails (enforced in code, not just prompted)

1. `PROTECTED.md` paths are diffed against every evolve change; touching one fails the run.
2. `state/budget.json` caps runs per day / tokens per run; evolve refuses to start over cap.
3. `tests/` must pass or the change is reverted, never committed.
4. Diff size cap per evolve run (default 3 files / 150 lines) — forces incremental change.
5. `PAUSED` file, checked first, halts everything.
6. Every evolve run writes a changelog entry before committing — human-readable trail.
