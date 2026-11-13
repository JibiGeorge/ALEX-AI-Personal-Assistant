# Milestone A03 – Tester Sign-Off Certificate & Evaluation Matrix

**Document Version:** 1.0  
**Project:** Alex Desktop Assistant  
**Milestone:** A03 – External Workstation Runtime Acceptance & Handoff Sign-Off  
**Authoritative References:** [`A03_EXTERNAL_TESTER_HANDOFF.md`](./A03_EXTERNAL_TESTER_HANDOFF.md), [`A03_TEST_EXECUTION_CHECKLIST.md`](./A03_TEST_EXECUTION_CHECKLIST.md), [`A03_EVIDENCE_TEMPLATE.md`](./A03_EVIDENCE_TEMPLATE.md)  

---

## 1. Workstation & Environment Attestation

*The authorized external tester must complete this section prior to executing the test protocol:*

| Environment Dimension | Recorded Workstation Details |
|---|---|
| **Workstation Hostname / Device ID** | `__________________________________________________` |
| **Operating System & Exact Build** | `Windows 11 Pro / Enterprise (Build: ____________)` |
| **Execution Policy Status** | `Unrestricted (PowerShell & Python subshells permitted)` |
| **Python Version & Architecture** | `Python 3.12.____ (64-bit)` |
| **Node.js & npm Versions** | `Node.js v______, npm v______` |
| **Physical Display & Scaling** | `______ x ______ resolution at 100% display scaling` |
| **Physical Microphone Model** | `__________________________________________________` |
| **Physical Output Audio (Speakers/Headphones)** | `__________________________________________________` |
| **Google Gemini API Key Scope** | `Valid test key with gemini-2.5-flash & Live API access (gemini-3.1-flash-live-preview)` |
| **Authorized Tester Name & Title** | `__________________________________________________` |
| **Testing Organization / Team** | `__________________________________________________` |
| **Test Execution Date Range** | `2026-____-____ to 2026-____-____` |

---

## 2. Test Execution Scorecard

### Workstream 1: Unified Launcher & Electron Desktop Shell

| Test ID | Test Protocol Description | Status | Evidence File Location | Tester Remarks |
|---|---|---|---|---|
| `A03-LCH-01` | Environment & Dependency Doctor | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/launcher/doctor_stdout.txt` | |
| `A03-LCH-02` | Full-Stack Sequential Launch | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/launcher/launch_stdout.txt`<br>`evidence/electron/window_boot.png` | |
| `A03-LCH-03` | Status Command & PID Tracking | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/launcher/status_stdout.txt` | |
| `A03-LCH-04` | Token Redaction in JSON Status | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/launcher/status_json.txt` | |
| `A03-LCH-05` | Headless Mode Launch | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/launcher/headless_launch.txt` | |
| `A03-LCH-06` | Graceful Multi-Process Stop | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/launcher/stop_stdout.txt` | |
| `A03-LCH-07` | Full Session Restart | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/launcher/restart_stdout.txt` | |
| `A03-LCH-08` | Port Conflict Auto-Reassignment | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/failures/port_conflict_stdout.txt` | |
| `A03-LCH-09` | Electron Context Isolation & Preload | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/electron/devtools_context_isolation.png`| |
| `A03-LCH-10` | IPC Sender & Origin Security Suite | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/security/electron_security_stdout.txt` | |
| `A03-LCH-11` | Production Build Packaging Verification | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/electron/packaging_stdout.txt` | |

**Workstream 1 Subtotal:** Pass: `___/11` | Fail: `___/11` | Blocked: `___/11`  
**Workstream 1 Decision:** `[ ] ACCEPTED    [ ] NOT ACCEPTED    [ ] BLOCKED_BY_ENVIRONMENT`

---

### Workstream 2: A02 Computer Control Physical Desktop Verification

| Test ID | Test Protocol Description | Status | Evidence File Location | Tester Remarks |
|---|---|---|---|---|
| `A03-CTRL-01` | Guarded Windows Interaction Smoke Run | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/smoke_stdout.txt` | |
| `A03-CTRL-02` | Physical Mouse Movement & Click | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/mouse_click_approval.png` | |
| `A03-CTRL-03` | Double-Click & Right-Click Execution | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/right_click_context.png` | |
| `A03-CTRL-04` | Drag Interpolation & Emergency Stop | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/drag_emergency_stop.png` | |
| `A03-CTRL-05` | Text Typing (ASCII & Unicode Smart Type)| `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/typing_notepad.png` | |
| `A03-CTRL-06` | Viewport Downward Scrolling Advance | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/scroll_advance.png` | |
| `A03-CTRL-07` | In-Memory Screenshot Thumbnail Preview | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/screenshot_preview.png` | |
| `A03-CTRL-08` | Win32 Window Enumeration & Title Focus | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/focus_notepad.png` | |
| `A03-CTRL-09` | Polite Window Close via `WM_CLOSE` | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/close_smoke_stdout.txt`| |
| `A03-CTRL-10` | Proposal Expiry & Replay Protection | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/proposal_expiry_log.txt` | |
| `A03-CTRL-11` | Emergency Stop Latch & Watchdog Timeout| `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/computer-control/emergency_latch.png` | |

**Workstream 2 Subtotal:** Pass: `___/11` | Fail: `___/11` | Blocked: `___/11`  
**Workstream 2 Decision:** `[ ] ACCEPTED    [ ] NOT ACCEPTED    [ ] BLOCKED_BY_ENVIRONMENT`

---

### Workstream 3: Gemini Live AI Voice & Function Calling Integration

| Test ID | Test Protocol Description | Status | Evidence File Location | Tester Remarks |
|---|---|---|---|---|
| `A03-GEM-01` | OS Credential Store Key Save via UI | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/credential_saved.png` | |
| `A03-GEM-02` | Live Gemini REST Multi-Turn Chat | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/rest_turn_chat.png` | |
| `A03-GEM-03` | Gemini Live WebSocket Handshake | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/websocket_connected.png` | |
| `A03-GEM-04` | 16 kHz Microphone PCM Audio Capture | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/mic_streaming.png` | |
| `A03-GEM-05` | 24 kHz Audio Playback & Hologram Sync | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/assistant_speaking.png` | |
| `A03-GEM-06` | Physical Barge-In Audio Interruption | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/barge_in_interrupted.png` | |
| `A03-GEM-07` | Push-to-Talk (PTT) Gating with Ctrl+Space| `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/ptt_gated_turn.png` | |
| `A03-GEM-08` | Dynamic Live Tool Call (`system.get_metrics`)| `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/live_tool_metrics.png` | |
| `A03-GEM-09` | Voice-Initiated Computer Control Proposal | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/voice_proposal_enqueued.png` | |
| `A03-GEM-10` | Human Approval & Live Result Return | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/voice_proposal_approved.png` | |
| `A03-GEM-11` | Invalid Credential & Disconnect Error | `[ ] PASS  [ ] FAIL  [ ] BLOCKED` | `evidence/gemini/invalid_key_banner.png` | |

**Workstream 3 Subtotal:** Pass: `___/11` | Fail: `___/11` | Blocked: `___/11`  
**Workstream 3 Decision:** `[ ] ACCEPTED    [ ] NOT ACCEPTED    [ ] BLOCKED_BY_ENVIRONMENT`

---

## 3. Formal Acceptance Decision Rules

* **ACCEPTED:**  
  All 33 test cases evaluate to `PASS`. All required evidence artifacts are committed under `Alex/docs/external-acceptance/evidence/`. Zero unhandled exceptions or security bypasses exist.
* **NOT ACCEPTED:**  
  One or more test cases evaluate to `FAIL`, a functional regression occurs, or security boundaries are violated.
* **BLOCKED_BY_ENVIRONMENT:**  
  One or more test cases cannot run due to workstation policies, absent hardware peripherals, or cloud API unavailability.

---

## 4. Formal Milestone A03 Sign-Off Certificate

### Milestone Evaluation Summary:
```text
[   ] ACCEPTED                - All 33 test cases PASS; verified by empirical evidence.
[   ] NOT ACCEPTED            - One or more test cases FAILED; implementation defect found.
[ X ] BLOCKED_BY_ENVIRONMENT  - Host Active Directory Group Policy blocks interactive subshells.
```

### Lead Tester Sign-Off:
* **Tester Name:** _______________________________________
* **Signature:** _______________________________________
* **Date:** ________________________
* **Formal Recommendation:** __________________________________________________

### Lead Software Architect Sign-Off:
* **Architect Name:** Antigravity AI Assistant / Engineering Lead
* **Signature:** *Antigravity QA/Architecture Lead*
* **Date:** 2026-11-01
* **Audit Determination:** `BLOCKED_BY_ENVIRONMENT` on current runner host. Handoff package ready for external workstation verification.

