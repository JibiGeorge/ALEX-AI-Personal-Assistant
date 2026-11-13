# Alex – External Tester Setup & Workstation Preparation Guide

**Document:** `TESTER_SETUP.md`  
**Purpose:** Pre-flight configuration and hardware environment checklist for external acceptance testers.

---

## 1. Authorized Workstation Profile Template

The tester must record their testing workstation hardware and software specifications below prior to beginning acceptance tests:

| Parameter | Recommended Specification | Tester Recorded Value |
|---|---|---|
| **Operating System** | Windows 10/11 64-bit (Build 19045+ or 22621+) | *(e.g. Windows 11 Pro 23H2 Build 22631.4317)* |
| **User Privileges** | Standard User or Local Administrator | *(Must NOT be restricted by AppLocker/SRP)* |
| **Primary Terminal** | Windows Command Prompt (`cmd.exe`) / Git Bash | *(Specify terminal used)* |
| **PowerShell Version** | PowerShell 5.1+ or PowerShell 7+ | *(e.g. 5.1.22621)* |
| **Python Version** | Python 3.11 or newer (64-bit) | *(e.g. Python 3.11.9)* |
| **Node.js Version** | Node.js 20.x LTS or 22.x LTS | *(e.g. v20.18.0)* |
| **npm Version** | npm 10.x or newer | *(e.g. 10.8.2)* |
| **Primary Display Resolution** | 1920x1080 or higher | *(e.g. 1920x1080)* |
| **Windows Display Scaling** | 100% or 125% recommended | *(e.g. 100%)* |
| **Loopback Interface** | `127.0.0.1` and `localhost` unblocked | *(Confirmed)* |

---

## 2. Environment Preparation Instructions

From the root of the `Alex/` repository:

### Step 2.1: Python Virtual Environment Setup
Ensure Python 3.11+ is installed and available in your PATH:

**Windows Command Prompt (`cmd.exe`):**
```cmd
cd /d D:\Workspace\Jibi\Alex
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

**Git Bash / MINGW64:**
```bash
cd /d/Workspace/Jibi/Alex
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install --upgrade pip
backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
```

### Step 2.2: Node.js & Electron Dependencies Setup
Install the React, Vite, Tailwind CSS, and Electron dependencies:

```bash
cd /d/Workspace/Jibi/Alex
npm --prefix frontend install
```

Verify that `frontend/node_modules/electron` exists and is functional.

### Step 2.3: Environment Files Verification
Confirm the presence of all three required local configuration files:
1. Root configuration: [`.env`](file:///d:/Workspace/Jibi/Alex/.env)
   * Verify default loopback settings (`ALEX_BACKEND_HOST=127.0.0.1`, `ALEX_BACKEND_PORT=8765`, `ALEX_FRONTEND_URL=http://127.0.0.1:5173/`).
2. Backend configuration: [`backend/.env`](file:///d:/Workspace/Jibi/Alex/backend/.env)
   * Verify `ALEX_LOG_LEVEL=INFO`.
3. Frontend configuration: [`frontend/.env`](file:///d:/Workspace/Jibi/Alex/frontend/.env)
   * Verify `VITE_PORT=5173` and `VITE_HOST=127.0.0.1`.

> [!NOTE]
> If testing Gemini Live voice interaction, paste a valid Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) into `GEMINI_API_KEY=` in `.env` (or configure it interactively in the Alex Setup drawer). For launcher and desktop UI lifecycle tests, an API key is optional.

---

## 3. CLI Command Configuration

Alex provides multiple equivalent methods to invoke the unified launcher:

### Option A: Direct Command Prompt Wrapper (Recommended on Windows)
Run from the `Alex/` directory:
```cmd
alex.cmd doctor
alex.cmd launch
```

### Option B: Git Bash Wrapper (Recommended on Bash)
Run from the `Alex/` directory:
```bash
./alex doctor
./alex launch
```

### Option C: PATH Integration
Add the `Alex/bin` directory to your system or session PATH:
```cmd
set PATH=D:\Workspace\Jibi\Alex\bin;%PATH%
alex doctor
alex launch
```

---

## 4. Pre-Flight Diagnostic Check

Execute the built-in system doctor to verify environment readiness before starting runtime acceptance:

```bash
alex doctor --verbose
```

### Expected Doctor Output
```text
  Alex Desktop Assistant v0.1.0 — System Doctor Diagnostic

  [PASS] Operating System         Windows 11 (AMD64)
  [PASS] Python Runtime           Python 3.11.x (backend\.venv\Scripts\python.exe)
  [PASS] Node.js Runtime          v20.x.x (node.exe)
  [PASS] npm Package Manager      v10.x.x (npm.cmd)
  [PASS] Virtual Environment      Found backend/.venv
  [PASS] Backend Packages         10/10 required packages verified
  [PASS] Frontend Dependencies    node_modules with Vite and Electron verified
  [PASS] Backend Port 8765        Port is available
  [PASS] Frontend Port 5173       Port is available
  [PASS] Credential Store         Available (Windows)

  ────────────────────────────────────────────────────────────────────────
  ✔ All checks passed: 10/10 checks verified. System is ready.
```

### Remediation Guidance
* If **Backend Packages** fail: Re-run `pip install -r backend/requirements.txt`.
* If **Frontend Dependencies** fail: Re-run `npm --prefix frontend install`.
* If **Backend Port** or **Frontend Port** shows `[WARN]`: The launcher will automatically reassign available ports upon launch, but you can also terminate conflicting processes.
* Save the full doctor stdout output to [`evidence/launcher/doctor_stdout.txt`](./evidence/launcher/).

