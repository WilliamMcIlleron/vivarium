# Running unattended on Windows (no WSL, no cron)

Windows has no `cron`. `crontab.example` only works inside WSL. If you're
running plain Windows, use Task Scheduler instead.

## Already set up

The folder was renamed from `self-evolving-world` to `vivarium` on
2026-09-04. These tasks exist on this machine, pointing at the current path,
all with `AllowStartIfOnBatteries` + `DontStopIfGoingOnBatteries` +
`StartWhenAvailable` set (schtasks defaults to the opposite of all three,
which would silently break this on a laptop usually running on battery or
asleep - see `Get-ScheduledTask` / `New-ScheduledTaskSettingsSet` if
recreating by hand):

- **Vivarium-Simulate** - every 30 minutes, runs `driver.py simulate`.
- **Vivarium-Evolve-1/2/3** - daily at 03:00, 11:00, and 19:00 (bumped from
  once/day to 3x/day on 2026-09-04, now that the diff-size guardrail
  actually works correctly). `schtasks` has no clean single-task way to fire
  3x/day, so these are three separate daily tasks rather than one with a
  repeat interval - `driver.py`'s own budget check
  (`max_evolve_runs_per_day` in `state/budget.json`) is the real enforcement
  either way, so this is just a scheduling convenience, not a guardrail.

Check status any time with:

```powershell
schtasks /query /tn "Vivarium-Simulate" /v /fo list
schtasks /query /tn "Vivarium-Evolve-1" /v /fo list
```

## Recreating from scratch (if deleted, moved again, or on a new machine)

From PowerShell (not as admin - these are per-user tasks):

```powershell
$world = "C:\Users\weebm\OneDrive\Desktop\Projects\vivarium"
$python = (Get-Command python).Source

# simulate: free, no LLM call, safe to run often
schtasks /create /tn "Vivarium-Simulate" /tr "`"$python`" `"$world\driver.py`" simulate" /sc minute /mo 30 /st 00:00 /f

# evolve: calls Claude, 3x/day (budget.json's max_evolve_runs_per_day is the
# real cap - these three triggers just spread out when it gets a chance to run)
schtasks /create /tn "Vivarium-Evolve-1" /tr "`"$python`" `"$world\driver.py`" evolve" /sc daily /st 03:00 /f
schtasks /create /tn "Vivarium-Evolve-2" /tr "`"$python`" `"$world\driver.py`" evolve" /sc daily /st 11:00 /f
schtasks /create /tn "Vivarium-Evolve-3" /tr "`"$python`" `"$world\driver.py`" evolve" /sc daily /st 19:00 /f

# Apply reliability settings schtasks doesn't expose directly - without
# these, the tasks silently don't run on battery or after a missed trigger.
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
foreach ($name in "Vivarium-Simulate", "Vivarium-Evolve-1", "Vivarium-Evolve-2", "Vivarium-Evolve-3") {
    Set-ScheduledTask -TaskName $name -Settings $settings | Out-Null
}
```

Or from Git Bash - `schtasks` is a native Windows tool, and Git Bash's MSYS
layer auto-converts any argument starting with `/` (like `/tn`, `/create`)
into a Windows path, which breaks it. Prefix with `MSYS_NO_PATHCONV=1` to
disable that (the settings step above still needs PowerShell - there's no
Git Bash equivalent for `New-ScheduledTaskSettingsSet`):

```bash
WORLD_WIN='C:\Users\weebm\OneDrive\Desktop\Projects\vivarium'
PYTHON_WIN=$(cygpath -w "$(which python)")

MSYS_NO_PATHCONV=1 schtasks /create /tn "Vivarium-Simulate" /tr "\"$PYTHON_WIN\" \"$WORLD_WIN\\driver.py\" simulate" /sc minute /mo 30 /st 00:00 /f
MSYS_NO_PATHCONV=1 schtasks /create /tn "Vivarium-Evolve-1" /tr "\"$PYTHON_WIN\" \"$WORLD_WIN\\driver.py\" evolve" /sc daily /st 03:00 /f
MSYS_NO_PATHCONV=1 schtasks /create /tn "Vivarium-Evolve-2" /tr "\"$PYTHON_WIN\" \"$WORLD_WIN\\driver.py\" evolve" /sc daily /st 11:00 /f
MSYS_NO_PATHCONV=1 schtasks /create /tn "Vivarium-Evolve-3" /tr "\"$PYTHON_WIN\" \"$WORLD_WIN\\driver.py\" evolve" /sc daily /st 19:00 /f
```

Both task types run with the working directory set to wherever `schtasks`
runs from by default (your user profile), and `driver.py` resolves all its
paths relative to its own file location (`ROOT = Path(__file__).parent`), so
the working directory doesn't actually matter here - only the full paths
above do.

Test each one manually before trusting the schedule (PowerShell shown; from
Git Bash, prefix with `MSYS_NO_PATHCONV=1` as above):

```powershell
schtasks /run /tn "Vivarium-Simulate"
schtasks /run /tn "Vivarium-Evolve-1"
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

`driver.py` logs to `logs/simulate.log` and `logs/evolve.log` itself now
(rotating, 512KB x 3 backups) - no `>>` redirection needed in the scheduled
command, unlike `crontab.example`. This exists specifically because Task
Scheduler captures no stdout at all, so before this was added a scheduled
failure would have been completely invisible.

## Pausing

Same as any other backend: drop an empty `PAUSED` file in the project root
and `evolve` refuses to run. `simulate` is unaffected by `PAUSED` (it's free
and has no guardrails to bypass).

## Removing the tasks later

```powershell
schtasks /delete /tn "Vivarium-Simulate" /f
schtasks /delete /tn "Vivarium-Evolve-1" /f
schtasks /delete /tn "Vivarium-Evolve-2" /f
schtasks /delete /tn "Vivarium-Evolve-3" /f
```

From Git Bash: `MSYS_NO_PATHCONV=1 schtasks /delete /tn "Vivarium-Simulate" /f` (see the MSYS note above - without it, `/delete` gets mangled into a path and schtasks rejects it).
