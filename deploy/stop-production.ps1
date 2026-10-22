$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = [IO.Path]::GetFullPath((Join-Path $projectRoot ".venv\Scripts\python.exe"))

Get-ScheduledTask -TaskName "CancerRegistrySystem-??" -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-ScheduledTask -TaskName $_.TaskName -ErrorAction SilentlyContinue
    Write-Host "Stopped scheduled task: $($_.TaskName)"
}
Get-ScheduledTask -TaskName "CancerRegistrySystem-LLM-??" -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-ScheduledTask -TaskName $_.TaskName -ErrorAction SilentlyContinue
    Write-Host "Stopped scheduled task: $($_.TaskName)"
}

$managedProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
    if ([string]::IsNullOrWhiteSpace($_.ExecutablePath) -or [string]::IsNullOrWhiteSpace($_.CommandLine)) {
        return $false
    }

    $processPython = [IO.Path]::GetFullPath($_.ExecutablePath)
    $usesProjectPython = [string]::Equals($processPython, $python, [StringComparison]::OrdinalIgnoreCase)
    $runsProductionWorker = $_.CommandLine -match '(?i)(^|[\\/\s"])app\.py([\s"]|$)' -or $_.CommandLine -match '(?i)(^|[\\/\s"])llm_worker\.py([\s"]|$)'
    return $usesProjectPython -and $runsProductionWorker
})

$managedProcesses | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
    Write-Host "Stopped Cancer Registry Python process: $($_.ProcessId)"
}
