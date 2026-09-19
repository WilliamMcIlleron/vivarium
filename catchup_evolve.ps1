<#
Catch-up runner: fires N evolve cycles back to back, each preceded by
TicksBetween free simulate ticks - for when the scheduled Vivarium-Evolve-*
tasks were missed (machine off/asleep) and the world needs to jump forward
by hand.

driver.py's own daily budget (state/budget.json: max_evolve_runs_per_day)
is a real guardrail against runaway evolve calls, and a catch-up run of this
size will hit it after 2-3 calls under the normal cap. This script raises
the cap just enough to cover the requested count, runs the whole batch, then
restores the original cap - it does NOT touch runs_today or
total_evolve_runs, so history stays honest.

Each evolve call shells out to the `claude` CLI and can take 12-16 minutes,
against your normal Pro/Max usage pool - the same one your interactive
sessions use. 10 evolves is a multi-hour, real-quota operation. Don't run
this unattended without knowing that.

Usage:
    powershell -File catchup_evolve.ps1
    powershell -File catchup_evolve.ps1 -Evolves 10 -TicksBetween 60
#>

param(
    [int]$Evolves = 10,
    [int]$TicksBetween = 60
)

$ErrorActionPreference = "Stop"
$world = $PSScriptRoot
$python = (Get-Command python).Source
$budgetPath = Join-Path $world "state\budget.json"

# Windows PowerShell 5.1's `Set-Content -Encoding utf8` writes a UTF-8 BOM.
# driver.py reads this file with Path.read_text() (no BOM handling), so a
# BOM'd write makes json.loads choke on the very first byte and crashes
# every subsequent simulate/evolve call - this is what broke the first run
# of this script. Write without a BOM instead.
function Set-JsonNoBom($Path, $Object) {
    $json = $Object | ConvertTo-Json -Depth 10
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $json, $utf8NoBom)
}

Write-Host "=== Vivarium catch-up: $Evolves evolves, $TicksBetween ticks between each ==="
Write-Host "World: $world"
Write-Host "Python: $python"
Write-Host ""

# --- temporarily raise the daily evolve cap so this batch isn't blocked ---
$budget = Get-Content $budgetPath -Raw | ConvertFrom-Json
$originalCap = $budget.max_evolve_runs_per_day
$neededCap = [Math]::Max($originalCap, $budget.runs_today + $Evolves)

if ($neededCap -ne $originalCap) {
    Write-Host "Raising max_evolve_runs_per_day from $originalCap to $neededCap for this catch-up run."
    $budget.max_evolve_runs_per_day = $neededCap
    Set-JsonNoBom $budgetPath $budget
}

try {
    for ($i = 1; $i -le $Evolves; $i++) {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-Host ""
        Write-Host "--- [$stamp] catch-up cycle $i of $Evolves : $TicksBetween ticks then evolve ---"

        for ($t = 1; $t -le $TicksBetween; $t++) {
            & $python (Join-Path $world "driver.py") simulate | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "simulate tick $t of cycle $i exited $LASTEXITCODE - continuing anyway"
            }
        }
        Write-Host "  $TicksBetween ticks done, running evolve..."

        & $python (Join-Path $world "driver.py") evolve
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "evolve cycle $i exited $LASTEXITCODE (see logs\evolve.log for why - rejected/reverted/rate-limited runs still exit non-zero and are expected sometimes)"
        }
    }
}
finally {
    # Always restore the original cap, even if a cycle throws or the run is
    # interrupted - this batch should never leave the guardrail permanently
    # loosened.
    $budget = Get-Content $budgetPath -Raw | ConvertFrom-Json
    if ($budget.max_evolve_runs_per_day -eq $neededCap -and $neededCap -ne $originalCap) {
        $budget.max_evolve_runs_per_day = $originalCap
        Set-JsonNoBom $budgetPath $budget
        Write-Host ""
        Write-Host "Restored max_evolve_runs_per_day to $originalCap."
    }
}

Write-Host ""
Write-Host "=== Catch-up done: $Evolves cycles attempted. Check logs\evolve.log and state\changelog.md for what actually landed. ==="
