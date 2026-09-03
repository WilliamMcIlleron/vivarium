#!/usr/bin/env python3
"""
Entry point for the world.

    python driver.py simulate   # one free tick of the ecosystem, no LLM call
    python driver.py evolve     # one LLM-driven self-modification, guardrailed

See README.md for the guardrail design. This file is itself listed in
PROTECTED.md — evolve can never modify it.
"""

import datetime
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


# ---------------------------------------------------------------- simulate --

def cmd_simulate() -> None:
    world = _load_world()
    world.step()
    _save_world(world)
    pop = len(world.creatures)
    print(f"tick {world.tick}: population={pop} events={len(world.events)}")
    if world.events:
        for e in world.events[:5]:
            print(f"  - {e}")
    if pop == 0:
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

Rules for your response:
- Change at most {max_files} files, at most {max_lines} total changed lines.
- You may write to files under rules/, and to state/goals.md if you want to \
update the goals themselves. You may create NEW files under rules/ (e.g. a \
new species file) if that's cleaner than one giant ecosystem.py.
- Never touch anything listed in PROTECTED.md: {protected_paths}
- The simulation must remain pure Python with no new dependencies beyond \
what's already imported, unless you add the dependency to requirements.txt \
as part of your file list.
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
    prompt = EVOLVE_PROMPT_TEMPLATE.format(
        world_summary=json.dumps(world.to_dict()["population"], indent=2),
        changelog_tail=_tail(CHANGELOG_PATH, 30),
        goals=GOALS_PATH.read_text(),
        ecosystem_source=(ROOT / "rules" / "ecosystem.py").read_text(),
        max_files=budget["max_diff_files_per_run"],
        max_lines=budget["max_diff_lines_per_run"],
        protected_paths=", ".join(_protected_paths()),
    )

    backend = get_backend()
    raw = backend.complete(prompt)
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

    budget["runs_today"] += 1
    budget["total_evolve_runs"] += 1
    _save_budget(budget)
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

    total_lines = sum(content.count("\n") + 1 for content in files.values())
    if total_lines > budget["max_diff_lines_per_run"]:
        return False, f"{total_lines} lines changed, max is {budget['max_diff_lines_per_run']}"

    protected = _protected_paths()
    for path in files:
        norm = path.strip("/")
        for p in protected:
            if norm == p.strip("/") or norm.startswith(p.strip("/").rstrip("/") + "/"):
                return False, f"proposal touches protected path: {path}"

    return True, ""


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
