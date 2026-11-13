$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
$python = if ($env:ALEX_PYTHON) {
    $env:ALEX_PYTHON
}
elseif (Test-Path $venvPython) {
    $venvPython
}
else {
    "python"
}

Push-Location $backend
try {
    & $python -m PyInstaller --noconfirm --clean --onedir `
        --name alex-backend `
        --paths . `
        --collect-all keyring `
        --collect-all google.genai `
        --collect-all openwakeword `
        --collect-all piper `
        --collect-all faster_whisper `
        --collect-all yt_dlp `
        app\main.py
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
