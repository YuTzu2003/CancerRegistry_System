$ErrorActionPreference = "Stop"
$firewallRuleName = "Cancer Registry System HTTP"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required program was not found in PATH: $Name"
    }
}

function Get-EnvironmentValue {
    param([string]$Name)
    $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match ("^{0}=" -f [regex]::Escape($Name)) } | Select-Object -Last 1
    if ($line) { return $line.Substring($Name.Length + 1) }
    return ""
}

function Test-Health {
    param([string]$Uri)
    try {
        $response = Invoke-RestMethod -Uri $Uri -TimeoutSec 3 -ErrorAction Stop
        return $response.status -eq "ok"
    }
    catch {
        return $false
    }
}

function Test-DatabaseConnection {
    $python = Join-Path $projectRoot ".venv\Scripts\python.exe"
    & $python -c "from modules.services.db import get_engine; get_engine().connect().close()"
    if ($LASTEXITCODE -ne 0) {
        throw "SQL Server connection failed. Correct SQLALCHEMY_DATABASE_URI and TLS/ODBC settings before IIS is changed."
    }
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated PowerShell window."
}

Require-Command "uv"
if (-not (Test-Path -LiteralPath $envFile)) {
    throw ".env was not found. Copy .env.example to .env and configure production settings."
}

$driver18 = Test-Path "HKLM:\SOFTWARE\ODBC\ODBCINST.INI\ODBC Driver 18 for SQL Server"
$driver17 = Test-Path "HKLM:\SOFTWARE\ODBC\ODBCINST.INI\ODBC Driver 17 for SQL Server"
if (-not $driver18 -and -not $driver17) {
    throw "ODBC Driver 17 or 18 for SQL Server was not found."
}

$requiredSettings = "APP_ENV", "APP_DEBUG", "SECRET_KEY", "SQLALCHEMY_DATABASE_URI", "PUBLIC_HTTP_PORT", "BACKEND_BASE_PORT", "APP_WORKERS", "LLM_WORKERS", "WAITRESS_HOST", "WAITRESS_THREADS", "WAITRESS_BACKLOG", "WAITRESS_CONNECTION_LIMIT", "WAITRESS_CHANNEL_TIMEOUT", "TRUSTED_PROXY", "PROXY_COUNT", "SESSION_COOKIE_SECURE", "SESSION_COOKIE_SAMESITE", "SESSION_LIFETIME_SECONDS"
$missingSettings = @($requiredSettings | Where-Object { [string]::IsNullOrWhiteSpace((Get-EnvironmentValue $_)) })
if ($missingSettings.Count -gt 0) { throw "Missing required .env settings: $($missingSettings -join ', ')" }

$appEnvironment = Get-EnvironmentValue "APP_ENV"
$appDebug = Get-EnvironmentValue "APP_DEBUG"
$secretKey = Get-EnvironmentValue "SECRET_KEY"
$databaseUri = Get-EnvironmentValue "SQLALCHEMY_DATABASE_URI"
$publicPort = [int](Get-EnvironmentValue "PUBLIC_HTTP_PORT")
$backendBasePort = [int](Get-EnvironmentValue "BACKEND_BASE_PORT")
$workerCount = [int](Get-EnvironmentValue "APP_WORKERS")
$llmWorkerCount = [int](Get-EnvironmentValue "LLM_WORKERS")
$waitressHost = Get-EnvironmentValue "WAITRESS_HOST"
$trustedProxy = Get-EnvironmentValue "TRUSTED_PROXY"
if ($appEnvironment -ne "production" -or $appDebug -notmatch '^(false|0|no|off)$') { throw "Set APP_ENV=production and APP_DEBUG=false in .env before deployment." }
if ($secretKey.Length -lt 32 -or $secretKey -eq "development-only-change-before-production") { throw "Set a production SECRET_KEY with at least 32 characters." }
if ([string]::IsNullOrWhiteSpace($databaseUri) -or $databaseUri -match 'user:password|your_database') { throw "Set a valid SQLALCHEMY_DATABASE_URI in .env before deployment." }
if ($publicPort -lt 1 -or $publicPort -gt 65535) { throw "PUBLIC_HTTP_PORT must be between 1 and 65535." }
if ($backendBasePort -lt 1 -or ($backendBasePort + $workerCount - 1) -gt 65535) { throw "BACKEND_BASE_PORT and APP_WORKERS must stay within TCP port range." }
if ($workerCount -lt 1 -or $workerCount -gt 8) { throw "APP_WORKERS must be between 1 and 8." }
if ($llmWorkerCount -ne 1) { throw "LLM_WORKERS must be 1 until the LLM task schema migration is applied." }
if ($waitressHost -notmatch '^127\.0\.0\.1$' -or $trustedProxy -notmatch '^127\.0\.0\.1$') { throw "WAITRESS_HOST and TRUSTED_PROXY must be 127.0.0.1 in production." }
if ((Get-EnvironmentValue "PROXY_COUNT") -ne "1") { throw "PROXY_COUNT must be 1 in production." }
if ($databaseUri -match 'ODBC\+Driver\+18' -and -not $driver18) { throw "SQLALCHEMY_DATABASE_URI requires ODBC Driver 18, but it is not installed." }
if ($databaseUri -match 'ODBC\+Driver\+17' -and -not $driver17) { throw "SQLALCHEMY_DATABASE_URI requires ODBC Driver 17, but it is not installed." }

Set-Location -LiteralPath $projectRoot
& uv sync
if ($LASTEXITCODE -ne 0) { throw "uv sync failed." }
Test-DatabaseConnection

& (Join-Path $PSScriptRoot "prepare-iis.ps1")
& (Join-Path $PSScriptRoot "configure-iis.ps1") -PublicPort $publicPort

$existingRule = Get-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue
if ($existingRule) {
    $existingPorts = @($existingRule | Get-NetFirewallPortFilter | Select-Object -ExpandProperty LocalPort)
    if ($existingPorts -notcontains "$publicPort") {
        throw "Firewall rule '$firewallRuleName' already exists with a different port. Review it manually before deployment."
    }
}
else {
    New-NetFirewallRule -DisplayName $firewallRuleName -Direction Inbound -Protocol TCP -LocalPort $publicPort -Action Allow | Out-Null
}

& (Join-Path $PSScriptRoot "stop-production.ps1")
& (Join-Path $PSScriptRoot "register-autostart.ps1")
Get-ScheduledTask -TaskName "CancerRegistrySystem-??" -ErrorAction Stop | ForEach-Object { Start-ScheduledTask -TaskName $_.TaskName }
Get-ScheduledTask -TaskName "CancerRegistrySystem-LLM-??" -ErrorAction Stop | ForEach-Object { Start-ScheduledTask -TaskName $_.TaskName }

$allHealthy = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    $allHealthy = $true
    for ($index = 0; $index -lt $workerCount; $index++) {
        $address = "127.0.0.$($index + 1)"
        $port = $backendBasePort + $index
        if (-not (Test-Health "http://${address}:${port}/health")) {
            $allHealthy = $false
            break
        }
    }
    if ($allHealthy) { break }
    Start-Sleep -Seconds 2
}
if (-not $allHealthy) { throw "One or more Waitress workers did not become ready. Read tasks\\logs\\cancer-registry-*.log" }
if (-not (Test-Health "http://127.0.0.1:${publicPort}/health")) { throw "IIS + ARR did not become ready on public port $publicPort." }
if (@(Get-ScheduledTask -TaskName "CancerRegistrySystem-LLM-??" -ErrorAction Stop).Count -ne $llmWorkerCount) { throw "Not every LLM worker scheduled task was registered." }
Test-DatabaseConnection
& (Join-Path $projectRoot ".venv\Scripts\python.exe") .\deploy\check_llm_readiness.py
if ($LASTEXITCODE -ne 0) { throw "LLM provider readiness failed. Read tasks\\logs\\cancer-registry-llm-*.log" }

Write-Host "Deployment completed. Open http://<server-ip>:$publicPort/"
