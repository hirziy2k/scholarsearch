# Redis8 Scheduled Task Fix
# Run this as Administrator to fix auto-start on logon.
# Fixes: battery suppression, missed triggers, Start In directory.

$taskName = "Redis8"
$batPath = "C:\Program Files\Redis\start-redis.bat"

# Remove old task
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Create new task: runs at logon, ignores battery, catches missed triggers
$action = New-ScheduledTaskAction -Execute $batPath -WorkingDirectory "C:\Program Files\Redis"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet `
    -DisallowStartIfOnBatteries:$false `
    -StopIfGoingOnBatteries:$false `
    -StartWhenAvailable:$true `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force

Write-Host "Task '$taskName' recreated. Verifying..."
Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State
