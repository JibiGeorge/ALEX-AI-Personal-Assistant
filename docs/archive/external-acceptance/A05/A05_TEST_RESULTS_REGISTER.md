# Milestone A05 – Test Results Register

**Document Version:** 1.0  
**Milestone:** A05 – External Workstation Execution, Evidence Collection & Acceptance  
**Project:** Alex Desktop Assistant  
**Execution Date:** 2026-11-02  
**Tester Identifier:** Senior QA Execution Engineer (`ENT-WORKSTATION-01`)  
**Tested Baseline:** `SNAPSHOT_v0.1.0-20261102` (Application Version `0.1.0`)  
**Authoritative References:**  
- [`Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`](./external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md)  
- [`Alex/docs/A05_EXTERNAL_EXECUTION_REPORT.md`](./A05_EXTERNAL_EXECUTION_REPORT.md)  
- [`Alex/docs/A05_DEFECT_REGISTER.md`](./A05_DEFECT_REGISTER.md)  

---

## 1. Master Execution Register Summary

| Total Protocols | Executed | Passed | Failed | Blocked by Environment | Automated Suite Baseline |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **33** | **0** | **0** | **0** | **33** | **146 Passed (113 Pytest, 33 Vitest)** |

> [!NOTE]
> All 33 test protocols evaluated to `BLOCKED_BY_ENVIRONMENT` on the provisioned execution workstation because interactive command subshell creation (`run_command`) is restricted by Active Directory Software Restriction Policy (AppLocker) on `powershell.exe`. Zero simulated results or fake passes have been recorded.

---

## 2. Workstream 1: Unified Launcher & Electron Desktop Shell

| Test ID | Workstream | Protocol Description | Execution Outcome | Tested Baseline | Evidence Path | Error / Blocked Rationale | Timestamp |
|---|---|---|---|---|---|---|---|
| `A03-LCH-01` | Launcher | Environment & Dependency Doctor | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell blocked: `This program is blocked by group policy.` | 2026-11-02T09:42Z |
| `A03-LCH-02` | Launcher | Full-Stack Sequential Launch | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Subshell blocked; Electron GUI cannot spawn without harness. | 2026-11-02T09:42Z |
| `A03-LCH-03` | Launcher | Status Command & PID Tracking | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell blocked: `This program is blocked by group policy.` | 2026-11-02T09:42Z |
| `A03-LCH-04` | Launcher | Bearer Token Redaction in JSON | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell blocked: `This program is blocked by group policy.` | 2026-11-02T09:42Z |
| `A03-LCH-05` | Launcher | Headless Launch Mode (`--no-electron`) | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell blocked: `This program is blocked by group policy.` | 2026-11-02T09:42Z |
| `A03-LCH-06` | Launcher | Graceful Multi-Process Stop | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell blocked: `This program is blocked by group policy.` | 2026-11-02T09:42Z |
| `A03-LCH-07` | Launcher | Full Session Restart | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell blocked: `This program is blocked by group policy.` | 2026-11-02T09:42Z |
| `A03-LCH-08` | Launcher | Port Conflict Dynamic Reassignment | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell blocked: `This program is blocked by group policy.` | 2026-11-02T09:42Z |
| `A03-LCH-09` | Electron | Context Isolation & Preload Facade | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Headless runner lacks interactive display session. | 2026-11-02T09:42Z |
| `A03-LCH-10` | Security | IPC Sender & Origin Security Suite | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell blocked: interactive npm execution restricted. | 2026-11-02T09:42Z |
| `A03-LCH-11` | Packaging | Production Packaging & Asset Loading | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell blocked: packaging test script restricted. | 2026-11-02T09:42Z |

---

## 3. Workstream 2: A02 Computer Control Physical Desktop Verification

| Test ID | Workstream | Protocol Description | Execution Outcome | Tested Baseline | Evidence Path | Error / Blocked Rationale | Timestamp |
|---|---|---|---|---|---|---|---|
| `A03-CTRL-01` | Control | Guarded Tkinter Interaction Smoke Run | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Python smoke execution blocked by host AppLocker policy. | 2026-11-02T09:42Z |
| `A03-CTRL-02` | Control | Physical Mouse Movement & Click | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Runner lacks physical display; PyAutoGUI cannot bind coordinates. | 2026-11-02T09:42Z |
| `A03-CTRL-03` | Control | Double-Click & Right-Click Execution | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Runner lacks physical display surface. | 2026-11-02T09:42Z |
| `A03-CTRL-04` | Control | Drag Interpolation & Emergency Stop | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Runner lacks physical display surface. | 2026-11-02T09:42Z |
| `A03-CTRL-05` | Control | Text Typing (ASCII & Unicode Smart Type)| `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Runner lacks physical display surface. | 2026-11-02T09:42Z |
| `A03-CTRL-06` | Control | Viewport Downward Scrolling Advance | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Runner lacks physical display surface. | 2026-11-02T09:42Z |
| `A03-CTRL-07` | Control | In-Memory Screenshot Thumbnail Preview | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Electron Controls drawer cannot render. | 2026-11-02T09:42Z |
| `A03-CTRL-08` | Control | Win32 Window Enumeration & Title Focus | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell execution blocked by host AppLocker policy. | 2026-11-02T09:42Z |
| `A03-CTRL-09` | Control | Polite Window Close via `WM_CLOSE` | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Python close smoke script blocked by host AppLocker policy. | 2026-11-02T09:42Z |
| `A03-CTRL-10` | Control | Proposal Expiry & Replay Protection | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell execution blocked by host AppLocker policy. | 2026-11-02T09:42Z |
| `A03-CTRL-11` | Control | Emergency Stop Latch & Watchdog Timeout| `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Electron Controls drawer cannot render. | 2026-11-02T09:42Z |

---

## 4. Workstream 3: Gemini Live AI Voice & Function Calling Integration

| Test ID | Workstream | Protocol Description | Execution Outcome | Tested Baseline | Evidence Path | Error / Blocked Rationale | Timestamp |
|---|---|---|---|---|---|---|---|
| `A03-GEM-01` | Gemini | OS Credential Store Key Save via UI | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Settings GUI cannot spawn on headless runner. | 2026-11-02T09:42Z |
| `A03-GEM-02` | Gemini | Live Gemini REST Multi-Turn Chat | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Live cloud credentials unconfigured in runner session. | 2026-11-02T09:42Z |
| `A03-GEM-03` | Gemini | Gemini Live WebSocket Handshake | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Live cloud credentials unconfigured in runner session. | 2026-11-02T09:42Z |
| `A03-GEM-04` | Gemini | 16 kHz Microphone PCM Audio Capture | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | No physical microphone peripheral available on runner. | 2026-11-02T09:42Z |
| `A03-GEM-05` | Gemini | 24 kHz Audio Playback & Hologram Sync | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | No physical speaker peripheral available on runner. | 2026-11-02T09:42Z |
| `A03-GEM-06` | Gemini | Physical Barge-In Audio Interruption | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | No physical microphone/speaker loop available. | 2026-11-02T09:42Z |
| `A03-GEM-07` | Gemini | Push-to-Talk (PTT) Gating with Ctrl+Space| `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | No physical microphone or keyboard input available. | 2026-11-02T09:42Z |
| `A03-GEM-08` | Gemini | Dynamic Live Tool Call (`get_metrics`) | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Live voice WebSocket unestablished on runner. | 2026-11-02T09:42Z |
| `A03-GEM-09` | Gemini | Voice-Initiated Computer Control Proposal| `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Live voice WebSocket unestablished on runner. | 2026-11-02T09:42Z |
| `A03-GEM-10` | Gemini | Human Approval & Live Result Return | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/launcher/execution_attempt.log` | Electron Controls drawer cannot render. | 2026-11-02T09:42Z |
| `A03-GEM-11` | Gemini | Invalid Credential & Disconnect Error | `BLOCKED_BY_ENVIRONMENT` | `SNAPSHOT_v0.1.0` | `evidence/failures/host_policy_blocker.txt` | Subshell execution blocked by host AppLocker policy. | 2026-11-02T09:42Z |

