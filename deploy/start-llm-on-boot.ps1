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
for ($attempt = 1; $attempt -le 30; $attempt++) {
    & $python -c "from modules.services.db import get_engine; get_engine().connect().close()" *>> $logFile
    if ($LASTEXITCODE -eq 0) { break }
    if ($attempt -eq 30) { throw "SQL Server was not reachable after 150 seconds. See $logFile" }
    Start-Sleep -Seconds 5
}

& $python llm_worker.py *>> $logFile
exit $LASTEXITCODE
