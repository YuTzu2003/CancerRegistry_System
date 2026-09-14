$ErrorActionPreference = "Stop"
Write-Host "Starting first-time Cancer Registry System deployment."
Write-Host "The target database must be empty; schema initialization will run before IIS is changed."
& (Join-Path $PSScriptRoot "deploy-production.ps1") -InitializeDatabase
