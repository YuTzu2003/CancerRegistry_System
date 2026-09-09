$ErrorActionPreference = "Stop"
Get-ScheduledTask -TaskName "CancerRegistrySystem-??" -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-ScheduledTask -TaskName $_.TaskName -ErrorAction SilentlyContinue
    Write-Host "Stopped scheduled task: $($_.TaskName)"
}