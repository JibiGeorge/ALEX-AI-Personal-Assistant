# Milestone A08 – External QA Workstation Handoff Package

**Document Version:** 1.0  
**Milestone:** A08 – External Workstation Readiness & Runtime Execution Gate  
**Target Application Version:** `0.1.0`  
**Approved Baseline:** `SNAPSHOT_v0.1.0-20261102`  
**Release Gate Status:** `NOT_AUTHORIZED_FOR_RELEASE` (Release Hold Active)  
**Authoritative References:**  
- [`Alex/docs/A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md`](./A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md)  
- [`Alex/docs/A08_EXECUTION_ENTRY_CRITERIA.md`](./A08_EXECUTION_ENTRY_CRITERIA.md)  
- [`Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`](./external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md)  
- [`Alex/docs/external-acceptance/A03_TESTER_SIGNOFF.md`](./external-acceptance/A03_TESTER_SIGNOFF.md)  

---

## 1. Overview & Handoff Purpose

This document serves as the master instructional handoff kit for the **independent external QA test engineer** assigned to perform the physical runtime acceptance of the Alex AI Desktop Assistant.

Because corporate development workstations (e.g., `ENT-WORKSTATION-01`) enforce Active Directory AppLocker policies that prevent subshell process creation and lack physical audio/display hardware, this handoff package facilitates the seamless setup, validation, execution, and sign-off on an authorized external Windows 11 workstation.

---

## 2. External Workstation Provisioning Requirements

The external testing machine must satisfy the following physical profile:
- **Operating System:** Windows 11 64-bit (Version 23H2 or 24H2) standalone/workgroup installation (outside enterprise GPO/AppLocker).
- **Session:** Interactive Win32 user desktop session (`winsta0\default`, Session ID >= 1).
- **Display:** Physical 1920x1080 display (100% DPI scaling recommended).
- **Peripherals:** Standard hardware keyboard, two-button mouse, physical 16kHz PCM microphone, and stereo playback speakers/headphones.
- **Network:** Direct internet connectivity with open outbound TLS 443 egress to `generativelanguage.googleapis.com`.
- **Runtime Toolchains:**
  - Python 3.11.x (or 3.12.x 64-bit) with `venv` module.
  - Node.js >= 18.0.0 (v20 LTS recommended) and npm >= 9.0.0.

---

## 3. Step-by-Step Setup & Baseline Verification

### Step 1: Repository Clone & Commit SHA Recording
Clone the authoritative repository onto the external workstation:
```powershell
git clone <AUTHORITATIVE_REPO_URL> Alex-Testing
cd Alex-Testing/Alex
```
Verify working tree and record the exact 40-character Git commit SHA:
```powershell
git status
git rev-parse HEAD
```
*Requirement:* The working tree must be 100% clean, and the commit SHA must match `SNAPSHOT_v0.1.0-20261102`. Record this SHA in [`A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md`](./A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md).

### Step 2: Backend Virtual Environment Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```
Verify automated unit test baseline passes locally:
```powershell
pytest tests/
```
*Expected Output:* 113 passed, 1 skipped (symlink test on Windows), 0 failed.

### Step 3: Frontend & Electron Environment Setup
```powershell
cd ..\frontend
npm install
npm test
```
*Expected Output:* 33 passed, 0 failed across all 8 Vitest suites.

### Step 4: Secure Keyring Credential Provisioning
Provision a dedicated, billed Google Gemini API test key in the Windows Credential Manager:
```powershell
python -c "import keyring; keyring.set_password('alex', 'gemini_api_key', 'AIzaSyYourActualTestKeyHere')"
```
Verify that the key is stored and readable:
```powershell
python -c "import keyring; print('Key configured:', bool(keyring.get_password('alex', 'gemini_api_key')))"
```
*Expected Output:* `Key configured: True`.

---

## 4. Phase 1 Verification: Workstation Readiness Audit

Before running any application processes, the tester must complete and sign:
[`Alex/docs/A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md`](./A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md)

Confirm all 12 checks pass. Only proceed to Phase 2 if the formal outcome is **`SUITABLE_FOR_TESTING`**.

---

## 5. Phase 2 Execution: The 33 Acceptance Protocols

The tester must systematically execute all 33 protocols defined in:
[`Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`](./external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md)

### Execution Sequencing:
1. **Workstream 1 (Unified Launcher & Electron Shell):** Execute `A03-LCH-01` through `A03-LCH-11`.
   - Command: `python -m launcher.cli doctor`
   - Command: `python -m launcher.cli launch`
   - Verify Electron window renders cyan HUD avatar at `http://127.0.0.1:5173`.
   - Test port fallback, `--headless`, `alex status --json`, and graceful shutdown (`alex stop`).
2. **Workstream 2 (A02 Computer Control):** Execute `A03-CTRL-01` through `A03-CTRL-11`.
   - Set smoke test environment variable: `$env:ALEX_ENABLE_DESKTOP_SMOKE = "1"`
   - Open Computer Control page in UI; toggle permission switch ON.
   - Run guarded smoke script: `python -m launcher.cli test-control` (or `python tests/manual_computer_control_smoke.py`).
   - Verify disposable test window is focused, typed into, and closed via `WM_CLOSE`.
   - Test latched emergency stop button (immediate queue abort).
3. **Workstream 3 (Gemini Live AI Voice):** Execute `A03-GEM-01` through `A03-GEM-11`.
   - Speak spoken prompt into physical microphone: *"Hello Alex, can you hear me?"*
   - Verify voice waveform responds in HUD avatar and assistant answers via speakers.
   - Speak during assistant response to verify barge-in interruption.
   - Speak tool proposal prompt: *"Please create a note in my memory about project status."*
   - Verify proposal card appears in UI requiring physical user approval click.

---

## 6. Evidence Collection & Directory Structure

All genuine execution logs, screenshots, and audio samples must be stored in:
```
Alex/docs/external-acceptance/evidence/
├── launcher/
│   ├── a08_doctor_output.txt
│   ├── a08_launch_success.log
│   ├── a08_status_json.txt
│   └── a08_electron_window_screenshot.png
├── computer-control/
│   ├── a08_control_permission_toggle.png
│   ├── a08_proposal_queue_approval.png
│   ├── a08_smoke_script_execution.log
│   └── a08_emergency_stop_latched.png
├── gemini-live/
│   ├── a08_voice_session_handshake.log
│   ├── a08_voice_waveform_capture.png
│   ├── a08_barge_in_latency.txt
│   └── a08_multimodal_flow_trace.log
└── failures/
    └── (Any defect reproduction logs if encountered)
```

> [!CAUTION]
> **Redaction Requirement:**  
> Verify all files are sanitized. Never commit raw API keys (`AIzaSy...`) or plaintext bearer tokens to git.

---

## 7. Defect Escalation & Tester Sign-Off

1. **Defects Encountered:** If a protocol fails, log the defect in `Alex/docs/A08_DEFECT_REGISTER.md` with reproducible steps and evidence.
2. **Milestone Completion:** Upon completing all 33 protocols, complete the signed certificate in:
   [`Alex/docs/external-acceptance/A03_TESTER_SIGNOFF.md`](./external-acceptance/A03_TESTER_SIGNOFF.md)
3. **Submission:** Notify the Release Acceptance Coordinator and Technical PM for formal release authorization review.

