# Milestone A07 – Defect & Blocker Register

**Document Version:** 1.0  
**Milestone:** A07 – Final External Workstation Execution & Production Release Acceptance  
**Register Date:** 2026-11-02T10:48:30+05:30  
**Evaluator:** Senior QA Execution Engineer, Security Validation Engineer, and Defect Manager  
**Approved Baseline:** `SNAPSHOT_v0.1.0-20261102` (Application Version `0.1.0`)  
**Authoritative References:**  
- [`Alex/docs/A07_WORKSTATION_ATTESTATION_REPORT.md`](./A07_WORKSTATION_ATTESTATION_REPORT.md)  
- [`Alex/docs/A07_TEST_RESULTS_REGISTER.md`](./A07_TEST_RESULTS_REGISTER.md)  
- [`Alex/docs/external-acceptance/evidence/failures/a07_suitability_blocker.txt`](./external-acceptance/evidence/failures/a07_suitability_blocker.txt)  

---

## 1. Executive Summary & Defect Taxonomy

Under **Section 6 and 7** of the Milestone A07 governance charter:
- **Application Software Defects** must be kept strictly separate from **Environmental Blockers**.
- A software defect represents a bug, regression, crash, or logic error within the application codebase (`backend/`, `frontend/`, `launcher/`).
- An environmental blocker represents an external operating system policy, absent peripheral hardware, or missing credential prerequisite on the test workstation.

### Summary Statistics
- **Application Software Defects Identified in Executed Tests:** **0 Defects** (Physical runtime defects unassessed due to environmental block)
- **Environmental Blockers:** **5 Blockers** (All 5 categorized as Release Blockers for physical testing)

---

## 2. Software Defect Audit

No software defects were identified by the automated test suites actually executed (146 passed tests) or static code inspection. Physical runtime defects cannot be evaluated because physical testing was blocked by the environment:
- All 146 automated tests pass with 100% determinism.
- TypeScript compilation passes with zero errors across both main renderer (`tsconfig.json`) and Electron main process (`tsconfig.electron.json`).
- Vite production build packages cleanly.
- Python linting (`ruff`) and static imports are clean.

---

## 3. Environmental Blocker Register

### `DEF-A07-001`: Active Directory AppLocker Restricts Shell Process Creation
- **Severity:** Critical (Release Blocker)
- **Category:** Environmental / Operating System Security Policy
- **Impacted Workstreams:** Workstream 1 (Unified Launcher), Workstream 2 (Computer Control), Workstream 3 (Gemini Live)
- **Impacted Protocols:** All 33 protocols (`A03-LCH-01..11`, `A03-CTRL-01..11`, `A03-GEM-01..11`)
- **Observed Behavior:** Spawning `powershell.exe` fails immediately with OS message:
  ```
  Command failed to run: This program is blocked by group policy. For more information, contact your system administrator.
  ```
- **Root Cause:** Workstation `ENT-WORKSTATION-01` is enrolled in an enterprise Active Directory domain. Group Policy Objects enforce an executable path rule blocking non-interactive child process instantiation of PowerShell.
- **Evidence Reference:** [`Alex/docs/external-acceptance/evidence/failures/a07_suitability_blocker.txt`](file:///d:/Workspace/Jibi/Alex/docs/external-acceptance/evidence/failures/a07_suitability_blocker.txt)
- **Remediation Requirement:** Execute test suite on a dedicated, standalone, non-domain-joined Windows 11 workstation or configure an authorized bypass rule for the designated test user account.

---

### `DEF-A07-002`: Headless Runner Context Lacks Interactive Win32 Desktop Station
- **Severity:** Critical (Release Blocker)
- **Category:** Environmental / Display & Window Management
- **Impacted Workstreams:** Workstream 1 (Electron GUI), Workstream 2 (A02 Computer Control)
- **Impacted Protocols:** `A03-LCH-02`, `A03-LCH-08`, `A03-CTRL-01` through `A03-CTRL-11`
- **Observed Behavior:** Desktop coordinate querying (`pyautogui.size()`), window enumeration (`EnumWindows`), window focus (`SetForegroundWindow`), and Tkinter GUI instantiation fail due to absent interactive window station (`winsta0\default`).
- **Root Cause:** Background automation service runs in Session 0 or non-interactive service station without an allocated physical monitor canvas.
- **Remediation Requirement:** Log in to a physical Windows 11 desktop console session with a physical display running at 1920x1080 resolution.

---

### `DEF-A07-003`: Absence of Physical Multimedia Audio Hardware
- **Severity:** Critical (Release Blocker)
- **Category:** Environmental / Peripheral Hardware
- **Impacted Workstreams:** Workstream 3 (Gemini Live AI Voice)
- **Impacted Protocols:** `A03-GEM-01` through `A03-GEM-06`, `A03-GEM-09`, `A03-GEM-11`
- **Observed Behavior:** PyAudio / sounddevice cannot open input audio streams; no physical 16kHz PCM microphone or stereo playback speakers exist on the runner.
- **Root Cause:** Virtualized or headless server host does not provide physical audio input/output endpoints.
- **Remediation Requirement:** Connect a physical USB microphone and headphones/speakers to the authorized test workstation.

---

### `DEF-A07-004`: Enterprise Network Proxy Blocks Outbound WebSocket to Gemini Live
- **Severity:** High (Release Blocker)
- **Category:** Environmental / Network Infrastructure
- **Impacted Workstreams:** Workstream 3 (Gemini Live AI Voice)
- **Impacted Protocols:** `A03-GEM-01` through `A03-GEM-07`, `A03-GEM-11`
- **Observed Behavior:** WSS handshake to `generativelanguage.googleapis.com:443` fails or is intercepted by corporate TLS inspection proxy without valid client certificates.
- **Root Cause:** Enterprise firewall and egress proxy restrictions.
- **Remediation Requirement:** Provide unrestricted outbound HTTPS/WSS access to `generativelanguage.googleapis.com` on the testing host.

---

### `DEF-A07-005`: Absence of Live Production Gemini API Credentials in OS Keyring
- **Severity:** High (Release Blocker)
- **Category:** Environmental / Credential Configuration
- **Impacted Workstreams:** Workstream 3 (Gemini Live AI Voice)
- **Impacted Protocols:** `A03-GEM-01` through `A03-GEM-11`
- **Observed Behavior:** Alex settings service queries Windows Credential Manager (`keyring.get_password("alex", "gemini_api_key")`) and returns `None`. Real-key Live audio cannot initialize.
- **Root Cause:** Live credentials intentionally excluded from development machine configuration to prevent credential exposure.
- **Remediation Requirement:** Provision a dedicated, budgeted Google Gemini API test key in the OS keyring using `alex config` or Windows Credential Manager on the external test workstation.

---

## 4. Remediation Roadmap for External Release Execution

To transition from `BLOCKED_BY_ENVIRONMENT` to `PASS`, an authorized human QA engineer must be provisioned with a workstation meeting the following exact profile:
1. **Host:** Standalone Windows 11 (23H2/24H2) outside enterprise GPO/AppLocker restrictions.
2. **Display:** Physical 1920x1080 display in active user session.
3. **Audio:** Physical USB microphone and stereo speakers/headphones.
4. **Network:** Direct internet connection with open TLS 443 egress to Google APIs.
5. **Key:** Valid `GEMINI_API_KEY` stored in Windows Credential Manager.

