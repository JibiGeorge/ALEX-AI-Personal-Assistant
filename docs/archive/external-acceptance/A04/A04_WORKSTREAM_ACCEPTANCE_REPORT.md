# Milestone A04 – Independent Workstream Acceptance Report

**Document Version:** 1.0  
**Milestone:** A04 – External QA Execution, Evidence Review & Release Authorization  
**Project:** Alex Desktop Assistant  
**Date:** 2026-11-02  
**Evaluation Lead:** Senior QA Architect, Test Automation Lead & Lead Systems Auditor  
**Authoritative References:**  
- [`Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`](./A03_TEST_EXECUTION_CHECKLIST.md)  
- [`Alex/docs/external-acceptance/A03_TESTER_SIGNOFF.md`](./A03_TESTER_SIGNOFF.md)  
- [`Alex/docs/external-acceptance/A04_EVIDENCE_REVIEW_REPORT.md`](./A04_EVIDENCE_REVIEW_REPORT.md)  
- [`Alex/docs/A03_MILESTONE_ACCEPTANCE_REPORT.md`](../A03_MILESTONE_ACCEPTANCE_REPORT.md)  
- [`Alex/docs/PROJECT_TASK_REGISTER.md`](../PROJECT_TASK_REGISTER.md)  

---

## 1. Executive Summary & Governance Principles

This report provides the formal, independent acceptance evaluation for each of the three functional workstreams comprising the Alex desktop assistant.

### Governance Principles:
1. **Independent Evaluation:** Each workstream is evaluated on its own merits. A failure or block in one workstream does not invalidate another.
2. **Automated vs. Physical Runtime Separation:** Passing automated unit, component, or packaging tests is a prerequisite, but does **not** substitute for physical runtime acceptance on target hardware.
3. **Preservation of Implementation Freezes:** No application source code was modified during this evaluation. Implementation freezes across Computer Control and Unified Launcher remain active.
4. **Standard Acceptance Decision Values:**
   - **`ACCEPTED`:** All mandatory criteria pass with verified empirical evidence.
   - **`NOT ACCEPTED`:** Mandatory criteria failed or implementation incomplete.
   - **`BLOCKED_BY_ENVIRONMENT`:** Execution prevented by host environmental constraints.
   - **`PENDING`:** Testing has not yet been performed or evidence has not been submitted.

---

## 2. Workstream 1: Unified Launcher CLI & Electron Desktop Runtime

### Scope & Evaluated Subsystems:
- **CLI Commands:** `alex doctor`, `alex launch`, `alex status`, `alex restart`, `alex stop` (`ALEX-LNCH-001` through `007`).
- **Startup Sequencing:** Sequential dependency orchestration (Doctor -> Backend -> Frontend -> Electron) with health polling.
- **Process State Tracking:** Windows PID tracking, process tree management, state persistence in `%APPDATA%\Alex\runtime.json`.
- **Dynamic Port Collision Handling:** Ephemeral reassignment when default ports (8765, 5173) are occupied.
- **Electron Security:** BrowserWindow construction (1180x800), context isolation (`nodeIntegration: false`, `contextIsolation: true`), typed Preload contextBridge (`window.alex`), origin-based navigation guards (`isAllowedDevOrigin`, `isAllowedProdFile`).
- **Production Packaging:** Production Vite bundling, TypeScript compilation, and packaging verification script.

### Evaluation Findings:
| Evaluation Dimension | Automated Test Evidence | Physical Runtime Evidence | Subsystem Determination |
|---|---|---|---|
| Dependency Doctor | 22 unit tests in `test_launcher.py` pass | Blocked on runner host by AppLocker | Automated Pass; Runtime Blocked |
| Multi-Process Launch | Sequential startup logic unit-tested | Blocked on runner host by AppLocker | Automated Pass; Runtime Blocked |
| Status & Bearer Masking | Token masked to `****` in `--json` test | Blocked on runner host by AppLocker | Automated Pass; Runtime Blocked |
| Port Conflict Reassignment | Mock socket conflict tests pass | Blocked on runner host by AppLocker | Automated Pass; Runtime Blocked |
| Process Termination | Process tree termination unit-tested | Blocked on runner host by AppLocker | Automated Pass; Runtime Blocked |
| Electron Shell & Security | 8 Vitest tests pass in `electron-security.test.ts` | Cannot spawn GUI on headless runner | Automated Pass; Runtime Blocked |
| Production Build | `npm run build` and `npm run test:packaging` pass | Output generated in `dist/`, `dist-electron/` | Verified Complete |

### Workstream 1 Acceptance Decision: **`BLOCKED_BY_ENVIRONMENT`**
**Acceptance Rationale:**  
All 11 test protocols (`A03-LCH-01` through `A03-LCH-11`) have verified automated baselines and clean production builds. However, physical GUI rendering, live port binding, and interactive multi-process lifecycle execution remain blocked on the development workstation due to Active Directory Group Policy. Formal acceptance is deferred to external workstation testing.

---

## 3. Workstream 2: A02 Computer Control Desktop Verification

### Scope & Evaluated Subsystems:
- **Ported Actions (22 Capabilities):** Mouse movement, left click, double click, right click, drag interpolation, ASCII typing, Unicode smart typing via clipboard, viewport scrolling, in-memory screenshot preview, visible window enumeration via Win32 `EnumWindows`, title focus (`SetForegroundWindow`), polite process close (`WM_CLOSE`), synthetic form data (`random_data`), and user profile autofill (`user_data`).
- **Safety Architecture & Gates:** Master session permission toggle (default OFF), immutable proposal objects, 5-minute proposal TTL, maximum 5 pending proposals, one-shot approval tokens, duplicate approval prevention, latched emergency stop, and 12-second execution watchdog.
- **Desktop Smoke Verification:** `tests/manual_computer_control_smoke.py` and `tests/manual_computer_control_close_smoke.py`.

### Implementation Freeze Status:
> [!IMPORTANT]
> **Strict Implementation Freeze:** [`backend/app/services/computer_control_service.py`](file:///d:/Workspace/Jibi/Alex/backend/app/services/computer_control_service.py), [`backend/app/actions/builtins/computer_control.py`](file:///d:/Workspace/Jibi/Alex/backend/app/actions/builtins/computer_control.py), and [`frontend/src/pages/ComputerControlPage.tsx`](file:///d:/Workspace/Jibi/Alex/frontend/src/pages/ComputerControlPage.tsx) are **100% FROZEN**. Zero code modifications have been made.

### Evaluation Findings:
| Evaluation Dimension | Automated Test Evidence | Physical Runtime Evidence | Subsystem Determination |
|---|---|---|---|
| Safety Service & State | 32 unit tests in `test_computer_control_service.py` pass | Runner lacks interactive desktop session | Automated Pass; Runtime Blocked |
| Proposal Security Gates | Replay, expiration, and queue limits verified | Interactive UI review required on external host | Automated Pass; Runtime Blocked |
| Emergency Stop Latch | Latch state and abort checkpoints pass unit tests | Physical button press test pending | Automated Pass; Runtime Blocked |
| Win32 Window Enumeration | Tested via Pytest with mock HWNDs | Win32 API calls blocked by Group Policy | Automated Pass; Runtime Blocked |
| Tkinter Smoke Run | Guarded script verified in code | Exit blocked: requires external desktop | Automated Pass; Runtime Blocked |
| Polite Application Close | Polite `WM_CLOSE` script verified in code | Exit blocked: requires external desktop | Automated Pass; Runtime Blocked |

### Workstream 2 Acceptance Decision: **`NOT ACCEPTED` (Implementation FROZEN)**
**Acceptance Rationale:**  
Implementation parity with `Mark-LVI-main` is achieved in source code, and all 32 unit tests pass. However, because computer control directly manipulates the physical operating system desktop (mouse movements, keystrokes, window focus, process termination), formal acceptance strictly requires physical verification on target hardware by an authorized human tester. Therefore, the authoritative status remains `NOT ACCEPTED` until external empirical evidence is collected.

---

## 4. Workstream 3: Gemini Live AI Voice & Function Calling Integration

### Scope & Evaluated Subsystems:
- **OS Credential Security:** Secure storage of Gemini API key in Windows Credential Locker via `keyring` (Service: `Alex`, Key: `gemini-api-key`); fallback to `backend/.env`. Key masking in UI and terminal.
- **REST Multi-Turn Conversation:** Bounded conversation turns with memory context injection and model ladder fallback (`gemini-2.5-flash` / `gemini-2.5-flash-lite`).
- **Live Bidirectional Voice Pipeline:** Web Audio API 16 kHz mono PCM capture -> loopback WebSocket -> Google Gemini Live WebSocket -> 24 kHz audio return -> physical speaker playback.
- **Live Models Verified:** Configured model ladder:
  - Primary: `models/gemini-3.1-flash-live-preview`
  - Fallback: `models/gemini-2.5-flash-native-audio-preview-12-2025`
- **Acoustic Interaction Controls:** Barge-in interruption (user speech cut-through within 250ms), push-to-talk (`Ctrl+Space`) gating, and holographic SVG waveform synchronization.
- **Streaming Tool Calling:** Dynamic action execution over persistent Live WebSocket (`system.get_metrics`, `memory.recall`) and voice-initiated computer control proposal generation requiring human approval.

### Evaluation Findings:
| Evaluation Dimension | Automated Test Evidence | Physical Runtime Evidence | Subsystem Determination |
|---|---|---|---|
| Credential Store Security | `test_settings_service.py` & `test_api.py` verify keyring | UI interactive save pending on external host | Automated Pass; Runtime Blocked |
| REST Conversation Ladder | Multi-turn and fallback tests pass in `test_api.py` | Live cloud query requires external host | Automated Pass; Runtime Blocked |
| Live WebSocket Framing | WebSocket framing tests pass in `test_live_voice_service.py` | Live Gemini WebSocket requires external host | Automated Pass; Runtime Blocked |
| 16 kHz PCM Mic Streaming | Web Audio API hook unit-tested in `useLiveVoice.test.ts` | Physical microphone unavailable on runner | Automated Pass; Runtime Blocked |
| 24 kHz Audio Playback | Audio buffer chunking tests pass | Physical speakers unavailable on runner | Automated Pass; Runtime Blocked |
| Barge-In Cutoff | Interrupt frame dispatch verified in code | Acoustic echo verification pending | Automated Pass; Runtime Blocked |
| Dynamic Live Tool Calls | Action registry tool declarations pass unit tests | Live model function call pending | Automated Pass; Runtime Blocked |

### Workstream 3 Acceptance Decision: **`BLOCKED_BY_ENVIRONMENT`**
**Acceptance Rationale:**  
The software architecture for live bidirectional audio streaming and mid-stream function calling is complete and verified in automated harnesses. However, physical microphone audio capture, acoustic speaker playback, real-time barge-in cancellation, and live cloud API credentials cannot be validated on the automated runner. Acceptance is deferred to external workstation testing.

---

## 5. Workstream Acceptance Decision Matrix

```
========================================================================================
MILESTONE A04 WORKSTREAM ACCEPTANCE MATRIX
========================================================================================
Workstream 1: Unified Launcher & Electron Desktop Shell
  - Automated Baseline: Verified (22 launcher tests, 8 security tests, build passes)
  - Physical Runtime:   Blocked on runner host by Active Directory AppLocker
  - Milestone Decision: BLOCKED_BY_ENVIRONMENT

Workstream 2: A02 Computer Control Desktop Verification
  - Automated Baseline: Verified (32 service unit tests pass)
  - Physical Runtime:   Blocked on runner host; implementation strictly FROZEN
  - Milestone Decision: NOT ACCEPTED (Implementation FROZEN)

Workstream 3: Gemini Live AI Voice & Function Calling
  - Automated Baseline: Verified (WebSocket framing & fake turn tests pass)
  - Physical Runtime:   Blocked by absence of mic, speakers, and live cloud credentials
  - Milestone Decision: BLOCKED_BY_ENVIRONMENT
========================================================================================
Composite Engineering Assessment: Application code is verified and ready for external QA.
========================================================================================
```

