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
import subprocess
import sys
from pathlib import Path

from config import get_backend
from rules.ecosystem import World

ROOT = Path(__file__).parent
STATE = ROOT / "state"
WORLD_PATH = STATE / "world.json"
GOALS_PATH = STATE / "goals.md"
CHANGELOG_PATH = STATE / "changelog.md"
BUDGET_PATH = STATE / "budget.json"
PROTECTED_PATH = ROOT / "PROTECTED.md"
PAUSED_PATH = ROOT / "PAUSED"

# What evolve is allowed to write, independent of PROTECTED.md. PROTECTED.md is
# a denylist (documents specific paths that must never change); this is an
# allowlist (only these paths may change at all). Both are checked - a path
# has to pass the allowlist AND not match the denylist.
ALLOWED_PREFIXES = ("rules/", "viewer/")
ALLOWED_EXACT = ("state/goals.md",)


# ---------------------------------------------------------------- simulate --

def cmd_simulate() -> None:
    world = _load_world()
    world.step()
    _save_world(world)
    d = world.to_dict()
    print(
        f"tick {world.tick}: population={d['population']} "
        f"(grazers={d['grazers']}, hunters={d['hunters']}) events={len(world.events)}"
    )
    if world.events:
        for e in world.events[:5]:
            print(f"  - {e}")
    if d["population"] == 0:
        print("Population extinct. `evolve` runs will see this and should treat")
        print("recovery as the top-priority goal on the next run.")


def _load_world() -> World:
    if WORLD_PATH.exists():
        return World.from_dict(json.loads(WORLD_PATH.read_text()))
    return World.new()


def _save_world(world: World) -> None:
    WORLD_PATH.write_text(json.dumps(world.to_dict(), indent=2))


# ------------------------------------------------------------------ evolve --

EVOLVE_PROMPT_TEMPLATE = """\
You are making ONE incremental change to a self-modifying artificial-life \
simulation. Respond with ONLY a JSON object, no markdown fences, no preamble.

Current world state (summary):
{world_summary}

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

Respond with exactly this JSON shape:
{{
  "files": {{"relative/path.py": "full new file content", ...}},
  "goals_update": "full new content of state/goals.md, or null if unchanged",
  "changelog_entry": "1-3 sentences: what you changed and why"
}}
"""


def cmd_evolve() -> None:
    if PAUSED_PATH.exists():
        print("PAUSED file present - evolve will not run. Delete it to resume.")
        return

    budget = _load_budget()
    today = datetime.date.today().isoformat()
    if budget["last_run_date"] != today:
        budget["runs_today"] = 0
        budget["last_run_date"] = today
    if budget["runs_today"] >= budget["max_evolve_runs_per_day"]:
        print(f"Daily evolve budget ({budget['max_evolve_runs_per_day']}) already used today.")
        return

    world = _load_world()
    summary = world.to_dict()
    prompt = EVOLVE_PROMPT_TEMPLATE.format(
        world_summary=json.dumps(
            {
                "tick": summary["tick"],
                "population": summary["population"],
                "grazers": summary["grazers"],
                "hunters": summary["hunters"],
                "resources": len(world.resources),
            },
            indent=2,
        ),
        changelog_tail=_tail(CHANGELOG_PATH, 30),
        goals=GOALS_PATH.read_text(),
        ecosystem_source=(ROOT / "rules" / "ecosystem.py").read_text(),
        viewer_source=(ROOT / "viewer" / "index.html").read_text(),
        max_files=budget["max_diff_files_per_run"],
        max_lines=budget["max_diff_lines_per_run"],
        protected_paths=", ".join(_protected_paths()),
    )

    backend = get_backend()
    raw = backend.complete(prompt)

    # Count this against the daily budget the moment the LLM call happens -
    # that's the expensive/quota-consuming step, regardless of whether the
    # proposal ends up valid or passes tests. Otherwise repeated rejected
    # proposals are free to retry and can burn your whole session on nothing.
    budget["runs_today"] += 1
    budget["total_evolve_runs"] += 1
    _save_budget(budget)

    proposal = _parse_proposal(raw)
    if proposal is None:
        _append_changelog("evolve run FAILED: could not parse model response as JSON.")
        sys.exit(1)

    ok, reason = _validate_proposal(proposal, budget)
    if not ok:
        _append_changelog(f"evolve run REJECTED: {reason}")
        sys.exit(1)

    backups = _write_files(proposal["files"])
    tests_ok = _run_tests()

    if not tests_ok:
        _restore_files(backups)
        _append_changelog(
            f"evolve run REVERTED (tests failed): attempted - {proposal['changelog_entry']}"
        )
        sys.exit(1)

    if proposal.get("goals_update"):
        GOALS_PATH.write_text(proposal["goals_update"])

    _append_changelog(proposal["changelog_entry"])
    _git_commit(proposal["changelog_entry"])
    print("evolve run committed:", proposal["changelog_entry"])


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


def _run_tests() -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    return result.returncode == 0


def _git_commit(message: str) -> None:
    if not (ROOT / ".git").exists():
        return
    subprocess.run(["git", "add", "-A"], cwd=ROOT)
    subprocess.run(["git", "commit", "-m", f"evolve: {message}"], cwd=ROOT)


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
    all_lines = path.read_text().splitlines()
    return "\n".join(all_lines[-lines:])


# --------------------------------------------------------------------- cli --

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("simulate", "evolve"):
        print("usage: python driver.py [simulate|evolve]")
        sys.exit(1)
    if sys.argv[1] == "simulate":
        cmd_simulate()
    else:
        cmd_evolve()
