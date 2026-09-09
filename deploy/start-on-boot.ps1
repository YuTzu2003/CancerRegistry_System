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

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
Set-Location -LiteralPath $projectRoot
Start-Sleep -Seconds 30
$env:APP_ENV = "production"
$env:WAITRESS_HOST = $ListenAddress
$env:WAITRESS_PORT = "$Port"
& $python app.py *>> $logFile
exit $LASTEXITCODE