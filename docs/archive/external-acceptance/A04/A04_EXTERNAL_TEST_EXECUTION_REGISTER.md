# Milestone A04 – External Test Execution Register

**Document Version:** 1.0  
**Milestone:** A04 – External QA Execution, Evidence Review & Release Authorization  
**Project:** Alex Desktop Assistant  
**Date:** 2026-11-02  
**Governance Notice:** In strict accordance with Milestone A04 audit rules, **PASS results are not prepopulated**. All test protocols remain in `PENDING` execution status (or recorded as `BLOCKED_BY_ENVIRONMENT` for the development host runner attempt) until empirical evidence is captured on an authorized external workstation.  
**Authoritative References:**  
- [`Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`](./A03_TEST_EXECUTION_CHECKLIST.md)  
- [`Alex/docs/external-acceptance/A03_TESTER_SIGNOFF.md`](./A03_TESTER_SIGNOFF.md)  
- [`Alex/docs/external-acceptance/A03_EVIDENCE_TEMPLATE.md`](./A03_EVIDENCE_TEMPLATE.md)  
- [`Alex/docs/external-acceptance/A04_EXTERNAL_QA_EXECUTION_PLAN.md`](./A04_EXTERNAL_QA_EXECUTION_PLAN.md)  

---

## 1. Execution Register Summary Metrics

| Metric Dimension | Recorded Value | Evaluation Standard |
|---|---|---|
| **Total Test Protocols** | **33** | Comprehensive physical acceptance coverage |
| **Workstream 1 (Launcher & Electron)** | 11 Protocols (`A03-LCH-01` through `A03-LCH-11`) | CLI lifecycle, port reassignment, Electron HUD, IPC security |
| **Workstream 2 (A02 Computer Control)** | 11 Protocols (`A03-CTRL-01` through `A03-CTRL-11`) | Tkinter smoke, mouse, keyboard, scroll, polite close, safety gates |
| **Workstream 3 (Gemini Live AI Voice)** | 11 Protocols (`A03-GEM-01` through `A03-GEM-11`) | Keyring, REST chat, WebSocket, 16k PCM, 24k audio, barge-in, tools |
| **Pre-populated PASS Statuses** | **0 / 33 (0%)** | Strictly prohibited by governance rules |
| **Host Runner Baseline Status** | 33 Blocked by Policy / Unexecuted | Blocked by host Active Directory AppLocker |
| **External Workstation Execution Status** | **33 PENDING** | Awaiting independent external tester run |

---

## 2. Workstream 1: Unified Launcher & Electron Desktop Shell

| Test ID | Workstream | Target Protocol Description | Execution Status | External Tester | Execution Date | Designated Evidence File Path | Defect Ref | Review Status |
|---|---|---|---|---|---|---|---|---|
| `A03-LCH-01` | Launcher | Environment & Dependency Doctor | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/launcher/doctor_stdout.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-LCH-02` | Launcher | Full-Stack Sequential Launch | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/launcher/launch_stdout.txt`<br>`evidence/electron/window_boot.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-LCH-03` | Launcher | Process Status & PID Verification | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/launcher/status_stdout.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-LCH-04` | Launcher | Bearer Token Redaction in JSON | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/launcher/status_json.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-LCH-05` | Launcher | Headless Launch Mode (`--no-electron`) | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/launcher/headless_launch.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-LCH-06` | Launcher | Graceful Multi-Process Stop | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/launcher/stop_stdout.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-LCH-07` | Launcher | Full Session Restart | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/launcher/restart_stdout.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-LCH-08` | Launcher | Port Conflict Dynamic Reassignment | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/failures/port_conflict_stdout.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-LCH-09` | Electron | Context Isolation & Preload Facade | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/electron/devtools_context_isolation.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-LCH-10` | Security | IPC Sender & Origin Security Suite | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/security/electron_security_stdout.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-LCH-11` | Packaging | Production Packaging & Asset Loading | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/electron/packaging_stdout.txt` | None | `AWAITING_EXTERNAL_RUN` |

---

## 3. Workstream 2: A02 Computer Control Physical Desktop Verification

> [!IMPORTANT]
> **Implementation Freeze:** Computer Control code in `backend/app/services/computer_control_service.py` is frozen. No modifications permitted during test execution.

| Test ID | Workstream | Target Protocol Description | Execution Status | External Tester | Execution Date | Designated Evidence File Path | Defect Ref | Review Status |
|---|---|---|---|---|---|---|---|---|
| `A03-CTRL-01` | Control | Guarded Tkinter Interaction Smoke Run | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/smoke_stdout.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-CTRL-02` | Control | Physical Mouse Movement & Click | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/mouse_click_approval.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-CTRL-03` | Control | Double-Click & Right-Click Execution | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/right_click_context.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-CTRL-04` | Control | Drag Interpolation & Emergency Stop | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/drag_emergency_stop.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-CTRL-05` | Control | Text Typing (ASCII & Unicode Smart Type)| `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/typing_notepad.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-CTRL-06` | Control | Viewport Downward Scrolling Advance | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/scroll_advance.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-CTRL-07` | Control | In-Memory Screenshot Thumbnail Preview | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/screenshot_preview.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-CTRL-08` | Control | Win32 Window Enumeration & Title Focus | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/focus_notepad.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-CTRL-09` | Control | Polite Window Close via `WM_CLOSE` | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/close_smoke_stdout.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-CTRL-10` | Control | Proposal Expiry & Replay Protection | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/proposal_expiry_log.txt` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-CTRL-11` | Control | Emergency Stop Latch & Watchdog Timeout| `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/computer-control/emergency_latch.png` | None | `AWAITING_EXTERNAL_RUN` |

---

## 4. Workstream 3: Gemini Live AI Voice & Function Calling Integration

| Test ID | Workstream | Target Protocol Description | Execution Status | External Tester | Execution Date | Designated Evidence File Path | Defect Ref | Review Status |
|---|---|---|---|---|---|---|---|---|
| `A03-GEM-01` | Gemini | OS Credential Store Key Save via UI | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/credential_saved.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-GEM-02` | Gemini | Live Gemini REST Multi-Turn Chat | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/rest_turn_chat.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-GEM-03` | Gemini | Gemini Live WebSocket Handshake | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/websocket_connected.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-GEM-04` | Gemini | 16 kHz Microphone PCM Audio Capture | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/mic_streaming.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-GEM-05` | Gemini | 24 kHz Audio Playback & Hologram Sync | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/assistant_speaking.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-GEM-06` | Gemini | Physical Barge-In Audio Interruption | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/barge_in_interrupted.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-GEM-07` | Gemini | Push-to-Talk (PTT) Gating with Ctrl+Space| `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/ptt_gated_turn.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-GEM-08` | Gemini | Dynamic Live Tool Call (`get_metrics`) | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/live_tool_metrics.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-GEM-09` | Gemini | Voice-Initiated Computer Control Proposal| `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/voice_proposal_enqueued.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-GEM-10` | Gemini | Human Approval & Live Result Return | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/voice_proposal_approved.png` | None | `AWAITING_EXTERNAL_RUN` |
| `A03-GEM-11` | Gemini | Invalid Credential & Disconnect Error | `PENDING` | `[Assigned Tester]` | `YYYY-MM-DD` | `evidence/gemini/invalid_key_banner.png` | None | `AWAITING_EXTERNAL_RUN` |

---

## 5. Tester Instructions for Updating this Register

When executing tests on the external workstation:
1. Replace `PENDING` with `PASS`, `FAIL`, or `BLOCKED` based solely on actual observation.
2. Fill in the `External Tester` name and `Execution Date`.
3. Confirm that the exact evidence file exists in the designated directory under `evidence/`.
4. If a test fails, enter the defect reference ID and attach logs in `evidence/failures/`.
5. Update `Review Status` to `SUBMITTED_FOR_REVIEW`.

