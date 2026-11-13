# Alex Unified CLI Launcher for PowerShell
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$LauncherArgs
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

$Python = if ($env:ALEX_PYTHON) {
    $env:ALEX_PYTHON
} elseif (Test-Path (Join-Path $ProjectRoot "backend\.venv\Scripts\python.exe")) {
    Join-Path $ProjectRoot "backend\.venv\Scripts\python.exe"
} else {
    "python"
}

$env:PYTHONPATH = "$ProjectRoot;$env:PYTHONPATH"
& $Python -m launcher.cli $LauncherArgs
exit $LASTEXITCODE

