# Alex AI Desktop Assistant — Master Migration Plan

**Document Version:** 1.0  
**Inspection Date:** 2026-11-03  
**Approved Baseline:** `SNAPSHOT_v0.1.0-20261102` (Application Version `0.1.0`)  
**Status:** `ACTIVE_MASTER_PLAN`  

---

## 1. Executive Summary & Migration Mandate

The primary objective of the Alex migration is to achieve complete **functional parity** with the reference project `Mark-LVI-main`, while establishing a secure, maintainable, cross-platform architecture supporting **Windows 10/11, Ubuntu Linux, macOS, and iOS**.

This master plan establishes the ten sequential phases required to transition Alex from its current initial baseline (`0.1.0`, `0/33` physical acceptance, `BLOCKED_BY_ENVIRONMENT`) to complete functional parity, multi-platform certification, and production release authorization.

---

## 2. Master Phase Progression Roadmap

```
+-------------------------------------------------------------------------------------------------+
|                                 TEN-PHASE MASTER MIGRATION ROADMAP                              |
+-------------------------------------------------------------------------------------------------+
| Phase 0: Repository Baseline & Governance Preservation           --> [ COMPLETED ]              |
| Phase 1: Comprehensive Migration & Functional Gap Analysis       --> [ COMPLETED ]              |
| Phase 2: Architecture & Cross-Platform Foundation Design         --> [ COMPLETED ]              |
| Phase 3: Core Application Parity (Actions, Local LLMs & Schemas)  --> [ PENDING ]                |
| Phase 4: Voice, Media & Advanced Capabilities (STT, TTS, Vision)  --> [ PENDING ]                |
| Phase 5: Desktop Platform Implementations (Win, Ubuntu, macOS)   --> [ PENDING ]                |
| Phase 6: iOS Mobile Companion Client (Swift/PWA & LAN Pairing)   --> [ PENDING ]                |
| Phase 7: Security Hardening, Threat Modeling & Performance       --> [ PENDING ]                |
| Phase 8: Automated & Cross-Platform Test Matrix Execution        --> [ PENDING ]                |
| Phase 9: External Acceptance & Production Release Authorization  --> [ PENDING ]                |
+-------------------------------------------------------------------------------------------------+
```

---

## 3. Phase Specifications & Exit Criteria

### Phase 0: Repository Baseline & Governance Preservation
- **Objective:** Establish authoritative baseline, preserve existing A02–A08 records, enforce implementation freezes, and audit repository provenance.
- **Key Deliverables:**
  - Frozen A02 Computer Control, Unified Launcher, and Electron Shell.
  - Read-only preservation of `Mark-LVI-main`.
  - Baseline verification: `SNAPSHOT_v0.1.0-20261102`, version `0.1.0`, physical score `0/33`.
- **Status:** **COMPLETED**.

### Phase 1: Comprehensive Migration & Functional Gap Analysis
- **Objective:** Exhaustive source inspection across all 40 feature categories, discovery of all parity units, and documentation of technical gaps.
- **Key Deliverables:**
  - `docs/migration/SOURCE_CODE_INVENTORY.md`
  - `docs/migration/FEATURE_PARITY_MATRIX.md`
  - `docs/migration/MIGRATION_GAP_ANALYSIS.md`
  - `docs/migration/MIGRATION_DECISIONS.md`
- **Status:** **COMPLETED**.

### Phase 2: Architecture & Cross-Platform Foundation Design
- **Objective:** Design the target cross-platform architecture, hardware abstraction layers (HAL), iOS companion strategy, multi-provider pipeline, and security threat model.
- **Key Deliverables:**
  - `docs/architecture/TARGET_ARCHITECTURE.md`
  - `docs/architecture/CROSS_PLATFORM_ARCHITECTURE.md`
  - `docs/architecture/IOS_ARCHITECTURE.md`
  - `docs/architecture/AI_PROVIDER_ARCHITECTURE.md`
  - `docs/architecture/ACTION_EXECUTION_ARCHITECTURE.md`
- **Status:** **COMPLETED (Delivered in this reassessment)**.

### Phase 3: Core Application Parity Implementation
- **Objective:** Implement missing action handlers, the multi-model fallback ladder, and OpenAI-compatible local/hosted LLM provider.
- **Scope & Tasks:**
  - `TASK-P3-01`: Implement `ModelLadderService` (9-rung Gemini fallback with 429 auto-retry).
  - `TASK-P3-02`: Implement `OpenAICompatibleProvider` for Ollama, LM Studio, Groq, DeepSeek.
  - `TASK-P3-03`: Implement `ToolBudgetManager` (count and size tool slicing for small models).
  - `TASK-P3-04`: Port missing action modules: `documents.py` (PDF, DOCX, XLSX), `coding.py` (Dev agent), `settings.py` (Hardware volume/brightness/battery).
  - `TASK-P3-05`: Implement standard Five-Word Outcome Contract across all action handlers.
- **Exit Criteria:** Local Ollama model executes sandboxed document analysis; Model Ladder seamlessly absorbs simulated 429 quota errors.

### Phase 4: Voice, Media & Advanced Capabilities
- **Objective:** Implement offline speech recognition (Whisper), speech synthesis (Piper), local wake-word detection, media player, and 3D avatar facial mesh.
- **Scope & Tasks:**
  - `TASK-P4-01`: Implement `LocalSpeechService` with `faster-whisper` and language detection.
  - `TASK-P4-02`: Implement `SpeechSynthesisService` with Piper neural TTS and OS system voice fallback.
  - `TASK-P4-03`: Implement `WakeWordService` using `openwakeword` ("Hey Jarvis" / "Hey Alex").
  - `TASK-P4-04`: Add audio device live peak dB VU meter and speaker test chime in `AudioDevicesPage.tsx`.
  - `TASK-P4-05`: Port software-rendered 3D MediaPipe face mesh and formant viseme lip-sync to React `HudAvatar.tsx`.
  - `TASK-P4-06`: Implement embedded video player stage for YouTube and local media streams.
- **Exit Criteria:** Spoken commands execute completely offline (Whisper $\rightarrow$ Ollama $\rightarrow$ Piper) with animated avatar lip-sync.

### Phase 5: Desktop Platform Implementations (Windows, Ubuntu, macOS)
- **Objective:** Implement platform-specific adapters, permission detectors, and packaging for all three desktop operating systems.
- **Scope & Tasks:**
  - `TASK-P5-01`: Implement `Win32WindowAdapter` (Windows ctypes EnumWindows, WM_CLOSE, AttachThreadInput).
  - `TASK-P5-02`: Implement `MacOSWindowAdapter` (AppleScript / Quartz) and TCC permission checks.
  - `TASK-P5-03`: Implement `LinuxWindowAdapter` (X11 EWMH / xdotool) and Wayland capability detector.
  - `TASK-P5-04`: Cross-platform packaging: Windows NSIS installer, macOS DMG, and Ubuntu AppImage/DEB.
- **Exit Criteria:** Alex builds and runs natively on Windows 11, Ubuntu 22.04/24.04, and macOS 14+ (Apple Silicon & Intel).

### Phase 6: iOS Mobile Companion Client
- **Objective:** Implement mobile companion architecture enabling LAN voice/text streaming, memory review, and remote action authorization.
- **Scope & Tasks:**
  - `TASK-P6-01`: Implement `RemoteDashboardService` in sidecar with QR code pairing and PBKDF2/AES-256-GCM authentication.
  - `TASK-P6-02`: Implement responsive mobile web client / iOS companion app.
  - `TASK-P6-03`: Wire mobile push notifications for pending desktop computer control approvals.
- **Exit Criteria:** Mobile device scans desktop QR code, authenticates, streams bidirectional voice, and approves pending desktop automation actions over LAN.

### Phase 7: Security Hardening, Threat Modeling & Performance Optimization
- **Objective:** Conduct rigorous STRIDE threat modeling, verify untrusted prompt injection defanging, and optimize startup latency.
- **Scope & Tasks:**
  - `TASK-P7-01`: Enforce `<DATA>` tag defanging around external search and document text.
  - `TASK-P7-02`: Implement lazy module loading for heavy backend dependencies (`cv2`, `playwright`, `faster-whisper`).
  - `TASK-P7-03`: Add GPU telemetry monitoring via `pynvml` (NVIDIA) and Metal (macOS).
  - `TASK-P7-04`: Audit OS Keyring credential protection across all target platforms.
- **Exit Criteria:** Zero security vulnerabilities identified; startup latency under 4 seconds; untrusted prompt injection payloads safely defanged.

### Phase 8: Automated & Cross-Platform Test Matrix Execution
- **Objective:** Expand automated test coverage across all new providers, adapters, and services; maintain 100% regression pass rate.
- **Scope & Tasks:**
  - `TASK-P8-01`: Author unit test suites for local LLM, STT, TTS, and document processors.
  - `TASK-P8-02`: Author cross-platform integration tests for window management adapters.
  - `TASK-P8-03`: Run full regression suite: 200+ unit and integration tests passing with 100% determinism.
- **Exit Criteria:** All unit and integration test suites pass on Windows, Ubuntu Linux, and macOS.

### Phase 9: External Acceptance & Production Release Authorization
- **Objective:** Provision dedicated physical test workstations across target operating systems, evaluate the Five Entry Gates, execute the 33 Physical Acceptance Protocols, and formally authorize release.
- **Scope & Tasks:**
  - `TASK-P9-01`: Provision dedicated standalone Windows 11 64-bit test workstation.
  - `TASK-P9-02`: Complete 12-item readiness checklist and verify Five Entry Gates.
  - `TASK-P9-03`: Execute protocols `A03-LCH-01..11`, `A03-CTRL-01..11`, `A03-GEM-01..11`.
  - `TASK-P9-04`: Repeat acceptance verification on Ubuntu Linux and macOS test hosts.
  - `TASK-P9-05`: Formal release authorization and transition from `NOT_AUTHORIZED_FOR_RELEASE` to `AUTHORIZED_FOR_RELEASE`.
- **Exit Criteria:** 33/33 physical acceptance protocols pass with empirical evidence; multi-platform release authorized.

