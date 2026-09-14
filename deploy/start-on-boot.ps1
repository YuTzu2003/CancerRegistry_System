param(
    [Parameter(Mandatory = $true)]
    [int]$Port,
    [Parameter(Mandatory = $true)]
    [string]$ListenAddress
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logDirectory = Join-Path $projectRoot "tasks\logs"
$logFile = Join-Path $logDirectory ("cancer-registry-{0}.log" -f $Port)
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment not found. Run uv sync first."
}

$envLine = Get-Content -LiteralPath (Join-Path $projectRoot ".env") |
    Where-Object { $_ -match '^APP_ENV=' } |
    Select-Object -Last 1
if ($envLine -ne "APP_ENV=production") {
    throw "Set APP_ENV=production in .env before enabling automatic startup."
}

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
Set-Location -LiteralPath $projectRoot
# Let IIS, SQL Server, and network services complete their boot sequence.
Start-Sleep -Seconds 30

$env:APP_ENV = "production"
$env:WAITRESS_HOST = $ListenAddress
$env:WAITRESS_PORT = "$Port"
& $python app.py *>> $logFile
exit $LASTEXITCODE
