# Alex Development Guide

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- Windows PowerShell for the included Windows build helper

## Setup

Run these commands from the Alex project directory:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
npm --prefix frontend install
```

Set `ALEX_PYTHON` if Electron should use a different interpreter. Set `ALEX_DATA_DIR` only when intentionally choosing a different application data directory.

## Run in development

From the Alex project directory:

```powershell
npm --prefix frontend run dev
```

The Electron main process starts a local Python sidecar, chooses a loopback port and passes an ephemeral token via the child process environment. In development it prefers `backend\.venv\Scripts\python.exe` on Windows or `backend/.venv/bin/python` on macOS/Linux, so it uses the project dependencies even if Electron was launched from a terminal where the virtual environment is not activated. Set `ALEX_PYTHON` to override this interpreter. The React renderer communicates only through the typed preload bridge.

To run the backend by itself from `Alex\backend` for local API development, use `python -m app.main --port 8765`. The entry point also supports `python app/main.py`; if no port is supplied, it defaults to `8765`. Standalone API requests still require a bearer token (`ALEX_API_TOKEN`); normal desktop development should use Electron so it can provide the token securely.

## Tests and checks

```powershell
python -m pytest backend\tests
npm --prefix frontend test
npm --prefix frontend run build
```

Keep tests focused on service/API behavior and renderer behavior. Do not put real API keys, personal memory or screenshots in fixtures.

## Code organization

- Add API request/response contracts under `backend/app/schemas/`.
- Keep business rules in `backend/app/services/`, not FastAPI route functions.
- Keep disk/credential access behind backend repositories/services.
- Add one explicitly typed IPC operation at a time; update preload declarations and main-process validation together.
- Renderer code must not import Electron, Node, backend files or arbitrary IPC APIs.
- Add a feature to `FEATURE_MIGRATION_STATUS.md` only when real implementation work begins; mark Complete only with parity tests.

## Configuration, logs and errors

- Runtime configuration is environment-based; secrets must use the OS credential store.
- Use standard Python logging and avoid logging credentials, user memory or message contents unnecessarily.
- Backend errors must remain explicit through HTTP/IPC and be shown in the UI.
- Text conversation and attached-file analysis require a Gemini API key in the system keychain; chat context is in-memory only and is cleared when Alex closes.
- Live voice additionally requires an OS microphone grant. Alex captures mono PCM in an audio worklet, resamples to 16 kHz, and streams it through Electron main to the authenticated Python WebSocket; 24 kHz response audio is played in the renderer. Validate on real hardware before enabling voice in a release.
- Text entered while the microphone is active is sent into that same Gemini Live session and is included in its transcript. With the microphone stopped, text chat uses the separate REST conversation service.
- Grounded web search is available from the feature drawer in search, news, research, price, and comparison modes. Gemini grounding returns source links when available; opening a link is an explicit user action handled by the restricted external-link IPC method. Search results are untrusted data and are not passed into desktop actions.
- The same panel can open a Google weather search for a city/time. Electron main validates the bounded fields and constructs the URL; this deliberately preserves Mark LVI's browser-search behavior and does not provide structured forecast data.
- The two header buttons open mutually exclusive Setup and Controls drawers. The Setup drawer routes to migrated settings, memory, search and conversation pages. The Controls drawer invokes fullscreen and current voice-session actions. Voice choices (Charon, Puck, Kore, Fenrir, Aoede) are saved in settings and apply to the next Gemini Live connection.
- Windows can create an Alex shortcut on the current user's desktop and Windows/macOS can enable login-at-startup from Setup. These are explicit user-triggered native operations; shortcut creation refuses to overwrite an existing shortcut. Linux startup and non-Windows shortcuts are not supported by this UI.
- Drawer actions whose source-backed services are not migrated yet—remote control, provider/plugin administration, morning briefing and wake word—are visibly disabled rather than represented as functioning controls. Push-to-talk is a persisted focused-window Ctrl+Space gate: start a Live microphone session first, then hold the chord to transmit audio; releasing sends silence. It is not a global hotkey.
- Audio Devices opens an input/output selector. Device labels can require microphone permission; requesting that permission is explicit. Input/output selections are saved locally and applied at the next voice session. Use the microphone test to check for captured signal and the speaker test to play a brief tone; actual device and output-routing support depends on the Electron/OS audio backend. HUD style can be switched between the animated face and reactor core.
- Reminders are stored in the local backend and checked while the Alex desktop app is running. Due reminders use Electron desktop notifications, with an in-app notice if OS notifications are unavailable. They do not fire while Alex is closed; do not rely on them for critical deadlines.
- The HUD system monitor reads host metrics through the authenticated `/api/v1/system/metrics` route. N/A GPU/temperature readings mean those sensors are not exposed by the current host/backend.
- Resource alerts use the authenticated `/api/v1/system/alerts` route and are checked every 10 seconds. CPU must exceed 90% for three samples; memory, GPU and temperature thresholds are 90%, 95% and 85 C, with a five-minute per-metric cooldown. Alerts use Electron notifications and an in-app fallback.
- Attachments are limited to 8 MiB and supported image, audio, video, PDF, and text/code/data MIME types. Do not pass filesystem paths from the renderer.
- Do not use shell command strings for OS operations. Any migrated OS action belongs in a bounded backend service.

## Feature workflow

1. Read the corresponding source implementation and inventory entry.
2. Define behavior, input/output, permission and failure semantics.
3. Add Pydantic schema and service tests.
4. Add a narrow authenticated API and allowlisted IPC method.
5. Add UI loading/error/confirmation states and renderer tests.
6. Validate behavior on the target OS and update migration status and docs.

The staged plan and known source gaps are in [../archive/migration-analysis/MIGRATION_PLAN.md](../archive/migration-analysis/MIGRATION_PLAN.md).
