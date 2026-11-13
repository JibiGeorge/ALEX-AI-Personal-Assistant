# Alex Desktop Assistant — Setup & Installation Guide

**Document Version:** 1.0  
**Last Updated:** 2026-11-03  
**Status:** Authoritative Development Reference  
**Cross-References:** [`./DEVELOPMENT_GUIDE.md`](./DEVELOPMENT_GUIDE.md), [`./TESTING.md`](./TESTING.md), [`../../README.md`](../../README.md)

---

## 1. System Requirements

### Supported Operating Systems
- **Windows (Target Platform):** Windows 10 (22H2+) or Windows 11 (23H2/24H2) 64-bit.
- **macOS (Development Environment):** macOS 14+ (Apple Silicon or Intel).
- **Linux (Development Environment):** Ubuntu 22.04+, Debian 12+, or Fedora 39+.

### Toolchain Prerequisites
- **Python:** `>= 3.11` (Python 3.11 or 3.12 64-bit recommended; include `venv` and `pip`).
- **Node.js & npm:** Node.js `>= 20.0.0` (LTS) and npm `>= 9.0.0`.
- **Git:** Git `>= 2.40` for version control.

---

## 2. Step-by-Step Installation

### Step 1: Clone the Repository
```bash
git clone <AUTHORITATIVE_REPO_URL> Alex
cd Alex
```

### Step 2: Backend Virtual Environment Setup
From the repository root:

**On Windows (PowerShell):**
```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

**On macOS / Linux:**
```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

### Step 3: Frontend Dependencies Setup
```bash
cd frontend
npm install
cd ..
```

---

## 3. Pre-Flight Verification

Alex includes a built-in diagnostic doctor command to verify all runtimes, packages, and loopback ports before launching:

```bash
# Using the Alex CLI
./alex doctor

# Or using the Python module
python -m launcher.cli doctor --verbose
```

Expected output:
```text
[PASS] Python Runtime (Python 3.11.x)
[PASS] Virtual Environment (backend/.venv active)
[PASS] Python Dependencies (FastAPI, Uvicorn, Pydantic, Keyring, etc.)
[PASS] Node.js Runtime (v20.x)
[PASS] npm Package Manager (v10.x)
[PASS] Frontend Dependencies (node_modules present)
[PASS] Loopback Ports (8765, 5173 available)
```

---

## 4. Running the Application

### Method A: Unified Launcher (Recommended)
Orchestrates backend sidecar, frontend server, and Electron desktop window in one command:
```bash
./alex launch
```

Useful launcher options:
- `./alex launch --no-electron`: Starts backend and frontend in headless/web browser mode at `http://127.0.0.1:5173`.
- `./alex launch --port 8900`: Overrides backend loopback port.
- `./alex launch --frontend-port 5180`: Overrides frontend Vite port.
- `./alex status`: Displays health, assigned ports, and process IDs.
- `./alex stop`: Gracefully terminates all Alex child processes.

### Method B: Standalone Component Execution

**Backend Only:**
```bash
# From repository root with virtualenv active
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8765
```

**Frontend Only (Web Dev):**
```bash
cd frontend
npm run dev:vite
```

**Electron Only (Connecting to existing backend):**
```bash
cd frontend
npm run dev:electron
```

---

## 5. Configuration & Environment Variables

Copy the example environment configuration:
```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `ALEX_PYTHON` | Path to preferred Python executable | Auto-discovered (`backend/.venv`) |
| `ALEX_DATA_DIR` | Custom user application data directory | `%APPDATA%/Alex` or `~/.alex` |
| `ALEX_LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `ALEX_API_TOKEN` | Custom backend bearer token | 32-byte secure random string |
| `ALEX_BACKEND_PORT` | Loopback port for backend API | `8765` |
| `ALEX_FRONTEND_URL` | Custom frontend URL for Electron window | `http://127.0.0.1:5173/` |
| `GEMINI_API_KEY` | Google Gemini API key (fallback if keyring empty) | None (Store via `keyring`) |

> [!TIP]
> Always prefer storing API keys in the OS Credential Manager (`keyring`) rather than plaintext `.env` files:
> ```bash
> python -c "import keyring; keyring.set_password('alex', 'gemini_api_key', 'AIzaSy...')"
> ```

---

## 6. Packaging & Production Builds

### Step 1: Package Python Sidecar with PyInstaller
```powershell
# Windows PowerShell
.\scripts\build-backend.ps1
```
This compiles the Python backend into a standalone executable under `frontend/dist-backend/`.

### Step 2: Package Desktop Electron Application
```bash
cd frontend
npm run build
npm run dist
```
This produces the platform installer (NSIS installer `.exe` for Windows, `.dmg` for macOS, or `.AppImage` for Linux) in `frontend/dist/`.

