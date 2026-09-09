param(
    [switch]$InitializeDatabase
)

$ErrorActionPreference = "Stop"
$siteName = "CancerRegistrySystem"
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

$appEnvironment = Get-EnvironmentValue "APP_ENV"
$secretKey = Get-EnvironmentValue "SECRET_KEY"
$databaseUri = Get-EnvironmentValue "SQLALCHEMY_DATABASE_URI"
$publicPort = [int](Get-EnvironmentValue "PUBLIC_HTTP_PORT")
$backendBasePort = [int](Get-EnvironmentValue "BACKEND_BASE_PORT")
$workerCount = [int](Get-EnvironmentValue "APP_WORKERS")
if ($appEnvironment -ne "production") { throw "Set APP_ENV=production in .env before deployment." }
if ($secretKey.Length -lt 32 -or $secretKey -eq "development-only-change-before-production") { throw "Set a production SECRET_KEY with at least 32 characters." }
if ([string]::IsNullOrWhiteSpace($databaseUri) -or $databaseUri -match 'user:password|your_database') { throw "Set a valid SQLALCHEMY_DATABASE_URI in .env before deployment." }
if ($publicPort -lt 1 -or $publicPort -gt 65535) { throw "PUBLIC_HTTP_PORT must be between 1 and 65535." }
if ($backendBasePort -lt 1 -or ($backendBasePort + $workerCount - 1) -gt 65535) { throw "BACKEND_BASE_PORT and APP_WORKERS must stay within TCP port range." }
if ($workerCount -lt 1 -or $workerCount -gt 8) { throw "APP_WORKERS must be between 1 and 8." }
if ($databaseUri -match 'ODBC\+Driver\+18' -and -not $driver18) { throw "SQLALCHEMY_DATABASE_URI requires ODBC Driver 18, but it is not installed." }
if ($databaseUri -match 'ODBC\+Driver\+17' -and -not $driver17) { throw "SQLALCHEMY_DATABASE_URI requires ODBC Driver 17, but it is not installed." }

Set-Location -LiteralPath $projectRoot
& uv sync
if ($LASTEXITCODE -ne 0) { throw "uv sync failed." }

if ($InitializeDatabase) {
    & uv run python .\deploy\init_database.py
    if ($LASTEXITCODE -ne 0) { throw "Database initialization failed." }
}

& (Join-Path $PSScriptRoot "configure-iis.ps1") -PublicPort $publicPort
Get-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName $firewallRuleName -Direction Inbound -Protocol TCP -LocalPort $publicPort -Action Allow | Out-Null

& (Join-Path $PSScriptRoot "register-autostart.ps1")
Get-ScheduledTask -TaskName "CancerRegistrySystem-??" -ErrorAction Stop | ForEach-Object { Start-ScheduledTask -TaskName $_.TaskName }

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
if (-not $allHealthy) {
    throw "One or more Waitress workers did not become ready. Read tasks\\logs\\cancer-registry-*.log"
}

if (-not (Test-Health "http://127.0.0.1:${publicPort}/health")) {
    throw "IIS + ARR did not become ready on public port $publicPort."
}

Write-Host "Deployment completed. Open http://<server-ip>:$publicPort/"