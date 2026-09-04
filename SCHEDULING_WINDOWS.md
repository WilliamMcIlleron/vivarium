# Running unattended on Windows (no WSL, no cron)

Windows has no `cron`. `crontab.example` only works inside WSL. If you're
running plain Windows, use Task Scheduler instead.

## Already set up

These two tasks exist on this machine (created 2026-09-04):

- **SelfEvolvingWorld-Simulate** - every 30 minutes, runs `driver.py simulate`.
  Confirmed working: manually triggered once, tick advanced in
  `state/world.json`.
- **SelfEvolvingWorld-Evolve** - daily at 03:00, runs `driver.py evolve`. Not
  manually test-run, since that would spend a real evolve call against the
  daily budget and your Pro/Max usage pool - it'll fire on its own schedule,
  or trigger it yourself with `schtasks /run /tn "SelfEvolvingWorld-Evolve"`
  when you want to watch one happen.

Check status any time with:

```powershell
schtasks /query /tn "SelfEvolvingWorld-Simulate" /v /fo list
schtasks /query /tn "SelfEvolvingWorld-Evolve" /v /fo list
```

## Recreating from scratch (if deleted, or on a new machine)

Open PowerShell (not as admin - these are per-user tasks) and run:

```powershell
$world = "C:\Users\weebm\OneDrive\Desktop\Projects\self-evolving-world"
$python = (Get-Command python).Source

# simulate: free, no LLM call, safe to run often
schtasks /create /tn "SelfEvolvingWorld-Simulate" /tr "`"$python`" `"$world\driver.py`" simulate" /sc minute /mo 30 /st 00:00 /f

# evolve: calls Claude, keep infrequent (budget defaults to 1/day)
schtasks /create /tn "SelfEvolvingWorld-Evolve" /tr "`"$python`" `"$world\driver.py`" evolve" /sc daily /st 03:00 /f
```

Both tasks run with the working directory set to wherever `schtasks` runs
from by default (your user profile), and `driver.py` resolves all its paths
relative to its own file location (`ROOT = Path(__file__).parent`), so the
working directory doesn't actually matter here - only the full paths above do.

Test each one manually before trusting the schedule:

```powershell
schtasks /run /tn "SelfEvolvingWorld-Simulate"
schtasks /run /tn "SelfEvolvingWorld-Evolve"
```

Then check `state/world.json` and `state/changelog.md` for signs of life.

## 3. Claude CLI auth

`WORLD_BACKEND=cli` (the default, see `config.py`) shells out to `claude -p`
using your Pro/Max subscription login. Task Scheduler runs as your own user
account by default, so if `claude login` works in a normal terminal, it
should work here too - but confirm with a manual `schtasks /run` above before
relying on the schedule, since scheduled-task environments sometimes don't
inherit the same PATH or credentials as an interactive shell.

## 4. Logs

Nothing here writes logs automatically the way `crontab.example` does with
`>> logs/simulate.log`. If you want that, wrap the command in a small `.bat`
or PowerShell script that redirects output, and point `schtasks /tr` at the
script instead of `python.exe` directly.

## 5. Pausing

Same as any other backend: drop an empty `PAUSED` file in the project root
and `evolve` refuses to run. `simulate` is unaffected by `PAUSED` (it's free
and has no guardrails to bypass).

## Removing the tasks later

```powershell
schtasks /delete /tn "SelfEvolvingWorld-Simulate" /f
schtasks /delete /tn "SelfEvolvingWorld-Evolve" /f
```
