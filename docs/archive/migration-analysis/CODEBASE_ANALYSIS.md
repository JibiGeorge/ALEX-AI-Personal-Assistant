# Mark-LVI-main Codebase Analysis

## Scope and method

This analysis is based on the checked-out source under `../../Mark-LVI-main/`, not on the README alone. The original tree was inspected without modification. The checkout contains 75 listed paths (65 Python files, two HTML pages, one JavaScript file, configuration/assets and project metadata). No Electron or frontend package manifest is present.

The documented behavior in `readme.md` is not always backed by files in this checkout. Items with missing implementation are called out explicitly rather than treated as working features.

## Executive summary

Mark LVI is a cross-platform, local desktop voice assistant. Its application is a Python/PyQt6 monolith with an asynchronous Gemini Live conversation, an audio pipeline, file-discovered actions, JSON-backed settings and memory, and an optional FastAPI phone dashboard. A second, opt-in conversational engine assembles speech recognition, an LLM and speech synthesis behind the Live session interface.

The application has substantial feature depth: live audio and text input, computer and file automation, screen/webcam vision, reminders, monitoring, memory, undo and confirmation flows, media, provider selection and remote phone control. The desktop UI and main orchestrator are large single files, while most actions are separate modules. There is no database and no checked-in user data or API key.

The current checkout does **not** contain the plugin implementations listed in parts of the README; `plugins/` contains only its package initializer and `_template.py`. Therefore those README-only integrations cannot be faithfully migrated from the supplied source.

## 1. Structure and architecture

| Area | Observed responsibility |
|---|---|
| `main.py` | Process entry point and session orchestrator: configures the Gemini Live session, audio capture/playback, tool routing, reconnects, monitoring jobs and dashboard relays. |
| `ui.py` | PyQt6 desktop HUD, setup overlay, settings drawers, status/activity log, audio and provider controls, memory/confirmation panels, video/camera presentation and dashboard pairing UI. |
| `actions/` | 21 modules. Seventeen expose a `TOOL` declaration to `core/action_loader.py`; the rest provide shared runtime services or helpers. |
| `core/` | Audio/session helpers, action and plugin registries, capability reporting, avatar rendering, echo/viseme processing, wake word, confirmation and undo. |
| `providers/` | Optional providers discovered and imported on demand: OpenAI-compatible LLM, Whisper or remote STT, and local/system/ElevenLabs TTS, assembled by `engine_pipeline.py`. |
| `memory/` | JSON settings and long-term memory persistence. |
| `dashboard/` | Optional FastAPI/uvicorn remote-control service and static mobile pages. |
| `plugins/` | Extension loader contract and template only in this checkout; no concrete plugin files are present. |
| `config/` | `__init__.py` provides OS/config helpers. Runtime config and dashboard certificates are generated locally and ignored. |

This is a modularized monolith rather than a client/server desktop application: GUI, orchestration, audio streams, platform automation and API calls share one Python process. The optional phone dashboard is the only separate HTTP service.

## 2. Languages, frameworks and dependencies

- Python 3.11+ is required by `setup.py`; the setup script notes testing through Python 3.12 and warns rather than blocks newer interpreters.
- PyQt6 provides the desktop application; `sounddevice` and NumPy support PCM I/O and analysis.
- `google-genai` provides the Gemini Live session and text/image model calls.
- FastAPI and uvicorn provide the optional local-network dashboard.
- The mobile pages are hand-written HTML/CSS/JavaScript; the dashboard is not a React application.
- Browser automation uses Playwright; ordinary search uses `ddgs` (with a legacy package fallback).
- OS automation uses PyAutoGUI, pyperclip, psutil and platform-native commands/APIs.
- Document/media features use optional or declared libraries such as Pillow, OpenCV, `mss`, pdfplumber, PyPDF2, python-docx, python-pptx, yt-dlp and YouTube transcript support.
- Provider extras include faster-whisper, Piper, HTTPX and ElevenLabs API support. `openwakeword` is installed on demand.
- There is no `package.json`, TypeScript, React, Tailwind, Electron, `pyproject.toml`, or general pytest/Vitest suite in the original project.

See [DEPENDENCY_ANALYSIS.md](./DEPENDENCY_ANALYSIS.md) for the dependency groups and migration implications.

## 3. Entry points and execution flow

1. `python setup.py` installs `requirements.txt` for the detected OS and attempts to install Playwright Chromium and Firefox. Playwright browser installation failure is non-fatal.
2. `python main.py` starts the desktop application. The GUI handles first-run Gemini key setup and application preferences.
3. `JarvisLive` discovers actions and any concrete plugins at initialization, composes the system prompt and tool declarations, then opens the chosen conversational engine.
4. The default engine is Gemini Live. Concurrent asynchronous tasks capture microphone frames, stream them to the session, receive text/audio/tool events, play returned audio, and run monitor/proactive/dashboard tasks.
5. Tool calls are dispatched to inline session-aware handlers, the action registry or plugin registry. Blocking work is moved to executor threads where appropriate.
6. Voice/device changes and failed or stalled sessions trigger controlled reconnects. Conversation context may be resumed when supported.
7. On shutdown, session summaries are saved and session-scoped resources are closed.

The optional engine path uses the providers registry only when selected. `PipelineEngine` adapts STT → LLM → TTS events and tool results to the Live-shaped contract expected by `main.py`.

## 4. Core business logic and workflows

- **Conversation:** real-time, multilingual voice via Gemini Live, with typed text commands, transcript display, interruption, optional push-to-talk, and optional local wake-word gating.
- **Response presentation:** assistant audio and transcripts update the activity log and animated avatar; voice, audio-device and HUD preferences are configured in the UI.
- **Tool use:** typed tool schemas are auto-discovered and passed to the model. Results distinguish verified completion, unverified attempts, failures and user confirmation requests.
- **Computer interaction:** application launching, keyboard/mouse/window control, system settings, filesystem work, browser automation, screen/camera capture, media and messaging are separate action families.
- **Memory and recovery:** categorized facts persist in `memory/long_term.json`; prompt content is budgeted and local recall searches the full store. Reversible actions register closures on a bounded in-memory undo stack; irreversible operations use a UI confirmation gate.
- **Background behavior:** system telemetry, once-daily topic checks, startup news/briefing, session summaries and time/context-aware proactive check-ins run alongside the conversation.
- **Remote operation:** an optional LAN dashboard pairs a phone, relays text/wake/audio, streams state/events and accepts uploads.

The exhaustive implementation-by-feature record, including migration risks, is in [FEATURE_INVENTORY.md](./FEATURE_INVENTORY.md).

## 5. Integrations and data management

- Gemini Live is the main conversational dependency. `core/gemini.py` centralizes one-shot model calls, model fallbacks/cooldowns and optional configured provider use.
- Web search/news uses Gemini grounding and DuckDuckGo with mode-specific fallback behavior. Weather opens a Google search result page rather than implementing a weather-data API.
- Flight search opens Google Flights through browser automation and asks a model to parse the visible page.
- Playwright drives browser sessions; yt-dlp resolves playable YouTube streams; YouTube transcript support retrieves subtitles for summaries.
- A configured OpenAI-compatible provider can target local servers or hosted vendors. Optional STT/TTS providers have their own external services, models and setup requirements.
- OS automation, notifications, audio devices and scheduled reminders depend on platform APIs and installed native tools.
- Persistent data is JSON: `config/api_keys.json`, `memory/long_term.json`, and dashboard certificate material. Monitor state shares the memory JSON. Dashboard pairing/session state is in memory; uploaded files are stored on disk. No SQL or other database is present.

## 6. Configuration and authentication

- User settings, assistant/user names, Gemini key, selected voice, audio devices, feature toggles, plugin settings, provider configuration and dashboard options share `config/api_keys.json`.
- No environment-based configuration or checked-in `.env.example` exists. The Gemini key and provider credentials are stored in the local JSON file; the source does not encrypt that file.
- Long-term facts and session summaries are local JSON data. `.gitignore` excludes the key file, certificates, memory, OAuth tokens, linked WhatsApp state, logs and runtime output.
- Desktop setup is keyed by a locally entered Gemini API key; no separate user account or authorization model exists for the desktop app.
- The remote dashboard uses an expiring pairing key, per-address login throttling, session tokens, device-login/revocation flows and optional HTTPS. HTTPS is configuration-dependent; dashboard content notes when command payload encryption is unavailable over HTTP. The code and old static login page should be reconciled before reuse: server comments describe an eight-character pairing code while `login.html` limits typed input to six characters.
- Dashboard routes expose command, wake, audio, upload and status/file operations. The feature is LAN-facing and requires a newly designed local service boundary in Alex; it must not be copied as an unrestricted renderer capability.

## 7. Background work, logging and error handling

- `asyncio.TaskGroup` owns the session's send/listen/receive/play, reconnect, stall, system-monitor, background-monitor, proactive, wake-sleep and optional dashboard/audio-relay tasks.
- Wake-word inference, OS key polling, action imports and several expensive operations use dedicated threads or executors. The audio callback is intended to keep its work bounded.
- Scheduled reminder delivery delegates to native operating-system schedulers and generated per-reminder scripts.
- Logging is split between `print`/tracebacks and the GUI activity log. Some modules have explicit error classification, timeouts, cooldowns and structured tool outcomes; logging is not centralized or consistently structured.
- Many optional integrations intentionally catch import or platform errors and return a user-readable outcome. Elsewhere, broad catches return empty config/data, print a warning or suppress a failure. The migration should retain useful degraded modes while replacing silent fallbacks with explicit typed results and logs.

## 8. Authentication, safety and privacy observations

- Local API credentials and personal memory are plaintext files in the user's data area. The ignore rules protect source control but do not protect the files at rest.
- Computer-control, file, browser and messaging tools have direct side effects. Existing safeguards include path checks in filesystem actions, outcome verification, explicit human confirmation for irreversible operations and an undo stack for selected reversible operations.
- Generated-code execution formerly existed in `desktop.py` but is explicitly removed; the current desktop action set is bounded. Do not reintroduce generated Python execution as an automation strategy.
- Search results are treated as untrusted content in tool results and the prompt.
- The dashboard is an optional LAN service with pairing/authentication controls. Its pairing lengths, HTTPS mode and static client behavior must be reconciled and tested before migration.
- Electron must keep Node disabled in the renderer, enable context isolation, validate typed IPC requests, and keep backend credentials and filesystem access behind the main process/backend.

## 9. Limitations, technical debt and source-of-truth discrepancies

1. `main.py` and especially `ui.py` are large orchestration/UI modules. Their shared thread/event-loop/UI contracts make incremental extraction and lifecycle testing important.
2. The single JSON settings document is read and written in multiple modules. There is no migration/versioning layer or transactional storage.
3. The README describes numerous concrete plugins and integrations not present in the checkout. The `plugins/` folder only contains the extension contract/template; README-only features are not source-verifiable.
4. `core/installer.py`, `core/llm_client.py`, `core/stt.py` and `core/tts.py` have older MARK XL-era documentation/contracts and overlap with the current `providers/` implementation. Their live call sites should be traced before deciding whether they are legacy.
5. `requirements.txt` declares plugin-only and optional dependencies even though their corresponding plugin files are absent here; this increases install size and complicates distribution.
6. Dashboard documentation and static UI disagree on pairing-key length. The setup UI and code should be treated as the authority only after runtime validation.
7. Error handling is not uniform: console output, generic strings, suppressed exceptions and silent defaults coexist with careful typed outcomes.
8. The original has a self-test for providers (`python -m providers._tests`) but no broad project test suite or desktop/backend integration harness. No build/distribution configuration for Electron or a bundled Python backend exists.
9. External services, OS versions, permissions (Wayland/macOS accessibility/screen recording), codecs, browser versions and native schedulers create platform-specific behavior that needs explicit migration coverage.

## 10. Migration implications

Migrate behavior behind well-defined services rather than translating files line-for-line. Start with configuration, memory, typed API contracts, process lifecycle and a secure IPC bridge. Keep privileged automation in Python and expose narrow, validated operations. Treat computer-control, file writes/deletes, messaging, reminders, wake-word/audio and LAN dashboard as separate feature slices with confirmation, cancellation and integration tests.

Do not claim full parity until each row in [FEATURE_MIGRATION_STATUS.md](./FEATURE_MIGRATION_STATUS.md) has implementation and regression evidence. README-only integrations require their missing original source or explicit scope approval before a faithful migration can be made.
