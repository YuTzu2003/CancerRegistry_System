$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated PowerShell window."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"
$startupScript = Join-Path $PSScriptRoot "start-on-boot.ps1"
$powershell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
if (-not (Test-Path -LiteralPath $envFile)) { throw ".env was not found." }
if (-not (Test-Path -LiteralPath $startupScript)) { throw "Startup script was not found." }

function Get-EnvironmentValue {
    param([string]$Name)

    $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match ("^{0}=" -f [regex]::Escape($Name)) } | Select-Object -Last 1
    if ($line) { return $line.Substring($Name.Length + 1) }
    return ""
}

$workerCount = [int](Get-EnvironmentValue "APP_WORKERS")
$backendBasePort = [int](Get-EnvironmentValue "BACKEND_BASE_PORT")
if ($workerCount -lt 1 -or $workerCount -gt 8) { throw "APP_WORKERS must be between 1 and 8." }

Get-ScheduledTask -TaskName "CancerRegistrySystem-??" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$settings.ExecutionTimeLimit = "PT0S"
$settings.RestartCount = 3
$settings.RestartInterval = "PT1M"
$taskPrincipal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

for ($index = 0; $index -lt $workerCount; $index++) {
    $port = $backendBasePort + $index
    $listenAddress = "127.0.0.$($index + 1)"
    $taskName = "CancerRegistrySystem-{0:D2}" -f ($index + 1)
    $arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -Port {1} -ListenAddress {2}' -f $startupScript, $port, $listenAddress
    $action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $taskPrincipal -Description "Starts Cancer Registry Waitress worker on port $port." -Force | Out-Null
    Write-Host "Registered scheduled task: $taskName"
}