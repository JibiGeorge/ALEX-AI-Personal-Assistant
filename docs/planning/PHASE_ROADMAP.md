# Phased Migration Roadmap: Alex AI Desktop Assistant

**Document Version:** 1.0  
**Inspection Date:** 2026-11-03  
**Status:** `ACTIVE_PHASE_ROADMAP`  
**Current Milestone State:** Phase 0, 1, 2 & 3 Complete; Phase 4 Active (Owner-Authorized 2026-11-04)  

---

## 1. Master Phase Progression Matrix

```
+---------------------------------------------------------------------------------------------------+
|                                      MIGRATION PHASE TIMELINE                                     |
+---------------------------------------------------------------------------------------------------+
| Phase 0: Baseline & Governance Verification                     --> [ COMPLETED ]                 |
| Phase 1: Comprehensive Gap Analysis & Parity Discovery          --> [ COMPLETED ]                 |
| Phase 2: Architecture & Cross-Platform Foundation Design        --> [ COMPLETED ]                 |
| Phase 3: Core Application Parity (Actions, Local LLMs, Budgets) --> [ COMPLETED ]                 |
| Phase 4: Voice, Media & Advanced Capabilities (STT, TTS, Mesh)   --> [ COMPLETED ]                 |
| Phase 5: Desktop Platform Implementations (Win, Ubuntu, macOS)  --> [ COMPLETED ]                 |
| Phase 6: iOS Mobile Companion Client (SwiftUI / PWA)            --> [ IN PROGRESS (P6-01 Done) ]   |
| Phase 7: Security Hardening, Threat Modeling & Optimization     --> [ PLANNED - Depends on P3-P6] |
| Phase 8: Automated & Cross-Platform Regression Suites           --> [ PLANNED - Depends on P7 ]   |
| Phase 9: External Acceptance & Production Release Authorization --> [ PLANNED - Final Gate ]     |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Granular Phase Details & Dependencies

### Phase 0: Baseline & Governance Preservation
- **Objectives:** Establish authoritative baseline snapshot (`SNAPSHOT_v0.1.0-20261102`), freeze A02 Computer Control, Unified Launcher, Electron shell, and preserve `Mark-LVI-main` as read-only reference.
- **Entry Gate:** None.
- **Exit Gate:** Verified implementation freezes, clean git baseline where available, 148 automated tests passed.
- **Status:** **COMPLETED**.

### Phase 1: Migration & Functional Gap Analysis
- **Objectives:** Complete source code discovery across both repositories, build 40-category parity matrix, document all technical gaps, and record architectural decisions.
- **Entry Gate:** Phase 0 verified.
- **Exit Gate:** Complete deliverable suite: `SOURCE_CODE_INVENTORY.md`, `FEATURE_PARITY_MATRIX.md`, `MIGRATION_GAP_ANALYSIS.md`, `MIGRATION_DECISIONS.md`.
- **Status:** **COMPLETED**.

### Phase 2: Architecture & Cross-Platform Foundation Design
- **Objectives:** Design target cross-platform architecture, Hardware Abstraction Layer (HAL), iOS companion client architecture, and multi-provider AI pipeline.
- **Entry Gate:** Phase 1 completed.
- **Exit Gate:** Complete architecture specifications: `TARGET_ARCHITECTURE.md`, `CROSS_PLATFORM_ARCHITECTURE.md`, `IOS_ARCHITECTURE.md`, `AI_PROVIDER_ARCHITECTURE.md`, `ACTION_EXECUTION_ARCHITECTURE.md`.
- **Status:** **COMPLETED**.

### Phase 3: Core Application Parity Implementation
- **Objectives:** Implement the 9 foundational AI provider and operational action scopes detailed in `docs/planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md`:
  1. `TASK-P3-01`: AI Provider Abstraction Layer (`base.py`, `registry.py`)
  2. `TASK-P3-02`: Nine-Rung Model Fallback Ladder & Quota Resilience (`model_ladder_service.py`)
  3. `TASK-P3-03`: Ollama Local LLM Integration (`http://127.0.0.1:11434`)
  4. `TASK-P3-04`: LM Studio Local LLM Integration (`http://127.0.0.1:1234`)
  5. `TASK-P3-05`: OpenAI-Compatible API Provider (`/v1/chat/completions`)
  6. `TASK-P3-06`: Cloud Providers Integration (Groq & DeepSeek with `<think>` tag filter)
  7. `TASK-P3-07`: Dynamic Tool Budgeting Engine (`schema.py` count & size slicing)
  8. `TASK-P3-08`: Standardized Five-Word Outcome Contract (`done`, `unverified`, `failed`, `ask`, `started`)
  9. `TASK-P3-09`: Deep Document Parsing Action (`documents.py` for PDF/DOCX/PPTX/XLSX)
- **Prerequisites:** Project owner authorization recorded in `docs/architecture/ARCHITECTURE_GOVERNANCE.md`.
- **Dependencies:** `pdfplumber`, `python-docx`, `openpyxl`, `python-pptx`, `httpx`.
- **Exit Gate:** 100% passing automated unit tests for all 9 scopes; simulated 429 auto-downgrades cleanly; local Ollama/LM Studio chat verified offline; zero modifications to frozen files.
- **Status:** **COMPLETED** (Archived in `docs/archive/phase-3/`).

### Phase 4: Voice, Media & Advanced Capabilities
- **Objectives:** Implement local speech recognition (Faster-Whisper on CPU), speech synthesis (Piper neural voices + system voices), wake-word detection ("Hey Alex"), live VU metering, 3D avatar MediaPipe face mesh, and embedded HUD media stage.
- **Prerequisites:** Phase 3 completed.
- **Dependencies:** `faster-whisper`, `piper-tts`, `openwakeword`, `yt-dlp`, HTML5 Canvas 2D/Video.
- **Target Deliverables:**
  - `backend/app/services/speech_service.py` (Faster-Whisper STT)
  - `backend/app/services/tts_service.py` (Piper Neural TTS + System Voices)
  - `backend/app/services/wake_word_service.py` (Local Wake-Word "Hey Alex")
  - `backend/app/services/media_service.py` (Embedded Media Service)
  - `backend/app/actions/builtins/media.py` (Media actions: play, stop, pause, resume, mute)
  - `frontend/src/components/AudioMeter.tsx` (Real-time VU meter)
  - `frontend/src/utils/audioChime.ts` (Synthesized 440 Hz -> 880 Hz dual-tone chime)
  - `frontend/src/components/HudAvatar.tsx` (3D MediaPipe 468-vertex face mesh & visemes)
  - `frontend/src/components/VideoPlayer.tsx` (Embedded HUD Video Stage)
- **Exit Gate:** 100% passing automated unit tests across all 6 Phase 4 scopes (35 backend tests, 57 frontend tests); zero modifications to frozen files.
- **Status:** **COMPLETED** (Archived in `docs/archive/phase-4/`).

### Phase 5: Desktop Platform Implementations (Windows, Ubuntu, macOS)
- **Objectives:** Implement platform-specific adapters for window management, audio volume, and permission detection across Windows, Ubuntu, and macOS.
- **Prerequisites:** Phase 3 and Phase 4 completed.
- **Target Deliverables:**
  - `backend/app/services/adapters/win32_window_adapter.py` (Win32 EnumWindows + AttachThreadInput + WM_CLOSE)
  - `backend/app/services/adapters/macos_window_adapter.py` (macOS Quartz + AppKit + osascript)
  - `backend/app/services/adapters/linux_window_adapter.py` (Linux EWMH wmctrl + xdotool + Wayland detection)
  - `backend/app/services/window_management_service.py` (Unified Cross-Platform Dispatch)
  - `scripts/build-backend.sh` (Cross-Platform Unix PyInstaller Sidecar Builder)
- **Exit Gate:** 100% passing automated unit tests across all 4 Phase 5 scopes (34 platform adapter tests, 3 packaging tests); standalone binary executable verified.
- **Status:** **COMPLETED** (Archived in `docs/archive/phase-5/`).

### Phase 6: iOS Mobile Companion Client
- **Objectives:** Implement the mobile companion client (SwiftUI native and PWA) with QR code pairing, AES-256-GCM encryption, mobile voice streaming, and FaceID remote action authorization.
- **Prerequisites:** Phase 5 desktop stabilization.
- **Target Deliverables:**
  - `backend/app/services/dashboard_service.py` (Mobile Gateway, PBKDF2/AES-GCM crypto, pending approvals)
  - `frontend/mobile/ios/` (Native SwiftUI companion app)
  - `frontend/mobile/web/` (Responsive HTML5/PWA companion client)
  - `backend/app/actions/action_executor.py` (Remote action authorization hook)
- **Exit Gate:** Scanning QR code pairs mobile client over LAN, streams voice, and authorizes desktop automation via biometric prompt.
- **Status:** **COMPLETED** (Archived in `docs/archive/phase-6/`).

### Phase 7: Security Hardening & Performance Optimization
- **Objectives:** Enforce `<DATA>` tag prompt injection defanging, implement lazy loading for heavy packages, and optimize cold startup latency.
- **Prerequisites:** Phase 3 through Phase 6 completed.
- **Exit Gate:** Cold startup under 4.0 seconds; STRIDE security audit clean.

### Phase 8: Automated & Cross-Platform Regression Test Matrix
- **Objectives:** Author unit, integration, and packaging test suites across all new services; verify 200+ automated tests passing with 100% determinism.
- **Prerequisites:** Phase 7 completed.
- **Exit Gate:** All automated tests green across Windows, macOS, and Linux runners.

### Phase 9: External Acceptance & Production Release Authorization
- **Objectives:** Provision dedicated standalone test workstations across target OS environments, verify Five Entry Gates, execute 33 Physical Acceptance Protocols, and formally grant production release authorization.
- **Prerequisites:** Phase 8 passed.
- **Exit Gate:** 33/33 physical acceptance protocols pass with empirical evidence; release signed by Technical Lead and QA Manager.

