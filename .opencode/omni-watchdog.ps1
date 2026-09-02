# OmniRoute watchdog - detects a crashed/down OmniRoute server and restarts it.
#
# Usage:
#   One-shot check (restart if down):  powershell -File omni-watchdog.ps1
#   Continuous loop (every 30s):      powershell -File omni-watchdog.ps1 -Loop
#   Cron/Task Scheduler every minute: powershell -File omni-watchdog.ps1
#
# Why: the local OmniRoute server (npm `omniroute`, base http://localhost:20128)
# died with NO clean shutdown under heavy concurrent request load. This watchdog
# verifies the health endpoint and resurrects the daemon when it is missing.

param(
    [int]$Port = 20128,
    [int]$IntervalSec = 30,
    [switch]$Loop
)

$LogDir   = "$env:USERPROFILE\.omniroute\watchdog"
$LogFile  = Join-Path $LogDir ("watchdog-" + (Get-Date -Format "yyyyMMdd") + ".log")
$opencodeDir = $null  # not needed here

# Load the real API key from the OmniRoute .env so health checks are authenticated.
$OmniEnv = "$env:USERPROFILE\.omniroute\.env"
$ApiKey  = $null
if (Test-Path $OmniEnv) {
    foreach ($line in (Get-Content $OmniEnv -ErrorAction SilentlyContinue)) {
        if ($line -match '^OMNIROUTE_API_KEY=(.+)$') {
            # strip surrounding quotes if present
            $v = $Matches[1].Trim().Trim('"').Trim("'")
            if ($v.Length -gt 0) { $ApiKey = $v; break }
        }
    }
}

function Write-Log($msg) {
    if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
    $line = (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "  " + $msg
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

function Test-ServerUp {
    # Quick socket check (no HTTP round-trip needed)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conn) { return $false }
    # Confirm it actually answers (not a stale listener)
    try {
        $hdrs = @{}
        if ($ApiKey) { $hdrs["Authorization"] = "Bearer $ApiKey" }
        $r = Invoke-WebRequest -Uri "http://localhost:$Port/v1/models" -Headers $hdrs -TimeoutSec 8 -UseBasicParsing
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

function Start-Server {
    $out = "$env:TEMP\opencode\omni_watchdog_start.out.log"
    $err = "$env:TEMP\opencode\omni_watchdog_start.err.log"
    if (-not (Test-Path "$env:TEMP\opencode")) { New-Item -ItemType Directory -Path "$env:TEMP\opencode" -Force | Out-Null }
    try {
        # Run via cmd so the PSP shim resolves; daemon detaches itself.
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c","omniroute serve --daemon --no-open --port $Port > `"$out`" 2> `"$err`"" -WindowStyle Hidden
        Start-Sleep -Seconds 10
        if (Test-ServerUp) {
            Write-Log "SUCCESS: restarted OmniRoute on port $Port"
            return $true
        } else {
            Write-Log "WARNING: issued restart but port $Port still not up after 10s (check $err)"
            return $false
        }
    } catch {
        Write-Log "ERROR starting server: $($_.Exception.Message)"
        return $false
    }
}

function Run-Check {
    if (Test-ServerUp) {
        Write-Log "OK: OmniRoute healthy on port $Port"
        return
    }
    Write-Log "DOWN: OmniRoute not responding on port $Port - restarting"
    Start-Server
}

if ($Loop) {
    Write-Log "Watchdog starting (loop every ${IntervalSec}s) on port $Port. API key loaded: $([bool]$ApiKey)"
    while ($true) {
        Run-Check
        Start-Sleep -Seconds $IntervalSec
    }
} else {
    Run-Check
}
