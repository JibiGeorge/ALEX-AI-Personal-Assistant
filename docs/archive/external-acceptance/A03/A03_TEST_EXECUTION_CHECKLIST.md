# Milestone A03 – Test Execution Checklist

**Document Version:** 1.0  
**Last Updated:** 2026-11-01  
**Project:** Alex Desktop Assistant  
**Authoritative References:** [`A03_EXTERNAL_TESTER_HANDOFF.md`](./A03_EXTERNAL_TESTER_HANDOFF.md), [`A03_TESTER_SIGNOFF.md`](./A03_TESTER_SIGNOFF.md), [`A03_EVIDENCE_TEMPLATE.md`](./A03_EVIDENCE_TEMPLATE.md)  

---

## 1. Execution Instructions for External Tester

1. Follow the test protocols sequentially within each workstream.
2. For command-line tests, redirect stdout and stderr to the specified evidence path under `Alex/docs/external-acceptance/evidence/`.
3. For GUI and visual verification steps, capture a full-screen screenshot (`.png`) and save it to the designated evidence folder.
4. Redact all production API keys, raw bearer tokens, and private user paths to `****` before committing evidence.
5. Record actual outcomes, exit codes, and timestamps in [`A03_TESTER_SIGNOFF.md`](./A03_TESTER_SIGNOFF.md).

---

## 2. Workstream 1: Unified Launcher & Electron Desktop Shell

### A03-LCH-01: Environment & Dependency Doctor
* **Prerequisites:** Clean terminal, virtualenv initialized at `backend/.venv`, npm dependencies installed.
* **Exact Command:**
  ```powershell
  python -m launcher.cli doctor --verbose > docs/external-acceptance/evidence/launcher/doctor_stdout.txt 2>&1
  ```
* **Expected Result:**
  - Exit code `0`.
  - Terminal displays passing checks for: Python >= 3.11, Node.js >= 18, npm, virtualenv presence, backend dependencies, frontend dependencies, and environment files.
  - No red `[FAIL]` flags appear.
* **Evidence File:** `docs/external-acceptance/evidence/launcher/doctor_stdout.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-LCH-02: Full-Stack Sequential Launch
* **Prerequisites:** Ports 8765 and 5173 available.
* **Exact Command:**
  ```powershell
  python -m launcher.cli launch > docs/external-acceptance/evidence/launcher/launch_stdout.txt 2>&1
  ```
* **Expected Result:**
  - Step 1: Doctor pre-flight passes.
  - Step 2: Backend starts on loopback `127.0.0.1:8765`.
  - Step 3: Backend health check `/api/v1/health` returns HTTP 200 with bearer token.
  - Step 4: Frontend Vite server starts on `127.0.0.1:5173`.
  - Step 5: Frontend readiness verified.
  - Step 6: Electron window opens (1180x800) displaying holographic cyan HUD.
  - Exit code `0` (or process continues running in foreground).
* **Evidence File:** `docs/external-acceptance/evidence/launcher/launch_stdout.txt`, `docs/external-acceptance/evidence/electron/window_boot.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-LCH-03: Process Status & PID Verification
* **Prerequisites:** Active launch session running in background or separate terminal.
* **Exact Command:**
  ```powershell
  python -m launcher.cli status > docs/external-acceptance/evidence/launcher/status_stdout.txt 2>&1
  ```
* **Expected Result:**
  - Status summary table prints with green `RUNNING` indicators for Backend, Frontend, and Electron.
  - Actual Windows PIDs and port numbers (8765, 5173) are reported.
  - Runtime state file (`%APPDATA%\Alex\runtime.json` or `$ALEX_DATA_DIR/runtime.json`) contains active process metadata.
* **Evidence File:** `docs/external-acceptance/evidence/launcher/status_stdout.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-LCH-04: Bearer Token Redaction in JSON Status
* **Prerequisites:** Active launch session running.
* **Exact Command:**
  ```powershell
  python -m launcher.cli status --json > docs/external-acceptance/evidence/launcher/status_json.txt 2>&1
  ```
* **Expected Result:**
  - Valid JSON output is emitted.
  - `backend.token` field contains the masked string `"****"`.
  - The raw cryptographic token URL-safe string is **never** printed.
* **Evidence File:** `docs/external-acceptance/evidence/launcher/status_json.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-LCH-05: Headless Launch Mode
* **Prerequisites:** Application stopped (`python -m launcher.cli stop`).
* **Exact Command:**
  ```powershell
  python -m launcher.cli launch --no-electron > docs/external-acceptance/evidence/launcher/headless_launch.txt 2>&1
  ```
* **Expected Result:**
  - Backend starts and passes health check.
  - Frontend starts and becomes ready.
  - Electron window is **not** spawned.
  - `alex status` reports Backend and Frontend `RUNNING`, Electron `NOT RUNNING`.
* **Evidence File:** `docs/external-acceptance/evidence/launcher/headless_launch.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-LCH-06: Graceful Multi-Process Stop
* **Prerequisites:** Active application running.
* **Exact Command:**
  ```powershell
  python -m launcher.cli stop > docs/external-acceptance/evidence/launcher/stop_stdout.txt 2>&1
  ```
* **Expected Result:**
  - Electron window closes immediately.
  - Frontend Node/Vite process terminates.
  - Backend receives HTTP `/api/v1/shutdown` or SIGTERM and exits cleanly.
  - Ports 8765 and 5173 are released within 10 seconds.
  - Runtime state file (`runtime.json`) is cleaned up.
* **Evidence File:** `docs/external-acceptance/evidence/launcher/stop_stdout.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-LCH-07: Full Session Restart
* **Prerequisites:** Application running.
* **Exact Command:**
  ```powershell
  python -m launcher.cli restart > docs/external-acceptance/evidence/launcher/restart_stdout.txt 2>&1
  ```
* **Expected Result:**
  - All running processes stop cleanly.
  - Ports are confirmed released.
  - Full sequential boot sequence re-executes.
  - Electron window re-opens successfully.
* **Evidence File:** `docs/external-acceptance/evidence/launcher/restart_stdout.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-LCH-08: Port Conflict Dynamic Reassignment
* **Prerequisites:** Occupy port 8765 externally before launch (e.g. `python -m http.server 8765`).
* **Exact Command:**
  ```powershell
  python -m launcher.cli launch > docs/external-acceptance/evidence/failures/port_conflict_stdout.txt 2>&1
  ```
* **Expected Result:**
  - Launcher detects port 8765 is occupied.
  - Emits warning: `Port 8765 is in use. Assigning next available port (8766)...`
  - Backend successfully binds to port 8766.
  - Electron connects to port 8766 via `ALEX_BACKEND_PORT=8766`.
* **Evidence File:** `docs/external-acceptance/evidence/failures/port_conflict_stdout.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-LCH-09: Electron Context Isolation & Preload Facade
* **Prerequisites:** Electron window open in development mode (`alex launch`).
* **Procedure:**
  1. In the Electron window, press `Ctrl+Shift+I` to open Chrome DevTools.
  2. In the DevTools Console, execute:
     ```javascript
     console.log({
       alex: typeof window.alex,
       process: typeof window.process,
       require: typeof window.require,
       ipcRenderer: typeof window.ipcRenderer
     });
     ```
* **Expected Result:**
  - DevTools prints: `{ alex: "object", process: "undefined", require: "undefined", ipcRenderer: "undefined" }`.
  - Context isolation is strictly confirmed.
* **Evidence File:** `docs/external-acceptance/evidence/electron/devtools_context_isolation.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-LCH-10: IPC Sender & Origin Security Suite
* **Prerequisites:** Node.js installed, terminal in `frontend/`.
* **Exact Command:**
  ```powershell
  cd frontend
  npm test -- electron-security.test.ts > ../docs/external-acceptance/evidence/security/electron_security_stdout.txt 2>&1
  cd ..
  ```
* **Expected Result:**
  - 8 test cases pass: origin matching (`isAllowedDevOrigin`), canonical file path verification (`isAllowedProdFile`), and startup failure error dialog diagnostics (`stepDescription`).
  - Exit code `0`.
* **Evidence File:** `docs/external-acceptance/evidence/security/electron_security_stdout.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-LCH-11: Production Build Packaging & Asset Loading
* **Prerequisites:** Clean terminal in `frontend/`.
* **Exact Command:**
  ```powershell
  cd frontend
  npm run build
  npm run test:packaging > ../docs/external-acceptance/evidence/electron/packaging_stdout.txt 2>&1
  cd ..
  ```
* **Expected Result:**
  - TypeScript compiles with 0 errors.
  - Vite generates production bundle in `frontend/dist/`.
  - Electron TypeScript compiles to `frontend/dist-electron/`.
  - `verify-sidecar.test.mjs` passes all platform checks.
* **Evidence File:** `docs/external-acceptance/evidence/electron/packaging_stdout.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

## 3. Workstream 2: A02 Computer Control Physical Desktop Verification

> [!IMPORTANT]
> **Implementation Freeze:** Do not modify any code in `backend/app/services/computer_control_service.py` or `frontend/src/pages/ComputerControlPage.tsx`. Execute these tests strictly as designed.

### A03-CTRL-01: Guarded Windows Interaction Smoke Run
* **Prerequisites:** Unrestricted Windows 10/11 desktop, Python virtualenv activated in `backend/`.
* **Exact Command:**
  ```powershell
  cd backend
  $env:ALEX_ENABLE_DESKTOP_SMOKE = "1"
  .\.venv\Scripts\python.exe tests/manual_computer_control_smoke.py > ../docs/external-acceptance/evidence/computer-control/smoke_stdout.txt 2>&1
  cd ..
  ```
* **Expected Result:**
  - Spawns a disposable Tkinter test window titled `Alex Test Target`.
  - Focuses window, moves mouse, types test text, performs clipboard write and paste, executes downward scroll (verifying Text viewport position change), and captures an in-memory screenshot.
  - Target window closes automatically; script prints `ALL CHECKS PASSED` with exit code `0`.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/smoke_stdout.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-CTRL-02: Physical Mouse Movement & Coordinate Click
* **Prerequisites:** Alex desktop application running (`alex launch`).
* **Procedure:**
  1. Open the Controls drawer -> Computer Control page.
  2. Toggle `Computer Control Permission` to **ON**.
  3. Propose a mouse move and click on screen coordinates (e.g. `x: 500, y: 300`).
  4. Inspect the pending proposal card; click **Approve**.
* **Expected Result:**
  - Physical mouse cursor glides to `(500, 300)` and clicks.
  - Coordinates outside the primary monitor bounds are rejected with a validation error.
  - Proposal card disappears immediately upon execution.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/mouse_click_approval.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-CTRL-03: Double-Click & Right-Click Execution
* **Prerequisites:** Session permission ON.
* **Procedure:**
  1. Open a desktop folder or Notepad window.
  2. Issue approved `double_click` and `right_click` operations.
* **Expected Result:**
  - Double-click opens target item or selects word in text field.
  - Right-click brings up the Windows context menu.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/right_click_context.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-CTRL-04: Drag Interpolation & Emergency Stop Checkpoint
* **Prerequisites:** Session permission ON.
* **Procedure:**
  1. Dispatch a pointer drag from `(300, 300)` to `(700, 300)`.
  2. While the drag is in motion, hit the **Emergency Stop** button.
* **Expected Result:**
  - Mouse movement terminates mid-trajectory.
  - Left mouse button is immediately released via `adapter.mouseUp()`.
  - Emergency latch state is entered: `EMERGENCY STOP ENGAGED`.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/drag_emergency_stop.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-CTRL-05: Text Typing (ASCII & Unicode Smart Type)
* **Prerequisites:** Open Windows Notepad, focus text area.
* **Procedure:**
  1. Approve a `type` action containing ASCII text: `"Hello Alex Desktop Assistant!"`.
  2. Approve a `smart_type` action containing Unicode: `"Quantum Mechanics — ℏ = 1.054×10⁻³⁴ J·s"`.
* **Expected Result:**
  - ASCII string typed character by character.
  - Unicode string pasted from clipboard without character corruption.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/typing_notepad.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-CTRL-06: Viewport Downward Scrolling
* **Prerequisites:** Open a document or browser page with vertical scrollable content.
* **Procedure:**
  1. Focus the window and approve a `scroll` action (`direction: "down", amount: 5`).
* **Expected Result:**
  - Window viewport scrolls down smoothly.
  - Vertical scroll position advances visibly.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/scroll_advance.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-CTRL-07: In-Memory Screenshot Preview
* **Prerequisites:** Controls drawer open.
* **Procedure:**
  1. Approve a `screenshot` action.
* **Expected Result:**
  - A 1280x720 JPEG thumbnail preview renders immediately inside the Controls drawer.
  - Verify that **no** `.png` or `.jpg` file has been written to the user's home directory or `%TEMP%`.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/screenshot_preview.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-CTRL-08: Win32 Visible Window Enumeration & Title Focus
* **Prerequisites:** Open Calculator (`calc.exe`) and Notepad (`notepad.exe`).
* **Procedure:**
  1. Approve a `list_windows` action.
  2. Approve a `focus_window` action with `title: "Notepad"`.
* **Expected Result:**
  - `list_windows` returns only visible titled application windows (Calculator, Notepad, Alex).
  - `focus_window` brings Notepad to the foreground as the active window.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/focus_notepad.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-CTRL-09: Polite Application Close via `WM_CLOSE`
* **Prerequisites:** Virtualenv activated in `backend/`.
* **Exact Command:**
  ```powershell
  cd backend
  $env:ALEX_ENABLE_DESKTOP_SMOKE = "1"
  .\.venv\Scripts\python.exe tests/manual_computer_control_close_smoke.py > ../docs/external-acceptance/evidence/computer-control/close_smoke_stdout.txt 2>&1
  cd ..
  ```
* **Expected Result:**
  - Spawns disposable Tkinter window titled `Alex Polite Close Target`.
  - Dispatches polite `close_app` action.
  - Sends Win32 `WM_CLOSE` message to window HWND.
  - Verifies target process terminates and exits cleanly.
  - Verifies Alex process tree itself is protected and not terminated.
  - Exit code `0`.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/close_smoke_stdout.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-CTRL-10: Proposal Expiry & Replay Protection
* **Prerequisites:** Application running, session permission ON.
* **Procedure:**
  1. Enqueue a proposal; wait 5 minutes without clicking approve.
  2. Attempt to approve the expired proposal via API or UI.
  3. Approve an active proposal, then attempt to submit the same approval token a second time.
* **Expected Result:**
  - Expired proposal returns HTTP 410 / `Proposal has expired`.
  - Replayed token returns HTTP 404 / `Proposal not found or already consumed`.
  - Desktop receives zero automated input.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/proposal_expiry_log.txt`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-CTRL-11: Emergency Stop Latching & Watchdog Cancellation
* **Prerequisites:** Session permission ON.
* **Procedure:**
  1. Click the large red **Emergency Stop** button in the Controls drawer.
  2. Attempt to dispatch any mouse or keyboard action.
  3. Click **Reset & Re-arm Control**.
* **Expected Result:**
  - Emergency latch state is engaged immediately.
  - All pending proposals in the queue are flushed.
  - All incoming actions are rejected until the user manually clicks Re-arm.
* **Evidence File:** `docs/external-acceptance/evidence/computer-control/emergency_latch.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

## 4. Workstream 3: Gemini Live AI Voice & Function Calling Integration

### A03-GEM-01: OS Credential Store Key Save
* **Prerequisites:** Alex application open, valid Google Gemini API key available.
* **Procedure:**
  1. Navigate to Settings page.
  2. Paste active API key into the `Gemini API Key` input field.
  3. Click **Save Credential**.
* **Expected Result:**
  - Key is stored in Windows Credential Locker (`keyring`).
  - Settings page updates to display: `API Key Status: Configured (Saved securely in OS Credential Store)`.
  - The plaintext key is **never** printed in DevTools Console, network request response, or terminal.
* **Evidence File:** `docs/external-acceptance/evidence/gemini/credential_saved.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-GEM-02: Live Gemini REST Multi-Turn Chat
* **Prerequisites:** Gemini API key configured.
* **Procedure:**
  1. Navigate to Conversation page.
  2. Type: `"What is the speed of light in vacuum in meters per second?"` and submit.
* **Expected Result:**
  - Assistant responds with natural language text citing `299,792,458 m/s`.
  - Response renders cleanly in chat transcript.
* **Evidence File:** `docs/external-acceptance/evidence/gemini/rest_turn_chat.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-GEM-03: Gemini Live WebSocket Handshake
* **Prerequisites:** Physical microphone connected.
* **Procedure:**
  1. Click the cyan microphone button on the Conversation page.
* **Expected Result:**
  - Electron connects to `ws://127.0.0.1:8765/api/v1/conversation/live?token=...`.
  - Live voice session establishes connection with Google Gemini Live API (`models/gemini-3.1-flash-live-preview` or fallback `models/gemini-2.5-flash-native-audio-preview-12-2025`).
  - Avatar transitions to active state; terminal logs `[voice] Live session connected`.
* **Evidence File:** `docs/external-acceptance/evidence/gemini/websocket_connected.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-GEM-04: 16 kHz Microphone PCM Streaming
* **Prerequisites:** Live voice session active.
* **Procedure:**
  1. Speak clearly into the microphone: `"Alex, can you hear me?"`.
* **Expected Result:**
  - Web Audio API captures microphone stream at 16 kHz, 16-bit mono PCM.
  - Audio visualizer waveform animates in response to user voice volume.
  - User speech transcript appears in the conversation log.
* **Evidence File:** `docs/external-acceptance/evidence/gemini/mic_streaming.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-GEM-05: 24 kHz Audio Playback & Holographic Waveform
* **Prerequisites:** Live voice session active.
* **Procedure:**
  1. Listen for the assistant's spoken response through speakers / headphones.
* **Expected Result:**
  - 24 kHz PCM audio returns from Gemini Live and plays smoothly through default audio output device.
  - Holographic avatar pulse and waveform animate in synchronization with spoken output.
* **Evidence File:** `docs/external-acceptance/evidence/gemini/assistant_speaking.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-GEM-06: Physical Barge-In Interruption
* **Prerequisites:** Assistant actively speaking through speakers.
* **Procedure:**
  1. While the assistant is in mid-sentence, speak loudly: `"Stop, I have a question"`.
* **Expected Result:**
  - Assistant audio output silences immediately within 250ms.
  - Backend sends `{"type": "interrupt"}` to WebSocket.
  - Assistant stops speaking and listens for the user's new question.
* **Evidence File:** `docs/external-acceptance/evidence/gemini/barge_in_interrupted.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-GEM-07: Push-to-Talk (PTT) Gating
* **Prerequisites:** Enable Push-to-Talk in Audio Devices page (`push_to_talk_enabled: true`).
* **Procedure:**
  1. Press and hold `Ctrl+Space`; speak into microphone; release `Ctrl+Space`.
* **Expected Result:**
  - Audio PCM is transmitted **only** while `Ctrl+Space` is held down.
  - Releasing keys sends silence/flush frame; microphone input is gated.
* **Evidence File:** `docs/external-acceptance/evidence/gemini/ptt_gated_turn.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-GEM-08: Dynamic Tool Calling over Live Voice
* **Prerequisites:** Live voice session active.
* **Procedure:**
  1. Ask spoken question: `"Alex, what is the current CPU and RAM usage?"`.
* **Expected Result:**
  - Model issues function call to `system.get_metrics`.
  - Backend executes action, returns metric data mid-stream, and assistant speaks the actual CPU percentage aloud.
  - Max 4 tool calls per turn limit enforced.
* **Evidence File:** `docs/external-acceptance/evidence/gemini/live_tool_metrics.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-GEM-09: Voice-Initiated Computer Control Proposal
* **Prerequisites:** Live voice session active, session permission ON.
* **Procedure:**
  1. Say: `"Alex, please minimize all windows and show my desktop"`.
* **Expected Result:**
  - Model emits a `computer.request` proposal call.
  - Proposal card appears in the Controls drawer.
  - **No automated desktop input occurs yet.**
* **Evidence File:** `docs/external-acceptance/evidence/gemini/voice_proposal_enqueued.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-GEM-10: Human Proposal Approval & Voice Result Return
* **Prerequisites:** Proposal card visible from A03-GEM-09.
* **Procedure:**
  1. Click **Approve** on the proposal card.
* **Expected Result:**
  - Desktop action executes.
  - Execution outcome is returned to the live model session.
  - Assistant acknowledges: `"I have completed that action for you."`
* **Evidence File:** `docs/external-acceptance/evidence/gemini/voice_proposal_approved.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

---

### A03-GEM-11: Invalid Credential & Disconnect Error Handling
* **Prerequisites:** Test with an invalid API key (e.g. `AIzaSyFakeKey12345`).
* **Procedure:**
  1. Attempt to start a REST turn or live voice session.
* **Expected Result:**
  - UI displays polite error banner: `Gemini API key is invalid or quota exceeded`.
  - Backend process does **not** crash or exit.
  - Error is logged cleanly without exposing the invalid key string.
* **Evidence File:** `docs/external-acceptance/evidence/gemini/invalid_key_banner.png`
* **Status:** `[ ] PASS   [ ] FAIL   [ ] BLOCKED`

