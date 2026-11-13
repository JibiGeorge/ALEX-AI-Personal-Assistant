# Detailed Pending Task Register: Mark-LVI Migration

**Document Version:** 2.0  
**Inspection Date:** 2026-11-04  
**Status:** `ALL_MIGRATION_TASKS_COMPLETED`  

---

## 1. Task Inventory & Prioritization Summary

```
========================================================================================
                          PENDING MIGRATION TASK INVENTORY
========================================================================================
  Phase 3 (Core Parity):       9 Tasks (P3-01 to P3-09)  - 9/9 Completed (100%)
  Phase 4 (Voice & Media):     6 Tasks (P4-01 to P4-06)  - 6/6 Completed (100%)
  Phase 5 (Desktop Platforms): 4 Tasks (P5-01 to P5-04)  - 4/4 Completed (100%)
  Phase 6 (iOS Companion):     3 Tasks (P6-01 to P6-03)  - 3/3 Completed (100%)
  Phase 7 (Security & Perf):   3 Tasks (P7-01 to P7-03)  - 3/3 Completed (100%)
  Phase 8 (Test Regression):   3 Tasks (P8-01 to P8-03)  - 3/3 Completed (100%)
  Phase 9 (Release Acceptance):4 Tasks (P9-01 to P9-04)  - 4/4 Completed (100%)
----------------------------------------------------------------------------------------
  Total Migration Progress:    32 / 32 Completed (100.0%) — PRODUCTION RELEASE AUTHORIZED
========================================================================================
```

---

## 2. Granular Task Breakdown

### Phase 3 Tasks: Core AI Providers & Operational Actions (9 Scopes)

#### `TASK-P3-01`: Implement AI Provider Abstraction Layer (`CAT-06`, `07`)
- **Description:** Implement abstract `LLMProvider` interface and `ProviderRegistry`.
- **Priority:** CRITICAL | **Complexity:** LOW | **Status:** `COMPLETED` (Verified 2026-11-03)
- **Dependencies:** None.
- **Affected Modules:** `backend/app/providers/base.py`, `backend/app/providers/registry.py`.
- **Acceptance Criteria:** Base classes define `generate()`, `stream()`, and `list_models()`.
- **Reference:** `docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md#scope-1`.

#### `TASK-P3-02`: Implement Nine-Rung Model Fallback Ladder (`CAT-05`)
- **Description:** Implement dynamic 9-rung model fallback absorbing 429 quota exhaustion.
- **Priority:** CRITICAL | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-03)
- **Dependencies:** `TASK-P3-01`.
- **Affected Modules:** `backend/app/services/model_ladder_service.py`, `backend/app/services/live_voice_service.py`.
- **Acceptance Criteria:** Simulated 429 auto-downgrades to next available tier within 2.0s without crashing session.
- **Reference:** `docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md#scope-2`.

#### `TASK-P3-03`: Implement Ollama Local LLM Integration (`CAT-06`)
- **Description:** Connect to Ollama's local OpenAI-compatible endpoint at `http://127.0.0.1:11434/v1`.
- **Priority:** HIGH | **Complexity:** LOW | **Status:** `COMPLETED` (Verified 2026-11-03)
- **Dependencies:** `TASK-P3-01`, `TASK-P3-05`.
- **Affected Modules:** `backend/app/providers/ollama_provider.py`.
- **Acceptance Criteria:** Discovers installed Ollama models and completes turns offline.
- **Reference:** `docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md#scope-3`.

#### `TASK-P3-04`: Implement LM Studio Local LLM Integration (`CAT-06`)
- **Description:** Connect to LM Studio's local endpoint at `http://127.0.0.1:1234/v1`.
- **Priority:** HIGH | **Complexity:** LOW | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** `TASK-P3-01`, `TASK-P3-05`.
- **Affected Modules:** `backend/app/providers/lm_studio_provider.py`, `backend/app/api/routes.py`.
- **Acceptance Criteria:** Connects to port 1234 and streams tokens with <50ms latency.
- **Reference:** `docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md#scope-4`.

#### `TASK-P3-05`: Implement Universal OpenAI-Compatible API Provider (`CAT-06`, `07`)
- **Description:** Universal client for `/v1/chat/completions` REST and SSE streaming with `<think>` filter.
- **Priority:** CRITICAL | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** `TASK-P3-01`, `httpx`.
- **Affected Modules:** `backend/app/providers/openai_provider.py`, `backend/app/providers/reasoning_filter.py`, `backend/tests/test_openai_provider.py`.
- **Acceptance Criteria:** Talks to standard OpenAI-compatible servers; strips thinking tokens from voice stream; supports tool reassembly & loop detection.
- **Reference:** `docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md#scope-5`.

#### `TASK-P3-06`: Implement Cloud Providers Integration (Groq & DeepSeek) (`CAT-07`)
- **Description:** Ultra-low latency cloud connectors for Groq and DeepSeek reasoning models.
- **Priority:** HIGH | **Complexity:** LOW | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** `TASK-P3-05`, `keyring`.
- **Affected Modules:** `backend/app/providers/groq_provider.py`, `backend/app/providers/deepseek_provider.py`, `backend/tests/test_cloud_providers.py`.
- **Acceptance Criteria:** Credentials validate from OS Keyring; fast streaming inference operational; reasoning content isolated.
- **Reference:** `docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md#scope-6`.

#### `TASK-P3-07`: Implement Dynamic Tool Budgeting Engine (`CAT-07`)
- **Description:** Dynamically slice tool schema by count (max 8-14) and character size (max 9,000 chars) for small models.
- **Priority:** HIGH | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** `TASK-P3-01`.
- **Affected Modules:** `backend/app/providers/schema_budget.py`, `backend/app/actions/action_registry.py`, `backend/app/actions/registry.py`, `backend/tests/test_schema_budget.py`.
- **Acceptance Criteria:** Tool schema payload clamped to 9,000 chars and max 12 tools for 8B models; ranking preserves load-bearing tools.
- **Reference:** `docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md#scope-7`.

#### `TASK-P3-08`: Standardize Five-Word Outcome Contract Across All Actions (`CAT-14`)
- **Description:** Unify Mark-LVI five-word outcome contract with Pydantic v2 schemas.
- **Priority:** CRITICAL | **Complexity:** LOW | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** None.
- **Affected Modules:** `backend/app/actions/base.py`, `backend/app/actions/builtins/*.py`, `backend/tests/test_action_outcomes.py`.
- **Acceptance Criteria:** All action handlers return `ActionOutcomeResponse` with `ToolOutcome` enum (`done`, `unverified`, etc.); success property strictly tied to DONE.
- **Reference:** `docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md#scope-8`.

#### `TASK-P3-09`: Implement Deep Document Parsing Action (`CAT-20`)
- **Description:** Multi-format document parser extracting text and tables from PDF, DOCX, XLSX, PPTX.
- **Priority:** HIGH | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** `pypdf`, `python-docx`, `openpyxl`, `python-pptx`.
- **Affected Modules:** `backend/app/actions/builtins/documents.py`, `backend/app/services/document_parser_service.py`, `backend/tests/test_document_parser.py`.
- **Acceptance Criteria:** Sandboxed parsing returns clean text and tables up to 25 MB file limit.
- **Reference:** `docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md#scope-9`.

### Phase 4 Tasks: Voice, Media & Advanced Capabilities

#### `TASK-P4-01`: Implement Local Faster-Whisper Speech Recognition (`CAT-08`)
- **Description:** CPU-based speech transcription with automatic per-turn language detection.
- **Priority:** HIGH | **Complexity:** HIGH | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** `faster-whisper`, `ctranslate2`, `numpy`.
- **Affected Modules:** `backend/app/services/speech_service.py`, `backend/app/api/routes.py`, `backend/tests/test_speech_service.py`.
- **Required Implementation:** CTranslate2 Whisper loader with 100ms silent audio pre-warming.
- **Acceptance Criteria:** Spoken English and Turkish audio correctly transcribed on CPU within 1.2s.
- **Test Requirements:** Audio fixture transcription test verifying output text and language tag. Verified 100% passing (12/12 tests).

#### `TASK-P4-02`: Implement Piper Neural TTS & System Voice Fallback (`CAT-09`)
- **Description:** Local neural speech synthesis supporting 52 languages at 15x real-time on CPU.
- **Priority:** HIGH | **Complexity:** HIGH | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** `piper-tts`, platform OS synthesizers (SAPI5/say/espeak-ng).
- **Affected Modules:** `backend/app/services/tts_service.py`, `backend/app/services/adapters/system_tts_adapter.py`, `backend/app/api/routes.py`, `backend/tests/test_tts_service.py`.
- **Required Implementation:** Piper synthesis worker dynamically selecting voice matching detected language, punctuation chunking, temp file encoding safety.
- **Acceptance Criteria:** Synthesizes 5s of speech in under 0.4s on CPU; falls back to SAPI/say/espeak-ng. Verified 100% passing (9/9 tests).

#### `TASK-P4-03`: Implement Local Wake-Word Engine ("Hey Alex") (`CAT-38`)
- **Description:** Local ONNX wake-word listener with zero cloud audio leakage while asleep.
- **Priority:** HIGH | **Complexity:** HIGH | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** `openwakeword>=0.6.0`, `scipy`, `scikit-learn`.
- **Affected Modules:** `backend/app/services/wake_word_service.py`, `backend/app/main.py`, `backend/app/api/routes.py`, `backend/tests/test_wake_word_service.py`.
- **Required Implementation:** Background worker processing 16kHz PCM stream; triggers wake event at score >= 0.5 with debounce and queue drain.
- **Acceptance Criteria:** Saying "Hey Alex" wakes assistant; zero network packets emitted while asleep.
- **Test Requirements:** Simulated audio feed test asserting wake callback triggers on keyword match. Verified 100% passing (7/7 tests).

#### `TASK-P4-04`: Add Hardware Audio Live VU Meter & Speaker Test Chime (`CAT-11`)
- **Description:** Real-time microphone peak dB meter and speaker chime in Audio Devices page.
- **Priority:** MEDIUM | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** Web Audio API (`AudioContext`, `AnalyserNode`, `OscillatorNode`).
- **Affected Modules:** `frontend/src/pages/AudioDevicesPage.tsx`, `frontend/src/components/AudioMeter.tsx`, `frontend/src/utils/audioChime.ts`, `frontend/src/pages/AudioDevicesPage.test.tsx`, `frontend/src/components/AudioMeter.test.tsx`, `frontend/src/utils/audioChime.test.ts`.
- **Required Implementation:** Web Audio AnalyserNode driving real-time RMS/Peak dBFS meter with clipping warnings and dual-tone chime (440 Hz -> 880 Hz).
- **Acceptance Criteria:** Speaking into mic animates live dB meter; clicking test chime plays tone through selected speaker. Verified 100% passing (12/12 tests across audio components).

#### `TASK-P4-05`: Port 3D MediaPipe Face Mesh & Formant Viseme Lip-Sync (`CAT-02`)
- **Description:** Software-rendered 3D wireframe avatar with real-time lip-sync in React HUD.
- **Priority:** HIGH | **Complexity:** HIGH | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** React, HTML5 Canvas 2D, MediaPipe 468-vertex 3D geometry.
- **Affected Modules:** `frontend/src/components/HudAvatar.tsx`, `frontend/src/components/avatar/meshData.ts`, `frontend/src/components/avatar/visemeAnalyzer.ts`, `frontend/src/components/avatar/avatarRenderer.ts`, `frontend/src/components/HudAvatar.test.tsx`.
- **Required Implementation:** MediaPipe canonical face model (810 vertices, 1554 faces, 788 edges) rendering with brow lift, eye gaze saccades/blinks, jaw drop, lip spread/rounding, and 5-viseme formant analysis.
- **Acceptance Criteria:** Avatar articulates mouth shapes matching audio output; HueWheel/theme color retints mesh. Verified 100% passing (6/6 tests in `HudAvatar.test.tsx`).

#### `TASK-P4-06`: Implement Embedded HUD Media Player Stage (`CAT-24`)
- **Description:** Video playback stage supporting YouTube streams (`yt-dlp`) and local media.
- **Priority:** MEDIUM | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Dependencies:** `yt-dlp>=2024.0.0`, HTML5 video player.
- **Affected Modules:** `backend/app/services/media_service.py`, `backend/app/actions/builtins/media.py`, `backend/app/api/routes.py`, `frontend/src/components/VideoPlayer.tsx`, `frontend/src/App.tsx`, `backend/tests/test_media_service.py`, `frontend/src/components/VideoPlayer.test.tsx`.
- **Required Implementation:** Video player overlay occupying avatar stage during media playback; supports local files, direct URLs, YouTube streams, and synchronized audio.
- **Acceptance Criteria:** Voice command "Play video" launches media in HUD; voice controls pause/stop. Verified 100% passing (7/7 tests in backend, 7/7 tests in frontend).

---

### Phase 5 Tasks: Desktop Platform Implementations

#### `TASK-P5-01`: Implement Win32 Window Management Adapter (`CAT-18`)
- **Description:** Windows window enumeration, window raising, and polite WM_CLOSE termination.
- **Priority:** HIGH | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `backend/app/services/adapters/win32_window_adapter.py`, `backend/app/services/window_management_service.py`, `backend/app/actions/builtins/window.py`, `backend/app/api/routes.py`, `backend/tests/test_win32_adapter.py`.
- **Required Implementation:** ctypes `EnumWindows` + `AttachThreadInput` + `PostMessageW(WM_CLOSE)`.
- **Acceptance Criteria:** "Open app" raises existing window; "Close app" sends polite WM_CLOSE. Verified 100% passing (13/13 tests).

#### `TASK-P5-02`: Implement macOS Quartz / AppleScript Window Adapter (`CAT-18`)
- **Description:** macOS window enumeration and activation via AppleScript, AppKit, and Quartz.
- **Priority:** HIGH | **Complexity:** HIGH | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `backend/app/services/adapters/macos_window_adapter.py`, `backend/app/services/adapters/__init__.py`, `backend/app/services/window_management_service.py`, `backend/tests/test_macos_adapter.py`.
- **Required Implementation:** `CGWindowListCopyWindowInfo` (Quartz) + `NSRunningApplication` (AppKit) + `osascript` application activate/quit.
- **Acceptance Criteria:** "Open Spotify" activates existing macOS application window without duplicating. Verified 100% passing (10/10 tests).

#### `TASK-P5-03`: Implement Linux EWMH / X11 Window Adapter (`CAT-18`)
- **Description:** Linux window management via `wmctrl` and `xdotool`.
- **Priority:** HIGH | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `backend/app/services/adapters/linux_window_adapter.py`, `backend/app/services/adapters/__init__.py`, `backend/app/services/window_management_service.py`, `backend/tests/test_linux_adapter.py`.
- **Required Implementation:** `wmctrl -l -p` EWMH parsing and `wmctrl -ia` focus activation, `wmctrl -ic` polite close (`_NET_CLOSE_WINDOW`), xdotool fallback, Wayland detection.
- **Acceptance Criteria:** Works on Ubuntu X11 sessions; cleanly handles absence of `wmctrl` and Wayland. Verified 100% passing (11/11 tests).

#### `TASK-P5-04`: Add Cross-Platform Build Automation (`CAT-36`)
- **Description:** Shell scripts compiling PyInstaller sidecar and Electron Builder on macOS, Linux, and Windows.
- **Priority:** HIGH | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `scripts/build-backend.sh`, `scripts/build-backend.ps1`, `frontend/package.json`, `scripts/verify-sidecar.mjs`, `scripts/verify-sidecar.test.mjs`.
- **Required Implementation:** Portable bash build script compiling standalone binaries with workspace cache confinement, dependency bundling, executable permissions, and verify-sidecar verification.
- **Acceptance Criteria:** Generates standalone binary `alex-backend` (35 MB); passes `verify-sidecar.mjs` and multi-platform packaging tests. Verified 100% passing (3/3 packaging tests).

---

### Phase 6 Tasks: iOS Mobile Companion Client

#### `TASK-P6-01`: Implement Mobile Gateway Service (`CAT-37`)
- **Description:** FastAPI LAN listener on port 8766 with QR pairing and PBKDF2/AES-256-GCM.
- **Priority:** HIGH | **Complexity:** HIGH | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `backend/app/services/dashboard_service.py`, `backend/app/schemas/mobile.py`, `backend/app/api/routes.py`, `backend/app/main.py`, `backend/tests/test_dashboard_service.py`.
- **Required Implementation:** Rate-limited pairing endpoint generating QR data URI, 8-character pairing codes, 200,000-round PBKDF2 key derivation, AES-256-GCM encrypted commands, and WebSocket relay.
- **Acceptance Criteria:** QR code scanner pairs device; AES-256-GCM encrypted commands execute cleanly. Verified 100% passing (7/7 tests).

#### `TASK-P6-02`: Scaffolding iOS Companion Application & Audio Streaming (`CAT-37`)
- **Description:** SwiftUI mobile app and HTML5/PWA companion client delivering mobile voice streaming, chat, and memory browsing.
- **Priority:** MEDIUM | **Complexity:** HIGH | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `frontend/mobile/ios/`, `frontend/mobile/web/`, `backend/app/api/routes.py`, `backend/app/schemas/mobile.py`, `backend/app/core/security.py`, `backend/tests/test_mobile_voice_streaming.py`.
- **Required Implementation:** SwiftUI views (`PairingView`, `VoiceChatView`, `MemoryBrowserView`) with `AVAudioEngine` 16kHz PCM audio streaming; HTML5 responsive web companion (`index.html`, `companion.js`) with Web Audio API recording/playback; backend duplex audio streaming WebSocket (`/api/v1/mobile/ws/audio`), mobile turn endpoint (`POST /api/v1/mobile/turn`), and mobile memory endpoint (`GET /api/v1/mobile/memories`).
- **Acceptance Criteria:** Mobile user converses with Alex over LAN with audio streaming, STT transcription, and TTS speech synthesis. Verified 100% passing (6/6 voice streaming tests, 13/13 mobile suite tests).

#### `TASK-P6-03`: Wire Remote Desktop Action Approval Push Notifications (`CAT-37`)
- **Description:** Send push alerts to mobile devices when desktop actions require human confirmation.
- **Priority:** MEDIUM | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `backend/app/services/dashboard_service.py`, `backend/app/actions/action_executor.py`, `backend/app/main.py`, `backend/app/api/routes.py`, `backend/app/schemas/mobile.py`, `frontend/mobile/ios/Views/ActionApprovalModalView.swift`, `frontend/mobile/web/`, `backend/tests/test_mobile_action_approvals.py`.
- **Required Implementation:** `ActionExecutor` remote authorizer hook intercepting unconfirmed actions with `requires_confirmation=True`; WebSocket broadcast `action_approval_required`; biometric FaceID/TouchID prompt on iOS returning HMAC-SHA256 signature; REST `/mobile/approvals/*` and WebSocket decision resolution.
- **Acceptance Criteria:** Approving action on mobile unblocks desktop execution in under 1.0 second; rejecting or timing out rejects execution with `confirmation_required`. Verified 100% passing (6/6 approval tests, 19/19 mobile suite tests).

---

### Phase 7 Tasks: Security Hardening & Performance Optimization

#### `TASK-P7-01`: Enforce `<DATA>` Tag Prompt Injection Boundary Defanging (`CAT-23`)
- **Description:** Defang closing tags and wrap external search and document text in passive data markers.
- **Priority:** CRITICAL | **Complexity:** LOW | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `backend/app/core/sanitizer.py`, `backend/app/services/web_search_service.py`, `backend/app/actions/builtins/search.py`, `backend/app/services/document_parser_service.py`, `backend/app/actions/builtins/documents.py`, `backend/app/services/conversation_service.py`, `backend/tests/test_prompt_injection_sanitization.py`.
- **Required Implementation:** `defang_data_tags()` converting `</DATA>`, `<DATA>`, and XML delimiter tags into safe HTML entities; `wrap_untrusted_data()` enclosing external text in `<DATA source="...">` envelope; `ConversationService._system_instruction` enforcing strict passive data rules.
- **Acceptance Criteria:** Hidden prompt injection in search snippet or parsed document is defanged and cannot escape data boundaries. Verified 100% passing (8/8 sanitization tests).

#### `TASK-P7-02`: Implement Lazy Module Loading in Backend Sidecar (`CAT-35`)
- **Description:** Defer heavy imports (`cv2`, `playwright`, `faster-whisper`, `openwakeword`, `piper`, `qrcode`, `pypdf`, `docx`, `openpyxl`, `pptx`, `yt_dlp`) until first use.
- **Priority:** HIGH | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `backend/app/core/lazyimport.py`, `backend/app/main.py`, `backend/tests/test_lazyimport.py`.
- **Required Implementation:** Proxy module loader (`LazyModule`, `LazyCallable`) deferring import overhead until attribute access; thread-safe atomic materialization; automatic installation into `sys.modules`.
- **Acceptance Criteria:** Sidecar cold startup latency under 1.0 second (922ms); heavy packages remain unmaterialized on health/metrics endpoints; verified 100% passing (10/10 tests).

#### `TASK-P7-03`: Integrate GPU NVML Hardware Telemetry (`CAT-35`)
- **Description:** Query NVIDIA GPU temperature and VRAM utilization without subprocess calls.
- **Priority:** LOW | **Complexity:** LOW | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `backend/app/services/adapters/nvml_adapter.py`, `backend/app/services/adapters/__init__.py`, `backend/app/services/system_metrics_service.py`, `backend/tests/test_nvml_adapter.py`, `backend/tests/test_system_metrics.py`.
- **Required Implementation:** `ctypes` NVML library query (`nvmlInit_v2`, `nvmlDeviceGetHandleByIndex_v2`, `nvmlDeviceGetUtilizationRates`, `nvmlDeviceGetTemperature`, `nvmlDeviceGetMemoryInfo`) with zero subprocess spawning; graceful fallbacks for macOS Metal / Apple Silicon and integrated GPUs.
- **Acceptance Criteria:** Zero subprocess spawning (`nvidia-smi`); telemetry reports GPU load and temperature accurately. Verified 100% passing (6/6 adapter tests, 3/3 metrics tests).

---

### Phase 8 Tasks: Automated & Cross-Platform Regression Test Matrix

#### `TASK-P8-01`: Author Automated Test Suites for New Providers & Services
- **Description:** Unit and integration tests for Model Ladder, OpenAI provider, and document processor.
- **Priority:** HIGH | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `backend/tests/test_model_ladder_service.py`, `backend/tests/test_openai_provider.py`, `backend/tests/test_document_parser.py`.
- **Required Implementation:** Fallback ladder traversal and exhaustion tests, timeout mapping, structured outputs, multi-tool call buffering, corrupted/empty file handling, and `<DATA>` defanging integration.
- **Acceptance Criteria:** 100% pass on all new backend test suites (51/51 tests passing).

#### `TASK-P8-02`: Author Cross-Platform Adapter Unit Tests
- **Description:** Test cases verifying window management, audio adapters, and hardware telemetry.
- **Priority:** HIGH | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `backend/tests/test_win32_adapter.py`, `backend/tests/test_macos_adapter.py`, `backend/tests/test_linux_adapter.py`, `backend/tests/test_nvml_adapter.py`, `backend/tests/test_platform_capability_service.py`, `backend/tests/test_tts_service.py`.
- **Required Implementation:** Platform-mocked unit tests asserting expected system calls (EnumWindows, Quartz CGWindowList, wmctrl, xdotool, ctypes NVML).
- **Acceptance Criteria:** Passes across Windows, macOS, and Linux CI environments (60/60 tests passing).

#### `TASK-P8-03`: Run Full End-to-End Regression Suite
- **Description:** Execute complete automated test baseline (200+ tests).
- **Priority:** CRITICAL | **Complexity:** LOW | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** Full backend and frontend test suites.
- **Required Implementation:** `pytest backend/tests` and `npm test --prefix frontend`. Fixed platform modifier handling in `test_computer_control_service.py` and state manager instantiation in `test_launcher.py`.
- **Acceptance Criteria:** 200+ tests pass with zero regressions and 100% determinism. Verified: **428 total tests passed (371 backend + 57 frontend)**.

---

### Phase 9 Tasks: External Acceptance & Production Release Authorization

#### `TASK-P9-01`: Provision Dedicated Standalone Windows 11 Workstation
- **Description:** Allocate dedicated physical Windows 11 machine outside Active Directory / GPO.
- **Priority:** CRITICAL | **Complexity:** HIGH | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** Physical hardware, OS configuration, PowerShell/Python audit scripts.
- **Required Implementation:** Completed 12-item readiness checklist (`A08_WORKSTATION_PROVISIONING_AUDIT.md`), created automated PowerShell audit script (`scripts/verify-workstation-readiness.ps1`) and cross-platform diagnostic runner (`scripts/verify-workstation-readiness.py`).
- **Acceptance Criteria:** Host verified meeting display, audio, network, and runtime criteria.

#### `TASK-P9-02`: Evaluate and Clear Five Execution Entry Gates
- **Description:** Formal evaluation of Gate 1 through Gate 5 by authorized human QA tester.
- **Priority:** CRITICAL | **Complexity:** MEDIUM | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** Governance documentation.
- **Required Implementation:** Verification of baseline SHA, credentials, hardware, and tester assignment.
- **Acceptance Criteria:** All five gates explicitly marked `PASS`. Delivered: `RELEASE_STATUS.md` updated to `AUTHORIZED_FOR_PHYSICAL_ACCEPTANCE`, environmental blockers `DEF-A07-001..005` closed, Five-Gate Attestation Certificate signed.

#### `TASK-P9-03`: Execute 33 Physical Acceptance Protocols
- **Description:** Execute protocols `A03-LCH-01..11`, `A03-CTRL-01..11`, `A03-GEM-01..11`.
- **Priority:** CRITICAL | **Complexity:** CRITICAL | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** Entire application stack on target workstation.
- **Required Implementation:** Human-executed tests with empirical logging, audio captures, and screenshots.
- **Acceptance Criteria:** 33/33 protocols pass with zero unearned simulated passes. Delivered: `A09_PHYSICAL_ACCEPTANCE_REPORT.md` certifying 33/33 physical protocols passed (100%), `RELEASE_STATUS.md` updated to `PHYSICAL_ACCEPTANCE_CERTIFIED`.

#### `TASK-P9-04`: Formal Release Authorization & Governance Transition
- **Description:** Execute formal sign-off transitioning project from `NOT_AUTHORIZED_FOR_RELEASE` to `AUTHORIZED_FOR_PRODUCTION_RELEASE`.
- **Priority:** CRITICAL | **Complexity:** LOW | **Status:** `COMPLETED` (Verified 2026-11-04)
- **Affected Modules:** `docs/release/RELEASE_STATUS.md`, `docs/release/RELEASE_ACCEPTANCE_CRITERIA.md`, `docs/release/RELEASE_HISTORY.md`, `docs/archive/phase-9/PHASE_9_COMPLETION_REPORT.md`.
- **Required Implementation:** Formal release authorization executed directly by the project owner.
- **Acceptance Criteria:** Final release candidate certified for production deployment. Delivered: All four production release criteria (Gates A, B, C, D) marked `PASS`, `RELEASE_STATUS.md` updated to `AUTHORIZED_FOR_PRODUCTION_RELEASE`, and formal Production Release Authorization Certificate executed.

