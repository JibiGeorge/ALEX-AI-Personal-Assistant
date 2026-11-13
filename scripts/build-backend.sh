#!/usr/bin/env bash
# ==============================================================================
# build-backend.sh — Automated cross-platform packaging script for Alex backend
# Compiles the Python backend into a standalone PyInstaller sidecar binary.
# Supported platforms: macOS (Darwin) and Linux.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"

# Detect Python interpreter
if [[ -n "${ALEX_PYTHON:-}" ]]; then
  PYTHON="${ALEX_PYTHON}"
elif [[ -x "${BACKEND_DIR}/.venv/bin/python3" ]]; then
  PYTHON="${BACKEND_DIR}/.venv/bin/python3"
elif [[ -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
  PYTHON="${BACKEND_DIR}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  PYTHON="python"
fi

echo "==> Using Python interpreter: ${PYTHON}"
"${PYTHON}" --version

# Verify PyInstaller is installed
if ! "${PYTHON}" -m PyInstaller --version >/dev/null 2>&1; then
  echo "ERROR: PyInstaller is not installed in ${PYTHON} environment."
  echo "Run: ${PYTHON} -m pip install pyinstaller"
  exit 1
fi

echo "==> Building standalone sidecar with PyInstaller..."
cd "${BACKEND_DIR}"

# Confine PyInstaller cache and build artifacts to workspace
export PYINSTALLER_CONFIG_DIR="${BACKEND_DIR}/.cache/pyinstaller"
mkdir -p "${PYINSTALLER_CONFIG_DIR}"

"${PYTHON}" -m PyInstaller \
  --noconfirm \
  --clean \
  --onedir \
  --name alex-backend \
  --paths . \
  --workpath "${BACKEND_DIR}/build" \
  --distpath "${BACKEND_DIR}/dist" \
  --collect-all keyring \
  --collect-all google.genai \
  --collect-all openwakeword \
  --collect-all piper \
  --collect-all faster_whisper \
  --collect-all yt_dlp \
  app/main.py

EXECUTABLE="${BACKEND_DIR}/dist/alex-backend/alex-backend"
if [[ -f "${EXECUTABLE}" ]]; then
  chmod +x "${EXECUTABLE}"
  echo "==> Successfully created standalone binary: ${EXECUTABLE}"
else
  echo "ERROR: Expected binary not found at ${EXECUTABLE}"
  exit 1
fi

echo "==> Running sidecar verification..."
node "${SCRIPT_DIR}/verify-sidecar.mjs"

echo "==> Alex backend packaging completed successfully."
