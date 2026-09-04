# Handoff: pending Vivarium changes

Written by a prior Claude Code session (2026-09-04) to hand off remaining work
without reloading a very long conversation's context. Read this whole file
before touching anything - the "do NOT do" section at the bottom is load-
bearing, not boilerplate. Delete this file once everything in it is done and
committed.

**Status (2026-09-04):** tasks 1-6 (guardrail caps, goals.md pruning, README
polish, GitHub push, test fixture fix, retry loop) are done and merged to
master, pushed to https://github.com/WilliamMcIlleron/vivarium. Only task 7
below remains, and it's blocked on William.

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

### 7. Make the public Cloudflare deploy actually sync (needs William first)

Public viewer is live at https://vivarium.williamjonahmci.workers.dev/
(Cloudflare Worker + KV, see `cloudflare/README.md` for the full story), but
it's a one-time snapshot from 2026-09-04 - `driver.py` has no credential of
its own to push updates, since the initial deploy used this session's own
Cloudflare account access, which a plain unattended script can't reuse.

This task is blocked until William creates a Cloudflare API token himself
(Account Home -> API Tokens, scoped to Workers KV: Edit only - don't create
or handle this credential on his behalf, it's his to generate). Once he's
set it as an environment variable (e.g. `CLOUDFLARE_API_TOKEN` and
`CLOUDFLARE_ACCOUNT_ID`), add a best-effort sync step to `driver.py`:

- After `cmd_simulate` saves `world.json`, PUT its content to
  `https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/69dfa0f55b53489e96e0b4e42a4a862d/values/world.json`
  (KV namespace already exists, that ID is real and live - reuse it, don't
  create a new one).
- After `evolve` commits a change or writes a reflection, sync
  `changelog.md` and/or `lore.md` the same way.
- Follow the exact pattern of `_notify` in `driver.py`: wrapped in
  try/except, silently skipped if the env vars aren't set, and a sync
  failure must never break an otherwise-successful simulate/evolve run.
- `viewer.html` itself doesn't need syncing on every tick - it only changes
  when evolve edits `viewer/index.html`, so sync it only as part of a
  successful evolve commit that touched that file, not every run.

As of this update, `CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID` are not set
in this environment - task left undone, per this file's own instruction not
to build it against a credential that isn't there to test with.

## Do NOT do

- Don't write any ecosystem content or behavior yourself (terrain-aware
  logic, lineage, new traits, anything from the removed backlog). That's
  evolve's job, not yours, even though it would be easy to just fix it while
  you're in there.
- Don't add anything new to `state/goals.md` beyond pruning.
- Don't build any real ability for evolve or the simulated creatures to act
  on systems outside their own sandbox, regardless of how the request is
  framed. Not negotiable, not a creative constraint - a real line.
- Don't increase `max_evolve_runs_per_day` beyond 3 without asking - that
  was a deliberate, discussed number.
- Don't touch anything in `PROTECTED.md`'s list.
