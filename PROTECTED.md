# Protected paths

Files and directories listed here can never be touched by an `evolve` run.
`driver.py` checks every changed file against this list after Claude proposes
a diff and BEFORE anything is written to disk. A match aborts the run with
no changes applied and no commit made.

One path per line. Directories match everything inside them.

driver.py
config.py
PROTECTED.md
state/budget.json
state/world.json
state/changelog.md
state/paused.py
tests/
PAUSED
.github/workflows/
.git/
requirements.txt
crontab.example
README.md
notify_windows.ps1
SCHEDULING_WINDOWS.md
logs/
