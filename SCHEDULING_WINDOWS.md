# Running unattended on Windows (no WSL, no cron)

Windows has no `cron`. `crontab.example` only works inside WSL. If you're
running plain Windows, use Task Scheduler instead.

## Already set up

The folder was renamed from `self-evolving-world` to `vivarium` on
2026-09-04. These two tasks exist on this machine, pointing at the current
path:

- **Vivarium-Simulate** - every 30 minutes, runs `driver.py simulate`.
  Confirmed working both before and after the folder rename.
- **Vivarium-Evolve** - daily at 03:00, runs `driver.py evolve`. Not manually
  test-run, since that would spend a real evolve call against the daily
  budget and your Pro/Max usage pool - it'll fire on its own schedule, or
  trigger it yourself with `schtasks /run /tn "Vivarium-Evolve"` when you
  want to watch one happen.

Check status any time with:

```powershell
schtasks /query /tn "Vivarium-Simulate" /v /fo list
schtasks /query /tn "Vivarium-Evolve" /v /fo list
```

## Recreating from scratch (if deleted, moved again, or on a new machine)

From PowerShell (not as admin - these are per-user tasks):

```powershell
$world = "C:\Users\weebm\OneDrive\Desktop\Projects\vivarium"
$python = (Get-Command python).Source

# simulate: free, no LLM call, safe to run often
schtasks /create /tn "Vivarium-Simulate" /tr "`"$python`" `"$world\driver.py`" simulate" /sc minute /mo 30 /st 00:00 /f

# evolve: calls Claude, keep infrequent (budget defaults to 1/day)
schtasks /create /tn "Vivarium-Evolve" /tr "`"$python`" `"$world\driver.py`" evolve" /sc daily /st 03:00 /f
```

Or from Git Bash - `schtasks` is a native Windows tool, and Git Bash's MSYS
layer auto-converts any argument starting with `/` (like `/tn`, `/create`)
into a Windows path, which breaks it. Prefix with `MSYS_NO_PATHCONV=1` to
disable that:

```bash
WORLD_WIN='C:\Users\weebm\OneDrive\Desktop\Projects\vivarium'
PYTHON_WIN=$(cygpath -w "$(which python)")

MSYS_NO_PATHCONV=1 schtasks /create /tn "Vivarium-Simulate" /tr "\"$PYTHON_WIN\" \"$WORLD_WIN\\driver.py\" simulate" /sc minute /mo 30 /st 00:00 /f
MSYS_NO_PATHCONV=1 schtasks /create /tn "Vivarium-Evolve" /tr "\"$PYTHON_WIN\" \"$WORLD_WIN\\driver.py\" evolve" /sc daily /st 03:00 /f
```

Both tasks run with the working directory set to wherever `schtasks` runs
from by default (your user profile), and `driver.py` resolves all its paths
relative to its own file location (`ROOT = Path(__file__).parent`), so the
working directory doesn't actually matter here - only the full paths above do.

Test each one manually before trusting the schedule (PowerShell shown; from
Git Bash, prefix with `MSYS_NO_PATHCONV=1` as above):

```powershell
schtasks /run /tn "Vivarium-Simulate"
schtasks /run /tn "Vivarium-Evolve"
```

Then check `state/world.json` and `state/changelog.md` for signs of life.

## Claude CLI auth

`WORLD_BACKEND=cli` (the default, see `config.py`) shells out to `claude -p`
using your Pro/Max subscription login. Task Scheduler runs as your own user
account by default, so if `claude login` works in a normal terminal, it
should work here too - but confirm with a manual `schtasks /run` above before
relying on the schedule, since scheduled-task environments sometimes don't
inherit the same PATH or credentials as an interactive shell.

## Logs

Nothing here writes logs automatically the way `crontab.example` does with
`>> logs/simulate.log`. If you want that, wrap the command in a small `.bat`
or PowerShell script that redirects output, and point `schtasks /tr` at the
script instead of `python.exe` directly.

## Pausing

Same as any other backend: drop an empty `PAUSED` file in the project root
and `evolve` refuses to run. `simulate` is unaffected by `PAUSED` (it's free
and has no guardrails to bypass).

## Removing the tasks later

```powershell
schtasks /delete /tn "Vivarium-Simulate" /f
schtasks /delete /tn "Vivarium-Evolve" /f
```

From Git Bash: `MSYS_NO_PATHCONV=1 schtasks /delete /tn "Vivarium-Simulate" /f` (see the MSYS note above - without it, `/delete` gets mangled into a path and schtasks rejects it).
