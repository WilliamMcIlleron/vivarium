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

## Updates

Dated snapshots of what evolve has actually done, kept here rather than folded into the
description above since a "current state" line goes stale the moment the next run lands.
Full detail on every change lives in `state/changelog.md`; this is the summary.

**2026-09-13** — 34 evolve runs landed since the first one. The predator/prey system has
grown a real ecology on top of the hand-built foundation: herd cover and a
`gregariousness` gene for grazers, a functional response capping how much ground fear can
make an animal give up, seed dispersal so plants a population leaves alone reproduce
faster than ones eaten flat, genetic memory across extinctions (a re-migrating species
now inherits a mutated version of its last remembered genome instead of resetting to
default), and several rounds of fixing extinction spirals evolve found in its own world
(a cannibal loop where hunters were living off each other's carcasses; a
density-independent predation boom that could wipe out grazers faster than they bred).
Every mechanic above was evolve's own diagnosis and fix, not hand-built. As of tick 6685
the grid holds 0 grazers and 0 hunters — a real extinction, not a bug. Both migration
rates are small (5%/tick for grazers, 2% for hunters), so an empty grid can sit for a
while between re-migrations before the arms race picks back up.

**2026-09-05** — Evolve landed its first real self-committed change at 03:03: a
`camouflage` gene for grazers that shrinks a hunting hunter's effective sense range,
succeeding on the first attempt under the raised caps below. Before that, every real
attempt had been rejected by the guardrail bug described below (fixed), failed to parse
as JSON, or reverted after its tests failed. The predator/prey split, terrain, genome
framework, and reflection runs in the code were hand-built to bootstrap the world past
those early, failing runs; camouflage was the first trait evolve itself added to the
empty `TRAIT_REGISTRY`.

## Quick start

`simulate` needs nothing but Python. `evolve` needs Claude configured once, since it's
the step that actually calls the model - see below before running it.

```bash
git clone https://github.com/WilliamMcIlleron/vivarium.git
cd vivarium
pip install -r requirements.txt

python driver.py simulate      # one free tick, no LLM - works immediately
python driver.py evolve        # one LLM-driven evolution step - needs setup below first
```

Open `viewer/index.html` in a browser any time to watch the current world; it just reads
`state/world.json`, no server needed.

## Connecting `evolve` to Claude

This project doesn't ship an API key or any credentials - you connect your own, and it
defaults to the free-with-your-subscription path rather than the pay-per-token one.
`config.py` is the only file that knows about this; nothing else in the codebase cares
which backend is active.

### Option A: Claude Code CLI, your Pro/Max subscription (default, no extra cost)

This is what the default `WORLD_BACKEND=cli` setting uses. It shells out to the official
`claude` CLI in non-interactive mode (`claude -p`), authenticated with your normal Claude
login - the same subscription you'd use to chat with Claude Code interactively. No API
key, no per-token billing, but it shares your regular 5-hour/weekly usage pool, which is
why `evolve` defaults to running rarely (once a day) rather than continuously.

1. Install the CLI if you don't have it already:
   [docs.claude.com/en/docs/claude-code](https://docs.claude.com/en/docs/claude-code) has
   the current instructions for your OS.
2. Authenticate it once: `claude login` (opens a browser to sign in).
3. Confirm it works: `claude -p "say hi"` should print a reply with no further prompts.
4. That's it - `python driver.py evolve` will now use the same login.

Keep in mind this is meant for your own machine, run occasionally, not for CI or shared
infrastructure - see the caution in `config.py`.

### Option B: Anthropic API key (pay-per-token)

Needed if you want `evolve` running on a schedule somewhere other than your own machine
(GitHub Actions, a server), or more often than the CLI's usage pool comfortably allows.

```bash
export WORLD_BACKEND=api
export ANTHROPIC_API_KEY=sk-...    # from console.anthropic.com
```

Get a key at [console.anthropic.com](https://console.anthropic.com) (Settings → API
Keys). This bills per token against that account, separate from any Claude subscription.
See `.github/workflows/evolve.yml.disabled` for a ready-to-enable GitHub Actions workflow
once you're on this backend.

## Running it unattended (local schedule, Pro plan)

Once `evolve` works from the command line (above), the same call can run on a timer so
the world evolves without you manually invoking it. Both scheduling docs below assume the
CLI backend (Option A) and just run `python driver.py simulate` / `evolve` on an interval.

- Linux / macOS / WSL: see `crontab.example`.
- Plain Windows (no WSL): Windows has no `cron` - see `SCHEDULING_WINDOWS.md` for the
  Task Scheduler equivalent. Note two Task Scheduler defaults worth checking on a laptop:
  it won't fire while running on battery, and it won't catch up a missed trigger, unless
  you turn both off in the task's settings.

## Structure

```
driver.py              entry point: simulate | evolve
config.py               backend abstraction (CLI subscription vs API key)
rules/ecosystem.py      the simulation itself (pure Python, no LLM)
state/world.json        current world state (species, resources, tick count)
state/goals.md          what the world is currently trying to become (Claude edits this)
state/scratchpad.md     evolve's private notes to itself across runs, for changes too big for one diff
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
   everything else is rejected even before the `PROTECTED.md` check runs. `state/scratchpad.md`
   (evolve's private cross-run notes) is also writable, via the same out-of-band mechanism as
   `goals.md` rather than the diff-checked `files` list - it doesn't count toward diff caps.
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
