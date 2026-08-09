<#
.SYNOPSIS
    ClaimSight task runner for Windows PowerShell.
.DESCRIPTION
    Thin wrapper around the common project tasks so Windows users don't need
    `make`. Usage:  .\run.ps1 <task>
    Tasks: setup, up, down, generate, ingest, quality, dbt, reporting,
           pipeline, dashboard, excel, test, lint, all
#>
param(
    [Parameter(Position = 0)]
    [string]$Task = "help"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"

function Invoke-Py { param([string[]]$Args) & $Py @Args; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }

switch ($Task) {
    "setup" {
        python -m venv .venv
        & $Py -m pip install --upgrade pip
        & $Py -m pip install -r requirements.txt
        if (-not (Test-Path (Join-Path $Root ".env"))) { Copy-Item .env.example .env }
    }
    "up"       { docker compose up -d }
    "down"     { docker compose down }
    "generate" { Invoke-Py @("-m", "claimsight.generate.generate") }
    "ingest"   { Invoke-Py @("-m", "claimsight.ingest.ingest") }
    "quality"  { Invoke-Py @("-m", "claimsight.quality.run_quality") }
    "reporting"{ Invoke-Py @("-m", "claimsight.reporting.build_reporting") }
    "dbt"      { Push-Location dbt\claimsight_dw; try { & $Py -m dbt build } finally { Pop-Location } }
    "excel"    { Invoke-Py @("-m", "claimsight.export.excel_report") }
    "pipeline" {
        Invoke-Py @("-m", "claimsight.pipeline")
    }
    "dashboard"{ & $Py -m streamlit run dashboard\app.py }
    "test"     { Invoke-Py @("-m", "pytest", "-q") }
    "lint"     { Invoke-Py @("-m", "ruff", "check", "src", "tests", "dashboard") }
    "all"      { & $Root\run.ps1 up; & $Root\run.ps1 pipeline; & $Root\run.ps1 dbt; & $Root\run.ps1 reporting; & $Root\run.ps1 excel; & $Root\run.ps1 test }
    default {
        Write-Host "ClaimSight tasks:" -ForegroundColor Cyan
        Write-Host "  setup generate ingest quality dbt reporting pipeline dashboard excel test lint up down all"
    }
}
