param(
    [Parameter(Mandatory = $true)]
    [int]$WorkerNumber
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logDirectory = Join-Path $projectRoot "tasks\logs"
$logFile = Join-Path $logDirectory ("cancer-registry-export-{0:D2}.log" -f $WorkerNumber)
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Write-ExportStartupLog {
    param([string]$Message)

    Add-Content -LiteralPath $logFile -Value "[$(Get-Date -Format o)] $Message"
}

try {
    Write-ExportStartupLog "Export worker startup requested."
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Python environment not found. Run uv sync first."
    }

    Set-Location -LiteralPath $projectRoot
    $env:APP_ENV = "production"
    $env:EXPORT_WORKER_NUMBER = "$WorkerNumber"
    $attempt = 0
    while ($true) {
        $attempt++
        & $python -c "from modules.services.db import get_engine; get_engine().connect().close()" *>> $logFile
        if ($LASTEXITCODE -eq 0) { break }
        Write-ExportStartupLog "SQL Server is not ready (attempt $attempt); retrying in 5 seconds."
        Start-Sleep -Seconds 5
    }

    Write-ExportStartupLog "SQL Server is ready; starting export worker."
    & $python export_worker.py *>> $logFile
    if ($LASTEXITCODE -ne 0) { throw "Export worker exited with code $LASTEXITCODE." }
}
catch {
    Write-ExportStartupLog "Export worker startup failed: $($_.Exception.Message)"
    exit 1
}
