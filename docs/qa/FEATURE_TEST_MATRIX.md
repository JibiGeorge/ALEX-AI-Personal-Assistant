# ALEX AI — Complete Feature Test Matrix

**Document Version:** 1.0.0  
**Scope:** Complete End-to-End Quality & Verification Matrix for ALEX Desktop Assistant

---

## Matrix Overview

| Subsystem Code | Feature Area | Automated Specs | Unit/Integration Tests | Target E2E Coverage |
|---|---|---|---|---|
| **A-START** | Application Startup & Shutdown | `startup.spec.ts` | 42 backend + 7 frontend | 100% |
| **B-HUD** | Main HUD & Navigation | `hud.spec.ts`, `navigation.spec.ts` | 38 frontend | 100% |
| **C-AVATAR** | Avatar Positioning & Animation | `avatar.spec.ts` | 21 frontend | 100% |
| **D-WS** | Floating HUD Workspace (7 types) | `workspace.spec.ts`, `media-player.spec.ts`, `document-viewer.spec.ts`, `browser-workspace.spec.ts` | 28 frontend + 18 backend | 100% |
| **E-AI** | AI Providers & Model Ladder | `security.spec.ts`, `error-recovery.spec.ts` | 56 backend | 100% |
| **F-VOICE** | Voice, Audio & Wake-Word | `voice.spec.ts` | 48 backend + 12 frontend | 100% |
| **G-OS** | Computer Control & Platform Adapters | `security.spec.ts` | 34 backend + 8 frontend | 100% |
| **H-FILES** | Files & Document Parsing | `document-viewer.spec.ts` | 32 backend + 9 frontend | 100% |
| **I-MON** | System Monitoring & Telemetry | `system-monitor.spec.ts` | 22 backend + 14 frontend | 100% |
| **J-REM** | Reminders & OS Scheduler | `reminders.spec.ts` | 26 backend + 5 frontend | 100% |
| **K-MOB** | Mobile Companion & Pairing | `mobile-companion.spec.ts` | 38 backend | 100% |
| **L-JOB** | Job Hunting & Career Radar | `job-hunting.spec.ts` | 62 backend + 14 frontend | 100% |
| **M-SEC** | Security, Tokens & Isolation | `security.spec.ts`, `error-recovery.spec.ts` | 44 backend + 10 frontend | 100% |

---

## Detailed Test Cases by Area

### A. Application Startup & Shutdown (`startup.spec.ts`)
- **TC-START-01:** Launch via unified CLI (`bin/alex.js launch`) initiates port negotiation.
- **TC-START-02:** Backend sidecar spawns on loopback `127.0.0.1` with randomized bearer token.
- **TC-START-03:** Frontend wait-on verifies backend readiness before showing ready status.
- **TC-START-04:** Startup diagnostics lifecycle stages execute in sequence (`welcome` -> `hardware` -> `ai_ladder` -> `security` -> `ready`).
- **TC-START-05:** Graceful shutdown via HTTP `/shutdown` closes all open child processes without leaving orphans.
- **TC-START-06:** Abnormal termination handling: backend restart retains persisted settings and memory entries.

### B. Main HUD & Navigation (`hud.spec.ts`, `navigation.spec.ts`)
- **TC-HUD-01:** HUD header renders assistant branding, local cognitive core status, and real-time clock.
- **TC-HUD-02:** Top System Monitor updates CPU, RAM, network, and backend indicators dynamically.
- **TC-HUD-03:** Setup Drawer toggles on `⚙` click and opens Settings, Audio Devices, Memory, Reminders, and Actions.
- **TC-HUD-04:** Controls Drawer toggles on `🎛` click and reveals everyday mode switches and quick actions.
- **TC-HUD-05:** Activity Log drawer opens and closes with real-time telemetry events.
- **TC-HUD-06:** Navigation handles keyboard accessibility (Tab, Escape, Enter) across all drawers and modal panels.
- **TC-HUD-07:** Viewport responsiveness: No clipping or horizontal overflow at 1920x1080, 1366x768, 1280x720, 1024x768, 768x1024, or 390x844.

### C. Avatar & Animation (`avatar.spec.ts`)
- **TC-AVT-01:** Avatar centers in idle mode with subtle breathing/pulse animation.
- **TC-AVT-02:** When floating workspace opens, avatar transitions smoothly to bottom-right docked position.
- **TC-AVT-03:** When floating workspace is closed or dismissed, avatar returns to central HUD position.
- **TC-AVT-04:** Docked avatar remains clickable to restore focus or control audio/speech.
- **TC-AVT-05:** Motion preference: Avatar honors `@media (prefers-reduced-motion: reduce)` by halting heavy rotation and rapid pulsing.

### D. Floating HUD Workspace (`workspace.spec.ts`, `media-player.spec.ts`, `document-viewer.spec.ts`, `browser-workspace.spec.ts`)
- **TC-WS-01:** **YouTube/Video Stage:** Loads video source, controls playback (play, pause, mute, seek), window minimize, maximize, and external link.
- **TC-WS-02:** **Music Player Stage:** Renders track title, duration, seek bar, and live equalizer canvas.
- **TC-WS-03:** **PDF Viewer Stage:** Displays multi-page PDFs, pagination controls, zoom in/out, and zoom-to-fit.
- **TC-WS-04:** **Document Viewer Stage:** Displays Markdown and source code with syntax highlighting, line numbers, and file metadata.
- **TC-WS-05:** **Image Viewer Stage:** Preserves image aspect ratio, supports zoom, pan, and dimensions display.
- **TC-WS-06:** **Sandboxed Browser:** Sandboxed iframe with security pill, URL address bar, back/forward/reload, and external browser link.
- **TC-WS-07:** **Optical Camera Sensor:** Displays webcam video feed, capture still snapshot, horizontal mirror toggle, and stream refresh.
- **TC-WS-08:** **Window Reuse:** Opening a new modality replaces the active view in the single workspace window without creating duplicate stacked windows.

### E. AI & Model Ladder Providers (`security.spec.ts`)
- **TC-AI-01:** Model Ladder hierarchy discovery checks Gemini, Groq, DeepSeek, OpenAI, Ollama, LM Studio.
- **TC-AI-02:** Fallback activation: When primary provider fails, next available provider is selected automatically.
- **TC-AI-03:** Unavailable provider reporting: Explicit error reporting when credentials or services are missing.
- **TC-AI-04:** Tool calling & action execution: Structured parameters validated via Pydantic schemas.

### F. Voice & Audio (`voice.spec.ts`)
- **TC-VOICE-01:** Microphone permission detection and error handling.
- **TC-VOICE-02:** Push-to-talk voice recording and audio transcription via STT.
- **TC-VOICE-03:** Gemini Live streaming session WebSocket connectivity.
- **TC-VOICE-04:** Text-to-speech synthesis (Piper / ElevenLabs / Web Speech fallback).
- **TC-VOICE-05:** Audio interruption on user speech input.

### G. Computer Control & OS Integration (`security.spec.ts`)
- **TC-OS-01:** Permission detection: Desktop control requires explicit user consent per operation.
- **TC-OS-02:** Confirmation gate: Sensitive computer control commands show confirmation modal before execution.
- **TC-OS-03:** Window listing and focus management via platform adapters.
- **TC-OS-04:** Emergency abort: User can immediately cancel running computer control actions.

### H. Files & Document Parsing (`document-viewer.spec.ts`)
- **TC-FILE-01:** Drag-and-drop file upload with visual drop zone feedback.
- **TC-FILE-02:** Document parsing for PDF, DOCX, TXT, MD, JSON, and code files.
- **TC-FILE-03:** Original files remain strictly unchanged during parsing.
- **TC-FILE-04:** File size limit enforcement and corrupt file error states.

### I. System Monitoring (`system-monitor.spec.ts`)
- **TC-MON-01:** CPU, RAM, and disk utilization telemetry from real backend metrics.
- **TC-MON-02:** Network throughput indicator updates dynamically.
- **TC-MON-03:** AI engine and voice subsystem status indicators reflect real system states.
- **TC-MON-04:** Offline state handling when backend sidecar is unreachable.

### J. Reminders & Scheduler (`reminders.spec.ts`)
- **TC-REM-01:** Create reminder with natural language time or date.
- **TC-REM-02:** List active reminders with countdown timers.
- **TC-REM-03:** Cancel and delete reminders.
- **TC-REM-04:** Persistence across application restarts.

### K. Mobile Companion (`mobile-companion.spec.ts`)
- **TC-MOB-01:** Mobile pairing initialization and QR code generation.
- **TC-MOB-02:** Authenticated pairing verification with token handshake.
- **TC-MOB-03:** Remote action approval workflow for pending computer control actions.
- **TC-MOB-04:** Mobile file upload into desktop workspace.

### L. Job Hunting Module (`job-hunting.spec.ts`)
- **TC-JOB-01:** Candidate profile creation, skills verification, and resume upload.
- **TC-JOB-02:** Real job discovery across LinkedIn alerts, URLs, Greenhouse, Lever, company career pages.
- **TC-JOB-03:** Compatibility match scoring (Technical skills 30%, Experience 20%, Responsibilities 20%, Stack 15%, Location 10%, Seniority 5%).
- **TC-JOB-04:** Resume Studio tailoring for specific jobs without fabricating experience.
- **TC-JOB-05:** Cover letter generation and document export (DOCX/PDF).
- **TC-JOB-06:** Application tracker and approval workflow requiring explicit user confirmation.

### M. Security & Isolation (`security.spec.ts`)
- **TC-SEC-01:** API requests without valid Bearer token return 401 Unauthorized.
- **TC-SEC-02:** Backend sidecar binds strictly to loopback addresses (`127.0.0.1`, `::1`).
- **TC-SEC-03:** Electron renderer context isolation and disabled Node integration verified.
- **TC-SEC-04:** Preload bridge exposes only allowlisted API methods.
- **TC-SEC-05:** Sensitive credentials never leaked in logs, DOM, or error responses.

