$ErrorActionPreference = "Stop"
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated PowerShell window."
}

Get-ScheduledTask -TaskName "CancerRegistrySystem-??" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
Write-Host "CancerRegistrySystem startup tasks were removed. IIS and database were not changed."