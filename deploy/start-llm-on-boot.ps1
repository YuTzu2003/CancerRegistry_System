param(
    [Parameter(Mandatory = $true)]
    [int]$WorkerNumber
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logDirectory = Join-Path $projectRoot "tasks\logs"
$logFile = Join-Path $logDirectory ("cancer-registry-llm-{0:D2}.log" -f $WorkerNumber)
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment not found. Run uv sync first."
}

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
Set-Location -LiteralPath $projectRoot
$env:APP_ENV = "production"
$attempt = 0
while ($true) {
    $attempt++
    & $python -c "from modules.services.db import get_engine; get_engine().connect().close()" *>> $logFile
    if ($LASTEXITCODE -eq 0) { break }
    Add-Content -LiteralPath $logFile -Value "[$(Get-Date -Format o)] SQL Server is not ready (attempt $attempt); retrying in 5 seconds."
    Start-Sleep -Seconds 5
}

& $python llm_worker.py *>> $logFile
exit $LASTEXITCODE
