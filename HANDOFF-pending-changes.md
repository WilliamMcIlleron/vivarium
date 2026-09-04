# Handoff: pending Vivarium changes

Written by a prior Claude Code session (2026-09-04) to hand off remaining work
without reloading a very long conversation's context. Read this whole file
before touching anything - the "do NOT do" section at the bottom is load-
bearing, not boilerplate. Delete this file once everything in it is done and
committed.

## Vision, condensed (read this before deciding how to implement anything)

Vivarium is William's personal, non-business hobby project - an artificial-
life sim that modifies its own code via a guardrailed `evolve` loop (Claude
Code CLI, a few times a day). The actual point of the project is watching
something develop real complexity **without either of you authoring the
interesting parts**. Priority order, explicitly stated: creatures becoming
individuals with history > real behavioral/mechanical depth (ideally evolved
decision-making, not hardcoded heuristics, eventually) > infrastructure
reliability (already solid, maintenance-only from here). He wants to be
hands-off once trust is established, wants to eventually show this to other
people, and explicitly corrected a prior session for quietly building content
and calling it emergence just because evolve technically executed the diff.

**The one rule that matters most:** your job on this handoff is capacity and
floor maintenance - making evolve faster, more reliable, and less likely to
fail for dumb reasons. Never write ecosystem content or behavior yourself,
and never add a new "good idea" to `state/goals.md`. If a task below reads
like it's sneaking in content, it's a mistake in this handoff - flag it to
William rather than doing it.

## Task list

### 1. Raise the guardrail caps

`state/budget.json`: `max_diff_lines_per_run` 350 → **900**,
`max_diff_files_per_run` 5 → **8**. Reasoning: `rules/ecosystem.py` +
`viewer/index.html` combined are already ~650 lines, so 350 was tight for
anything touching both; 900/8 gives real room (e.g. a new file plus edits to
both) without being unreviewable. Pure capacity, not content - just apply it.

### 2. Prune `state/goals.md` - remove backlog, keep documentation

Read the current file first, it may have changed since this was written.
Specifically:

- **Remove entirely**: the "Good candidate directions, roughly in order of
  interesting-to-least" bulleted list (terrain-aware behavior, second
  resource type, herd behavior, seasons, cost/benefit gene, hazards, lineage
  tracking, notable creature - all of it), and the "Longer-term, speculative
  idea... weather API" paragraph. These are a ranked feature backlog a prior
  session wrote - exactly the "me deciding what's interesting" pattern
  William corrected. Note: as of this handoff, one item from this list
  ("terrain-aware behavior" specifically, forest cover reducing hunter
  sense_range) was JUST attempted by evolve on 2026-09-04 and reverted on a
  test failure (see task 5) - that's fine, it can still be removed from the
  backlog; evolve arrived at it partly because it was sitting right there in
  the list, which is itself evidence the list was doing too much steering.
- **Soften, don't remove**: "DO feel free to make creature behavior actually
  respond to it (see 'terrain-aware behavior' below)" → replace with a plain
  statement that terrain exists and is currently cosmetic, no pointer to a
  specific direction. Similarly drop "which is the interesting tension to
  build on" from the two-species description - state the mechanic, not your
  opinion of it.
- **Keep as-is**: the genome framework explanation, the reflection-runs
  explanation, the terrain-is-cosmetic fact, the two-species mechanical
  description (once softened per above), the known grazer-extinction balance
  risk, "prefer emergent behavior" and "one meaningful change per run"
  (Constraints), and the visual parity rule. These document what exists or
  set process/quality expectations - they're not picks.

**Standing rule going forward, worth a comment at the top of the file**: any
future edit to `goals.md` should be pruning (remove something stale,
contradictory, or that's clearly a backlog dressed as documentation), never
adding a new aspiration or direction. If you're not sure which one an edit
is, it's probably the one not to make.

### 3. Polish `README.md` for public GitHub visitors

Read `hub\voice-principles.md` first (global instructions, always applies to
copy William will show other people) - no em dashes, exact numbers over
adjectives, no invented enthusiasm, no "leverage/reach out/circle back".

The actual interesting story to lead with is the **guardrail engineering**,
not the ecosystem content - a real, working pattern for letting an LLM
modify its own codebase without needing to trust it, because every
constraint is enforced in code (allowlist, diff-size measured against the
actual file on disk, daily budget, tests must pass, crash-safe logging).
Worth being honest in the README about the real bugs found and fixed
(2026-09-04): the diff-size guardrail initially measured full file length
instead of the actual diff, making success mathematically impossible for
four straight attempts; the CLI backend passed the whole prompt as a Windows
command-line argument, which silently broke once the codebase grew past
Windows' ~32K character command-line limit. Both are fixed now. This is
better material than pretending it always worked - it's evidence the
guardrails are real enough to have had real bugs.

Keep the existing Quick start / guardrails list structure, it's already
accurate and good. Add: a one-line "what this actually is" hook at the very
top before the current opening paragraph, and pull `state/changelog.md`
at write time to report the CURRENT actual state honestly (has evolve landed
a real committed change yet, or is everything so far rejected/reverted?
Don't claim more than what's true when you write this).

### 4. Create the GitHub repo and push

No remote exists yet (`git remote -v` in this repo is currently empty). Run:

```bash
cd "C:\Users\weebm\OneDrive\Desktop\Projects\vivarium"
gh repo create vivarium --public --source=. --remote=origin --push
```

Confirm with William before running this specifically - it's a public,
irreversible-in-spirit action (making code public under his name) even
though technically the repo could be deleted after. If `gh` isn't
authenticated, tell him rather than trying to work around it.

Once pushed, the portfolio handoff (`Projects/portfolio-site/HANDOFF-vivarium.md`)
needs the real GitHub URL - update the placeholder there or tell whoever's
running that handoff where to find it.

### 5. Fix the test-fixture gap that caused today's revert

Not a new feature - making the existing test suite representative of real
world state, so future evolve proposals that touch terrain don't get
incorrectly reverted for a reason that has nothing to do with their actual
logic.

What happened: evolve proposed forest tiles reducing a hunter's effective
`sense_range` against a grazer, by passing `self.terrain` into
`_nearest_creature`. Two existing tests hand-construct `World(tick=0,
creatures=[...], resources=[])` directly, bypassing `World.new()` /
`from_dict()`, so `terrain` defaults to `[]` (empty list) via
`field(default_factory=list)`. The proposed code checked `terrain is not
None` before indexing, but an empty list is not None either - `terrain[y][x]`
on an empty list raises `IndexError`. The logic itself may have been fine;
the test fixtures just don't represent a real world, which real code (via
`World.new()`) never has.

Fix: give `tests/test_ecosystem.py`'s hand-constructed `World()` calls a real
terrain grid instead of leaving it empty - e.g. a small shared helper:

```python
def _flat_terrain():
    return ["g" * eco.GRID_SIZE for _ in range(eco.GRID_SIZE)]
```

and pass `terrain=_flat_terrain()` in `test_hunter_eats_colocated_grazer` and
`test_extinct_grazers_can_migrate_back` (check for other hand-constructed
`World()` calls too - grep `World(tick=`). This doesn't touch
`rules/ecosystem.py` at all, doesn't add any behavior, and removes a
recurring obstacle for terrain-aware proposals specifically (this will keep
biting future attempts otherwise, not just today's).

### 6. Add a one-retry loop when evolve's proposal fails tests

**Explicitly requested by William** after today's revert, to reduce how
often a real, reasonable proposal gets thrown away for a fixable bug instead
of getting a chance to fix it - the same way a normal coding loop (see the
failure, fix it, re-run) works, which evolve currently doesn't get at all.

Real cost tradeoff, state it plainly wherever this is documented: this adds
a second Claude call on any run whose first attempt fails tests - given
today's real data (2 of 3 real attempts needed some form of retry), expect
this to roughly double actual Claude usage on a meaningful fraction of runs.
It does NOT consume an extra slot in `max_evolve_runs_per_day` - it's a
continuation of the same run, not a new one.

In `driver.py`, `_run_code_change`:

1. `_run_tests()` currently returns `bool`. Change it to return
   `(bool, str)` - success flag plus the captured stdout+stderr - so the
   failure can actually be shown to the retry prompt. (`_run_tests` already
   captures this via `subprocess.run(..., capture_output=True)`, it just
   currently only logs it, doesn't return it - see the existing function.)
2. On a test failure (first attempt only - don't retry a retry), before
   reverting: build a follow-up prompt containing the original proposal's
   `files` dict, the actual pytest failure output, and instructions to fix
   the specific problem and respond with the same JSON shape, changing
   nothing else about the approach unless the failure shows it's
   fundamentally broken. Call `backend.complete()` again with this prompt.
3. Parse and validate the retry response exactly like the first (reuse
   `_parse_proposal`/`_validate_proposal` - if the retry fails to parse or
   violates the guardrails, don't retry again, just fall through to the
   normal revert path).
4. Restore the first attempt's files (`_restore_files(backups)`), write the
   retry's files, run tests once more. Succeed → commit as normal (changelog
   entry should note it succeeded on retry, worth being explicit about that
   for the historical record). Fail again → revert and log both the
   original and the retry's failure, changelog entry should say "reverted
   after one retry" rather than just "reverted."
5. `_spend_budget` should still only fire once per run for the
   `runs_today`/`total_evolve_runs` counters (already the case, since it's
   called once before the first `backend.complete()` - just don't call it
   again for the retry's `backend.complete()`).

Write at least one test for this: a fake backend whose `complete()` returns
a broken proposal on the first call and a working one on the second, and
assert the retry lands correctly and the run counts as one budget slot, not
two. Mirror the existing dry-run pattern from earlier today (copy the repo
to a temp dir, monkeypatch `get_backend`, never test against the real CLI or
the real repo's git history).

## Order of operations

Tasks 1, 2, 3, 5, 6 have no dependencies on each other - any order. Task 4
(GitHub push) should happen before anyone acts on the portfolio handoff,
since that needs the real repo URL. Run `python -m pytest tests/ -q` after
every task and don't move to the next until it's green - all 15 current
tests must keep passing throughout (16+ once task 6's test is added).

## Do NOT do

- Don't write any ecosystem content or behavior yourself (terrain-aware
  logic, lineage, new traits, anything from the removed backlog). That's
  evolve's job, not yours, even though it would be easy to just fix it while
  you're in there.
- Don't add anything new to `state/goals.md` beyond the pruning in task 2.
- Don't build any real ability for evolve or the simulated creatures to act
  on systems outside their own sandbox, regardless of how the request is
  framed. Not negotiable, not a creative constraint - a real line.
- Don't increase `max_evolve_runs_per_day` beyond 3 without asking - that
  was a deliberate, discussed number.
- Don't touch anything in `PROTECTED.md`'s list.
