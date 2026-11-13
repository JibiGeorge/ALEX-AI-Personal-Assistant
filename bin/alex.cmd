@echo off
REM Alex Unified CLI Launcher for Windows
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

REM Discover Python interpreter
if defined ALEX_PYTHON (
    set "PYTHON=%ALEX_PYTHON%"
) else if exist "%PROJECT_ROOT%\backend\.venv\Scripts\python.exe" (
    set "PYTHON=%PROJECT_ROOT%\backend\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"
"%PYTHON%" -m launcher.cli %*
exit /b !ERRORLEVEL!

