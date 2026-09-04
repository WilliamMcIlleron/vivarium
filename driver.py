#!/usr/bin/env python3
"""
Entry point for the world.

    python driver.py simulate   # one free tick of the ecosystem, no LLM call
    python driver.py evolve     # one LLM-driven self-modification, guardrailed

See README.md for the guardrail design. This file is itself listed in
PROTECTED.md — evolve can never modify it.
"""

import datetime
import difflib
import json
import logging
import logging.handlers
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from config import get_backend
from rules.ecosystem import World

ROOT = Path(__file__).parent
STATE = ROOT / "state"
LOGS_DIR = ROOT / "logs"
WORLD_PATH = STATE / "world.json"
GOALS_PATH = STATE / "goals.md"
CHANGELOG_PATH = STATE / "changelog.md"
BUDGET_PATH = STATE / "budget.json"
PROTECTED_PATH = ROOT / "PROTECTED.md"
PAUSED_PATH = ROOT / "PAUSED"
NOTIFY_SCRIPT = ROOT / "notify_windows.ps1"
NOTABLE_EVENTS_PATH = STATE / "notable_events.log"
LORE_PATH = STATE / "lore.md"

# Backs the public viewer at https://vivarium.williamjonahmci.workers.dev/
# (Cloudflare Worker + KV, see cloudflare/README.md). This ID is the real,
# live namespace - not a secret, just an address.
CLOUDFLARE_KV_NAMESPACE_ID = "69dfa0f55b53489e96e0b4e42a4a862d"

# Events worth surfacing to evolve as real signal, distinct from routine
# per-tick noise (births/deaths happen constantly and aren't notable on
# their own).
NOTABLE_EVENT_MARKERS = ("EXTINCTION", "GRAZERS EXTINCT", "HUNTERS EXTINCT", "migrates into the world")

# Roughly once a week, evolve writes a reflection instead of a code change -
# tracked by calendar days, not run count, so it stays "weekly" regardless
# of how many times/day evolve actually fires.
REFLECTION_INTERVAL_DAYS = 7


def _make_logger(name: str) -> logging.Logger:
    """Logs to both a rotating file (so scheduled runs leave a trail even
    though Task Scheduler captures no stdout) and the console (so manual
    runs still see output as before). Capped at 512KB x 3 backups per log -
    simulate runs every 30 min forever, so this needs a ceiling.
    """
    LOGS_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:  # avoid duplicate handlers if called twice in-process
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / f"{name}.log", maxBytes=512_000, backupCount=3
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    return logger

# What evolve is allowed to write, independent of PROTECTED.md. PROTECTED.md is
# a denylist (documents specific paths that must never change); this is an
# allowlist (only these paths may change at all). Both are checked - a path
# has to pass the allowlist AND not match the denylist.
ALLOWED_PREFIXES = ("rules/", "viewer/")
ALLOWED_EXACT = ("state/goals.md",)


# ---------------------------------------------------------------- simulate --

def cmd_simulate() -> None:
    log = _make_logger("simulate")
    world = _load_world()
    world.step()
    world_text = _save_world(world)
    _sync_to_cloudflare("world.json", world_text, "application/json", log)
    d = world.to_dict()
    log.info(
        f"tick {world.tick}: population={d['population']} "
        f"(grazers={d['grazers']}, hunters={d['hunters']}) events={len(world.events)}"
    )
    if world.events:
        for e in world.events[:5]:
            log.info(f"  - {e}")
    _record_notable_events(world)
    if d["population"] == 0:
        log.info("Population extinct. `evolve` runs will see this and should treat")
        log.info("recovery as the top-priority goal on the next run.")


def _record_notable_events(world: World) -> None:
    notable = [e for e in world.events if any(m in e for m in NOTABLE_EVENT_MARKERS)]
    if not notable:
        return
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    new_lines = [f"{stamp} tick {world.tick}: {e}" for e in notable]
    existing = NOTABLE_EVENTS_PATH.read_text().splitlines() if NOTABLE_EVENTS_PATH.exists() else []
    NOTABLE_EVENTS_PATH.write_text("\n".join((existing + new_lines)[-100:]) + "\n")


def _load_world() -> World:
    if WORLD_PATH.exists():
        return World.from_dict(json.loads(WORLD_PATH.read_text()))
    return World.new()


def _save_world(world: World) -> str:
    text = json.dumps(world.to_dict(), indent=2)
    WORLD_PATH.write_text(text)
    return text


# ------------------------------------------------------------------ evolve --

EVOLVE_PROMPT_TEMPLATE = """\
You are making ONE incremental change to a self-modifying artificial-life \
simulation. Respond with ONLY a JSON object, no markdown fences, no preamble.

Current world state (summary):
{world_summary}

Genome snapshot (per-species averages, so you can see what's actually \
dominant right now, not just population counts):
{genome_stats}

Recent notable events (extinctions, migrations - not routine births/deaths):
{notable_events}

Recent changelog (most recent entries last):
{changelog_tail}

Current goals:
{goals}

Current contents of rules/ecosystem.py:
{ecosystem_source}

Current contents of viewer/index.html (the only way a human sees this world):
{viewer_source}

Rules for your response:
- If your change adds anything visually meaningful (a new species, a visible \
effect, a new attribute worth distinguishing), you MUST also update \
viewer/index.html in this same response to render it distinctly - a new \
color, shape, or size mapping. Do not leave new concepts invisible on screen. \
Purely internal tuning changes don't require this.
- Change at most {max_files} files, at most {max_lines} total changed lines \
(measured as actual added/removed lines against the current file, not full \
file length - editing a 180-line file by 10 lines costs 10 lines, not 180).
- You may ONLY write to: files under rules/, files under viewer/, and \
state/goals.md. Anything else is rejected even if it seems harmless. You may \
create NEW files under rules/ (e.g. a new species file) if that's cleaner \
than one giant ecosystem.py.
- Never touch anything listed in PROTECTED.md: {protected_paths}
- The simulation must remain pure Python with no new dependencies - \
requirements.txt is off-limits, so don't propose anything that needs a pip \
package.
- Pick ONE meaningful change. Do not attempt several goals from the goals \
file at once.
- rules/ecosystem.py has an extensible genome: Creature.traits is a dict, \
and TRAIT_REGISTRY (name -> (default, mutation_step, min, max)) makes \
whatever's in it mutate and inherit automatically. Adding a new gene is one \
entry there plus behavior code that reads creature.trait("name") - you \
don't need to touch _reproduce/_spawn_creature by hand for it.

Respond with exactly this JSON shape:
{{
  "files": {{"relative/path.py": "full new file content", ...}},
  "goals_update": "full new content of state/goals.md, or null if unchanged",
  "changelog_entry": "1-3 sentences: what you changed and why"
}}
"""

RETRY_PROMPT_TEMPLATE = """\
Your previous proposal for this same evolve run failed the test suite. Fix \
the specific problem shown below and respond again with exactly the same \
JSON shape. Change nothing else about your approach unless the failure shows \
it's fundamentally broken - this is a fix, not a new proposal.

Your previous proposal's files:
{previous_files}

pytest output from running the test suite against your proposal:
{test_output}

Respond with exactly this JSON shape:
{{
  "files": {{"relative/path.py": "full new file content", ...}},
  "goals_update": "full new content of state/goals.md, or null if unchanged",
  "changelog_entry": "1-3 sentences: what you changed and why"
}}
"""

REFLECTION_PROMPT_TEMPLATE = """\
You are writing a short field-journal entry about an artificial-life world \
you've been quietly observing and modifying - not proposing a code change \
this time. Write like a naturalist or chronicler: a few grounded paragraphs, \
evocative but built from what the data actually shows, not invented drama. \
Respond with plain prose only - no JSON, no markdown fences, no headers.

Current world state:
{world_summary}

Genome snapshot (per-species averages):
{genome_stats}

Recent notable events:
{notable_events}

Recent engineering changelog (most recent last):
{changelog_tail}

Previous chronicle entries (most recent last, for continuity - build on \
what's already been observed, don't repeat it):
{lore_tail}

Write 150-300 words. Notice something specific and true about this world \
right now - a population trend, a dominant trait, a pattern in the hunts, \
how long since the last real change - not generic scene-setting.
"""


def cmd_evolve() -> None:
    log = _make_logger("evolve")
    if PAUSED_PATH.exists():
        log.info("PAUSED file present - evolve will not run. Delete it to resume.")
        return

    budget = _load_budget()
    today = datetime.date.today().isoformat()
    if budget["last_run_date"] != today:
        budget["runs_today"] = 0
        budget["last_run_date"] = today
    if budget["runs_today"] >= budget["max_evolve_runs_per_day"]:
        log.info(f"Daily evolve budget ({budget['max_evolve_runs_per_day']}) already used today.")
        return

    world = _load_world()
    _record_population_history(budget, world)

    if _should_reflect(budget):
        _run_reflection(world, budget, log)
    else:
        _run_code_change(world, budget, log)


def _should_reflect(budget: dict) -> bool:
    last = budget.get("last_reflection_date")
    if last is None:
        return False  # nothing to reflect on yet - let a real history build up first
    days_since = (datetime.date.today() - datetime.date.fromisoformat(last)).days
    return days_since >= REFLECTION_INTERVAL_DAYS


def _record_population_history(budget: dict, world: World) -> None:
    d = world.to_dict()
    history = budget.get("population_history", [])
    history.append({"tick": world.tick, "grazers": d["grazers"], "hunters": d["hunters"]})
    budget["population_history"] = history[-14:]


def _genome_stats(world: World) -> dict:
    from rules.ecosystem import TRAIT_REGISTRY

    stats = {}
    for species in ("grazer", "hunter"):
        members = [c for c in world.creatures if c.species == species]
        if not members:
            continue
        entry = {
            "avg_speed": round(sum(c.speed for c in members) / len(members), 2),
            "avg_sense_range": round(sum(c.sense_range for c in members) / len(members), 2),
        }
        for name in TRAIT_REGISTRY:
            entry[f"avg_{name}"] = round(sum(c.trait(name) for c in members) / len(members), 3)
        stats[species] = entry
    return stats


def _shared_context(world: World, budget: dict) -> dict:
    summary = world.to_dict()
    return {
        "world_summary": json.dumps(
            {
                "tick": summary["tick"],
                "population": summary["population"],
                "grazers": summary["grazers"],
                "hunters": summary["hunters"],
                "resources": len(world.resources),
                # exclude the entry _record_population_history just added
                # for this run - the current tick/counts above already cover it.
                "recent_population_history": budget.get("population_history", [])[:-1],
            },
            indent=2,
        ),
        "genome_stats": json.dumps(_genome_stats(world), indent=2),
        "notable_events": _tail(NOTABLE_EVENTS_PATH, 20),
        "changelog_tail": _tail(CHANGELOG_PATH, 30),
    }


def _run_code_change(world: World, budget: dict, log: logging.Logger) -> None:
    prompt = EVOLVE_PROMPT_TEMPLATE.format(
        **_shared_context(world, budget),
        goals=GOALS_PATH.read_text(),
        ecosystem_source=(ROOT / "rules" / "ecosystem.py").read_text(),
        viewer_source=(ROOT / "viewer" / "index.html").read_text(),
        max_files=budget["max_diff_files_per_run"],
        max_lines=budget["max_diff_lines_per_run"],
        protected_paths=", ".join(_protected_paths()),
    )

    backend = get_backend()
    raw = backend.complete(prompt)
    _spend_budget(budget)

    proposal = _parse_proposal(raw)
    if proposal is None:
        msg = "evolve run FAILED: could not parse model response as JSON."
        _append_changelog(msg)
        log.error(msg)
        # The changelog stays short on purpose, but this failure is only
        # debuggable at all if the actual response is captured somewhere -
        # log-only, truncated, so a raw markdown-fenced or chatty reply
        # doesn't disappear without a trace like it did the first time.
        log.error(f"raw response was:\n{raw[:4000]}")
        sys.exit(1)

    ok, reason = _validate_proposal(proposal, budget)
    if not ok:
        msg = f"evolve run REJECTED: {reason}"
        _append_changelog(msg)
        log.warning(msg)
        sys.exit(1)

    backups = _write_files(proposal["files"])
    tests_ok, test_output = _run_tests()

    retried = False
    if not tests_ok:
        _restore_files(backups)
        retry_proposal = _attempt_retry(backend, proposal, test_output, budget, log)
        if retry_proposal is None:
            msg = f"evolve run REVERTED (tests failed): attempted - {proposal['changelog_entry']}"
            _append_changelog(msg)
            log.warning(msg)
            sys.exit(1)

        retried = True
        proposal = retry_proposal
        backups = _write_files(proposal["files"])
        tests_ok, test_output = _run_tests()
        if not tests_ok:
            _restore_files(backups)
            msg = (
                f"evolve run REVERTED after one retry (tests failed again): "
                f"attempted - {proposal['changelog_entry']}"
            )
            _append_changelog(msg)
            log.warning(msg)
            sys.exit(1)

    if proposal.get("goals_update"):
        GOALS_PATH.write_text(proposal["goals_update"])

    changelog_entry = proposal["changelog_entry"]
    if retried:
        changelog_entry = f"{changelog_entry} (succeeded on retry after an initial test failure)"
    _append_changelog(changelog_entry)
    _git_commit(changelog_entry)
    log.info(f"evolve run committed: {changelog_entry}")
    _notify("Vivarium evolved", changelog_entry)
    _sync_to_cloudflare("changelog.md", CHANGELOG_PATH.read_text(), "text/plain; charset=utf-8", log)
    if "viewer/index.html" in proposal["files"]:
        viewer_html = (ROOT / "viewer" / "index.html").read_text()
        _sync_to_cloudflare("viewer.html", viewer_html, "text/html; charset=utf-8", log)


def _attempt_retry(
    backend, proposal: dict, test_output: str, budget: dict, log: logging.Logger
) -> dict | None:
    """One retry after a first-attempt test failure - the same "see the failure,
    fix it, re-run" loop a normal coding session gets and evolve otherwise doesn't.
    Does NOT spend budget again; that already happened for the first
    backend.complete() call in _run_code_change.

    Returns the validated retry proposal, or None if the caller should fall
    through to the normal (non-retry) revert path - a retry that fails to
    parse or violates the guardrails is not retried again.
    """
    retry_prompt = RETRY_PROMPT_TEMPLATE.format(
        previous_files=json.dumps(proposal["files"], indent=2),
        test_output=test_output[-4000:],
    )
    raw = backend.complete(retry_prompt)

    retry_proposal = _parse_proposal(raw)
    if retry_proposal is None:
        log.error("evolve retry FAILED: could not parse retry response as JSON.")
        log.error(f"raw retry response was:\n{raw[:4000]}")
        return None

    ok, reason = _validate_proposal(retry_proposal, budget)
    if not ok:
        log.warning(f"evolve retry REJECTED: {reason}")
        return None

    return retry_proposal


def _run_reflection(world: World, budget: dict, log: logging.Logger) -> None:
    prompt = REFLECTION_PROMPT_TEMPLATE.format(
        **_shared_context(world, budget),
        lore_tail=_tail(LORE_PATH, 60),
    )

    backend = get_backend()
    raw = backend.complete(prompt)
    _spend_budget(budget)

    entry = raw.strip()
    if not entry:
        msg = "evolve run FAILED: reflection came back empty."
        _append_changelog(msg)
        log.error(msg)
        sys.exit(1)

    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    with LORE_PATH.open("a") as f:
        f.write(f"\n## {stamp}\n\n{entry}\n")

    budget["last_reflection_date"] = datetime.date.today().isoformat()
    _save_budget(budget)

    _append_changelog(f"evolve run: wrote a reflection to state/lore.md ({len(entry)} chars).")
    _git_commit("weekly reflection")
    log.info("evolve run: reflection written to state/lore.md")
    _notify("Vivarium reflects", entry[:200])
    _sync_to_cloudflare("lore.md", LORE_PATH.read_text(), "text/plain; charset=utf-8", log)
    _sync_to_cloudflare("changelog.md", CHANGELOG_PATH.read_text(), "text/plain; charset=utf-8", log)


def _spend_budget(budget: dict) -> None:
    """Counts an evolve call against the daily budget the moment the LLM
    call happens - that's the expensive/quota-consuming step, regardless of
    what happens after. Otherwise repeated rejected proposals are free to
    retry and can burn your whole session on nothing.
    """
    budget["runs_today"] += 1
    budget["total_evolve_runs"] += 1
    _save_budget(budget)


def _parse_proposal(raw: str) -> dict | None:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        cleaned = cleaned.removeprefix("json").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _validate_proposal(proposal: dict, budget: dict) -> tuple[bool, str]:
    files = proposal.get("files")
    if not files or not isinstance(files, dict):
        return False, "no files in proposal"
    if len(files) > budget["max_diff_files_per_run"]:
        return False, f"touched {len(files)} files, max is {budget['max_diff_files_per_run']}"

    for path in files:
        if not _path_allowed(path):
            return False, (
                f"proposal touches disallowed path: {path} "
                f"(only rules/, viewer/, and state/goals.md are writable)"
            )

    protected = _protected_paths()
    for path in files:
        norm = path.strip("/")
        for p in protected:
            if norm == p.strip("/") or norm.startswith(p.strip("/").rstrip("/") + "/"):
                return False, f"proposal touches protected path: {path}"

    total_lines = sum(_count_changed_lines(path, content) for path, content in files.items())
    if total_lines > budget["max_diff_lines_per_run"]:
        return False, f"{total_lines} lines changed, max is {budget['max_diff_lines_per_run']}"

    return True, ""


def _path_allowed(path: str) -> bool:
    norm = path.strip("/").replace("\\", "/")
    if norm in ALLOWED_EXACT:
        return True
    return any(norm.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def _count_changed_lines(rel_path: str, new_content: str) -> int:
    """Actual added+removed lines vs. the file on disk, not the file's full length.

    A brand-new file counts every line as added - there's no smaller diff to
    have. An edit to an existing file only counts lines that actually changed,
    so a 10-line tweak to a 200-line file costs 10, not 200.
    """
    full = ROOT / rel_path
    if not full.exists():
        return new_content.count("\n") + 1

    old_lines = full.read_text().splitlines()
    new_lines = new_content.splitlines()
    diff = difflib.unified_diff(old_lines, new_lines, n=0)
    changed = 0
    for line in diff:
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+") or line.startswith("-"):
            changed += 1
    return changed


def _write_files(files: dict) -> dict:
    """Writes new content, returns a backup map of {path: old_content_or_None}."""
    backups = {}
    for rel_path, content in files.items():
        full = ROOT / rel_path
        backups[rel_path] = full.read_text() if full.exists() else None
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
    return backups


def _restore_files(backups: dict) -> None:
    for rel_path, old_content in backups.items():
        full = ROOT / rel_path
        if old_content is None:
            full.unlink(missing_ok=True)
        else:
            full.write_text(old_content)


def _run_tests() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = f"{result.stdout}\n{result.stderr}".strip()
    if result.returncode != 0:
        log = logging.getLogger("evolve")
        log.warning(result.stdout)
        log.warning(result.stderr)
    return result.returncode == 0, output


def _git_commit(message: str) -> None:
    if not (ROOT / ".git").exists():
        return
    subprocess.run(["git", "add", "-A"], cwd=ROOT)
    subprocess.run(["git", "commit", "-m", f"evolve: {message}"], cwd=ROOT)


def _notify(title: str, message: str) -> None:
    """Fires a Windows toast when evolve commits a real change. Best-effort:
    a notification failure (no PowerShell, non-Windows, quiet hours, etc.)
    must never break an already-successful evolve run.
    """
    if sys.platform != "win32" or not NOTIFY_SCRIPT.exists():
        return
    try:
        subprocess.run(
            [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(NOTIFY_SCRIPT), "-Title", title, "-Message", message,
            ],
            cwd=ROOT,
            capture_output=True,
            timeout=15,
        )
    except Exception:
        pass


def _sync_to_cloudflare(key: str, content: str, content_type: str, log: logging.Logger) -> None:
    """Best-effort push of one file to the public KV store backing
    https://vivarium.williamjonahmci.workers.dev/. Silently does nothing if
    William hasn't set up his own Cloudflare credential - this can never be
    a hard dependency for simulate/evolve to work standalone, and a sync
    failure must never break an otherwise-successful run. Unlike _notify,
    failures ARE logged (not just swallowed) since a silently-stale public
    site is a real problem worth being able to debug later.
    """
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not token or not account_id:
        return

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/storage/kv/namespaces/{CLOUDFLARE_KV_NAMESPACE_ID}/values/{key}"
    )
    try:
        req = urllib.request.Request(
            url,
            data=content.encode("utf-8"),
            method="PUT",
            headers={"Authorization": f"Bearer {token}", "Content-Type": content_type},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        if not result.get("success"):
            log.warning(f"Cloudflare sync for {key!r} returned failure: {result.get('errors')}")
    except Exception as e:
        log.warning(f"Cloudflare sync for {key!r} failed: {e}")


def _protected_paths() -> list[str]:
    lines = PROTECTED_PATH.read_text().splitlines()
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


def _load_budget() -> dict:
    return json.loads(BUDGET_PATH.read_text())


def _save_budget(budget: dict) -> None:
    BUDGET_PATH.write_text(json.dumps(budget, indent=2))


def _append_changelog(entry: str) -> None:
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    with CHANGELOG_PATH.open("a") as f:
        f.write(f"\n## {stamp}\n\n{entry}\n")


def _tail(path: Path, lines: int) -> str:
    if not path.exists():
        return "(none yet)"
    all_lines = path.read_text().splitlines()
    return "\n".join(all_lines[-lines:]) or "(none yet)"


# --------------------------------------------------------------------- cli --

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("simulate", "evolve"):
        print("usage: python driver.py [simulate|evolve]")
        sys.exit(1)

    try:
        if sys.argv[1] == "simulate":
            cmd_simulate()
        else:
            cmd_evolve()
    except SystemExit:
        raise  # sys.exit() calls elsewhere already log their own reason
    except Exception:
        # Catch-all for anything NOT already anticipated (a rate-limited or
        # otherwise failing `claude` CLI call, a network error, etc.) - the
        # specific failure modes above already log themselves, but an
        # unexpected crash used to just print a traceback to stderr, which
        # Task Scheduler discards. That left zero trace of exactly the kind
        # of failure this logging exists to catch.
        logging.getLogger(sys.argv[1]).exception(f"{sys.argv[1]} crashed unexpectedly")
        sys.exit(1)
