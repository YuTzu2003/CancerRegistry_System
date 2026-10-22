param(
    [int]$Port = 51001,
    [string]$ListenAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment not found. Run uv sync first."
}

Set-Location -LiteralPath $projectRoot
$env:APP_ENV = "production"
$env:WAITRESS_HOST = $ListenAddress
$env:WAITRESS_PORT = "$Port"
$env:PYTHONFAULTHANDLER = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$ErrorActionPreference = "Continue"
& $python app.py
$pythonExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($pythonExitCode -ne 0) {
    throw "Waitress exited with code $pythonExitCode."
}
