<#
OSQAr convenience wrapper for PowerShell (Windows).

Usage:
  .\osqar.ps1 --help

If your execution policy blocks scripts, run:
  powershell -ExecutionPolicy Bypass -File .\osqar.ps1 --help

Preferred (uses Poetry venv if available):
  poetry run python -m tools.osqar_cli --help
#>

$ErrorActionPreference = 'Stop'

# Ensure module resolution works even if invoked from another directory.
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptRoot
try {
    if (Get-Command poetry -ErrorAction SilentlyContinue) {
        & poetry run python -m tools.osqar_cli @args
        exit $LASTEXITCODE
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -m tools.osqar_cli @args
        exit $LASTEXITCODE
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m tools.osqar_cli @args
        exit $LASTEXITCODE
    }

    Write-Error "Could not find 'poetry', 'py', or 'python' on PATH. Install Python (and optionally Poetry) and retry."
    exit 9009
}
finally {
    Pop-Location
}
