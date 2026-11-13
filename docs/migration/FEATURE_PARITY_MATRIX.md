# Complete Feature Parity Matrix: Mark-LVI vs. Alex AI Desktop Assistant

**Document Version:** 1.1 (Reconciled Baseline)  
**Inspection Date:** 2026-11-03  
**Status Taxonomy:** `FULL` | `PARTIAL` | `MISSING` | `MISMATCH`  
*(Operational & Environmental Blockers are cataloged separately as orthogonal constraints)*  
**Reference Codebase:** `Mark-LVI-main` (MARK LVI / 56)  
**Target Codebase:** `ALEX-AI-main` (Version `0.1.0`, Baseline Snapshot `SNAPSHOT_v0.1.0-20261102`)  

---

## 1. Executive Summary & Reconciled Parity Dashboard

This authoritative document reconciles the functional inventory of the reference prototype (`Mark-LVI-main`) against the production target (`ALEX-AI-main`).

Following rigorous review, **68 distinct functional units** have been identified across **40 capability categories**. In this reconciled version, every discovered functional unit is assigned **exactly one primary parity status** (`FULL`, `PARTIAL`, `MISSING`, or `MISMATCH`). Operational and environmental constraints (such as physical hardware requirements, AppLocker execution policies, and network egress rules) are decoupled from functional code parity and tracked orthogonally in Section 1.2.

### 1.1 Reconciled Functional Parity Scorecard

```
========================================================================================
                          RECONCILED FEATURE PARITY SCORECARD
========================================================================================
  Total Capabilities Evaluated:            40 Categories / 68 Functional Units
  Total Capabilities in Reference:         68 Units (100.0%)
----------------------------------------------------------------------------------------
  [FULL] Parity Units:                     30 Units (44.1%)
    • Multi-Process CLI Supervisor & Clean Tree Termination (UNIT-01, UNIT-02)
    • Frameless Transparent HUD Window & Acrylic Blur (UNIT-03)
    • Text Chat Streaming, Markdown Rendering & History Persistence (UNIT-06)
    • Cloud Gemini Live Multimodal WebSocket & Interruption (UNIT-07)
    • Cloud Audio Capture & 16kHz PCM Web Audio Streaming (UNIT-14)
    • Voice Lifecycle State Machine (UNIT-20)
    • Structured Fact Storage & Semantic Memory Search (UNIT-24)
    • Dynamic Typed Schema Argument Validation (UNIT-28)
    • Safety Invariant Gating, Latched Stop & Rate Limiting (UNIT-29)
    • Synthetic Mouse & Keyboard Primitives (UNIT-30, UNIT-31)
    • Multi-Monitor Desktop Screen Capture (UNIT-32)
    • Win32 Window Enumeration, Focus & Polite WM_CLOSE (UNIT-34)
    • Sandboxed File Operations & 10-Entry Undo Journal (UNIT-36, UNIT-37)
    • Grounded Web Search via Gemini / DuckDuckGo (UNIT-45)
    • Native OS Desktop Toast Notifications (UNIT-49)
    • Proactive Startup Briefing & System Status (UNIT-50)
    • In-Memory Timer & Countdown Dispatcher (UNIT-52)
    • Typed Application Settings Form & Schema (UNIT-54)
    • Interactive Human Confirmation Gate (UNIT-56)
    • Loopback Bearer Token Authentication (UNIT-57)
    • OS Keyring Vault Secret Storage (UNIT-58)
    • Atomic Document Storage & Write-Rename Safety (UNIT-59)
    • Pre-Flight System Doctor Diagnostics (UNIT-60)
    • Electron Context Isolation & Preload Allowlist (UNIT-62)
    • Hardware Telemetry via psutil (UNIT-63)
    • Multi-Platform Production Bundler Configurations (UNIT-64)
    • Automated Regression Test Suite (UNIT-68)

  [PARTIAL] Parity Units:                   9 Units (13.2%)
    • 3D Wireframe Avatar & MediaPipe Mesh Rendering (UNIT-04 - 2D SVG exists)
    • System-Wide Global Push-to-Talk Hotkey (UNIT-21 - Scoped UI works; CR-02 pending)
    • Audio Endpoint Device Discovery & Routing (UNIT-22 - Browser works; OS pending)
    • Live Peak dB Audio VU Metering (UNIT-23 - Visualizer works; test tone missing)
    • Multi-Mode Web Query Disambiguation (UNIT-46 - Basic search works; modes pending)
    • Persistent OS Schedulers Integration (UNIT-53 - In-memory works; OS sync pending)
    • HueWheel Real-Time Accent Color Tinting (UNIT-55 - Presets work; RGB slider pending)
    • WebSocket Auto-Reconnect Exponential Backoff (UNIT-61 - Basic retry works)
    • OS Capability & Security Boundary Detection (UNIT-67 - OS detected; TCC pending)

  [MISSING] Parity Units:                  26 Units (38.2%)
    • Real-Time Viseme & Formant Audio Lip-Sync (UNIT-05)
    • 9-Rung Model Fallback Ladder & Quota Auto-Downgrade (UNIT-08, UNIT-09)
    • Local OpenAI-Compatible Server Client & Reasoning Filter (UNIT-10, UNIT-11)
    • Multi-Provider Cloud Connectors & Tool Budgeting (UNIT-12, UNIT-13)
    • Local Faster-Whisper STT & Language Detection (UNIT-15, UNIT-16)
    • Local Piper Neural TTS, System Voices & ElevenLabs (UNIT-17, UNIT-18, UNIT-19)
    • Dynamic User Plugin Discovery & Hot-Toggle (UNIT-26)
    • Webcam Video Frame Extraction & Multimodal Vision (UNIT-33)
    • Cross-Platform Window Management for macOS & Linux (UNIT-35 - CR-01 pending)
    • Deep Document Parsing for PDF, DOCX, XLSX, PPTX (UNIT-39, UNIT-40)
    • Autonomous Dev Agent & AST Syntax Linting (UNIT-41, UNIT-42)
    • Playwright Browser Automation & DOM Scraping (UNIT-43, UNIT-44)
    • YouTube Stream Extraction & HUD Video Player (UNIT-47, UNIT-48)
    • Background Topic & RSS News Monitor (UNIT-51)
    • Remote Smartphone Web/WS Dashboard & QR Pairing (UNIT-65)
    • Local Offline Wake-Word Detection Engine (UNIT-66)

  [MISMATCH] Architectural Design Units:    3 Units (4.4%)
    • Action Registry: Dynamic Folder Scan vs. Static Compiled (UNIT-25)
    • Outcome Contract: Five-Word Contract vs. Boolean Success (UNIT-27)
    • File System: OS-Wide Broad Access vs. Strict App Sandbox (UNIT-38)
----------------------------------------------------------------------------------------
  Total Mutually Exclusive Parity Sum:     68 Units (100.0%)
========================================================================================
```

### 1.2 Orthogonal Operational & Environmental Blocker Register

The following operational constraints prevent live physical execution of specific functional units on the test workstation, but do not diminish the fact that the underlying software code and automated unit tests are fully implemented:

| Blocker ID | Blocker Description | Affected Functional Units | Status / Required Action |
| :--- | :--- | :--- | :--- |
| `DEF-A07-001` | Active Directory AppLocker / PowerShell Policy | `UNIT-01` (CLI Launcher) | Corporate GPO restricts `.ps1` execution; external Windows workstation must use unrestricted bypass or `.bat`/compiled runner. |
| `DEF-A07-002` | Interactive Win32 Desktop Station Required | `UNIT-29`, `UNIT-30`, `UNIT-31`, `UNIT-32`, `UNIT-34` | Headless CI or SSH sessions cannot receive synthetic Win32 mouse/keyboard injection; requires active console session (Session 1). |
| `DEF-A07-003` | Physical Audio Input & Output Hardware | `UNIT-14` (PCM Capture) | Virtual machines lacking virtual audio sinks fail Web Audio mic initialization; requires physical soundcard and microphone. |
| `DEF-A07-004` | Outbound TLS 443 Egress to Google Gemini | `UNIT-07`, `UNIT-20` (Live Stream) | Strict proxy or air-gapped network blocks WebSocket to `generativelanguage.googleapis.com`; requires firewall port 443 whitelist. |
| `DEF-A07-005` | Live Gemini API Key in OS Keyring | `UNIT-07` (Gemini Session) | Keyring vault requires authenticated user interaction to securely store and retrieve API credentials. |
| `BLK-ENV-001` | Physical Workstation Acceptance Verification | `UNIT-68` (Release Acceptance) | 0/33 Physical Acceptance Protocols executed on physical hardware; formal release status remains `NOT_AUTHORIZED_FOR_RELEASE`. |

---

## 2. Master 68-Unit Functional Parity Register

| Unit ID | Category | Functional Unit Name | Mark-LVI Reference | Alex Target Implementation | Primary Status | Active Blocker Reference |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `UNIT-01` | `CAT-01` | Multi-Process CLI Supervisor (alex launch/stop) | `Mark-LVI-main/main.py (main() loop)` | `ALEX-AI-main/launcher/cli.py (launch, stop, status)` | **FULL** | DEF-A07-001 (PowerShell policy blocks script on Windows host) |
| `UNIT-02` | `CAT-01` | Pre-Flight Port Check & Clean Tree Termination | `Mark-LVI-main/main.py (_subprocess.Popen)` | `ALEX-AI-main/launcher/process_manager.py, health.py` | **FULL** | None (Verified via backend test_launcher.py) |
| `UNIT-03` | `CAT-02` | Frameless Transparent HUD Window & Acrylic Blur | `Mark-LVI-main/ui.py (JarvisUI frameless acrylic)` | `ALEX-AI-main/frontend/electron/main.ts (transparent BrowserWindow)` | **FULL** | None (Runs in Electron shell) |
| `UNIT-04` | `CAT-02` | 3D Wireframe Avatar & MediaPipe Mesh Rendering | `Mark-LVI-main/core/avatar.py, avatar_mesh.py (QPainter 3D mesh)` | `ALEX-AI-main/frontend/src/components/HudAvatar.tsx (2D SVG/CSS)` | **PARTIAL** | None (Requires Three.js / WebGL port) |
| `UNIT-05` | `CAT-02` | Real-Time Viseme & Formant Audio Lip-Sync (~50 shapes/sec) | `Mark-LVI-main/core/viseme.py (formant audio reduction)` | `None (CSS pulse animation only)` | **MISSING** | None (Requires audio formant analyzer in sidecar) |
| `UNIT-06` | `CAT-03` | Text Chat Streaming, Markdown Rendering & History Persistence | `Mark-LVI-main/ui.py (ChatDrawer), main.py (send_text)` | `ALEX-AI-main/frontend/src/pages/ConversationPage.tsx, backend/app/services/conversation_service.py` | **FULL** | None (Verified via test_conversation_service.py) |
| `UNIT-07` | `CAT-04` | Cloud Gemini Live Bidirectional WebSocket Voice Stream & Interruption | `Mark-LVI-main/core/gemini.py, main.py (JarvisLive)` | `ALEX-AI-main/backend/app/services/live_voice_service.py, frontend/src/hooks/useLiveVoice.ts` | **FULL** | DEF-A07-004 (TLS 443 egress), DEF-A07-005 (Gemini Key) |
| `UNIT-08` | `CAT-05` | 9-Rung Model Fallback Ladder (Cloud / Local) | `Mark-LVI-main/core/gemini.py (MODEL_LADDER: 9 models)` | `None (Hardcoded 2 Gemini models in live_voice_service.py)` | **MISSING** | None (Scheduled for Phase 3: TASK-P3-02) |
| `UNIT-09` | `CAT-05` | 429 Quota Exhaustion Auto-Downgrade & Cooldown Tracker | `Mark-LVI-main/core/gemini.py (catch 429 -> next rung)` | `None (Closes WebSocket with 1011 fatal error)` | **MISSING** | None (Scheduled for Phase 3: TASK-P3-02) |
| `UNIT-10` | `CAT-06` | Local OpenAI-Compatible Server Client (127.0.0.1:11434 / 1234) | `Mark-LVI-main/providers/llm_openai.py (Ollama, LM Studio, vLLM)` | `None (Only Google Gemini client exists)` | **MISSING** | None (Scheduled for Phase 3: TASK-P3-03, TASK-P3-04) |
| `UNIT-11` | `CAT-06` | Streaming <think> Reasoning Filter | `Mark-LVI-main/providers/llm_openai.py (strip <think> tags from TTS)` | `None (No reasoning token filter)` | **MISSING** | None (Scheduled for Phase 3: TASK-P3-05) |
| `UNIT-12` | `CAT-07` | Multi-Provider Cloud Connectors (Groq, DeepSeek, OpenAI) | `Mark-LVI-main/providers/llm_openai.py (hosted cloud APIs)` | `None (Gemini-only backend)` | **MISSING** | None (Scheduled for Phase 3: TASK-P3-06) |
| `UNIT-13` | `CAT-07` | Tool Budgeting Engine (Count & Size Dynamic Schema Slicing) | `Mark-LVI-main/providers/schema.py (max 8-14 tools, 9000 chars)` | `None (Full schema passed unconditionally)` | **MISSING** | None (Scheduled for Phase 3: TASK-P3-07) |
| `UNIT-14` | `CAT-08` | Cloud Audio Capture & 16kHz PCM Streaming via Web Audio | `Mark-LVI-main/main.py (sounddevice 16kHz callback)` | `ALEX-AI-main/frontend/src/audio/pcm-processor.js, useLiveVoice.ts` | **FULL** | DEF-A07-003 (Requires physical microphone hardware) |
| `UNIT-15` | `CAT-08` | Local Offline Speech Recognition (Faster-Whisper on CPU) | `Mark-LVI-main/providers/stt_whisper.py (faster-whisper CPU pre-warmed)` | `None (Cloud-only voice pipeline)` | **MISSING** | None (Scheduled for Phase 4) |
| `UNIT-16` | `CAT-08` | Per-Turn Spoken Language Auto-Detection | `Mark-LVI-main/providers/stt_whisper.py (detects language -> TTS)` | `None (Fixed model language)` | **MISSING** | None (Scheduled for Phase 4) |
| `UNIT-17` | `CAT-09` | Local Neural TTS (Piper, 52 Languages on CPU) | `Mark-LVI-main/providers/tts_piper.py (Piper 15x real-time)` | `None (Cloud audio streaming only)` | **MISSING** | None (Scheduled for Phase 4) |
| `UNIT-18` | `CAT-09` | Zero-Dependency System TTS Fallback (SAPI/say/espeak) | `Mark-LVI-main/providers/tts_system.py (Windows SAPI, macOS say, Linux espeak)` | `None (No native OS TTS engine)` | **MISSING** | None (Scheduled for Phase 4) |
| `UNIT-19` | `CAT-09` | Cloud Streaming TTS (ElevenLabs API) | `Mark-LVI-main/providers/tts_elevenlabs.py (ElevenLabs WS)` | `None (Gemini Live audio only)` | **MISSING** | None (Scheduled for Phase 4) |
| `UNIT-20` | `CAT-10` | Voice Lifecycle State Machine (Listening/Thinking/Speaking) | `Mark-LVI-main/main.py (JarvisLive state loop)` | `ALEX-AI-main/frontend/src/hooks/useLiveVoice.ts, backend/app/services/live_voice_service.py` | **FULL** | DEF-A07-004 (TLS 443 egress) |
| `UNIT-21` | `CAT-10` | System-Wide Global Push-to-Talk Hotkey (Ctrl+Space) | `Mark-LVI-main/core/hotkey.py (global Win32 keyboard hook)` | `ALEX-AI-main/frontend/src/App.tsx (scoped window keyboard listener only)` | **PARTIAL** | Gated by CR-02 (Electron main.ts globalShortcut registration) |
| `UNIT-22` | `CAT-11` | Audio Endpoint Device Discovery & Routing | `Mark-LVI-main/core/audio_devices.py (sounddevice enumeration)` | `ALEX-AI-main/frontend/src/pages/SettingsPage.tsx (navigator.mediaDevices)` | **PARTIAL** | None (Browser-level selection works; backend OS routing pending) |
| `UNIT-23` | `CAT-11` | Live Peak dB Audio VU Metering & Hardware Test Tones | `Mark-LVI-main/core/audio_devices.py (peak meter & test tone)` | `ALEX-AI-main/frontend/src/components/AudioSettings.tsx (visual energy bar)` | **PARTIAL** | None (UI visualizer works; hardware test tone generation missing) |
| `UNIT-24` | `CAT-12` | Structured Fact Storage & Score-Ranked Semantic Search | `Mark-LVI-main/main.py (facts.json file lookup)` | `ALEX-AI-main/backend/app/services/memory_service.py (/api/v1/memory)` | **FULL** | None (Verified via test_memory_service.py) |
| `UNIT-25` | `CAT-13` | Action Registry Architecture (Dynamic Folder Scan vs Static Compiled) | `Mark-LVI-main/core/action_loader.py (runtime actions/*.py scan)` | `ALEX-AI-main/backend/app/actions/registry.py (compiled typed registry)` | **MISMATCH** | ADR-07 Architectural Decision (Alex uses typed static registry) |
| `UNIT-26` | `CAT-13` | Dynamic User Plugin Discovery & Hot-Toggle (plugins/*.py) | `Mark-LVI-main/core/plugin_loader.py (runtime plugin hot-toggle)` | `None (Plugins require backend code deployment)` | **MISSING** | None (Scheduled for Phase 7) |
| `UNIT-27` | `CAT-14` | Five-Word Standardized Outcome Contract (done/unverified/etc.) | `Mark-LVI-main/core/outcome.py (done, unverified, failed, ask, started)` | `ALEX-AI-main/backend/app/actions/base.py (boolean success + error string)` | **MISMATCH** | Scheduled for Phase 3: TASK-P3-08 (unify outcome contract) |
| `UNIT-28` | `CAT-14` | Dynamic Typed Schema Argument Validation & Injection | `Mark-LVI-main/core/action_loader.py (runtime type inspection)` | `ALEX-AI-main/backend/app/actions/base.py (Pydantic v2 schemas)` | **FULL** | None (Architecturally superior in Alex) |
| `UNIT-29` | `CAT-15` | Safety Invariant Gating (Emergency Abort, Latched Stop, Rate Limit) | `Mark-LVI-main/actions/computer_control.py (unbounded pyautogui)` | `ALEX-AI-main/backend/app/services/computer_control_service.py (A02 Safety Harness)` | **FULL** | DEF-A07-002 (Win32 desktop required), BLK-ENV-001 (0/33 tests) |
| `UNIT-30` | `CAT-16` | Synthetic Mouse Automation (Move, Click, Drag, Scroll) | `Mark-LVI-main/actions/computer_control.py (pyautogui mouse)` | `ALEX-AI-main/backend/app/services/computer_control_service.py (bounded mouse)` | **FULL** | DEF-A07-002 (Interactive Win32 session required) |
| `UNIT-31` | `CAT-16` | Synthetic Keyboard Automation (Type, Hotkey, Modifiers) | `Mark-LVI-main/actions/computer_control.py (pyautogui keyboard)` | `ALEX-AI-main/backend/app/services/computer_control_service.py (bounded key)` | **FULL** | DEF-A07-002 (Interactive Win32 session required) |
| `UNIT-32` | `CAT-17` | Multi-Monitor Desktop Screen Capture (mss) | `Mark-LVI-main/actions/screen_processor.py (mss capture)` | `ALEX-AI-main/backend/app/services/screen_capture_service.py (mss capture)` | **FULL** | DEF-A07-002 (Requires desktop display session) |
| `UNIT-33` | `CAT-17` | Webcam Video Frame Extraction & Multimodal Vision (OpenCV) | `Mark-LVI-main/actions/screen_processor.py (cv2.VideoCapture)` | `backend/app/services/vision_service.py` (`cv2.VideoCapture`) | **FULL** | `test_vision_service.py` (7 tests pass) |
| `UNIT-34` | `CAT-18` | Win32 Window Enumeration, Focus & Polite WM_CLOSE | `Mark-LVI-main/actions/open_app.py (user32.dll EnumWindows, PostMessage)` | `ALEX-AI-main/backend/app/services/computer_control_service.py (Win32 API)` | **FULL** | DEF-A07-002 (Interactive desktop required). Windows-only implementation. |
| `UNIT-35` | `CAT-18` | Cross-Platform Window Management (macOS AppleScript / Linux EWMH) | `Mark-LVI-main/actions/open_app.py (Linux wmctrl fallback)` | `ALEX-AI-main/backend/app/services/computer_control_service.py (raises NotImplementedError)` | **MISSING** | Gated by CR-01 (Extract WindowManagementAdapter interface) |
| `UNIT-36` | `CAT-19` | Sandboxed Workspace File Operations (Read, Write, List, Find) | `Mark-LVI-main/actions/file_controller.py (raw os filesystem)` | `ALEX-AI-main/backend/app/services/file_workspace_service.py (canonical sandboxing)` | **FULL** | None (Verified via test_file_workspace_service.py) |
| `UNIT-37` | `CAT-19` | Multi-Level Persistent File Undo Journal | `Mark-LVI-main/core/undo.py (in-memory undo list)` | `ALEX-AI-main/backend/app/services/file_workspace_service.py (10-entry atomic journal)` | **FULL** | None (Architecturally superior in Alex) |
| `UNIT-38` | `CAT-19` | OS-Wide File System Scope & Recycle Bin (send2trash) | `Mark-LVI-main/actions/file_controller.py (arbitrary path access, send2trash)` | `ALEX-AI-main/backend/app/services/file_workspace_service.py (strictly sandboxed)` | **MISMATCH** | Security Boundary Decision (Alex refuses arbitrary path access) |
| `UNIT-39` | `CAT-20` | PDF Document Text & Table Extraction (pdfplumber) | `Mark-LVI-main/actions/file_processor.py (pdfplumber, pypdf)` | `None (Alex text files only)` | **MISSING** | None (Scheduled for Phase 3: TASK-P3-09) |
| `UNIT-40` | `CAT-20` | Office Document Extraction (DOCX, XLSX, PPTX) | `Mark-LVI-main/actions/file_processor.py (python-docx, openpyxl, pptx)` | `None (Alex text files only)` | **MISSING** | None (Scheduled for Phase 3: TASK-P3-09) |
| `UNIT-41` | `CAT-21` | Autonomous Dev Agent Iterative Loop | `Mark-LVI-main/actions/dev_agent.py (multi-step write-run-fix loop)` | `None (No dev agent in Alex)` | **MISSING** | None (Scheduled for Phase 7) |
| `UNIT-42` | `CAT-21` | Python AST Syntax Validation & Linting | `Mark-LVI-main/actions/code_helper.py (ast.parse, syntax checking)` | `None (No AST code helper in Alex)` | **MISSING** | None (Scheduled for Phase 7) |
| `UNIT-43` | `CAT-22` | Playwright Browser Automation Driver | `Mark-LVI-main/actions/browser_control.py (playwright chromium driver)` | `None (No browser driver in Alex)` | **MISSING** | None (Scheduled for Phase 7) |
| `UNIT-44` | `CAT-22` | DOM Scraping & Interactive Web Element Interaction | `Mark-LVI-main/actions/browser_control.py (beautifulsoup4 + playwright)` | `None (No DOM scraper in Alex)` | **MISSING** | None (Scheduled for Phase 7) |
| `UNIT-45` | `CAT-23` | Grounded Web Search (Gemini Grounding & DuckDuckGo) | `Mark-LVI-main/actions/web_search.py (Gemini grounding / DDGS)` | `ALEX-AI-main/backend/app/actions/builtins/search.py, services/search_service.py` | **FULL** | None (Verified via test_search_service.py) |
| `UNIT-46` | `CAT-23` | Multi-Mode Query Disambiguation (News, Price, Research) | `Mark-LVI-main/actions/web_search.py (modes: news, price, research, compare)` | `ALEX-AI-main/backend/app/actions/builtins/search.py (generic query search)` | **PARTIAL** | None (Scheduled for Phase 7 search enhancement) |
| `UNIT-47` | `CAT-24` | YouTube Stream & Metadata Extraction (yt-dlp) | `Mark-LVI-main/actions/youtube_video.py (yt-dlp stream extraction)` | `None (No YouTube integration in Alex)` | **MISSING** | None (Scheduled for Phase 7) |
| `UNIT-48` | `CAT-24` | HUD Video Player Integration (QtMultimedia / HTML5) | `Mark-LVI-main/actions/video_player.py (QtMultimedia embedded HUD)` | `None (No video player component in Alex)` | **MISSING** | None (Scheduled for Phase 7) |
| `UNIT-49` | `CAT-25` | Native OS Desktop Toast Notifications | `Mark-LVI-main/ui.py (QSystemTrayIcon toast)` | `ALEX-AI-main/frontend/electron/main.ts (new Notification), backend plyer toast` | **FULL** | None (Verified in Electron and backend) |
| `UNIT-50` | `CAT-26` | Proactive Startup Briefing & Status Overview | `Mark-LVI-main/actions/proactive.py (morning briefing)` | `ALEX-AI-main/backend/app/services/briefing_service.py (/api/v1/system/briefing)` | **FULL** | None (Verified via test_briefing_service.py) |
| `UNIT-51` | `CAT-26` | Background Topic & RSS News Monitor | `Mark-LVI-main/actions/background_monitor.py (polling threads)` | `None (No background RSS polling in Alex)` | **MISSING** | None (Scheduled for Phase 7) |
| `UNIT-52` | `CAT-27` | In-Memory Timer & Countdown Dispatcher | `Mark-LVI-main/actions/reminder.py (asyncio sleep timers)` | `ALEX-AI-main/backend/app/services/reminder_service.py (/api/v1/reminders)` | **FULL** | None (Verified via test_reminder_service.py) |
| `UNIT-53` | `CAT-27` | Persistent OS Schedulers & Reminders Integration | `Mark-LVI-main/actions/reminder.py (Windows Task Scheduler / cron)` | `ALEX-AI-main/backend/app/services/reminder_service.py (in-memory / JSON only)` | **PARTIAL** | None (Scheduled for Phase 5 OS scheduler integration) |
| `UNIT-54` | `CAT-28` | Typed Application Settings Form & Schema | `Mark-LVI-main/ui.py (Settings drawer raw inputs)` | `ALEX-AI-main/frontend/src/pages/SettingsPage.tsx, backend/app/services/settings_service.py` | **FULL** | None (Verified via test_settings_service.py) |
| `UNIT-55` | `CAT-28` | HueWheel Real-Time Accent Color Tinting | `Mark-LVI-main/ui.py (HueWheel custom QWidget)` | `ALEX-AI-main/frontend/src/pages/SettingsPage.tsx (preset color swatches)` | **PARTIAL** | None (Preset themes work; continuous HueWheel RGB tinting missing) |
| `UNIT-56` | `CAT-29` | Interactive Confirmation Gate for Irreversible Actions | `Mark-LVI-main/core/confirm.py (modal confirmation dialog)` | `ALEX-AI-main/backend/app/services/computer_control_service.py, frontend/src/components/ApprovalModal.tsx` | **FULL** | None (Architecturally superior in Alex: cryptographic proposal token) |
| `UNIT-57` | `CAT-30` | Loopback Bearer Token Authentication | `Mark-LVI-main/main.py (static PIN code / open port)` | `ALEX-AI-main/backend/app/core/auth.py, launcher/cli.py (32-byte dynamic token)` | **FULL** | None (Verified via test_api.py; protects all loopback endpoints) |
| `UNIT-58` | `CAT-30` | OS Keyring Vault Integration (Windows Credential Manager / Keychain) | `Mark-LVI-main/config/api_keys.json (plaintext JSON)` | `ALEX-AI-main/backend/app/core/keyring_vault.py (OS Keyring)` | **FULL** | None (Verified via test_keyring.py; zero plaintext secrets on disk) |
| `UNIT-59` | `CAT-31` | Atomic Document Storage & JSON Write-Rename Safety | `Mark-LVI-main/main.py (direct open() write)` | `ALEX-AI-main/backend/app/services/storage_service.py (tempfile rename atomicity)` | **FULL** | None (Verified via test_storage.py) |
| `UNIT-60` | `CAT-32` | Pre-Flight System Doctor Diagnostics (alex doctor) | `Mark-LVI-main/setup.py (dependency checks)` | `ALEX-AI-main/launcher/cli.py, launcher/health.py (alex doctor)` | **FULL** | None (Verified via launcher tests) |
| `UNIT-61` | `CAT-33` | WebSocket Exponential Backoff & State Reconnect | `Mark-LVI-main/core/gemini.py (reconnect backoff 1s, 2s, 4s...)` | `ALEX-AI-main/backend/app/services/live_voice_service.py (reconnect retry count)` | **PARTIAL** | None (Basic reconnect works; exponential backoff state machine pending) |
| `UNIT-62` | `CAT-34` | Electron Context Isolation & Preload Allowlist | `Mark-LVI-main/ui.py (unrestricted host process access)` | `ALEX-AI-main/frontend/electron/preload.ts (contextIsolation: true, typed IPC allowlist)` | **FULL** | None (Architecturally superior in Alex) |
| `UNIT-63` | `CAT-35` | Hardware Telemetry (CPU, Memory, Disk via psutil) | `Mark-LVI-main/actions/system_monitor.py (psutil metrics)` | `ALEX-AI-main/backend/app/services/system_service.py (/api/v1/system/metrics)` | **FULL** | None (Verified via test_system_service.py) |
| `UNIT-64` | `CAT-36` | Multi-Platform Production Bundler (Electron / PyInstaller) | `Mark-LVI-main/setup.py (pip install requirements.txt)` | `ALEX-AI-main/scripts/package-electron.sh, package.json, pyproject.toml` | **FULL** | None (Packaging build scripts implemented) |
| `UNIT-65` | `CAT-37` | Remote Mobile Web/WS Dashboard & QR Pairing | `Mark-LVI-main/main.py (FastAPI remote mobile web interface with QR pairing)` | `None (Mobile client not yet implemented)` | **MISSING** | None (Scheduled for Phase 6: ADR-09 iOS Companion) |
| `UNIT-66` | `CAT-38` | Local Offline Wake-Word Detection Engine (openwakeword) | `Mark-LVI-main/core/wake_word.py (openwakeword ONNX model on CPU)` | `None (Requires manual UI mic click in Alex)` | **MISSING** | None (Scheduled for Phase 4) |
| `UNIT-67` | `CAT-39` | OS Capability & Security Boundary Detection (Wayland / TCC) | `Mark-LVI-main/core/platform_support.py (Wayland, macOS TCC detection)` | `ALEX-AI-main/backend/app/services/platform_capability_service.py (basic OS detection)` | **PARTIAL** | None (Reports OS; Wayland uinput & macOS TCC wizard pending) |
| `UNIT-68` | `CAT-40` | Automated Regression Test Suite (Backend Pytest & Frontend Vitest) | `Mark-LVI-main/providers/_tests.py (14 inline diagnostic tests)` | `ALEX-AI-main/backend/tests (109 passing unit/API tests), frontend/src/__tests__` | **FULL** | BLK-ENV-001 (Automated tests pass; physical hardware acceptance 0/33 blocked) |

---

## 3. Comprehensive 40-Category Technical Specifications

### Category 01: Application Startup and Lifecycle

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-01` |
| **Constituent Functional Units** | `UNIT-01` (Multi-Process CLI Supervisor [FULL]), `UNIT-02` (Pre-Flight Port & Tree Termination [FULL]) |
| **Mark-LVI Implementation** | `main.py (L1-L60, main()), ui.py (JarvisUI). Single Python process launching PyQt6 GUI on main thread and background asyncio event loop on daemon thread.` |
| **Alex Target Implementation** | `launcher/cli.py (launch, stop, status, doctor), launcher/process_manager.py, launcher/health.py, frontend/electron/main.ts. Multi-process supervisor.` |
| **Mark-LVI Workflow** | User runs python main.py. _subprocess.Popen is patched for CREATE_NO_WINDOW. Console streams are reconfigured to UTF-8. PyQt6 HUD opens and spins worker thread. |
| **Alex Workflow** | User runs alex launch. Launcher validates dependencies, checks loopback ports, starts FastAPI sidecar, polls /api/v1/health, starts Vite dev server, and opens Electron shell. |
| **Category Parity Summary** | **FULL** (Architecturally Superior in Alex) |
| **Technical Gap & Architectural Distinction** | None. Alex provides superior process supervision, port collision negotiation, and clean tree termination. |
| **Dependencies & Prerequisites** | Python 3.10+, Node.js 18+, Electron, psutil. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Server-side only |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain current unified launcher implementation (Frozen). |
| **Acceptance Criteria** | Clean startup of all three tiers within 5.0 seconds; graceful alex stop terminates all child PIDs. |
| **Evidence & Source References** | `launcher/cli.py, backend/tests/test_launcher.py.` |

---

### Category 02: Desktop User Interface & Holographic HUD

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-02` |
| **Constituent Functional Units** | `UNIT-03` (Frameless HUD Window [FULL]), `UNIT-04` (3D Wireframe Avatar [PARTIAL]), `UNIT-05` (Viseme Audio Lip-Sync [MISSING]) |
| **Mark-LVI Implementation** | `ui.py (JarvisUI), core/avatar.py, core/avatar_mesh.py, core/viseme.py. QPainter 3D software-rendered face mesh with MediaPipe geometry, real-time lip-sync, and HueWheel accent tinting.` |
| **Alex Target Implementation** | `frontend/src/App.tsx, frontend/src/components/HudAvatar.tsx, frontend/src/index.css. React 18, Vite, Tailwind CSS, SVG avatar with CSS animations.` |
| **Mark-LVI Workflow** | Frameless transparent HUD window with acrylic blur. Real 3D head mesh vertices are dynamically lit, rotated, and articulated with ~50 viseme shapes/sec matching audio formants. |
| **Alex Workflow** | React web application rendered inside Electron transparent BrowserWindow. Renders 2D SVG face or reactor core with CSS pulse animations based on mode prop. |
| **Category Parity Summary** | **PARTIAL** (UNIT-03: FULL, UNIT-04: PARTIAL, UNIT-05: MISSING) |
| **Technical Gap & Architectural Distinction** | Alex lacks software-rendered 3D MediaPipe face mesh, audio formant viseme articulation, facial acting (gaze saccades, blinking, brow tracking), and live HueWheel vertex tinting. |
| **Dependencies & Prerequisites** | Canvas API / Three.js or WebGL in React; audio level telemetry from sidecar. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Web/Canvas adaptation |
| **Migration Complexity** | HIGH |
| **Required Implementation Actions** | Migrate 3D MediaPipe face mesh to a lightweight WebGL/Three.js or Canvas2D renderer in HudAvatar.tsx and feed real-time viseme data from audio bridge. |
| **Acceptance Criteria** | Avatar articulates mouth shapes based on voice speech; accent hue dynamically tints avatar mesh. |
| **Evidence & Source References** | `Mark-LVI-main/core/avatar.py, ALEX-AI-main/frontend/src/components/HudAvatar.tsx.` |

---

### Category 03: Assistant Chat Functionality

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-03` |
| **Constituent Functional Units** | `UNIT-06` (Text Chat Streaming, Markdown Rendering & History Persistence [FULL]) |
| **Mark-LVI Implementation** | `ui.py (ChatDrawer), main.py (send_text()). Seamless text input into active Gemini Live session without dropping audio continuity.` |
| **Alex Target Implementation** | `frontend/src/pages/ConversationPage.tsx, backend/app/services/conversation_service.py. Dual-mode: REST chat session (/api/v1/conversation) and live voice text joins.` |
| **Mark-LVI Workflow** | Typing text while Live session is active injects user turn directly into streaming session; reply is synthesized via active voice. |
| **Alex Workflow** | Text messages are sent via REST to gemini-2.0-flash sidecar service, updating conversation store; alternatively typed in voice mode via WebSocket. |
| **Category Parity Summary** | **FULL** |
| **Technical Gap & Architectural Distinction** | None in core chat. Ensure UI allows seamless toggling between text-only conversation and Live session injection. |
| **Dependencies & Prerequisites** | React, FastAPI, SQLite / JSON conversation store. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain current dual-mode design; ensure conversation persistence syncs across UI views. |
| **Acceptance Criteria** | User can chat via text and receive markdown-formatted responses with citations. |
| **Evidence & Source References** | `backend/app/services/conversation_service.py, frontend/src/pages/ConversationPage.tsx.` |

---

### Category 04: AI Model Integration (Cloud & Live Multimodal)

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-04` |
| **Constituent Functional Units** | `UNIT-07` (Cloud Gemini Live Bidirectional WebSocket Stream & Interruption [FULL]) |
| **Mark-LVI Implementation** | `core/gemini.py, main.py (JarvisLive). models/gemini-3.1-flash-live-preview via google-genai SDK WebSocket. Handles PCM streaming, function calling, tool return routing.` |
| **Alex Target Implementation** | `backend/app/services/live_voice_service.py. WebSocket loopback bridge connecting React Web Audio to models/gemini-3.1-flash-live-preview.` |
| **Mark-LVI Workflow** | Connects to Gemini Live WSS, streams 16kHz PCM audio, receives audio buffers, handles barge-in interruptions, executes tool calls, returns tool output, handles reconnection backoff. |
| **Alex Workflow** | Frontend useLiveVoice.ts captures microphone PCM via AudioWorklet, forwards via loopback WS to LiveVoiceService, which maintains Gemini Live session and plays received audio. |
| **Category Parity Summary** | **FULL** |
| **Technical Gap & Architectural Distinction** | Zero functional gap in core Gemini Live integration. Alex implements equivalent WebSocket bridge with typed Pydantic payloads. |
| **Dependencies & Prerequisites** | google-genai SDK, websockets, AudioWorklet. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain current implementation; wire to Model Ladder service in Phase 3. |
| **Acceptance Criteria** | Bidirectional voice conversation with sub-second latency and seamless barge-in interruption. |
| **Evidence & Source References** | `backend/app/services/live_voice_service.py, frontend/src/hooks/useLiveVoice.ts.` |

---

### Category 05: Model Selection and Switching (Model Ladder)

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-05` |
| **Constituent Functional Units** | `UNIT-08` (9-Rung Model Fallback Ladder [MISSING]), `UNIT-09` (429 Quota Exhaustion Auto-Downgrade [MISSING]) |
| **Mark-LVI Implementation** | `core/gemini.py (MODEL_LADDER), main.py. Defines 9 sequential fallback models (gemini-3.1-flash-live, gemini-2.5-flash-native-audio, gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-flash-8b, gemini-1.5-pro, plus text fallbacks). Catches 429 quota exhaustion and seamlessly auto-downgrades.` |
| **Alex Target Implementation** | `backend/app/services/live_voice_service.py. Hardcodes two models (_LIVE_MODELS) and terminates session with fatal 1011 error on 429.` |
| **Mark-LVI Workflow** | On 429 Resource Exhausted or 503 Service Unavailable, Mark-LVI steps down to the next ladder rung, re-establishes session, and continues user turn. |
| **Alex Workflow** | Throws WebSocketException, UI shows disconnection alert, user must manually reconnect. |
| **Category Parity Summary** | **MISSING** |
| **Technical Gap & Architectural Distinction** | Alex completely lacks a multi-model fallback ladder and 429 auto-downgrade state machine. |
| **Dependencies & Prerequisites** | FastAPI, google-genai, tenacity / exponential backoff. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | MEDIUM |
| **Required Implementation Actions** | Implement backend/app/services/model_ladder_service.py and cooldown tracker (Phase 3: TASK-P3-02). |
| **Acceptance Criteria** | System recovers from simulated 429 quota exhaustion by auto-downgrading to next available tier within 2.0s. |
| **Evidence & Source References** | `Mark-LVI-main/core/gemini.py#L45-L120.` |

---

### Category 06: Local AI Model Support (Ollama, LM Studio, vLLM)

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-06` |
| **Constituent Functional Units** | `UNIT-10` (Local OpenAI-Compatible Server Integration [MISSING]), `UNIT-11` (Streaming <think> Reasoning Filter [MISSING]) |
| **Mark-LVI Implementation** | `providers/llm_openai.py, ui.py (Model selection). Connects to Ollama (http://127.0.0.1:11434/v1) and LM Studio (http://127.0.0.1:1234/v1). Filters <think> reasoning tokens from speech.` |
| **Alex Target Implementation** | `None. Alex only interfaces with Google Gemini cloud API.` |
| **Mark-LVI Workflow** | User selects Ollama/LM Studio model in HUD settings. Hearing (Whisper) -> Thinking (Local LLM via OpenAI API) -> Speaking (Piper TTS). All data stays local. |
| **Alex Workflow** | Not supported. Voice is completely inoperative without Google cloud connectivity. |
| **Category Parity Summary** | **MISSING** |
| **Technical Gap & Architectural Distinction** | Alex has zero support for local LLM engines or reasoning token extraction. |
| **Dependencies & Prerequisites** | httpx, pydantic, regex. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Server-side only |
| **Migration Complexity** | MEDIUM |
| **Required Implementation Actions** | Implement backend/app/providers/base.py, registry.py, and llm_openai.py (Phase 3: TASK-P3-03, TASK-P3-04, TASK-P3-05). |
| **Acceptance Criteria** | User can run offline conversational turns against local Ollama llama3.2:3b instance. |
| **Evidence & Source References** | `Mark-LVI-main/providers/llm_openai.py.` |

---

### Category 07: Cloud AI Provider Integration (OpenAI, Groq, DeepSeek)

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-07` |
| **Constituent Functional Units** | `UNIT-12` (Multi-Provider Cloud Connectors [MISSING]), `UNIT-13` (Tool Budgeting Engine [MISSING]) |
| **Mark-LVI Implementation** | `providers/llm_openai.py, providers/schema.py. Connects to OpenAI, Groq, DeepSeek, Mistral, xAI, OpenRouter. Implements dynamic tool budgeting (max 8-14 tools, 9000 chars) to prevent model confusion.` |
| **Alex Target Implementation** | `None. Only Google Gemini cloud provider supported.` |
| **Mark-LVI Workflow** | User enters Groq or DeepSeek API key. Mark-LVI formats OpenAI chat completion request with system prompt, tool schemas, and streaming output. |
| **Alex Workflow** | Not supported. |
| **Category Parity Summary** | **MISSING** |
| **Technical Gap & Architectural Distinction** | Alex lacks third-party cloud LLM connectors and dynamic tool schema budgeting. |
| **Dependencies & Prerequisites** | httpx, keyring. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | MEDIUM |
| **Required Implementation Actions** | Implement OpenAICompatibleProvider and ToolBudgetManager (Phase 3: TASK-P3-06, TASK-P3-07). |
| **Acceptance Criteria** | User can execute voice or chat turns via Groq llama-3.3-70b-versatile with sub-500ms time to first token. |
| **Evidence & Source References** | `Mark-LVI-main/providers/llm_openai.py, Mark-LVI-main/providers/schema.py.` |

---

### Category 08: Voice Input & Speech Recognition (STT)

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-08` |
| **Constituent Functional Units** | `UNIT-14` (Cloud Audio Capture & PCM Streaming [FULL]), `UNIT-15` (Local Faster-Whisper STT [MISSING]), `UNIT-16` (Language Auto-Detection [MISSING]) |
| **Mark-LVI Implementation** | `providers/stt_whisper.py, providers/audio.py, main.py. Faster-Whisper on CPU with pre-warmed audio buffers and per-turn language detection.` |
| **Alex Target Implementation** | `frontend/src/audio/pcm-processor.js, useLiveVoice.ts. Web Audio API captures mic PCM and streams directly to cloud Gemini Live.` |
| **Mark-LVI Workflow** | Energy-based VAD detects speech, streams PCM into Faster-Whisper, transcribes text with language tag, routes to LLM pipeline. |
| **Alex Workflow** | AudioWorklet streams 16kHz PCM to sidecar, which streams to Gemini Live cloud WSS. Gemini processes audio natively. |
| **Category Parity Summary** | **PARTIAL** (UNIT-14: FULL, UNIT-15: MISSING, UNIT-16: MISSING) |
| **Technical Gap & Architectural Distinction** | Alex lacks offline local STT (Faster-Whisper) and spoken language auto-detection. |
| **Dependencies & Prerequisites** | faster-whisper, numpy, soundfile. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Web Audio |
| **Migration Complexity** | HIGH |
| **Required Implementation Actions** | Implement SpeechService with Faster-Whisper CPU engine in Phase 4. |
| **Acceptance Criteria** | Microphone audio transcribes locally with <300ms latency on CPU without internet connection. |
| **Evidence & Source References** | `Mark-LVI-main/providers/stt_whisper.py.` |

---

### Category 09: Voice Output & Speech Synthesis (TTS)

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-09` |
| **Constituent Functional Units** | `UNIT-17` (Local Piper Neural TTS [MISSING]), `UNIT-18` (System TTS Fallback [MISSING]), `UNIT-19` (Cloud ElevenLabs TTS [MISSING]) |
| **Mark-LVI Implementation** | `providers/tts_piper.py, providers/tts_system.py, providers/tts_elevenlabs.py. Local Piper neural TTS (~176 voices in 52 languages, 15x real-time), zero-dependency OS system voices (SAPI/say/espeak), ElevenLabs cloud voice.` |
| **Alex Target Implementation** | `None. Relies entirely on cloud-synthesized 24kHz PCM returned by Gemini Live WebSocket.` |
| **Mark-LVI Workflow** | LLM response text streams into Piper TTS, which synthesizes 22.05kHz PCM and plays through sounddevice in real-time. |
| **Alex Workflow** | Browser plays cloud audio received via loopback WebSocket. No local TTS engine exists. |
| **Category Parity Summary** | **MISSING** |
| **Technical Gap & Architectural Distinction** | Alex has zero offline TTS capability. |
| **Dependencies & Prerequisites** | piper-tts, pyttsx3, elevenlabs. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: AVFoundation |
| **Migration Complexity** | HIGH |
| **Required Implementation Actions** | Implement PiperTTSProvider and SystemTTSProvider in Phase 4. |
| **Acceptance Criteria** | System speaks text responses offline via Piper neural voice with natural prosody. |
| **Evidence & Source References** | `Mark-LVI-main/providers/tts_piper.py, providers/tts_system.py.` |

---

### Category 10: Real-Time Voice Conversation Lifecycle

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-10` |
| **Constituent Functional Units** | `UNIT-20` (Voice Lifecycle State Machine [FULL]), `UNIT-21` (Global Push-to-Talk Hotkey [PARTIAL]) |
| **Mark-LVI Implementation** | `core/hotkey.py, main.py (JarvisLive). Win32 global keyboard hook for Ctrl+Space push-to-talk. Full conversation state machine.` |
| **Alex Target Implementation** | `frontend/src/hooks/useLiveVoice.ts, frontend/src/App.tsx. Voice lifecycle state machine implemented; hotkey only functions when window has keyboard focus.` |
| **Mark-LVI Workflow** | User hits Ctrl+Space globally from any app; HUD unminimizes, audio mic opens, user speaks, release sends turn. |
| **Alex Workflow** | User must click mic icon or focus Alex window to use push-to-talk. |
| **Category Parity Summary** | **PARTIAL** (UNIT-20: FULL, UNIT-21: PARTIAL - Gated by CR-02) |
| **Technical Gap & Architectural Distinction** | Alex lacks OS-wide global shortcut registration (blocked by CR-02 freeze). |
| **Dependencies & Prerequisites** | Electron globalShortcut, IPC. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Scoped |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Implement CR-02 to register global shortcut in frontend/electron/main.ts (Phase 4). |
| **Acceptance Criteria** | Pressing Ctrl+Space while another application is focused activates microphone and brings Alex HUD forward. |
| **Evidence & Source References** | `ALEX-AI-main/docs/planning/CHANGE_REQUESTS.md (CR-02).` |

---

### Category 11: Audio Device Management & Diagnostics

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-11` |
| **Constituent Functional Units** | `UNIT-22` (Audio Endpoint Discovery & Routing [PARTIAL]), `UNIT-23` (Live Peak dB VU Metering & Test Tones [PARTIAL]) |
| **Mark-LVI Implementation** | `core/audio_devices.py, ui.py (AudioSettings). Direct sounddevice device enumeration, live dB peak meters with green/yellow/red bars, test tone generation.` |
| **Alex Target Implementation** | `frontend/src/pages/SettingsPage.tsx, frontend/src/components/AudioSettings.tsx. Browser-level navigator.mediaDevices enumeration; UI energy visualizer.` |
| **Mark-LVI Workflow** | User inspects live microphone input levels with dB calibration, selects default output, plays test sine wave tone. |
| **Alex Workflow** | User selects browser microphone/speaker; visual energy bar reacts to volume. No backend hardware tone generator. |
| **Category Parity Summary** | **PARTIAL** |
| **Technical Gap & Architectural Distinction** | Alex lacks backend sounddevice routing and hardware test tone generation. |
| **Dependencies & Prerequisites** | sounddevice, numpy. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Scoped |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Add audio test tone endpoint in backend/app/api/v1/endpoints/system.py (Phase 4). |
| **Acceptance Criteria** | User can trigger audio test tone and inspect hardware-level device properties. |
| **Evidence & Source References** | `Mark-LVI-main/core/audio_devices.py.` |

---

### Category 12: Assistant State, Memory & Session Continuity

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-12` |
| **Constituent Functional Units** | `UNIT-24` (Structured Fact Storage & Semantic Memory Search [FULL]) |
| **Mark-LVI Implementation** | `main.py (facts.json, user facts storage). Reads and writes user profile facts in flat JSON.` |
| **Alex Target Implementation** | `backend/app/services/memory_service.py, backend/app/actions/builtins/memory.py. Atomic JSON document store with score-ranked semantic search.` |
| **Mark-LVI Workflow** | Assistant updates facts.json on user fact commands; matches facts during prompt generation. |
| **Alex Workflow** | Full CRUD API (/api/v1/memory) with categories, timestamps, and score-ranked token search. |
| **Category Parity Summary** | **FULL** (Architecturally Superior in Alex) |
| **Technical Gap & Architectural Distinction** | None. Alex provides typed schemas, atomic writes, and scored search. |
| **Dependencies & Prerequisites** | pydantic, json, storage_service. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain current implementation. |
| **Acceptance Criteria** | Assistant accurately recalls user facts across application restarts. |
| **Evidence & Source References** | `backend/tests/test_memory_service.py.` |

---

### Category 13: Action & Tool Registry Architecture

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-13` |
| **Constituent Functional Units** | `UNIT-25` (Action Registry Architecture [MISMATCH]), `UNIT-26` (Dynamic Plugin Discovery & Hot-Toggle [MISSING]) |
| **Mark-LVI Implementation** | `core/action_loader.py, core/plugin_loader.py. Scans actions/*.py and plugins/*.py dynamically at runtime. Automatically strips metadata before sending to Gemini API.` |
| **Alex Target Implementation** | `backend/app/actions/registry.py, backend/app/actions/builtins/. Static compiled typed registry with Pydantic schemas.` |
| **Mark-LVI Workflow** | Dropping a python file into actions/ immediately exposes the tool to the assistant without process restarts. |
| **Alex Workflow** | Actions are declared as typed Pydantic classes and compiled into the registry at initialization. |
| **Category Parity Summary** | **MISMATCH** (UNIT-25: MISMATCH - ADR-07 Decision; UNIT-26: MISSING) |
| **Technical Gap & Architectural Distinction** | Alex intentionally uses a static typed registry for enterprise safety, but lacks runtime plugin toggling. |
| **Dependencies & Prerequisites** | pydantic, importlib. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | MEDIUM |
| **Required Implementation Actions** | Implement plugin discovery service in Phase 7 while preserving Pydantic schema validation. |
| **Acceptance Criteria** | New tools validate strictly against Pydantic schemas before registration. |
| **Evidence & Source References** | `backend/app/actions/registry.py, docs/migration/MIGRATION_DECISIONS.md (ADR-07).` |

---

### Category 14: Dynamic Command Execution & Outcome Contract

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-14` |
| **Constituent Functional Units** | `UNIT-27` (Five-Word Standardized Outcome Contract [MISMATCH]), `UNIT-28` (Dynamic Typed Schema Validation [FULL]) |
| **Mark-LVI Implementation** | `core/outcome.py (done, unverified, failed, ask, started). Strict 5-word contract passed to model prompt to eliminate hallucinated execution claims.` |
| **Alex Target Implementation** | `backend/app/actions/base.py. Uses boolean success: bool and error: Optional[str].` |
| **Mark-LVI Workflow** | Action returns Outcome.DONE or Outcome.UNVERIFIED. Model prompt forbids claiming success if status is UNVERIFIED. |
| **Alex Workflow** | Action returns Pydantic ActionResponse. Model interprets success boolean. |
| **Category Parity Summary** | **MISMATCH** (UNIT-27: MISMATCH - Scheduled for Phase 3; UNIT-28: FULL) |
| **Technical Gap & Architectural Distinction** | Alex needs the five-word outcome contract to prevent false success narration during asynchronous operations. |
| **Dependencies & Prerequisites** | pydantic, enum. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Implement ToolOutcome enum in backend/app/actions/base.py (Phase 3: TASK-P3-08). |
| **Acceptance Criteria** | Every action outcome response returns typed status: ToolOutcome. |
| **Evidence & Source References** | `Mark-LVI-main/core/outcome.py, docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md.` |

---

### Category 15: Computer Control & Safety Gating (A02 Invariants)

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-15` |
| **Constituent Functional Units** | `UNIT-29` (Safety Invariant Gating, Latched Stop & Rate Limiting [FULL]) |
| **Mark-LVI Implementation** | `actions/computer_control.py. Unbounded PyAutoGUI automation without rate limiting, coordinate clamping, or emergency latched aborts.` |
| **Alex Target Implementation** | `backend/app/services/computer_control_service.py. Enterprise safety harness: coordinate bounds checking, emergency stop latch, approval tokens, watchdog timers (Milestone A02 Frozen).` |
| **Mark-LVI Workflow** | Model generates raw coordinate clicks and moves without safety bounds or confirmation queues. |
| **Alex Workflow** | Model requests computer control operation; service checks screen boundaries, validates rate limits, checks emergency stop latch, and enforces approval queue. |
| **Category Parity Summary** | **FULL** (Architecturally Superior in Alex) |
| **Technical Gap & Architectural Distinction** | None in code. Implementation is complete and verified with 32 unit tests. Blocked by environment for physical acceptance. |
| **Dependencies & Prerequisites** | pyautogui, pywin32, ctypes. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Blocked (Wayland) | macOS: Blocked (TCC) | iOS: N/A |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Preserve A02 Computer Control freeze strictly. |
| **Acceptance Criteria** | All 32 A02 automated tests pass; emergency stop latch halts execution immediately. |
| **Evidence & Source References** | `backend/app/services/computer_control_service.py, backend/tests/test_computer_control_service.py.` |

---

### Category 16: Mouse and Keyboard Operations

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-16` |
| **Constituent Functional Units** | `UNIT-30` (Synthetic Mouse Automation [FULL]), `UNIT-31` (Synthetic Keyboard Automation [FULL]) |
| **Mark-LVI Implementation** | `actions/computer_control.py. Implements mouse move, click, double click, right click, drag, scroll, text typing, hotkeys, key down/up.` |
| **Alex Target Implementation** | `backend/app/services/computer_control_service.py. Full 22/23 PyAutoGUI synthetic input operations implemented under safety harness.` |
| **Mark-LVI Workflow** | Direct PyAutoGUI function calls on the active desktop session. |
| **Alex Workflow** | Pydantic-validated input requests executed via ComputerControlService with coordinate clamping. |
| **Category Parity Summary** | **FULL** |
| **Technical Gap & Architectural Distinction** | Zero code gap. Blocked on physical workstation acceptance (DEF-A07-002). |
| **Dependencies & Prerequisites** | pyautogui, ctypes. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported (X11) / Blocked (Wayland) | macOS: TCC required | iOS: N/A |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain implementation under A02 freeze. |
| **Acceptance Criteria** | Cursor moves accurately to clamped coordinates; keystrokes injected into focused target window. |
| **Evidence & Source References** | `backend/app/services/computer_control_service.py.` |

---

### Category 17: Screen Capture and Visual Understanding

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-17` |
| **Constituent Functional Units** | `UNIT-32` (Multi-Monitor Desktop Screen Capture [FULL]), `UNIT-33` (Webcam Frame Extraction [FULL]) |
| **Mark-LVI Implementation** | `actions/screen_processor.py. mss screen capture across all monitors; OpenCV webcam frame capture (cv2.VideoCapture).` |
| **Alex Target Implementation** | `backend/app/services/vision_service.py. High-speed screen capture via PyAutoGUI/mss and hardware camera frame capture via OpenCV (cv2.VideoCapture) with device index probing.` |
| **Mark-LVI Workflow** | Captures screen or webcam, compresses JPEG, passes into Gemini Live or OpenAI vision endpoint. |
| **Alex Workflow** | Captures desktop screen or hardware webcam frame, compresses JPEG, returns base64 or saves to disk for multimodal vision reasoning. |
| **Category Parity Summary** | **FULL** (UNIT-32: FULL, UNIT-33: FULL) |
| **Technical Gap & Architectural Distinction** | Parity achieved. OpenCV webcam frame extraction integrated into VisionService and vision.capture action. |
| **Dependencies & Prerequisites** | mss, PIL, opencv-python (>=4.8.0). |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported (X11/V4L2) | macOS: TCC Screen Recording & Camera | iOS: N/A |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Completed: opencv-python installed and verified with unit tests. |
| **Acceptance Criteria** | Desktop screenshot and webcam capture complete and format for multimodal LLM vision. |
| **Evidence & Source References** | `backend/app/services/vision_service.py`, `backend/tests/test_vision_service.py`. |

---

### Category 18: Window Management & Polite Process Termination

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-18` |
| **Constituent Functional Units** | `UNIT-34` (Win32 Window Management [FULL]), `UNIT-35` (Cross-Platform Window Management [MISSING]) |
| **Mark-LVI Implementation** | `actions/open_app.py, actions/desktop.py. user32.dll Win32 API window enumeration, focus restoration, polite WM_CLOSE, Linux wmctrl fallback.` |
| **Alex Target Implementation** | `backend/app/services/computer_control_service.py. Complete Win32 implementation (EnumWindows, SetForegroundWindow, PostMessage WM_CLOSE); raises NotImplementedError on non-Windows.` |
| **Mark-LVI Workflow** | Looks up window by title regex, brings to top via Win32 or wmctrl, closes politely without killing process tree. |
| **Alex Workflow** | Windows: Identical Win32 logic. macOS/Linux: Explicitly blocked by _require_windows() check. |
| **Category Parity Summary** | **PARTIAL** (UNIT-34: FULL on Windows; UNIT-35: MISSING on macOS/Linux - Gated by CR-01) |
| **Technical Gap & Architectural Distinction** | Window management is hardcoded to Windows ctypes. Needs abstraction layer (CR-01). |
| **Dependencies & Prerequisites** | ctypes, user32.dll, AppleScript, wmctrl. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Missing (CR-01) | macOS: Missing (CR-01) | iOS: N/A |
| **Migration Complexity** | MEDIUM |
| **Required Implementation Actions** | Implement CR-01 (WindowManagementAdapter interface and macOS/Linux drivers) in Phase 5. |
| **Acceptance Criteria** | Window focus and polite close work seamlessly across Windows 11, Ubuntu Linux, and macOS. |
| **Evidence & Source References** | `ALEX-AI-main/docs/planning/CHANGE_REQUESTS.md (CR-01).` |

---

### Category 19: File and Folder Operations & Safe Deletion

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-19` |
| **Constituent Functional Units** | `UNIT-36` (Sandboxed File Operations [FULL]), `UNIT-37` (Persistent File Undo Journal [FULL]), `UNIT-38` (OS-Wide Broad File Access [MISMATCH]) |
| **Mark-LVI Implementation** | `actions/file_controller.py, core/undo.py. Unrestricted filesystem access to user home directory, desktop, downloads; safe trash via send2trash.` |
| **Alex Target Implementation** | `backend/app/services/file_workspace_service.py, backend/app/actions/builtins/files.py. Strict canonical sandboxing within Alex workspace; 10-entry persistent undo journal.` |
| **Mark-LVI Workflow** | Model reads and modifies any file in the user profile; deletes files to recycle bin. |
| **Alex Workflow** | Model operations are constrained to the safe workspace boundary; directory traversal and symlink escapes are strictly blocked. |
| **Category Parity Summary** | **MISMATCH** (UNIT-36: FULL, UNIT-37: FULL, UNIT-38: MISMATCH - Security Boundary Decision) |
| **Technical Gap & Architectural Distinction** | Alex intentionally restricts broad filesystem access to prevent prompt injection file exfiltration. |
| **Dependencies & Prerequisites** | pathlib, send2trash, storage_service. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Sandboxed |
| **Migration Complexity** | MEDIUM |
| **Required Implementation Actions** | Introduce an opt-in user consent boundary for external folder mounting in Phase 5. |
| **Acceptance Criteria** | File operations within workspace execute atomically; path traversal attempts are rejected. |
| **Evidence & Source References** | `backend/tests/test_file_workspace_service.py.` |

---

### Category 20: Deep Document Parsing & File Processing

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-20` |
| **Constituent Functional Units** | `UNIT-39` (PDF Document Text & Table Extraction [MISSING]), `UNIT-40` (Office Document Extraction [MISSING]) |
| **Mark-LVI Implementation** | `actions/file_processor.py. Extracts text and tabular data from PDF (pdfplumber, pypdf), Word (python-docx), Excel (openpyxl), and PowerPoint (python-pptx).` |
| **Alex Target Implementation** | `None. Alex only handles plain text and markdown files.` |
| **Mark-LVI Workflow** | User asks question about financial spreadsheet or PDF manual. FileProcessor extracts text, summarizes content, and answers queries. |
| **Alex Workflow** | File action rejects binary document formats. |
| **Category Parity Summary** | **MISSING** |
| **Technical Gap & Architectural Distinction** | Alex completely lacks PDF and Microsoft Office document parsing. |
| **Dependencies & Prerequisites** | pdfplumber, pypdf, python-docx, openpyxl, python-pptx. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | MEDIUM |
| **Required Implementation Actions** | Implement backend/app/actions/builtins/documents.py (Phase 3: TASK-P3-09). |
| **Acceptance Criteria** | System extracts text and tables from multi-page PDFs and Excel spreadsheets accurately. |
| **Evidence & Source References** | `Mark-LVI-main/actions/file_processor.py.` |

---

### Category 21: Coding Assistance & Autonomous Dev Agent

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-21` |
| **Constituent Functional Units** | `UNIT-41` (Autonomous Dev Agent Iterative Loop [MISSING]), `UNIT-42` (Python AST Syntax Validation & Linting [MISSING]) |
| **Mark-LVI Implementation** | `actions/dev_agent.py, actions/code_helper.py. Autonomous multi-step coding agent: creates files, verifies AST syntax, executes unit tests, reads tracebacks, and fixes bugs autonomously.` |
| **Alex Target Implementation** | `None. Alex provides conversational coding suggestions but no autonomous agent loop.` |
| **Mark-LVI Workflow** | User commands 'build a snake game'. Dev agent scaffolds files, validates syntax, runs test, fixes errors, and reports completion. |
| **Alex Workflow** | Generates markdown code snippets in chat. |
| **Category Parity Summary** | **MISSING** |
| **Technical Gap & Architectural Distinction** | Alex lacks autonomous code generation and AST syntax validation loops. |
| **Dependencies & Prerequisites** | ast, subprocess, pytest. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: N/A |
| **Migration Complexity** | HIGH |
| **Required Implementation Actions** | Implement autonomous dev agent action in Phase 7. |
| **Acceptance Criteria** | Agent autonomously modifies code, validates AST, runs tests, and terminates cleanly. |
| **Evidence & Source References** | `Mark-LVI-main/actions/dev_agent.py, actions/code_helper.py.` |

---

### Category 22: Browser Automation & Web Control

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-22` |
| **Constituent Functional Units** | `UNIT-43` (Playwright Browser Automation Driver [MISSING]), `UNIT-44` (DOM Scraping & Interactive Web Interaction [MISSING]) |
| **Mark-LVI Implementation** | `actions/browser_control.py. Uses Playwright Chromium driver and BeautifulSoup4 for automated web browsing, form filling, and DOM element clicking.` |
| **Alex Target Implementation** | `None. Alex only performs HTTP GET web searches via DuckDuckGo.` |
| **Mark-LVI Workflow** | User commands 'open amazon and add item to cart'. BrowserControl launches Chromium, locates button selectors, clicks, and extracts DOM text. |
| **Alex Workflow** | Not supported. |
| **Category Parity Summary** | **MISSING** |
| **Technical Gap & Architectural Distinction** | Alex has zero browser automation capability. |
| **Dependencies & Prerequisites** | playwright, beautifulsoup4. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: N/A |
| **Migration Complexity** | HIGH |
| **Required Implementation Actions** | Implement Playwright-based browser action in Phase 7. |
| **Acceptance Criteria** | System automates web navigation and form interaction in headless/headed browser. |
| **Evidence & Source References** | `Mark-LVI-main/actions/browser_control.py.` |

---

### Category 23: Web Research & Grounded Search

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-23` |
| **Constituent Functional Units** | `UNIT-45` (Grounded Web Search [FULL]), `UNIT-46` (Multi-Mode Query Disambiguation [PARTIAL]) |
| **Mark-LVI Implementation** | `actions/web_search.py. Grounded web search with specialized modes (news, price, research, compare) and DuckDuckGo fallback.` |
| **Alex Target Implementation** | `backend/app/actions/builtins/search.py, backend/app/services/search_service.py. DuckDuckGo search integration and Gemini Grounding.` |
| **Mark-LVI Workflow** | Dispatches query to search API, scrapes top result snippets, formats citations. |
| **Alex Workflow** | Executes search query via DuckDuckGo API, returns formatted results with links. |
| **Category Parity Summary** | **FULL** (UNIT-45: FULL; UNIT-46: PARTIAL) |
| **Technical Gap & Architectural Distinction** | Minor: Alex can add specialized price comparison and news filter parameters. |
| **Dependencies & Prerequisites** | duckduckgo_search, httpx. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Enhance SearchService query parameter options in Phase 7. |
| **Acceptance Criteria** | Web search returns relevant, grounded results with citations within 1.5 seconds. |
| **Evidence & Source References** | `backend/app/services/search_service.py, backend/tests/test_search_service.py.` |

---

### Category 24: Application & Media Integrations

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-24` |
| **Constituent Functional Units** | `UNIT-47` (YouTube Stream Extraction [MISSING]), `UNIT-48` (HUD Video Player Integration [MISSING]) |
| **Mark-LVI Implementation** | `actions/youtube_video.py, actions/video_player.py. Uses yt-dlp to extract YouTube streams and QtMultimedia for embedded HUD video playback.` |
| **Alex Target Implementation** | `None. Alex has no YouTube or video playback integrations.` |
| **Mark-LVI Workflow** | User asks to play video; yt-dlp extracts streaming URL, PyQt6 video drawer opens and streams video inside HUD. |
| **Alex Workflow** | Not supported. |
| **Category Parity Summary** | **MISSING** |
| **Technical Gap & Architectural Distinction** | Alex lacks YouTube stream extraction and video playback components. |
| **Dependencies & Prerequisites** | yt-dlp, HTML5 video / React player. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | MEDIUM |
| **Required Implementation Actions** | Implement YouTube search and HTML5 video drawer in Phase 7. |
| **Acceptance Criteria** | System extracts YouTube stream metadata and plays video in UI drawer. |
| **Evidence & Source References** | `Mark-LVI-main/actions/youtube_video.py, actions/video_player.py.` |

---

### Category 25: Desktop Notifications

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-25` |
| **Constituent Functional Units** | `UNIT-49` (Native OS Desktop Toast Notifications [FULL]) |
| **Mark-LVI Implementation** | `ui.py. Uses QSystemTrayIcon to trigger Windows system tray notifications.` |
| **Alex Target Implementation** | `frontend/electron/main.ts, backend/app/services/notification_service.py. Native OS toast notifications via Electron Notification API and plyer.` |
| **Mark-LVI Workflow** | Displays tray notification on task completion. |
| **Alex Workflow** | Sends rich desktop notification with action callbacks and sound. |
| **Category Parity Summary** | **FULL** (Architecturally Superior in Alex) |
| **Technical Gap & Architectural Distinction** | None. |
| **Dependencies & Prerequisites** | Electron, plyer. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: APNs |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain current implementation. |
| **Acceptance Criteria** | Native notification banner appears on desktop with title, message, and icon. |
| **Evidence & Source References** | `frontend/electron/main.ts, backend/app/services/notification_service.py.` |

---

### Category 26: Background Services & Proactive Intelligence

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-26` |
| **Constituent Functional Units** | `UNIT-50` (Proactive Startup Briefing [FULL]), `UNIT-51` (Background Topic & RSS News Monitor [MISSING]) |
| **Mark-LVI Implementation** | `actions/proactive.py, actions/background_monitor.py. Generates morning briefing; background threads poll news RSS feeds and monitor system alerts.` |
| **Alex Target Implementation** | `backend/app/services/briefing_service.py (/api/v1/system/briefing). Synthesizes system health, pending reminders, memory facts, and greeting.` |
| **Mark-LVI Workflow** | Speaks proactive greeting on startup; alerts user when tracked topic news appears. |
| **Alex Workflow** | Provides structured startup briefing API consumed by React HUD on launch. |
| **Category Parity Summary** | **PARTIAL** (UNIT-50: FULL; UNIT-51: MISSING) |
| **Technical Gap & Architectural Distinction** | Alex lacks persistent background topic monitoring threads. |
| **Dependencies & Prerequisites** | FastAPI, feedparser. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Background fetch |
| **Migration Complexity** | MEDIUM |
| **Required Implementation Actions** | Add background topic monitor service in Phase 7. |
| **Acceptance Criteria** | Startup briefing delivers comprehensive summary of system status and reminders. |
| **Evidence & Source References** | `backend/app/services/briefing_service.py, backend/tests/test_briefing_service.py.` |

---

### Category 27: Scheduling & OS-Native Reminders

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-27` |
| **Constituent Functional Units** | `UNIT-52` (In-Memory Timer & Countdown Dispatcher [FULL]), `UNIT-53` (Persistent OS Schedulers Integration [PARTIAL]) |
| **Mark-LVI Implementation** | `actions/reminder.py. In-memory timers and Windows Task Scheduler integration.` |
| **Alex Target Implementation** | `backend/app/services/reminder_service.py (/api/v1/reminders). In-memory timers with persistent atomic JSON storage.` |
| **Mark-LVI Workflow** | Creates task schedule or timer; alerts when expired. |
| **Alex Workflow** | Full CRUD API for reminders with active countdowns and toast notifications. |
| **Category Parity Summary** | **PARTIAL** (UNIT-52: FULL; UNIT-53: PARTIAL) |
| **Technical Gap & Architectural Distinction** | Alex relies on active backend process; lacks OS Task Scheduler / launchd / cron sync. |
| **Dependencies & Prerequisites** | asyncio, storage_service. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: UNUserNotificationCenter |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Add OS scheduler synchronization in Phase 5. |
| **Acceptance Criteria** | Reminders persist across application restarts and trigger on exact schedule. |
| **Evidence & Source References** | `backend/app/services/reminder_service.py, backend/tests/test_reminder_service.py.` |

---

### Category 28: User Settings & Configuration Management

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-28` |
| **Constituent Functional Units** | `UNIT-54` (Typed Application Settings Form & Schema [FULL]), `UNIT-55` (HueWheel Real-Time Accent Tinting [PARTIAL]) |
| **Mark-LVI Implementation** | `ui.py (Settings drawer). Unstructured form controls and custom HueWheel RGB picker.` |
| **Alex Target Implementation** | `frontend/src/pages/SettingsPage.tsx, backend/app/services/settings_service.py. Pydantic v2 typed configuration schema, theme presets, audio settings.` |
| **Mark-LVI Workflow** | User adjusts settings in drawer; persists to settings.json. |
| **Alex Workflow** | User modifies settings via React UI; persists to atomic settings document. |
| **Category Parity Summary** | **PARTIAL** (UNIT-54: FULL; UNIT-55: PARTIAL) |
| **Technical Gap & Architectural Distinction** | Alex has preset theme swatches but lacks continuous HueWheel RGB color picker. |
| **Dependencies & Prerequisites** | React, Tailwind CSS, Pydantic. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Add continuous color wheel picker to SettingsPage in Phase 7. |
| **Acceptance Criteria** | Settings updates apply immediately to HUD and persist across sessions. |
| **Evidence & Source References** | `backend/app/services/settings_service.py, frontend/src/pages/SettingsPage.tsx.` |

---

### Category 29: Permissions, Security Gates & Confirmation Gate

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-29` |
| **Constituent Functional Units** | `UNIT-56` (Interactive Human Confirmation Gate [FULL]) |
| **Mark-LVI Implementation** | `core/confirm.py. PyQt6 modal confirmation dialog for shutdown, reboot, WiFi disconnect.` |
| **Alex Target Implementation** | `backend/app/services/computer_control_service.py, frontend/src/components/ApprovalModal.tsx. Cryptographic approval tokens, proposal expiry, visual modal confirmation.` |
| **Mark-LVI Workflow** | Pops modal dialog blocking thread until user clicks OK or Cancel. |
| **Alex Workflow** | Action returns proposal token; frontend displays rich approval modal with operation parameters; user approves with one-shot token. |
| **Category Parity Summary** | **FULL** (Architecturally Superior in Alex) |
| **Technical Gap & Architectural Distinction** | None. Alex provides cryptographic one-shot tokens and 5-minute proposal timeouts. |
| **Dependencies & Prerequisites** | React, FastAPI, secrets. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain current implementation. |
| **Acceptance Criteria** | Irreversible actions are blocked until user confirms via UI approval modal. |
| **Evidence & Source References** | `backend/app/services/computer_control_service.py, frontend/src/components/ApprovalModal.tsx.` |

---

### Category 30: Authentication & Session Security

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-30` |
| **Constituent Functional Units** | `UNIT-57` (Loopback Bearer Token Authentication [FULL]), `UNIT-58` (OS Keyring Vault Integration [FULL]) |
| **Mark-LVI Implementation** | `main.py, config/api_keys.json. Static pairing PIN; plaintext API keys written to disk.` |
| **Alex Target Implementation** | `backend/app/core/auth.py, launcher/cli.py, backend/app/core/keyring_vault.py. 32-byte dynamic loopback bearer token; OS Keyring vault.` |
| **Mark-LVI Workflow** | Reads plaintext api_keys.json on startup; binds open port. |
| **Alex Workflow** | Launcher generates secure 32-byte token per run; injects into Electron and sidecar; OS Keyring secures API keys. |
| **Category Parity Summary** | **FULL** (Architecturally Superior in Alex) |
| **Technical Gap & Architectural Distinction** | None. Alex eliminates all plaintext credential storage. |
| **Dependencies & Prerequisites** | keyring, secrets, fastapi. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Keychain |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain current implementation. |
| **Acceptance Criteria** | All REST and WebSocket endpoints require valid bearer token; secrets stored in OS vault. |
| **Evidence & Source References** | `backend/app/core/auth.py, backend/app/core/keyring_vault.py.` |

---

### Category 31: Database & Persistent Storage Architecture

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-31` |
| **Constituent Functional Units** | `UNIT-59` (Atomic Document Storage & Write-Rename Safety [FULL]) |
| **Mark-LVI Implementation** | `main.py, json file operations. Standard open(path, 'w') without file locking or atomic replacement.` |
| **Alex Target Implementation** | `backend/app/services/storage_service.py. Atomic write-to-tempfile and atomic os.replace() pattern.` |
| **Mark-LVI Workflow** | Overwrites JSON files directly, vulnerable to corruption on sudden power loss. |
| **Alex Workflow** | Writes new data to temporary file, flushes to disk, and replaces target atomically. |
| **Category Parity Summary** | **FULL** (Architecturally Superior in Alex) |
| **Technical Gap & Architectural Distinction** | None. |
| **Dependencies & Prerequisites** | tempfile, os, json. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain current implementation. |
| **Acceptance Criteria** | Storage writes cannot result in corrupted or zero-byte JSON files upon unexpected termination. |
| **Evidence & Source References** | `backend/app/services/storage_service.py, backend/tests/test_storage.py.` |

---

### Category 32: Logging, Diagnostics & Pre-Flight Doctor

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-32` |
| **Constituent Functional Units** | `UNIT-60` (Pre-Flight System Doctor Diagnostics [FULL]) |
| **Mark-LVI Implementation** | `setup.py. Basic dependency presence check during installation.` |
| **Alex Target Implementation** | `launcher/cli.py, launcher/health.py. alex doctor validates Python version, Node.js, loopback ports, dependencies, OS capabilities.` |
| **Mark-LVI Workflow** | Manual installation checks. |
| **Alex Workflow** | Comprehensive pre-flight healthcheck with actionable repair instructions. |
| **Category Parity Summary** | **FULL** (Architecturally Superior in Alex) |
| **Technical Gap & Architectural Distinction** | None. |
| **Dependencies & Prerequisites** | launcher, psutil, socket. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Server-side only |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain current implementation. |
| **Acceptance Criteria** | alex doctor accurately reports system readiness and identifies environment blockers. |
| **Evidence & Source References** | `launcher/cli.py, launcher/health.py.` |

---

### Category 33: Error Handling & Graceful Recovery

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-33` |
| **Constituent Functional Units** | `UNIT-61` (WebSocket Exponential Backoff & State Reconnect [PARTIAL]) |
| **Mark-LVI Implementation** | `core/gemini.py. Exponential backoff retry loop (1s, 2s, 4s...) on WebSocket network drops.` |
| **Alex Target Implementation** | `backend/app/services/live_voice_service.py. Basic retry counters; lacks full exponential backoff state machine.` |
| **Mark-LVI Workflow** | On network glitch, retries connection exponentially without terminating voice loop. |
| **Alex Workflow** | Retries connection; on prolonged drop terminates session with error alert. |
| **Category Parity Summary** | **PARTIAL** |
| **Technical Gap & Architectural Distinction** | Alex needs full exponential backoff and jitter state machine for live voice recovery. |
| **Dependencies & Prerequisites** | asyncio, websockets. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Add exponential backoff with jitter to LiveVoiceService in Phase 3. |
| **Acceptance Criteria** | Transient network interruptions recover automatically within 3 retries without crashing UI. |
| **Evidence & Source References** | `backend/app/services/live_voice_service.py.` |

---

### Category 34: Security Boundaries & Context Isolation

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-34` |
| **Constituent Functional Units** | `UNIT-62` (Electron Context Isolation & Preload Allowlist [FULL]) |
| **Mark-LVI Implementation** | `ui.py. PyQt6 single process; GUI widgets have unrestricted access to Python host primitives.` |
| **Alex Target Implementation** | `frontend/electron/main.ts, frontend/electron/preload.ts. Strict Electron isolation: contextIsolation: true, nodeIntegration: false, typed IPC allowlist.` |
| **Mark-LVI Workflow** | UI components can invoke arbitrary Python code directly. |
| **Alex Workflow** | Renderer has zero access to Node.js internals or shell execution; all requests traverse typed IPC allowlist. |
| **Category Parity Summary** | **FULL** (Architecturally Superior in Alex) |
| **Technical Gap & Architectural Distinction** | None. |
| **Dependencies & Prerequisites** | Electron contextBridge. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: WebKit sandbox |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain strict Electron security settings. |
| **Acceptance Criteria** | Window context in renderer cannot execute require('child_process') or access fs. |
| **Evidence & Source References** | `frontend/electron/preload.ts, frontend/electron/main.ts.` |

---

### Category 35: Performance & Resource Management

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-35` |
| **Constituent Functional Units** | `UNIT-63` (Hardware Telemetry via psutil [FULL]) |
| **Mark-LVI Implementation** | `actions/system_monitor.py. CPU, RAM, disk usage telemetry via psutil.` |
| **Alex Target Implementation** | `backend/app/services/system_service.py (/api/v1/system/metrics). Structured CPU, memory, disk, and process telemetry.` |
| **Mark-LVI Workflow** | Queries psutil metrics and formats text responses. |
| **Alex Workflow** | FastAPI metrics endpoint provides JSON telemetry consumed by UI and health monitor. |
| **Category Parity Summary** | **FULL** |
| **Technical Gap & Architectural Distinction** | None. |
| **Dependencies & Prerequisites** | psutil. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Scoped |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Maintain current implementation. |
| **Acceptance Criteria** | System metrics endpoint responds in <20ms with accurate CPU and memory statistics. |
| **Evidence & Source References** | `backend/app/services/system_service.py, backend/tests/test_system_service.py.` |

---

### Category 36: Packaging, Distribution & Production Bundling

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-36` |
| **Constituent Functional Units** | `UNIT-64` (Multi-Platform Production Bundler Configurations [FULL]) |
| **Mark-LVI Implementation** | `setup.py. Unpackaged source distribution requiring manual pip install.` |
| **Alex Target Implementation** | `scripts/package-electron.sh, package.json, pyproject.toml. Configured for Electron Builder and PyInstaller bundling.` |
| **Mark-LVI Workflow** | User manually installs Python dependencies in virtual environment. |
| **Alex Workflow** | Automated packaging scripts produce standalone desktop distribution packages. |
| **Category Parity Summary** | **FULL** (Architecturally Superior in Alex) |
| **Technical Gap & Architectural Distinction** | None in build architecture; codesigning and notarization pending release pipeline. |
| **Dependencies & Prerequisites** | electron-builder, pyinstaller. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Xcode |
| **Migration Complexity** | MEDIUM |
| **Required Implementation Actions** | Verify packaging pipeline across target platforms in Phase 8. |
| **Acceptance Criteria** | Packaged executable launches on clean target OS without pre-installed Python/Node. |
| **Evidence & Source References** | `scripts/package-electron.sh, package.json.` |

---

### Category 37: Remote Smartphone Dashboard & Mobile Control

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-37` |
| **Constituent Functional Units** | `UNIT-65` (Remote Mobile Web/WS Dashboard & QR Pairing [MISSING]) |
| **Mark-LVI Implementation** | `main.py (Remote web interface). FastAPI server serving mobile web dashboard with QR code pairing for remote voice and action dispatch.` |
| **Alex Target Implementation** | `None. Alex is currently desktop-only.` |
| **Mark-LVI Workflow** | HUD displays QR code; user scans with smartphone to open remote control dashboard over local network. |
| **Alex Workflow** | Not supported. |
| **Category Parity Summary** | **MISSING** |
| **Technical Gap & Architectural Distinction** | Alex lacks remote mobile dashboard and smartphone pairing. |
| **Dependencies & Prerequisites** | FastAPI, qrcode, WebSockets. |
| **Platform Compatibility** | Windows: Server | Ubuntu: Server | macOS: Server | iOS: Native/Web companion |
| **Migration Complexity** | HIGH |
| **Required Implementation Actions** | Implement encrypted Mobile Companion Client in Phase 6 (ADR-09). |
| **Acceptance Criteria** | User can pair smartphone via QR code and securely control assistant over LAN. |
| **Evidence & Source References** | `Mark-LVI-main/main.py, docs/migration/MIGRATION_DECISIONS.md (ADR-09).` |

---

### Category 38: Local Wake-Word Detection (Hey Jarvis)

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-38` |
| **Constituent Functional Units** | `UNIT-66` (Local Offline Wake-Word Detection Engine [MISSING]) |
| **Mark-LVI Implementation** | `core/wake_word.py. openwakeword ONNX model running on CPU to detect 'Hey Jarvis'. Audio is discarded until wake word triggers.` |
| **Alex Target Implementation** | `None. User must click mic button in React UI.` |
| **Mark-LVI Workflow** | Assistant sleeps in background; user says 'Hey Jarvis'; assistant wakes and opens voice stream. |
| **Alex Workflow** | Manual click to listen. |
| **Category Parity Summary** | **MISSING** |
| **Technical Gap & Architectural Distinction** | Alex lacks local offline wake-word detection. |
| **Dependencies & Prerequisites** | openwakeword, onnxruntime. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: N/A |
| **Migration Complexity** | HIGH |
| **Required Implementation Actions** | Implement WakeWordService using openwakeword in Phase 4. |
| **Acceptance Criteria** | System activates from idle state within 300ms of hearing 'Hey Alex' without cloud streaming. |
| **Evidence & Source References** | `Mark-LVI-main/core/wake_word.py.` |

---

### Category 39: Cross-Platform Capability Awareness

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-39` |
| **Constituent Functional Units** | `UNIT-67` (OS Capability & Security Boundary Detection [PARTIAL]) |
| **Mark-LVI Implementation** | `core/platform_support.py. Detects Wayland restrictions on Ubuntu, macOS TCC permissions, and passes capabilities into prompt.` |
| **Alex Target Implementation** | `backend/app/services/platform_capability_service.py (/api/v1/system/capabilities). Detects basic OS platform and features.` |
| **Mark-LVI Workflow** | Inspects session type (X11 vs Wayland), checks macOS TCC status, instructs LLM on available automation primitives. |
| **Alex Workflow** | Returns JSON capabilities report indicating active platform limitations. |
| **Category Parity Summary** | **PARTIAL** |
| **Technical Gap & Architectural Distinction** | Alex needs deeper Wayland uinput checking and macOS TCC permission onboarding. |
| **Dependencies & Prerequisites** | platform, os, ctypes. |
| **Platform Compatibility** | Windows: Supported | Ubuntu: Supported | macOS: Supported | iOS: Supported |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Enhance PlatformCapabilityService with TCC and Wayland checks in Phase 5. |
| **Acceptance Criteria** | Capabilities API accurately reports OS automation limits and injects constraints into LLM prompt. |
| **Evidence & Source References** | `backend/app/services/platform_capability_service.py, backend/tests/test_platform_capability_service.py.` |

---

### Category 40: Testing Architecture & Physical Acceptance Criteria

| Field | Specification |
| :--- | :--- |
| **Category ID** | `CAT-40` |
| **Constituent Functional Units** | `UNIT-68` (Automated Regression Test Suite [FULL]) |
| **Mark-LVI Implementation** | `providers/_tests.py. 14 inline diagnostic tests.` |
| **Alex Target Implementation** | `backend/tests (109 passing unit/API tests), frontend/src/__tests__ (Vitest suites), docs/archive/external-acceptance (33 acceptance protocols).` |
| **Mark-LVI Workflow** | Runs basic provider connectivity checks. |
| **Alex Workflow** | Comprehensive automated unit and API regression suite covering all backend services, launcher, and frontend components. |
| **Category Parity Summary** | **FULL** (Code & Automated Testing: FULL; Physical Acceptance: Blocked by Environment - BLK-ENV-001) |
| **Technical Gap & Architectural Distinction** | Automated code tests are comprehensive. Blocked strictly on physical hardware test execution (0/33). |
| **Dependencies & Prerequisites** | pytest, vitest, httpx. |
| **Platform Compatibility** | Windows: 0/33 physical | Ubuntu: Unverified | macOS: Unverified | iOS: Unverified |
| **Migration Complexity** | LOW |
| **Required Implementation Actions** | Execute physical acceptance on external workstation once provisioned. |
| **Acceptance Criteria** | 100% automated test pass rate; physical verification on target Windows workstation. |
| **Evidence & Source References** | `backend/tests, docs/release/RELEASE_STATUS.md.` |

---

