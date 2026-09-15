param(
    [Parameter(Mandatory = $true)]
    [int]$WorkerNumber
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logDirectory = Join-Path $projectRoot "tasks\logs"
$logFile = Join-Path $logDirectory ("cancer-registry-llm-{0:D2}.log" -f $WorkerNumber)
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Write-LlmStartupLog {
    param([string]$Message)

    Add-Content -LiteralPath $logFile -Value "[$(Get-Date -Format o)] $Message"
}

try {
    Write-LlmStartupLog "LLM worker startup requested."
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Python environment not found. Run uv sync first."
    }

    Set-Location -LiteralPath $projectRoot
    $env:APP_ENV = "production"
    $attempt = 0
    while ($true) {
        $attempt++
        & $python -c "from modules.services.db import get_engine; get_engine().connect().close()" *>> $logFile
        if ($LASTEXITCODE -eq 0) { break }
        Write-LlmStartupLog "SQL Server is not ready (attempt $attempt); retrying in 5 seconds."
        Start-Sleep -Seconds 5
    }

    Write-LlmStartupLog "SQL Server is ready; starting LLM worker."
    & $python llm_worker.py *>> $logFile
    if ($LASTEXITCODE -ne 0) { throw "LLM worker exited with code $LASTEXITCODE." }
}
catch {
    Write-LlmStartupLog "LLM worker startup failed: $($_.Exception.Message)"
    exit 1
}
