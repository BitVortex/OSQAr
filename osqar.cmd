@echo off
setlocal EnableExtensions

REM OSQAr convenience wrapper for Windows.
REM
REM Usage (PowerShell or cmd.exe):
REM   .\osqar.cmd --help
REM
REM Preferred (uses Poetry venv if available):
REM   poetry run python -m tools.osqar_cli --help

where poetry >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  poetry run python -m tools.osqar_cli %*
  exit /b %ERRORLEVEL%
)

REM Fallback to invoking the module directly (expects deps installed in the active env).
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -m tools.osqar_cli %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python -m tools.osqar_cli %*
  exit /b %ERRORLEVEL%
)

echo ERROR: Could not find 'poetry', 'py', or 'python' on PATH. 1>&2
echo Install Python (and optionally Poetry) and retry. 1>&2
exit /b 9009
