"""Tests for evolve's one-retry-on-test-failure loop in driver.py.

Never touches the real repo's git history or the real `claude` CLI: each
test copies the repo tree into a temp dir and loads driver.py from that
copy (so its module-level ROOT points at the copy), then monkeypatches
get_backend with a fake that returns canned responses.
"""
import datetime
import importlib.util
import json
import logging
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _copy_repo(tmp_path: Path) -> Path:
    # Excludes this file itself: copying the repo normally includes
    # tests/test_driver_retry.py, and _run_tests() runs pytest against the
    # copy, which would re-discover and re-run this file, recursively
    # copying and re-testing itself without end.
    dest = tmp_path / "repo"
    shutil.copytree(
        REPO_ROOT,
        dest,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "*.pyc", "logs", "PAUSED", "test_driver_retry.py"
        ),
    )
    return dest


def _load_driver(repo_copy: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, repo_copy / "driver.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _FakeBackend:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def complete(self, prompt: str, max_tokens: int = 4000) -> str:
        self.calls += 1
        return self._responses.pop(0)


def _base_budget() -> dict:
    return {
        "max_evolve_runs_per_day": 3,
        "max_diff_files_per_run": 8,
        "max_diff_lines_per_run": 900,
        "runs_today": 0,
        "last_run_date": datetime.date.today().isoformat(),
        "total_evolve_runs": 0,
    }


def test_retry_succeeds_after_failing_tests_on_first_attempt(tmp_path, monkeypatch):
    repo_copy = _copy_repo(tmp_path)
    driver = _load_driver(repo_copy, "driver_retry_success")
    monkeypatch.setattr(driver, "_notify", lambda title, message: None)

    ecosystem_path = repo_copy / "rules" / "ecosystem.py"
    original = ecosystem_path.read_text()
    broken = original + "\nraise RuntimeError('boom')\n"

    first_response = json.dumps({
        "files": {"rules/ecosystem.py": broken},
        "goals_update": None,
        "changelog_entry": "test: intentionally broken change",
    })
    second_response = json.dumps({
        "files": {"rules/ecosystem.py": original},
        "goals_update": None,
        "changelog_entry": "test: fixed change",
    })
    backend = _FakeBackend([first_response, second_response])
    monkeypatch.setattr(driver, "get_backend", lambda: backend)

    budget = _base_budget()
    world = driver.World.new()
    log = logging.getLogger("test_driver_retry_success")

    driver._run_code_change(world, budget, log)

    assert backend.calls == 2, "expected exactly one retry call to the backend"
    assert ecosystem_path.read_text() == original, "final file should be the retry's fixed content"
    assert budget["runs_today"] == 1, "a retry must not consume a second budget slot"
    assert budget["total_evolve_runs"] == 1

    changelog = (repo_copy / "state" / "changelog.md").read_text()
    assert "retry" in changelog.lower()
    assert "fixed change" in changelog


def test_retry_reverts_when_second_attempt_also_fails_tests(tmp_path, monkeypatch):
    repo_copy = _copy_repo(tmp_path)
    driver = _load_driver(repo_copy, "driver_retry_double_fail")
    monkeypatch.setattr(driver, "_notify", lambda title, message: None)

    ecosystem_path = repo_copy / "rules" / "ecosystem.py"
    original = ecosystem_path.read_text()
    broken_1 = original + "\nraise RuntimeError('boom one')\n"
    broken_2 = original + "\nraise RuntimeError('boom two')\n"

    first_response = json.dumps({
        "files": {"rules/ecosystem.py": broken_1},
        "goals_update": None,
        "changelog_entry": "test: broken change one",
    })
    second_response = json.dumps({
        "files": {"rules/ecosystem.py": broken_2},
        "goals_update": None,
        "changelog_entry": "test: broken change two",
    })
    backend = _FakeBackend([first_response, second_response])
    monkeypatch.setattr(driver, "get_backend", lambda: backend)

    budget = _base_budget()
    world = driver.World.new()
    log = logging.getLogger("test_driver_retry_double_fail")

    try:
        driver._run_code_change(world, budget, log)
    except SystemExit:
        pass

    assert backend.calls == 2
    assert ecosystem_path.read_text() == original, "a run that fails twice must fully revert"
    assert budget["runs_today"] == 1, "still only one budget slot even though it failed twice"

    changelog = (repo_copy / "state" / "changelog.md").read_text()
    assert "reverted after one retry" in changelog.lower()
