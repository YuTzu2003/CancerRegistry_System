$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) { throw ".env was not found." }

function Get-EnvironmentValue {
    param([string]$Name)

    $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match ("^{0}=" -f [regex]::Escape($Name)) } | Select-Object -Last 1
    if ($line) { return $line.Substring($Name.Length + 1) }
    return ""
}

$publicPort = [int](Get-EnvironmentValue "PUBLIC_HTTP_PORT")
$backendBasePort = [int](Get-EnvironmentValue "BACKEND_BASE_PORT")
$workerCount = [int](Get-EnvironmentValue "APP_WORKERS")
for ($index = 0; $index -lt $workerCount; $index++) {
    $address = "127.0.0.$($index + 1)"
    $port = $backendBasePort + $index
    $uri = "http://${address}:${port}/health"
    Write-Host "Worker $($index + 1): $uri"
    try { Invoke-RestMethod -Uri $uri -TimeoutSec 3 -ErrorAction Stop | ConvertTo-Json -Compress } catch { Write-Host "Unavailable: $($_.Exception.Message)" -ForegroundColor Red }
}

$publicUri = "http://127.0.0.1:${publicPort}/health"
Write-Host "IIS + ARR: $publicUri"
try { Invoke-RestMethod -Uri $publicUri -TimeoutSec 3 -ErrorAction Stop | ConvertTo-Json -Compress } catch { Write-Host "Unavailable: $($_.Exception.Message)" -ForegroundColor Red }
Get-Website -Name "CancerRegistrySystem" -ErrorAction SilentlyContinue | Select-Object Name,State,PhysicalPath
Get-ScheduledTask -TaskName "CancerRegistrySystem-??" -ErrorAction SilentlyContinue | Select-Object TaskName,State
Get-ScheduledTask -TaskName "CancerRegistrySystem-01" -ErrorAction SilentlyContinue | Get-ScheduledTaskInfo | Select-Object LastRunTime,LastTaskResult