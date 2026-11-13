# Milestone A03 – Acceptance Evidence Recording Templates & Sanitization Standard

**Document Version:** 1.0  
**Last Updated:** 2026-11-01  
**Project:** Alex Desktop Assistant  
**Authoritative References:** [`A03_EXTERNAL_TESTER_HANDOFF.md`](./A03_EXTERNAL_TESTER_HANDOFF.md), [`A03_TEST_EXECUTION_CHECKLIST.md`](./A03_TEST_EXECUTION_CHECKLIST.md), [`A03_TESTER_SIGNOFF.md`](./A03_TESTER_SIGNOFF.md)  

---

## 1. Overview & Redaction Standard

To maintain strict compliance with enterprise security standards and audit requirements, all evidence artifacts committed to `Alex/docs/external-acceptance/evidence/` must adhere to these sanitization rules:

### Mandatory Redaction Rules:
1. **Google Gemini API Keys:** Any key matching `AIza[0-9A-Za-z-_]{35}` or similar secret strings must be replaced with `****` or `[REDACTED_API_KEY]`.
2. **Backend Bearer Tokens:** Per-session random tokens (e.g. 32-byte base64url strings) must be replaced with `****`.
3. **Personal User Paths:** Replace private host usernames (e.g. `C:\Users\john.doe\`) with `%USERPROFILE%\` or `C:\Users\tester\`.
4. **Network IP Addresses:** Loopback addresses (`127.0.0.1`, `localhost`) are permitted. External public IP addresses must be masked.

---

## 2. Standardized Evidence Recording Templates

### Template A: Terminal / Command Output (`.txt` / `.log`)

Prepend the following header block to all captured terminal output files:

```text
================================================================================
ALEX RUNTIME ACCEPTANCE EVIDENCE – COMMAND LOG
================================================================================
Test ID:             A03-LCH-XX / A03-CTRL-XX / A03-GEM-XX
Protocol Name:       <Test Protocol Name>
Execution Timestamp: YYYY-MM-DDTHH:MM:SSZ
Workstation OS:      Windows 11 (Build XXXXX.XXXX)
Execution Shell:     PowerShell 7.x / Windows PowerShell 5.1
Command Invoked:     <exact command executed>
Exit Code Returned:  0 (or non-zero error code)
Sanitization Status: Verified (Zero plaintext API keys or bearer tokens)
Tester Name:         <Tester Name>
================================================================================

[COMMAND OUTPUT FOLLOWS BELOW]
```

---

### Template B: JSON Process State Dump (`.json` / `.txt`)

When dumping process states (such as `alex status --json`), ensure structure conforms to the masked format:

```json
{
  "timestamp": "2026-11-01T23:00:00Z",
  "status": "running",
  "backend": {
    "status": "running",
    "pid": 12345,
    "port": 8765,
    "token": "****",
    "health": "ready"
  },
  "frontend": {
    "status": "running",
    "pid": 23456,
    "port": 5173,
    "ready": true
  },
  "electron": {
    "status": "running",
    "pid": 34567,
    "window_count": 1
  }
}
```

---

### Template C: Visual Screenshot Metadata Sidecar (`.meta.txt`)

For every captured `.png` screenshot (e.g., `window_boot.png`), commit a companion metadata file (`window_boot.meta.txt`):

```text
Screenshot Artifact: window_boot.png
Test ID:             A03-LCH-02
Capture Timestamp:   YYYY-MM-DDTHH:MM:SSZ
Display Surface:     Physical Primary Display (1920x1080 @ 100% DPI)
Window Dimensions:   1180 x 800 pixels
Visual Features:     Holographic cyan HUD shell, animated avatar, live telemetry cards
DevTools Open:       No
Verified By:         <Tester Name>
```

---

### Template D: Live AI Transcript & Tool Call Trace (`.txt`)

For multi-turn REST or Gemini Live voice tests:

```text
================================================================================
GEMINI LIVE INTERACTION TRACE
================================================================================
Test ID:             A03-GEM-08
Session Transport:   WebSocket (ws://127.0.0.1:8765/api/v1/conversation/live)
Audio Format In:     16 kHz, 16-bit Mono PCM
Audio Format Out:    24 kHz, 16-bit Mono PCM
Timestamp:           YYYY-MM-DDTHH:MM:SSZ

[USER SPEECH]:       "Alex, what is the current CPU and RAM usage?"
[MODEL TOOL CALL]:   system.get_metrics({})
[ACTION EXECUTOR]:   Action system.get_metrics executed in 12ms. Status: success.
[ACTION RESULT]:     {"cpu_percent": 14.2, "memory_percent": 48.6}
[MODEL AUDIO OUT]:   24 kHz PCM streamed to speakers ("Your current CPU usage is 14%...")
[TRANSCRIPT TEXT]:   "Your current CPU usage is 14.2% and RAM usage is 48.6%."
[BARGE-IN TESTED]:   No
================================================================================
```

---

## 3. Master Evidence Artifact Destination Mapping

The table below maps every test ID in [`A03_TEST_EXECUTION_CHECKLIST.md`](./A03_TEST_EXECUTION_CHECKLIST.md) to its required evidence artifact filename:

| Test ID | Workstream | Expected Evidence File Path | Artifact Type |
|---|---|---|---|
| `A03-LCH-01` | Launcher | `evidence/launcher/doctor_stdout.txt` | Terminal Log |
| `A03-LCH-02` | Launcher | `evidence/launcher/launch_stdout.txt`<br>`evidence/electron/window_boot.png` | Terminal Log + Screenshot |
| `A03-LCH-03` | Launcher | `evidence/launcher/status_stdout.txt` | Terminal Log |
| `A03-LCH-04` | Launcher | `evidence/launcher/status_json.txt` | Masked JSON Dump |
| `A03-LCH-05` | Launcher | `evidence/launcher/headless_launch.txt` | Terminal Log |
| `A03-LCH-06` | Launcher | `evidence/launcher/stop_stdout.txt` | Terminal Log |
| `A03-LCH-07` | Launcher | `evidence/launcher/restart_stdout.txt` | Terminal Log |
| `A03-LCH-08` | Launcher | `evidence/failures/port_conflict_stdout.txt` | Terminal Log |
| `A03-LCH-09` | Electron | `evidence/electron/devtools_context_isolation.png` | Screenshot |
| `A03-LCH-10` | Security | `evidence/security/electron_security_stdout.txt` | Vitest Test Output |
| `A03-LCH-11` | Packaging | `evidence/electron/packaging_stdout.txt` | Build Log |
| `A03-CTRL-01` | Control | `evidence/computer-control/smoke_stdout.txt` | Python Smoke Log |
| `A03-CTRL-02` | Control | `evidence/computer-control/mouse_click_approval.png` | Screenshot |
| `A03-CTRL-03` | Control | `evidence/computer-control/right_click_context.png` | Screenshot |
| `A03-CTRL-04` | Control | `evidence/computer-control/drag_emergency_stop.png` | Screenshot |
| `A03-CTRL-05` | Control | `evidence/computer-control/typing_notepad.png` | Screenshot |
| `A03-CTRL-06` | Control | `evidence/computer-control/scroll_advance.png` | Screenshot |
| `A03-CTRL-07` | Control | `evidence/computer-control/screenshot_preview.png` | Screenshot |
| `A03-CTRL-08` | Control | `evidence/computer-control/focus_notepad.png` | Screenshot |
| `A03-CTRL-09` | Control | `evidence/computer-control/close_smoke_stdout.txt` | Python Close Log |
| `A03-CTRL-10` | Control | `evidence/computer-control/proposal_expiry_log.txt` | Terminal / API Log |
| `A03-CTRL-11` | Control | `evidence/computer-control/emergency_latch.png` | Screenshot |
| `A03-GEM-01` | Gemini | `evidence/gemini/credential_saved.png` | Screenshot |
| `A03-GEM-02` | Gemini | `evidence/gemini/rest_turn_chat.png` | Screenshot |
| `A03-GEM-03` | Gemini | `evidence/gemini/websocket_connected.png` | Screenshot |
| `A03-GEM-04` | Gemini | `evidence/gemini/mic_streaming.png` | Screenshot |
| `A03-GEM-05` | Gemini | `evidence/gemini/assistant_speaking.png` | Screenshot |
| `A03-GEM-06` | Gemini | `evidence/gemini/barge_in_interrupted.png` | Screenshot |
| `A03-GEM-07` | Gemini | `evidence/gemini/ptt_gated_turn.png` | Screenshot |
| `A03-GEM-08` | Gemini | `evidence/gemini/live_tool_metrics.png` | Screenshot / Log |
| `A03-GEM-09` | Gemini | `evidence/gemini/voice_proposal_enqueued.png` | Screenshot |
| `A03-GEM-10` | Gemini | `evidence/gemini/voice_proposal_approved.png` | Screenshot |
| `A03-GEM-11` | Gemini | `evidence/gemini/invalid_key_banner.png` | Screenshot |
| Sign-Off | Sign-Off | `evidence/signoff/completed_A03_TESTER_SIGNOFF.md` | Signed Certificate |

