# Mark LVI Feature Inventory

## How to read this inventory

Each feature below was identified from implementation in `../../Mark-LVI-main/`. “Migration” is a design direction, not a claim that Alex already implements it. See [FEATURE_MIGRATION_STATUS.md](./FEATURE_MIGRATION_STATUS.md) for current delivery state. README-only plugin functions are listed separately as unavailable source.

## Conversation and presentation

### Real-time assistant conversation
- **Purpose:** Multilingual voice-first assistant with typed commands and tool use.
- **Current implementation:** Gemini Live session in `main.py`; `JarvisLive` handles PCM streams, transcripts, session events, tool dispatch, reconnects and turn state.
- **Dependencies:** `google-genai`, asyncio, `sounddevice`, NumPy, API key.
- **Input / output:** 16 kHz mono microphone audio or text; streamed 24 kHz audio, transcripts, tool calls and UI state.
- **Workflow:** Build prompt/tools → connect → run capture/send/receive/play loops → dispatch tools → continue or reconnect.
- **External integrations:** Gemini Live API.
- **Migration approach:** Python conversation/session service with explicit lifecycle and typed events; Electron receives only allowlisted event and command IPC.
- **Potential risks:** Live API protocol/model changes, audio device variability, session stalls, cancellation and preserving prompt/turn behavior.

### Text input and activity/transcript log
- **Purpose:** Let the user type into the same active conversation and review user/assistant turns in the activity log.
- **Current implementation:** `ui.py` logs typed text and invokes the `JarvisLive._on_text_command` callback; `main.py` submits it as a user turn to the active Gemini Live session and appends completed input/output transcripts to the session log.
- **Dependencies:** PyQt6 UI callback, Gemini Live session, `google-genai`.
- **Input / output:** User-entered text; transcript/log entries and the active session's assistant response.
- **Workflow:** Submit text → send a completed user turn to the active Live session → collect response transcription → log the completed exchange.
- **External integrations:** Gemini Live API.
- **Migration approach:** Alex has authenticated Gemini chat through IPC, bounded in-memory conversation context, saved-memory injection, a REST model fallback, HUD activity entries and bounded user-selected attachments. Typed input now joins the active Live session, though tool/event workflows and durable transcript storage remain.
- **Potential risks:** Different model/session context from voice, external API quotas, loss of in-memory context when the app exits and no tool execution in the text UI.

### One-shot model calls and model fallback
- **Purpose:** Support planning, summaries, image reasoning, search and other non-conversation model work.
- **Current implementation:** `core/gemini.py` centralizes tiered model ladders, timeouts, cooldowns, optional provider priority and typed/text/JSON wrappers.
- **Dependencies:** `google-genai`; optionally `providers/llm_openai.py` and HTTPX.
- **Input / output:** Text, image or structured prompts; text/JSON/model response.
- **Workflow:** Select tier → attempt available ladder rungs → cool down quota/unavailable models → return result or explicit failure.
- **External integrations:** Gemini models and optional OpenAI-compatible local/cloud servers.
- **Migration approach:** Alex's current text conversation has an SDK timeout, a REST model fallback and process-local model cooldowns. Grounded search also has a dedicated Gemini search call. A shared tiered one-shot provider interface and optional provider adapters are not yet migrated.
- **Potential risks:** Quota cost, provider-specific schemas, multimodal compatibility and preserving source-grounding metadata.

### Web search, news, research, price lookup and comparison
- **Purpose:** Return current web-grounded answers with source references rather than guessing.
- **Current implementation:** `actions/web_search.py` uses Gemini Google Search grounding, DuckDuckGo text/news fallback, specialized query modes and a grounding-quota circuit breaker.
- **Dependencies:** `google-genai`; `ddgs` for fallback.
- **Input / output:** Query, mode, and optional comparison items/aspect; synthesized answer and source links (or formatted fallback results).
- **Workflow:** Build mode-specific query → try grounded Gemini → use a cooldown after quota exhaustion → fall back to DuckDuckGo when Gemini fails → return untrusted result content to the conversation.
- **External integrations:** Gemini Search grounding and DuckDuckGo.
- **Migration approach:** Alex implements grounded Gemini search/news/research/price/compare queries through authenticated API/IPC and shows source links opened only after an explicit user click. DuckDuckGo fallback and the original untrusted-content wrapper are not yet migrated.
- **Potential risks:** Grounding quota, stale/low-quality sources, hostile page content, and external-link navigation. Treat answers as untrusted and inspect source provenance.

### Alternative STT/LLM/TTS pipeline
- **Purpose:** Keep conversation available with local models, other APIs and offline speech.
- **Current implementation:** `providers/base.py`, registry/schema/audio adapters and `PipelineEngine`; OpenAI-compatible chat, faster-whisper/remote STT and Piper/system/ElevenLabs TTS.
- **Dependencies:** Optional `httpx`, `faster-whisper`, Piper, system speech tools and ElevenLabs credentials.
- **Input / output:** PCM/text/tools; Live-shaped transcript/audio/tool events.
- **Workflow:** Capture and detect speech → transcribe → LLM generation/tool cycle → synthesize audio → stream events.
- **External integrations:** Local model servers, hosted LLM/STT/TTS APIs, Hugging Face model downloads and ElevenLabs.
- **Migration approach:** Keep provider protocols separate from conversation and UI, implement provider adapters incrementally.
- **Potential risks:** High download size, slow first-run model loads, differing tool-call semantics and language/latency regressions.

### Audio devices, push-to-talk and wake word
- **Purpose:** Choose microphone/speakers; support hold-to-speak and optional hands-free wake.
- **Current implementation:** `core/audio_devices.py` filters/probes device APIs and stores device names; `core/hotkey.py` polls a global Windows chord and uses a window-scoped shortcut elsewhere; `core/wake_word.py` runs local openwakeword inference and optional download.
- **Dependencies:** sounddevice; platform key hooks; optional `openwakeword` model.
- **Input / output:** User settings and microphone frames; device streams, push state, wake/sleep state.
- **Workflow:** Probe devices → open selected streams → gate microphone on PTT/wake state → auto-sleep after inactivity.
- **External integrations:** OS audio backends and optional model download.
- **Migration approach:** Alex persists browser device IDs and exposes explicit permission/testing controls. Its focused-window Ctrl+Space PTT gate sends silence when released; global Windows polling and local wake-word lifecycle remain staged.
- **Potential risks:** Device changes, microphone privacy, global-hotkey differences and model-download UX.

### Avatar, transcript lip-sync and echo handling
- **Purpose:** Animated face/status display and prevent the assistant replying to its own speaker output.
- **Current implementation:** `core/avatar.py`, `avatar_mesh.py`, `face_model.obj`, `viseme.py`, `main.py` spectral audio analysis and `core/echo.py`.
- **Dependencies:** PyQt6 painter, NumPy and shipped face mesh asset.
- **Input / output:** Audio levels, transcript, state and theme; animated face/mouth and echo classifications.
- **Workflow:** Analyze audio/transcript → schedule visemes against playback → render avatar; compare mic with recent output.
- **External integrations:** None beyond local audio hardware.
- **Migration approach:** Reimplement the status/avatar UX in React/CSS/canvas only after conversational behavior; preserve a no-GPU fallback.
- **Potential risks:** Visual behavior cannot be ported line-for-line; timing and echo performance require real-device validation.

### UI setup, settings and activity display
- **Purpose:** First-run key setup, chat/activity, state, settings, theme, audio/providers, memory, plugin controls, confirmation and media panels.
- **Current implementation:** Large PyQt6 UI in `ui.py`, with callbacks, Qt signals, workers and local styling.
- **Dependencies:** PyQt6, config manager and runtime services.
- **Input / output:** User settings, text, file selection, UI actions; config updates, activity/status, confirmations and content panels.
- **Workflow:** Show setup if not configured → display HUD → open drawers/panels → invoke callbacks → persist changes.
- **External integrations:** OS file dialogs and desktop shortcut/autostart behavior.
- **Migration approach:** React component/page architecture and typed store; Electron main owns native dialogs and window operations.
- **Potential risks:** The UI is a 5K+ line monolith with undocumented callback contracts; settings parity and keyboard UX need explicit tests.

### Top-bar setup and controls drawers
- **Purpose:** Separate one-time setup choices from everyday controls using two compact dashboard menus.
- **Current implementation:** `ui.py` builds a Setup drawer (remote control, shortcut, auto-start, assistant customization, audio devices, memory, plugins, plugin settings, and engine/providers) and a Controls drawer (fullscreen, morning briefing, wake/sleep, push-to-talk, and HUD style).
- **Dependencies:** PyQt6; settings/config manager; OS startup and shortcut APIs; audio device service; provider/plugin registries; wake-word and hotkey services.
- **Input / output:** User menu selections; settings persistence, page/overlay changes, platform actions and conversation lifecycle updates.
- **Workflow:** Toggle one drawer from the header → choose a setup or daily-control action → validate/save preference or invoke the owning service → update visible state and activity log.
- **External integrations:** OS startup/shortcut facilities, audio devices, provider services and optional plugins.
- **Migration approach:** Alex now has separate Setup and Controls drawers. Settings, memory, search, conversation, fullscreen, microphone controls, audio-device management, face/core HUD selection, five supported Gemini Live voice choices and focused-window Ctrl+Space push-to-talk are wired. Native desktop shortcuts are created on Windows only; login-at-startup is supported on Windows/macOS. Remote control, provider/plugin administration, morning briefing and wake word remain staged for migration; missing plugin implementations are not exposed as working features.
- **Potential risks:** OS side effects require explicit user intent and platform-specific verification; audio identifiers can change; optional provider/plugin code must not be dynamically trusted.

### Persistent reminders
- **Purpose:** Notify the user at a chosen local date and time.
- **Current implementation:** Mark LVI schedules standalone OS tasks on Windows, macOS and Linux and invokes a notification script when they fire.
- **Dependencies:** Platform task schedulers, OS notification APIs and packaged Python execution.
- **Input / output:** Message plus date/time; scheduled desktop notification.
- **Workflow:** Validate a future date/time → register a platform job → display a notification at the due time.
- **External integrations:** Windows Task Scheduler, launchd, systemd/`at`, and desktop notification services.
- **Migration approach:** Alex stores timezone-aware reminders through its authenticated backend, supports listing/cancellation, polls due entries and only marks a reminder delivered after the desktop notification is handled.
- **Potential risks:** Current delivery is app-session scoped; reminders are not fired while Alex is closed. Time-zone changes, daylight-saving transitions, notification permissions, and system scheduler integration remain to be implemented and tested.

### System monitoring and hardware alerts
- **Purpose:** Watch resource and sensor levels and alert the user when a threshold is exceeded.
- **Current implementation:** `actions/system_monitor.py` checks CPU, RAM, GPU and temperature with CPU streak/debounce and a per-sensor cooldown; GPU and thermal data are explicitly unavailable where sensors cannot be read.
- **Dependencies:** `psutil`, optional NVML/WMI sensor interfaces and the active conversation for source voice alerts.
- **Input / output:** Host metric samples; localized system warning.
- **Workflow:** Sample metrics periodically → apply threshold/cooldown checks → send an alert only when the assistant is awake and not interrupting speech.
- **External integrations:** OS hardware sensor APIs and Gemini Live for spoken warnings.
- **Migration approach:** Alex uses its authenticated metrics service, three-sample CPU debounce, source thresholds and per-metric cooldowns, surfacing notifications through Electron without interrupting conversation.
- **Potential risks:** Sensor APIs vary by device/OS; GPU and temperature values are unavailable on many systems. Current Alex monitoring requires its desktop process to be running and has not been hardware-validated.

## Memory, safety and extension boundaries

### Persistent memory and session continuity
- **Purpose:** Remember user facts, support local recall and make prior conversation available on later sessions.
- **Current implementation:** `memory/memory_manager.py` stores category/key/value/date records in JSON, trims runaway size, budgets prompt content and performs local search; session summaries are saved and consumed.
- **Dependencies:** Python JSON/filesystem and model summarization.
- **Input / output:** Model memory updates, recall query, session turns; persisted facts and prompt text/search results.
- **Workflow:** Merge and timestamp facts → atomically? (current implementation writes JSON directly) → render a prompt core/index → search full store on recall.
- **External integrations:** Gemini/provider for session summarization only.
- **Migration approach:** Versioned Pydantic schemas, atomic writes and migration for existing JSON; keep data local and user-visible.
- **Potential risks:** Corrupt/partial writes, personal-data handling, old schema compatibility and data loss during conversion.

### Undo and human confirmation
- **Purpose:** Reverse selected actions and gate genuinely irreversible operations.
- **Current implementation:** `core/undo.py` keeps up to ten in-memory closures; file/settings actions register selected reversals. `core/confirm.py` presents a UI confirmation with a 90-second timeout and executes accepted work off the UI thread.
- **Dependencies:** Action handlers and UI callbacks.
- **Input / output:** Undo/list tool request or human confirm/cancel; status/result.
- **Workflow:** Capture prior state → execute reversible action and register inverse, or queue irreversible callable → explicit human decision.
- **External integrations:** OS-level action handlers.
- **Migration approach:** Typed action receipts and explicit confirmation IDs; never accept “confirmed” only from a model parameter.
- **Potential risks:** Undo state is lost on restart; captured data can be stale; destructive actions need careful policy and duplicate-click handling.

### Action and plugin discovery
- **Purpose:** Add skills without hard-coding every declaration in the orchestrator.
- **Current implementation:** `core/action_loader.py` discovers/validates `TOOL` declarations; `core/plugin_loader.py` discovers `PLUGIN` declarations and reads enabled/config state dynamically. Only `_template.py` exists as a plugin implementation in this checkout.
- **Dependencies:** Python importlib and configuration.
- **Input / output:** Local module declarations and action arguments; schema declarations, results and settings metadata.
- **Workflow:** Import candidates → validate/collision-check → advertise enabled tools → dispatch with declared runtime context.
- **External integrations:** Whatever a plugin/action uses.
- **Migration approach:** Prefer an explicit, reviewed Python service registry over arbitrary renderer-loaded code; define a signed/permissioned extension model only if concrete plugins are in scope.
- **Potential risks:** Dynamic imports execute code; model tool schemas are vendor-specific; README-only plugins have no source to port.

### Runtime capability and safe outcome reporting
- **Purpose:** Tell the model and user what this machine can actually do and avoid claiming unverified results.
- **Current implementation:** `core/platform_support.py`, `core/outcome.py` and `core/appidentity.py` report OS limits, normalize app matching, protect the assistant's own process and classify outcomes.
- **Dependencies:** Platform APIs and optional psutil.
- **Input / output:** Platform/process observations and tool result; model capability prompt and typed outcome strings.
- **Workflow:** Detect platform → filter tools/describe limits → perform action → verify when possible → classify result.
- **External integrations:** OS process/window facilities.
- **Migration approach:** Central capability service and typed Pydantic result enum.
- **Potential risks:** Permission APIs can misreport success; platform probes can be incomplete; do not silently broaden capability.

## Monitoring and scheduling

### System status and hardware monitoring
- **Purpose:** Answer live system questions and proactively alert on high CPU/RAM/GPU/temperature.
- **Current implementation:** `actions/system_monitor.py` uses psutil, optional NVML/pynvml and WMI; a polling service applies thresholds, CPU streak and per-metric cooldown.
- **Dependencies:** psutil, optional NVIDIA/WMI support.
- **Input / output:** Timer ticks or status tool; CPU/RAM/temp/GPU/uptime/process count and alert prompts.
- **Workflow:** Poll metrics → apply thresholds/cooldown → log or inject alert into session.
- **External integrations:** OS hardware telemetry.
- **Migration approach:** Backend telemetry service with configurable thresholds and a typed event channel.
- **Potential risks:** Hardware sensors are absent/inconsistent and polling can add load.

### Topic monitoring, proactive check-ins and briefing
- **Purpose:** Check user-selected topics for new headlines; deliver news and context-aware prompts.
- **Current implementation:** `actions/background_monitor.py` stores topic state in the memory JSON and checks DDG news once daily; `actions/proactive.py` gates check-ins by silence/cooldown and rotates context; `main.py` schedules background checks, startup briefing and session summaries.
- **Dependencies:** DDG search, Gemini grounding/summarization, memory and session lifecycle.
- **Input / output:** Topics, memory, recent turns and clock; alert/news text injected into conversation.
- **Workflow:** Wait for startup/silence gate → fetch once per topic/day → compare headline hash → inject new alert or generated check-in.
- **External integrations:** DuckDuckGo and Gemini.
- **Migration approach:** Separate scheduler and notification service with opt-in settings, idempotent jobs and explicit cancellation.
- **Potential risks:** Time zone/day boundaries, network failure, duplicate alerts and uninvited speech.

### Reminders
- **Purpose:** Schedule a future desktop notification.
- **Current implementation:** `actions/reminder.py` creates a protected per-reminder script and registers it with Windows Task Scheduler, macOS LaunchAgents or Linux `systemd-run`/`at` paths.
- **Dependencies:** Native schedulers/notification tools and current Python executable.
- **Input / output:** Reminder text/time; OS scheduled task and later notification.
- **Workflow:** Normalize date/time → write script → register task → notify user; script removes itself after firing.
- **External integrations:** OS scheduler and notification system.
- **Migration approach:** Backend scheduler abstraction with durable records, cancellation and permission-aware UI.
- **Potential risks:** Platform-specific task formats, app uninstall/upgrades and timezone/DST behavior.

## Computer, file and web actions

### Application launch and identity matching
- **Purpose:** Open or close applications by natural name and report whether the outcome was observed.
- **Current implementation:** `actions/open_app.py` launches without a shell and watches for a process; `core/appidentity.py` normalizes/ranks candidates and protects the assistant's own processes.
- **Dependencies:** OS launcher, psutil and optional PyAutoGUI desktop search.
- **Input / output:** Application name; verified `done`, `unverified`, ambiguity or failure result.
- **Workflow:** Normalize aliases → launch through platform API → observe process/window change → report evidence.
- **External integrations:** OS process and window APIs.
- **Migration approach:** Python app-launch service with explicit allowlisted request schema and per-OS adapters.
- **Potential risks:** Store apps, launchers and background processes do not have uniform process evidence.

### Computer settings and shortcuts
- **Purpose:** Adjust volume/brightness/Wi-Fi/power and control windows, keyboard, clipboard, browser shortcuts and screenshots.
- **Current implementation:** `actions/computer_settings.py` implements a large named action map and platform-specific commands; `actions/computer_control.py` handles broader keyboard/mouse/data-entry tasks.
- **Dependencies:** PyAutoGUI/pyperclip and optional pycaw/comtypes/WMI/native commands.
- **Input / output:** Typed action, parameters and sometimes text; OS state change, captured screenshot or action status.
- **Workflow:** Validate action/arguments → use platform adapter → verify measurable state where possible → register undo or request confirmation for irreversible operations.
- **External integrations:** OS settings, accessibility/window APIs and clipboard.
- **Migration approach:** Split by capability into independently tested Python services; expose no arbitrary key/shell command endpoint to renderer.
- **Potential risks:** Very broad privilege surface, OS permissions, focus races and destructive shutdown/network actions.

### Desktop personalization and organization
- **Purpose:** Set wallpaper and list/organize/clean desktop items and report desktop statistics.
- **Current implementation:** `actions/desktop.py`; its former generated-Python `exec()` path is intentionally removed. Remaining actions are a bounded set.
- **Dependencies:** Filesystem, OS wallpaper APIs and optional Pillow.
- **Input / output:** Desktop action and path; changed wallpaper/files or listing/statistics.
- **Workflow:** Validate named action → resolve desktop path → invoke platform/filesystem operation → return bounded result.
- **External integrations:** OS desktop settings.
- **Migration approach:** Reuse safe filesystem service, use explicit actions and undo/confirmation rules.
- **Potential risks:** Desktop path differs by OS; cleanup/organization can alter user data.

### Browser automation
- **Purpose:** Navigate and interact with a browser, read page text and support web workflows.
- **Current implementation:** `actions/browser_control.py` uses Playwright, profile discovery, browser/session lifecycle and a declared action schema; module discovery rejects missing Playwright.
- **Dependencies:** Playwright package and installed browser binaries.
- **Input / output:** Browser action, URL/selector/text; page text, screenshot or status.
- **Workflow:** Start browser context → navigate/interact → extract bounded page state → return to model/action.
- **External integrations:** Arbitrary websites and browser engines.
- **Migration approach:** Isolated browser service with URL/scheme checks, explicit user permissions and cancellable sessions.
- **Potential risks:** Website changes, profile/session privacy, untrusted page prompt injection and arbitrary web navigation.

### Filesystem management
- **Purpose:** List/read/create/write/move/copy/rename/trash/search files, inspect disk usage and organize desktop.
- **Current implementation:** `actions/file_controller.py` resolves common directory shortcuts, constrains operations to the user's home roots, uses recoverable trash when available and registers undo for selected changes.
- **Dependencies:** Standard filesystem, optional send2trash and platform trash support.
- **Input / output:** Paths, names, contents, search filters; file results and operation status.
- **Workflow:** Resolve paths → enforce safe-root rules → apply operation → register inverse where possible → report.
- **External integrations:** OS filesystem and recycle bin/trash.
- **Migration approach:** Python file service with canonical path checks, file-size limits, atomic write and a per-operation confirmation policy.
- **Potential risks:** Symlinks/path traversal, overwrite races, permissions, huge files and undo snapshots.

### File/document/media processor
- **Purpose:** Process supported image, PDF, DOCX/text, CSV/XLSX, JSON/XML, code, audio/video, archive and PPTX files.
- **Current implementation:** `actions/file_processor.py` dispatches by extension and offers image analysis/OCR/transforms, document extraction/summarization, tabular operations and media/archive actions. Some paths use optional dependencies or external tools.
- **Dependencies:** Gemini, Pillow/OpenCV, pdfplumber/PyPDF2, python-docx/python-pptx, optional pandas/pydub/ffmpeg and other libraries.
- **Input / output:** Path, operation and options; text, analysis or new file.
- **Workflow:** Detect type → validate requested operation → parse/transform or call model → save derived result as applicable.
- **External integrations:** Gemini and local codecs/tools.
- **Migration approach:** Separate per-format services and tests; move large/slow tasks to background jobs and report progress.
- **Potential risks:** Untrusted documents, parser vulnerabilities, large-file memory use, conversion fidelity and optional dependency gaps.

### Search and current information
- **Purpose:** Search, news, research, price and comparison queries.
- **Current implementation:** `actions/web_search.py` uses Gemini grounded search with DuckDuckGo fallback, quota breaker, bounded tasks and an untrusted-content wrapper.
- **Dependencies:** Gemini and ddgs (legacy duckduckgo-search fallback).
- **Input / output:** Query/mode/items; result text, links and snippets.
- **Workflow:** Select mode and preferred source → fallback on quota/network failure → wrap external text as untrusted.
- **External integrations:** Google grounding and DuckDuckGo.
- **Migration approach:** Backend search adapter with citations/provenance and strict separation of retrieved content from instructions.
- **Potential risks:** Search quota, external content/prompt injection, source freshness and API changes.

### Weather lookup
- **Purpose:** Show weather information for a city/time.
- **Current implementation:** `actions/weather_report.py` constructs a Google search URL and opens it in the system browser; it does not parse a forecast API response.
- **Dependencies:** OS browser URL handler.
- **Input / output:** City; browser launch and activity message.
- **Workflow:** Validate city → open search URL → report that the page was shown.
- **External integrations:** Google Search page.
- **Migration approach:** Alex preserves the “open search” behavior through a city/time-validated IPC method that constructs a Google search URL in Electron main. It does not claim structured forecast data.
- **Potential risks:** Browser launch can be unverified; displayed page behavior may change.

### Flight finder
- **Purpose:** Find flight options from an origin/destination/date request.
- **Current implementation:** `actions/flight_finder.py` parses dates, constructs Google Flights URL, uses browser automation and model parsing for visible results.
- **Dependencies:** Playwright/browser action and Gemini.
- **Input / output:** Airports/cities, dates, passenger count and cabin; flight options or browser/page result.
- **Workflow:** Normalize date → open/search Google Flights → extract page text → ask model to return structured options.
- **External integrations:** Google Flights and Gemini.
- **Migration approach:** Prefer a licensed flight-data API if structured, durable results are required; otherwise isolate browser scraping.
- **Potential risks:** Search UI changes, stale prices, extraction errors and date ambiguity.

### Messaging
- **Purpose:** Send text through selected chat services.
- **Current implementation:** `actions/send_message.py` opens applications/sites and types via keyboard automation; WhatsApp attempts to import `plugins._whatsapp_core`, which is absent in this checkout, then falls back to blind typing. Non-verified paths report unverified outcomes.
- **Dependencies:** PyAutoGUI/pyperclip, OS app/browser and optional WhatsApp driver.
- **Input / output:** Platform/contact/message; attempted send and verified/unverified/failure result.
- **Workflow:** Select platform → open/search recipient → type/send → verify only when a specific driver can read back state.
- **External integrations:** Messaging apps/sites and potentially WhatsApp session state.
- **Migration approach:** Implement platform-specific adapter only with explicit user selection/confirmation and trustworthy verification.
- **Potential risks:** Sending to wrong recipient, unintended external communication, unavailable driver source and UI timing.

### YouTube search, playback and summaries
- **Purpose:** Search/open YouTube videos, read info/trending and summarize transcripts.
- **Current implementation:** `actions/youtube_video.py` scrapes search/watch/trending pages, uses `youtube-transcript-api` and Gemini for summaries, and can open a URL. `actions/video_player.py` resolves local/direct media and YouTube streams with yt-dlp and presents video in the HUD.
- **Dependencies:** requests, optional transcript API, Gemini, yt-dlp and Qt Multimedia.
- **Input / output:** Query/URL/action; browser/video playback, transcript summary or saved file.
- **Workflow:** Resolve URL/query → fetch transcript or media stream → summarize or render → optionally save.
- **External integrations:** YouTube, transcript service and Gemini.
- **Migration approach:** Keep search/summarization and desktop video playback separate; show progress and explicit source attribution.
- **Potential risks:** Scraping/API terms, unavailable transcripts, signed stream expiry, codec support and possible duplicate YouTube behavior in README.

### Reminders and media
- **Purpose:** Deliver scheduled notifications and play/mute/stop content in the HUD center.
- **Current implementation:** See Reminders above; `actions/video_player.py` requests media UI callbacks and resolves YouTube with yt-dlp, while `ui.py` uses Qt Multimedia when available.
- **Dependencies:** OS scheduler/notification backend; optional yt-dlp and Qt Multimedia plugins.
- **Input / output:** Reminder time/text or media source/action; notification or video state.
- **Workflow:** Schedule OS task or resolve source → update UI → start muted → user may unmute/stop.
- **External integrations:** OS notifications and YouTube/media hosts.
- **Migration approach:** Use native Electron media view only after confirming supported sources; Python owns resolution and only sends validated source state.
- **Potential risks:** Media URL lifetime, codecs, microphone echo and platform scheduler differences.

### Game updater
- **Purpose:** Search/install/update known Steam games.
- **Current implementation:** `actions/game_updater.py` detects Steam installations per OS, maps game names to app IDs and drives launcher/install/update workflows.
- **Dependencies:** Steam install files/registry, OS process/window controls and optional pywinauto/pygetwindow.
- **Input / output:** Game name and requested operation; launcher state and result.
- **Workflow:** Resolve game/app ID → locate Steam → inspect/install/update via platform-specific route.
- **External integrations:** Steam client and game catalog.
- **Migration approach:** Isolate to opt-in desktop automation with clear confirmation before installs/updates.
- **Potential risks:** Steam UI changes, account state, large downloads and README classifying this as a plugin despite action source being present.

### Code helper and development agent
- **Purpose:** Generate/edit/explain/run/build or iteratively debug code and multi-file projects.
- **Current implementation:** `actions/code_helper.py` classifies intent and uses model generation/file writes/subprocess execution; `actions/dev_agent.py` plans project files, writes them and iterates on execution errors.
- **Dependencies:** Gemini/provider calls, filesystem, Python/runtime toolchains, and screen capture for screen-debug paths.
- **Input / output:** Description, code/path/language or project request; code files, previews, execution/build output.
- **Workflow:** Classify/plan → read or generate source → write files → optionally execute/test → iterate on errors.
- **External integrations:** Model API and local toolchains.
- **Migration approach:** Treat as a distinct high-risk feature; define workspace allowlists, execution sandbox and approval before any run/build command.
- **Potential risks:** Arbitrary generated code execution, data loss/overwrite, command side effects and model-produced dependency installation.

## Remote access

### Phone dashboard
- **Purpose:** Remote text/audio commands, wake, status/events and file transfer from a paired phone.
- **Current implementation:** `dashboard/server.py` runs FastAPI/uvicorn, serves login/app pages, issues pairing/session/device tokens, provides WebSockets, commands, uploads and files. Optional TLS is configured in local JSON; HTTP mode has weaker transport guarantees.
- **Dependencies:** FastAPI, uvicorn, cryptography, python-multipart, qrcode and LAN/firewall behavior.
- **Input / output:** Pairing key, authenticated text/audio, upload and wake actions; conversation events/status/downloads.
- **Workflow:** Generate short-lived pairing key/QR → authenticate → open WS/API session → enqueue commands/audio → broadcast updates/files.
- **External integrations:** LAN clients, OS firewall/certificate tools and assistant session.
- **Migration approach:** Keep as a separately permissioned opt-in feature; establish authenticated local API/WebSocket contracts before implementation.
- **Potential risks:** LAN exposure, insecure HTTP mode, pairing UI/code length mismatch, uploads, token revocation and firewall side effects.

## Source claims without corresponding implementation

The current checkout does not contain concrete plugin modules for WhatsApp calls/guard, Telegram remote, chat takeover, screen agent, Gmail/Calendar, Obsidian, document review, Excel writing, image generation, YouTube upload, printer/home automation, shopping list, pomodoro, hydration, quiz, spaced repetition, calorie counter or pushup counter. Some names overlap with source-backed actions (for example game updater, flight finder, code helper, dev agent and YouTube). The README is evidence of prior/intended scope, not executable implementation. These items remain **unverified / source missing** and must not be replaced with invented behavior.
