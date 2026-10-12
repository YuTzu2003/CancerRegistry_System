param(
    [Parameter(Mandatory = $true)]
    [int]$Port,
    [Parameter(Mandatory = $true)]
    [string]$ListenAddress
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$startupScript = Join-Path $PSScriptRoot "start-production.ps1"
$logDirectory = Join-Path $projectRoot "tasks\logs"
$logFile = Join-Path $logDirectory ("cancer-registry-{0}.log" -f $Port)
if (-not (Test-Path -LiteralPath $startupScript)) {
    throw "Startup script was not found."
}

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
Set-Location -LiteralPath $projectRoot
# Let IIS, SQL Server, and network services complete their boot sequence.
Start-Sleep -Seconds 30

while ($true) {
    Add-Content -LiteralPath $logFile -Value "[$(Get-Date -Format o)] Starting Waitress on ${ListenAddress}:${Port}."
    & $startupScript -Port $Port -ListenAddress $ListenAddress *>> $logFile
    Add-Content -LiteralPath $logFile -Value "[$(Get-Date -Format o)] Waitress exited with code $LASTEXITCODE; restarting in 10 seconds."
    Start-Sleep -Seconds 10
}
