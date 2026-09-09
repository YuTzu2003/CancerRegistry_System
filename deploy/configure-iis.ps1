param(
    [Parameter(Mandatory = $true)]
    [int]$PublicPort
)

$ErrorActionPreference = "Stop"
Import-Module WebAdministration

$siteName = "CancerRegistrySystem"
$farmName = "CancerRegistryBackend"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"

function Get-EnvironmentValue {
    param([string]$Name)

    $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match ("^{0}=" -f [regex]::Escape($Name)) } | Select-Object -Last 1
    if ($line) {
        return $line.Substring($Name.Length + 1)
    }
    return ""
}

if (-not (Get-WebGlobalModule -Name "RewriteModule" -ErrorAction SilentlyContinue)) {
    throw "IIS URL Rewrite is not installed."
}

$workerCount = [int](Get-EnvironmentValue "APP_WORKERS")
$backendBasePort = [int](Get-EnvironmentValue "BACKEND_BASE_PORT")
if ($workerCount -lt 1 -or $workerCount -gt 8) {
    throw "APP_WORKERS must be between 1 and 8."
}

try {
    Set-WebConfigurationProperty -PSPath "MACHINE/WEBROOT/APPHOST" -Filter "system.webServer/proxy" -Name "enabled" -Value "True"
}
catch {
    throw "IIS ARR is not installed or proxy cannot be enabled."
}

$siteRoot = Join-Path $PSScriptRoot "iis-proxy"
New-Item -ItemType Directory -Path $siteRoot -Force | Out-Null
$webConfig = @"
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="Serve static files directly" stopProcessing="true">
          <match url="^static/.*" />
          <action type="None" />
        </rule>
        <rule name="Reverse proxy to Cancer Registry" stopProcessing="true">
          <match url="(.*)" />
          <action type="Rewrite" url="http://CancerRegistryBackend/{R:1}" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
  <location path="static">
    <system.webServer>
      <staticContent>
        <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="7.00:00:00" />
      </staticContent>
    </system.webServer>
  </location>
</configuration>
"@
[System.IO.File]::WriteAllText((Join-Path $siteRoot "web.config"), $webConfig, [System.Text.UTF8Encoding]::new($false))

$sitePath = "IIS:\Sites\$siteName"
$bindingInUse = Get-WebBinding | Where-Object { $_.protocol -eq "http" -and $_.bindingInformation.Split(":")[1] -eq "$PublicPort" -and $_.ItemXPath -notmatch ("name='{0}'" -f [regex]::Escape($siteName)) }
if ($bindingInUse) {
    throw "HTTP port $PublicPort is already bound by another IIS site."
}
if (-not (Test-Path -LiteralPath $sitePath)) {
    New-Website -Name $siteName -PhysicalPath $siteRoot -Port $PublicPort | Out-Null
}
else {
    Set-ItemProperty -LiteralPath $sitePath -Name physicalPath -Value $siteRoot
    if (-not (Get-WebBinding -Name $siteName -Protocol "http" | Where-Object { $_.bindingInformation.Split(":")[1] -eq "$PublicPort" })) {
        New-WebBinding -Name $siteName -Protocol "http" -Port $PublicPort
    }
}

$staticPath = "$sitePath/static"
if (Test-Path -LiteralPath $staticPath) {
    Set-ItemProperty -LiteralPath $staticPath -Name physicalPath -Value (Join-Path $projectRoot "static")
}
else {
    New-WebVirtualDirectory -Site $siteName -Name "static" -PhysicalPath (Join-Path $projectRoot "static") | Out-Null
}

$appCmd = Join-Path $env:windir "System32\inetsrv\appcmd.exe"
& $appCmd set config -section:webFarms ("/-`"[name='{0}']`"" -f $farmName) /commit:apphost 2>$null | Out-Null
& $appCmd set config -section:webFarms ("/+`"[name='{0}']`"" -f $farmName) /commit:apphost
if ($LASTEXITCODE -ne 0) { throw "Could not create ARR Server Farm $farmName." }
for ($index = 0; $index -lt $workerCount; $index++) {
    $address = "127.0.0.$($index + 1)"
    $port = $backendBasePort + $index
    & $appCmd set config -section:webFarms ("/+`"[name='{0}'].[address='{1}']`"" -f $farmName, $address) /commit:apphost
    if ($LASTEXITCODE -ne 0) { throw "Could not add ARR backend $address." }
    & $appCmd set config -section:webFarms ("/[name='{0}'].[address='{1}'].applicationRequestRouting.httpPort:{2}" -f $farmName, $address, $port) /commit:apphost
    if ($LASTEXITCODE -ne 0) { throw "Could not configure ARR backend port $port." }
}

Write-Host "Configured IIS site $siteName on port $PublicPort with $workerCount Waitress worker(s)."