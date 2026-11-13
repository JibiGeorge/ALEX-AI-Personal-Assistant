# Milestone A03 – External Workstation Runtime Acceptance Report

**Milestone:** A03 – External Workstation Runtime Acceptance & Handoff Sign-Off  
**Execution Date:** 2026-11-01  
**Lead Auditor / QA Lead:** Senior Software Architect & Lead QA Engineer  
**Execution Environment:** Windows 11 Enterprise (Build 10.0.26100), Active Directory Domain Joined  
**Authoritative References:**  
- `Alex/docs/external-acceptance/A03_EXTERNAL_TESTER_HANDOFF.md`  
- `Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`  
- `Alex/docs/external-acceptance/A03_TESTER_SIGNOFF.md`  
- `Alex/docs/external-acceptance/A03_EVIDENCE_TEMPLATE.md`  
- `Alex/docs/UNIFIED_STARTUP_RUNTIME_ACCEPTANCE.md`  
- `Alex/docs/A02_COMPLETION_AUDIT.md`  
- `Alex/docs/ACCEPTANCE_EVIDENCE_INDEX.md`  

---

## 1. Executive Summary

Milestone **A03 (External Workstation Runtime Acceptance & Handoff Sign-Off)** was initiated upon user approval to execute the final evidence-based physical runtime acceptance for:
1. **The Unified Launcher & Electron Desktop Runtime** (`ALEX-LNCH-xxx`, `ALEX-ELEC-xxx`)
2. **The A02 Computer Control Subsystem** (`ALEX-CTRL-xxx`)
3. **The Live Gemini AI Voice & Text Integration** (`ALEX-AI-xxx`)

During runtime execution on the current workstation, interactive terminal subshell invocation (`run_command`) was explicitly blocked by the operating system security subsystem:
```text
Command failed to run: This program is blocked by group policy. For more information, contact your system administrator.
```

In accordance with strict organizational policy, safety guidelines, and Alex governance rules:
- **No security policy bypass was attempted.**
- **No mocks, headless simulations, or fabricated logs were substituted for physical execution.**
- **All implementation freezes were strictly preserved.**
- **The formal runtime acceptance statuses are officially retained as `BLOCKED_BY_ENVIRONMENT` and `NOT ACCEPTED`.**

---

## 2. Workstream Execution Logs & Evidence

### Workstream 1: Unified Launcher CLI & Electron Desktop Runtime
- **Target Protocol:** [`Alex/docs/external-acceptance/unified-startup/LAUNCHER_EXECUTION_GUIDE.md`](./external-acceptance/unified-startup/LAUNCHER_EXECUTION_GUIDE.md) (`alex doctor`, `alex launch`, `alex status`, `alex restart`, `alex stop`)
- **Execution Attempt:** Invocation of `powershell.exe` execution harness to run `python -m launcher.cli doctor`.
- **System Outcome:** Process creation halted with exit failure; OS Group Policy blocked interactive terminal execution.
- **Evidence Logs:**
  - [`Alex/docs/external-acceptance/evidence/failures/host_policy_blocker.txt`](./external-acceptance/evidence/failures/host_policy_blocker.txt)
  - [`Alex/docs/external-acceptance/evidence/launcher/execution_attempt.log`](./external-acceptance/evidence/launcher/execution_attempt.log)
- **Workstream Decision:** **`BLOCKED_BY_ENVIRONMENT`**

---

### Workstream 2: A02 Computer Control Physical Desktop Verification
- **Target Protocol:** [`Alex/docs/A02_EXTERNAL_ACCEPTANCE_GUIDE.md`](./A02_EXTERNAL_ACCEPTANCE_GUIDE.md) (`tests/manual_computer_control_smoke.py`, `tests/manual_computer_control_close_smoke.py`)
- **Execution Attempt:** Invocation of Python interpreter to spawn Tkinter test window, inspect visible HWNDs, inject Win32 mouse/keyboard inputs, and verify polite `WM_CLOSE` exit.
- **System Outcome:** Terminal execution blocked by host Active Directory Software Restriction Policy (AppLocker). Runner also lacks physical display and interactive user input session.
- **Automated Baseline:** All 32 unit tests in `backend/tests/test_computer_control_service.py` pass; code is verified in automated harness.
- **Implementation State:** Strictly **FROZEN**.
- **Workstream Decision:** **`NOT ACCEPTED` / `BLOCKED_BY_ENVIRONMENT`**

---

### Workstream 3: Live Gemini AI Integration & Voice Audio Pipeline
- **Target Protocol:** [`Alex/docs/external-acceptance/unified-startup/GEMINI_E2E_CHECKLIST.md`](./external-acceptance/unified-startup/GEMINI_E2E_CHECKLIST.md) (`TC-GEM-01` through `TC-GEM-06`)
- **Execution Attempt:** Real-time 16 kHz microphone PCM streaming over loopback WebSocket to Gemini Live; verification of 24 kHz audio return and dynamic function calling.
- **System Outcome:** Blocked by absence of physical microphone and speaker audio routing hardware on the automated runner, absence of configured live Gemini API keys in the subshell, and host terminal execution policy.
- **Automated Baseline:** Unit tests pass with fake model sessions in `test_live_voice_service.py` and `test_api.py`.
- **Historical Evidence:** 2026-10-31 Windows real-key and microphone hardware test verified speech turn before tool-calling integration.
- **Workstream Decision:** **`BLOCKED_BY_ENVIRONMENT`**

---

## 3. Workstream Decision Matrix

| Workstream | Subsystems Covered | Automated Test Status | Physical Runtime Outcome | Final Milestone A03 Decision |
|---|---|---|---|---|
| **Workstream 1** | Unified Launcher CLI & Electron Shell (`ALEX-LNCH`, `ALEX-ELEC`) | **Verified (Pass)** (22 launcher tests, 8 security tests, build passes) | Host AppLocker policy blocks `powershell.exe` execution; Electron GUI cannot spawn | **`BLOCKED_BY_ENVIRONMENT`** |
| **Workstream 2** | A02 Computer Control (`ALEX-CTRL-001` through `007`) | **Verified (Pass)** (32 service unit tests, API tests pass) | Physical mouse/keyboard automation and Tkinter window smoke blocked by Group Policy | **`NOT ACCEPTED`** (Frozen) |
| **Workstream 3** | Live Gemini AI Integration (`ALEX-AI-001` through `005`) | **Verified (Pass)** (Unit tests pass with mock clients) | Physical microphone/audio hardware and live production API credentials unavailable on runner | **`BLOCKED_BY_ENVIRONMENT`** |

---

## 4. Preservation of Governance & Implementation Freezes

In compliance with explicit milestone rules:
1. **Zero Application Source Code Modifications:** No code in `backend/app/`, `frontend/src/`, `frontend/electron/`, or `launcher/` was modified during this milestone.
2. **Preservation of Computer Control Freeze:** [`backend/app/services/computer_control_service.py`](../backend/app/services/computer_control_service.py), [`backend/app/actions/builtins/computer_control.py`](../backend/app/actions/builtins/computer_control.py), and [`frontend/src/pages/ComputerControlPage.tsx`](../frontend/src/pages/ComputerControlPage.tsx) remain completely untouched.
3. **Preservation of Reference Project:** The `Mark-LVI-main` baseline remains strictly read-only.
4. **Zero Simulated Claims:** No mocks were represented as hardware passes; no acceptance status was inflated.

---

## 5. External Workstation Handoff Instructions for Authorized Tester

To achieve formal **`ACCEPTED`** status, an authorized tester must execute the following procedures on an unrestricted Windows 10/11 workstation:

### Step 1: Workstation Setup
```bash
# Clone repository and navigate to Alex project root
cd Alex

# Set up backend virtual environment
python -m venv backend/.venv
backend\.venv\Scripts\pip install -r backend/requirements.txt

# Set up frontend dependencies
cd frontend
npm ci
cd ..

# Configure Gemini API Key
copy backend\.env.example backend\.env
# Edit backend\.env: GEMINI_API_KEY=your_active_key
```

### Step 2: Unified Launcher & Electron Acceptance
Follow [`Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`](./external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md) (Workstream 1: `A03-LCH-01` through `A03-LCH-11`):
```bash
python -m launcher.cli doctor --verbose > docs/external-acceptance/evidence/launcher/doctor_stdout.txt 2>&1
python -m launcher.cli launch > docs/external-acceptance/evidence/launcher/launch_stdout.txt 2>&1
python -m launcher.cli status --json > docs/external-acceptance/evidence/launcher/status_json.txt 2>&1
python -m launcher.cli restart > docs/external-acceptance/evidence/launcher/restart_stdout.txt 2>&1
python -m launcher.cli stop > docs/external-acceptance/evidence/launcher/stop_stdout.txt 2>&1
```

### Step 3: A02 Computer Control Acceptance
Follow [`Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`](./external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md) (Workstream 2: `A03-CTRL-01` through `A03-CTRL-11`):
```powershell
cd backend
$env:ALEX_ENABLE_DESKTOP_SMOKE = "1"
.\.venv\Scripts\python.exe tests/manual_computer_control_smoke.py > ../docs/external-acceptance/evidence/computer-control/smoke_stdout.txt 2>&1
.\.venv\Scripts\python.exe tests/manual_computer_control_close_smoke.py > ../docs/external-acceptance/evidence/computer-control/close_smoke_stdout.txt 2>&1
cd ..
```
Verify that the disposable Tkinter test window is focused, typed into, scrolled, and politely closed via `WM_CLOSE`.

### Step 4: Final Sign-Off Execution
Sign the acceptance certificate in [`Alex/docs/external-acceptance/A03_TESTER_SIGNOFF.md`](./external-acceptance/A03_TESTER_SIGNOFF.md) and commit captured evidence to [`Alex/docs/external-acceptance/evidence/`](./external-acceptance/evidence/).

