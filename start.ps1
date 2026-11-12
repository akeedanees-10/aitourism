# VoyAIge - AI Tourism Recommendation Web Application Launcher
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   Starting VoyAIge - AI Tourism Recommendation Web Application       " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    & $VenvPython (Join-Path $PSScriptRoot "run.py") @args
} else {
    python (Join-Path $PSScriptRoot "run.py") @args
}
