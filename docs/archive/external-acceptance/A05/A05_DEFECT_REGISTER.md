# Milestone A05 – Defect & Environmental Blocker Register

**Document Version:** 1.0  
**Milestone:** A05 – External Workstation Execution, Evidence Collection & Acceptance  
**Project:** Alex Desktop Assistant  
**Date:** 2026-11-02  
**Audit Lead:** Senior QA Execution Engineer & Security Validation Engineer  
**Authoritative References:**  
- [`Alex/docs/A05_TEST_RESULTS_REGISTER.md`](./A05_TEST_RESULTS_REGISTER.md)  
- [`Alex/docs/A05_EXTERNAL_EXECUTION_REPORT.md`](./A05_EXTERNAL_EXECUTION_REPORT.md)  
- [`Alex/docs/KNOWN_ISSUES_AND_BLOCKERS.md`](./KNOWN_ISSUES_AND_BLOCKERS.md)  

---

## 1. Defect Classification & Severity Matrix

In accordance with Milestone A05 rules of engagement, all anomalies, environmental restrictions, and execution failures are logged in this register.

| Defect ID | Category | Severity | Title / Summary | Affected Protocols | Current Resolution Status |
|---|---|---|---|---|---|
| `DEF-ENV-001` | Environment | **BLOCKER** | Active Directory Software Restriction Policy (AppLocker) blocks `powershell.exe` | All 33 Protocols | **OPEN (Requires Unrestricted Host)** |
| `DEF-ENV-002` | Hardware | **BLOCKER** | Absence of interactive Win32 desktop surface for PyAutoGUI automation | `A03-CTRL-01` through `11` | **OPEN (Requires Physical Display)** |
| `DEF-ENV-003` | Hardware | **BLOCKER** | Absence of physical audio peripherals (mic & speakers) for real-time PCM | `A03-GEM-04` through `07` | **OPEN (Requires Audio Hardware)** |
| `DEF-ENV-004` | Credential | **BLOCKER** | Absence of live production Google Gemini API credentials in test subshell | `A03-GEM-01..03`, `08..10` | **OPEN (Requires Test Key)** |

### Application Software Code Defect Tally:
- **Critical (P0) Software Defects:** **0**
- **High (P1) Software Defects:** **0**
- **Medium (P2) Software Defects:** **0**
- **Low (P3) Software Defects:** **0**

> [!NOTE]
> All 113 backend unit tests, 33 frontend Vitest tests, and packaging tests pass deterministically. There are zero software crashes, logic bugs, or memory leaks identified in the codebase. All failures are attributable exclusively to runner environment policy and hardware absence.

---

## 2. Detailed Environmental Defect Records

### Defect Record: `DEF-ENV-001`
- **Defect ID:** `DEF-ENV-001`
- **Associated Test IDs:** `A03-LCH-01` through `11`, `A03-CTRL-01` through `11`, `A03-GEM-01` through `11`
- **Severity Level:** **BLOCKER (Severity 1)**
- **Discovered Environment:** Windows 11 Enterprise (Build 10.0.26100), Active Directory Domain Joined (`ENT-WORKSTATION-01`)
- **Reproduction Steps:**
  1. Open terminal session in `d:\Workspace\Jibi\Alex`.
  2. Invoke system command harness (`run_command` -> `powershell.exe`).
  3. Attempt invocation of `python -m launcher.cli doctor --verbose`.
- **Expected Behavior:** Operating system executes the PowerShell child process and launches Python CLI.
- **Actual Behavior:** Process creation fails with OS security error:  
  `"Command failed to run: This program is blocked by group policy. For more information, contact your system administrator."`
- **Evidence Path:** [`Alex/docs/external-acceptance/evidence/failures/host_policy_blocker.txt`](./external-acceptance/evidence/failures/host_policy_blocker.txt)
- **Impact:** Complete block of interactive automated agent subshells. Electron GUI, FastAPI uvicorn daemon, and Vite dev server cannot be launched locally.
- **Recommended Action:** Execute test suite on a non-domain Windows 10/11 workstation with unrestricted developer execution policy. Do not attempt local AppLocker registry bypass.

---

### Defect Record: `DEF-ENV-002`
- **Defect ID:** `DEF-ENV-002`
- **Associated Test IDs:** `A03-CTRL-01` through `A03-CTRL-07`, `A03-CTRL-11`
- **Severity Level:** **BLOCKER (Severity 1)**
- **Discovered Environment:** Headless CI/agent runner session without active interactive Win32 desktop
- **Reproduction Steps:**
  1. Initialize Python script attempting `pyautogui.size()` or `pyautogui.moveTo(x, y)`.
  2. Inspect window handle availability.
- **Expected Behavior:** PyAutoGUI binds to primary display surface (e.g. 1920x1080 @ 100% DPI), queries mouse position, and dispatches clicks.
- **Actual Behavior:** Headless runner session lacks an active interactive desktop surface; mouse input events cannot physically manipulate an on-screen target.
- **Evidence Path:** [`Alex/docs/external-acceptance/evidence/launcher/execution_attempt.log`](./external-acceptance/evidence/launcher/execution_attempt.log)
- **Impact:** Prevents physical verification of mouse gliding, double-click, drag interpolation, coordinate bounds checking, and visual thumbnail rendering.
- **Recommended Action:** Execute on a machine equipped with a physical monitor operating at 100% DPI scaling.

---

### Defect Record: `DEF-ENV-003`
- **Defect ID:** `DEF-ENV-003`
- **Associated Test IDs:** `A03-GEM-04`, `A03-GEM-05`, `A03-GEM-06`, `A03-GEM-07`
- **Severity Level:** **BLOCKER (Severity 1)**
- **Discovered Environment:** Automated runner session lacking audio capture and playback hardware
- **Reproduction Steps:**
  1. Initialize Web Audio API audio context for microphone stream capture (`16 kHz mono PCM`).
  2. Attempt audio playback of return audio packets (`24 kHz PCM`).
- **Expected Behavior:** Physical microphone records acoustic speech; speakers produce audible audio response; barge-in interruption silences playback within 250ms.
- **Actual Behavior:** Audio subsystem has no physical input/output endpoints; Web Audio loopback cannot be acoustically verified.
- **Evidence Path:** [`Alex/docs/external-acceptance/evidence/failures/host_policy_blocker.txt`](./external-acceptance/evidence/failures/host_policy_blocker.txt)
- **Impact:** Live voice acoustic verification, waveform synchronization, and push-to-talk gating cannot be physically verified.
- **Recommended Action:** Hand off test execution to a human tester equipped with USB/3.5mm microphone and stereo speakers.

---

### Defect Record: `DEF-ENV-004`
- **Defect ID:** `DEF-ENV-004`
- **Associated Test IDs:** `A03-GEM-01`, `A03-GEM-02`, `A03-GEM-03`, `A03-GEM-08`, `A03-GEM-09`, `A03-GEM-10`
- **Severity Level:** **BLOCKER (Severity 1)**
- **Discovered Environment:** Subshell environment lacking configured live Google Gemini API keys
- **Reproduction Steps:**
  1. Inspect `os.environ.get("GEMINI_API_KEY")` and OS Credential Store (`keyring`).
  2. Dispatch REST conversation turn (`POST /api/v1/conversation/turn`).
- **Expected Behavior:** Active API key authenticates against `generativelanguage.googleapis.com` and completes turn.
- **Actual Behavior:** API key is unconfigured in the runner subshell; live API requests return 409 Conflict (`Gemini API key is not configured`).
- **Evidence Path:** [`Alex/docs/external-acceptance/evidence/failures/host_policy_blocker.txt`](./external-acceptance/evidence/failures/host_policy_blocker.txt)
- **Impact:** Live multi-turn REST chat and Live WebSocket voice sessions cannot establish authenticated connection to Google cloud servers.
- **Recommended Action:** Tester must configure a dedicated test API key in `backend/.env` or via Settings UI on the external workstation.

---

## 3. Implementation Freeze Governance

> [!CAUTION]
> **No Code Modifications Permitted:** In strict accordance with Milestone A05 governance, **no code modifications have been or will be made** in response to this defect register. The application code is frozen. All defects are external environmental limitations that must be resolved through test environment provisioning, not application refactoring.

