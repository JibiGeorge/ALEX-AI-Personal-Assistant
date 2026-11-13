# Technical Migration Gap Analysis: Mark-LVI to Alex AI Desktop Assistant

**Document Version:** 1.1 (Reconciled Baseline)  
**Inspection Date:** 2026-11-03  
**Target Baseline:** `SNAPSHOT_v0.1.0-20261102` (Application Version `0.1.0`)  
**Status:** `VERIFIED_TECHNICAL_ANALYSIS`  

---

## 1. Executive Summary

This document performs an exhaustive technical gap analysis between the reference prototype (`Mark-LVI-main`) and the target production architecture (`ALEX-AI-main`).

Following the reconciliation of the functional inventory into **40 capability categories and 68 distinct functional units**, the technical gaps are structured into four critical engineering domains:
1. **AI Model & Speech Pipeline Gaps** (Local models, 9-rung model fallback ladder, Piper TTS, Whisper STT, wake-word engine: `UNIT-08` through `UNIT-19`, `UNIT-66`).
2. **Action Ecosystem & Execution Gaps** (Document parsing, dynamic plugin loader, five-word outcome contract: `UNIT-25` through `UNIT-27`, `UNIT-39` through `UNIT-48`).
3. **Cross-Platform System Integration Gaps** (Window management HAL, Wayland detection, macOS TCC, audio peak metering: `UNIT-21` through `UNIT-23`, `UNIT-35`, `UNIT-67`).
4. **Mobile & Remote Architecture Gaps** (Remote smartphone dashboard and companion client: `UNIT-65`).

---

## 2. Domain 1: AI Model & Speech Pipeline Gaps

### Gap 1.1: Multi-Model Fallback Ladder & Quota Resilience (`CAT-05`: `UNIT-08`, `UNIT-09`)
- **Observed State in Mark-LVI:** `core/gemini.py` defines `MODEL_LADDER` consisting of 9 sequential Gemini models:
  1. `models/gemini-3.1-flash-live-preview`
  2. `models/gemini-2.5-flash-native-audio-preview-12-2025`
  3. `models/gemini-2.0-flash-exp`
  4. `models/gemini-1.5-flash`
  5. `models/gemini-1.5-flash-8b`
  6. `models/gemini-1.5-pro`
  7. Down to text-only fallbacks.
  When an API call returns `429 Resource Exhausted` (quota limit) or `503 Service Unavailable`, Mark-LVI catches the error, steps down to the next rung, and re-establishes the session seamlessly without failing the user's turn.
- **Current State in Alex:** `backend/app/services/live_voice_service.py` hardcodes two models in `_LIVE_MODELS` and fails immediately with a fatal WebSocket error if the session drops.
- **Architectural Remedy:**
  - Create `backend/app/services/model_ladder_service.py` (Phase 3: `TASK-P3-02`).
  - Maintain an active connection state machine that catches 429/503 errors and attempts reconnection down the ladder before notifying the UI.
  - Implement a cooldown tracker (`model_cooldowns.py`) to prevent hammering depleted tiers.

### Gap 1.2: Local LLM & Multi-Provider Architecture (`CAT-06`: `UNIT-10`, `UNIT-11`; `CAT-07`: `UNIT-12`, `UNIT-13`)
- **Observed State in Mark-LVI:** `providers/llm_openai.py` implements a generic OpenAI `/v1/chat/completions` protocol client supporting:
  - Local engines: Ollama (`127.0.0.1:11434`), LM Studio (`127.0.0.1:1234`), llama.cpp, vLLM.
  - Hosted cloud APIs: OpenAI, Groq, DeepSeek, Mistral, xAI, OpenRouter, Together.
  - Features: Streaming `<think>` tag extraction (prevents reasoning tokens from being spoken aloud) and anti-repetition guards.
  - Tool budget management (`providers/schema.py`): Restricts tool declarations by count (max 8-14) and character size (max 9,000 chars) so small 8B local models do not hallucinate or crash.
- **Current State in Alex:** Completely absent. The backend communicates solely with the Google Gemini API.
- **Architectural Remedy:**
  - Implement an abstract `LLMProvider` interface in `backend/app/providers/base.py` (Phase 3: `TASK-P3-01`).
  - Implement `GeminiLiveProvider` (existing) and `OpenAICompatibleProvider` (new, `TASK-P3-05`).
  - Implement `ToolBudgetManager` (`TASK-P3-07`) to dynamically slice the action schema based on whether the active model is an 8B local model or cloud Gemini.
  - Implement a streaming thought tag filter (`<think>...</think>`).

### Gap 1.3: Offline Speech Recognition (STT) & Speech Synthesis (TTS) (`CAT-08`: `UNIT-15`, `UNIT-16`; `CAT-09`: `UNIT-17`, `UNIT-18`, `UNIT-19`)
- **Observed State in Mark-LVI:**
  - **STT (`providers/stt_whisper.py`):** Uses `faster-whisper` on CPU. Detects spoken language per turn (e.g. `tr`, `en`, `fr`) and passes language code down the pipeline. Includes 16kHz audio buffer warm-up on startup to eliminate the 8.5s first-run kernel compilation latency.
  - **TTS (`providers/tts_piper.py`):** Uses Piper neural voice engine (~176 voices in 52 languages) synthesizing speech at 15x real-time on CPU. The voice dynamically switches to match the language heard by Whisper.
  - **System Voices (`providers/tts_system.py`):** Zero-install fallback using Windows SAPI5, macOS `say`, and Linux `espeak-ng`.
  - **Cloud TTS (`providers/tts_elevenlabs.py`):** High-fidelity cloud voice.
- **Current State in Alex:** Relies 100% on server-side audio returned by Google Gemini Live over WebSocket. If internet connectivity drops, voice capability is completely dead.
- **Architectural Remedy:**
  - Create `backend/app/services/speech_service.py` exposing local STT (Faster-Whisper) and TTS (Piper + OS System Voices) in Phase 4.
  - Enable seamless offline mode: When offline or if Gemini quota is depleted, Alex falls back to local Whisper + local Ollama + local Piper TTS.

### Gap 1.4: Local Wake-Word Detection ("Hey Jarvis" / "Hey Alex") (`CAT-38`: `UNIT-66`)
- **Observed State in Mark-LVI:** `core/wake_word.py` integrates `openwakeword` ONNX models running on CPU. The assistant sleeps until "Hey Jarvis" is detected. While asleep, zero audio is streamed to cloud APIs.
- **Current State in Alex:** Completely absent. The user must manually click the microphone icon in the React UI to begin listening.
- **Architectural Remedy:**
  - Implement `WakeWordService` in `backend/app/services/wake_word_service.py` utilizing `openwakeword` (Phase 4).
  - Feed mic PCM frames into wake-word listener thread; when threshold $> 0.5$, dispatch an IPC event `alex:wake` to awaken the UI and open the Live session.

---

## 3. Domain 2: Action Ecosystem & Execution Gaps

### Gap 2.1: Missing Built-in Action Modules (`CAT-20`: `UNIT-39`, `UNIT-40`; `CAT-21`: `UNIT-41`, `UNIT-42`; `CAT-22`: `UNIT-43`, `UNIT-44`; `CAT-24`: `UNIT-47`, `UNIT-48`)
- **Observed State in Mark-LVI:** Mark-LVI ships with 21 rich action modules in `actions/`:
  - `file_processor.py`: Parses PDF, Word (DOCX), PowerPoint (PPTX), Excel (XLSX).
  - `dev_agent.py` & `code_helper.py`: Autonomous coding agent that writes, verifies AST syntax, runs unit tests, and iterates.
  - `browser_control.py`: Playwright + BeautifulSoup web driving.
  - `video_player.py` & `youtube_video.py`: Media player and YouTube stream extractor (`yt-dlp`).
  - `computer_settings.py`: Adjusts hardware volume, brightness, battery, WiFi, wallpaper.
  - `send_message.py`: WhatsApp and Telegram messaging.
  - `desktop.py`: Taskbar minimization, window tiling.
  - `game_updater.py`: Steam and Epic Games status.
- **Current State in Alex:** `backend/app/actions/builtins/` contains only 5 basic modules:
  - `computer_control.py` (Mouse/keyboard primitives)
  - `files.py` (Basic sandboxed text read/write)
  - `memory.py` (Fact CRUD)
  - `search.py` (DuckDuckGo search)
  - `system.py` (OS info, metrics, ping)
- **Architectural Remedy:**
  - Systematically port missing action logic into structured, typed Pydantic action handlers under `backend/app/actions/builtins/`:
    - `actions/builtins/documents.py` (Phase 3: `TASK-P3-09`: PDF, DOCX, XLSX via `pdfplumber`, `python-docx`, `openpyxl`).
    - `actions/builtins/coding.py` (Phase 7: Dev agent and syntax validation).
    - `actions/builtins/browser.py` (Phase 7: Browser control via Playwright).
    - `actions/builtins/media.py` (Phase 7: YouTube and local video playback).
    - `actions/builtins/settings.py` (Phase 7: Hardware settings adjustments).

### Gap 2.2: Dynamic Action & Plugin Discovery (`CAT-13`: `UNIT-25`, `UNIT-26`)
- **Observed State in Mark-LVI:** `core/action_loader.py` and `core/plugin_loader.py` dynamically scan `actions/*.py` and `plugins/*.py` at launch. A file declaring a `TOOL` dictionary is automatically registered without touching core code.
- **Current State in Alex:** All actions are statically declared and compiled into `backend/app/actions/registry.py`.
- **Architectural Remedy:**
  - Preserve Alex's type-safe compiled registry (ADR-07), and add a dynamic user plugin loader in Phase 7 that compiles external `.py` tool definitions into validated Pydantic models at runtime.

### Gap 2.3: Standardized Five-Word Outcome Contract (`CAT-14`: `UNIT-27`)
- **Observed State in Mark-LVI:** Every tool answers in one of five words (`done`, `unverified`, `failed`, `ask`, `started`) defined in `core/outcome.py`. The LLM is explicitly instructed that `unverified` must never be spoken as success.
- **Current State in Alex:** Returns boolean `{ "success": bool, ... }`.
- **Architectural Remedy:**
  - Implement `ToolOutcome` enum in `backend/app/actions/base.py` (Phase 3: `TASK-P3-08`) and require all action handlers to verify OS effects before returning `done`.

---

## 4. Domain 3: Cross-Platform System Integration Gaps

### Gap 3.1: Cross-Platform Window Management (`CAT-18`: `UNIT-34`, `UNIT-35`)
- **Observed State in Mark-LVI:** Handles window management on Windows (`user32.dll` EnumWindows, AttachThreadInput) and Linux X11 (`wmctrl`, `xdotool`).
- **Current State in Alex:** `backend/app/services/computer_control_service.py#L296` explicitly raises `NotImplementedError` on non-Windows platforms.
- **Architectural Remedy:**
  - Create `WindowManagementAdapter` interface (Gated by `CR-01`, Phase 5).
  - Implement `Win32WindowAdapter` (Windows ctypes).
  - Implement `MacOSWindowAdapter` (AppleScript / Quartz / PyObjC).
  - Implement `LinuxWindowAdapter` (EWMH / `xdotool`).

### Gap 3.2: Wayland & macOS TCC Capability Detection (`CAT-39`: `UNIT-67`)
- **Observed State in Mark-LVI:** `core/platform_support.py` detects Wayland (`XDG_SESSION_TYPE=wayland`) and macOS Accessibility/Screen Recording permissions. It feeds these limitations to the LLM system prompt so the model says: "I cannot drive the screen because Wayland does not permit synthetic input" instead of pretending it clicked.
- **Current State in Alex:** `platform_capability_service.py` reports capabilities to the frontend REST API, but never passes platform constraints into the LLM system prompt.
- **Architectural Remedy:**
  - Port `core/platform_support.py` capability checks into `backend/app/services/platform_capability_service.py` (Phase 5).
  - In `live_voice_service.py` and `conversation_service.py`, append platform limitations directly to system instructions.

### Gap 3.3: Hardware Audio Diagnostics & Peak dB Metering (`CAT-11`: `UNIT-22`, `UNIT-23`)
- **Observed State in Mark-LVI:** `core/audio_devices.py` queries native OS audio devices; includes live microphone peak dB metering and speaker test tone generation.
- **Current State in Alex:** `SettingsPage.tsx` uses browser `navigator.mediaDevices.enumerateDevices()`. There is no hardware test tone generator.
- **Architectural Remedy:**
  - In `frontend/src/components/AudioSettings.tsx`, wire an `AudioContext` 440Hz sine wave tone generator to test speaker output (Phase 4).

---

## 5. Domain 4: Mobile & Remote Architecture Gaps

### Gap 4.1: Smartphone Remote Control Strategy (`CAT-37`: `UNIT-65`)
- **Observed State in Mark-LVI:** `main.py` hosts a local FastAPI web server on port 8000. It generates a QR code on the desktop HUD; scanning the QR code opens a mobile web app on the phone over LAN, authenticated via an 8-character PBKDF2 pairing key.
- **Current State in Alex:** Alex has no remote mobile interface.
- **Architectural Evaluation for iOS / Mobile:**
  - An iOS application cannot run local Python or execute desktop computer control commands due to the Apple App Sandbox.
  - Alex supports mobile via an encrypted LAN Companion Client strategy (ADR-09, Phase 6):
    1. **Mobile Web PWA (Mark-LVI Parity):** Expose an authenticated LAN dashboard from the FastAPI sidecar with QR-code pairing for any smartphone on the same Wi-Fi.
    2. **Native iOS Companion App (Swift/SwiftUI):** Connects to the host Alex backend over LAN/TLS to provide mobile voice chat, memory access, notifications, and remote desktop action approval.

---

## 6. Reconciled Gap Remediation Matrix & Prioritization

| Gap ID | Feature Category | Affected Units | Complexity | Phase Target | Primary Modules to Create/Modify |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **GAP-01** | Multi-Model Fallback Ladder (`CAT-05`) | `UNIT-08`, `UNIT-09` | MEDIUM | Phase 3 | `backend/app/services/model_ladder_service.py` (`TASK-P3-02`) |
| **GAP-02** | Local LLM & Multi-Provider (`CAT-06`, `07`) | `UNIT-10`..`13` | HIGH | Phase 3 | `backend/app/providers/` (`TASK-P3-01`, `03`..`07`) |
| **GAP-03** | Deep Document Parsing (`CAT-20`) | `UNIT-39`, `UNIT-40` | MEDIUM | Phase 3 | `backend/app/actions/builtins/documents.py` (`TASK-P3-09`) |
| **GAP-04** | Five-Word Outcome Contract (`CAT-14`) | `UNIT-27` | LOW | Phase 3 | `backend/app/actions/base.py` (`TASK-P3-08`) |
| **GAP-05** | Offline STT (Whisper) & TTS (Piper) (`CAT-08`, `09`) | `UNIT-15`..`19` | HIGH | Phase 4 | `backend/app/services/speech_service.py` |
| **GAP-06** | Local Wake-Word Engine (`CAT-38`) | `UNIT-66` | HIGH | Phase 4 | `backend/app/services/wake_word_service.py` |
| **GAP-07** | Global Push-to-Talk Hotkey (`CAT-10`) | `UNIT-21` | LOW | Phase 4 | `frontend/electron/main.ts` (`CR-02`) |
| **GAP-08** | Audio Hardware Diagnostics (`CAT-11`) | `UNIT-22`, `UNIT-23` | LOW | Phase 4 | `frontend/src/components/AudioSettings.tsx` |
| **GAP-09** | Cross-Platform Window Management (`CAT-18`) | `UNIT-35` | HIGH | Phase 5 | `backend/app/services/adapters/window_adapter.py` (`CR-01`) |
| **GAP-10** | Wayland & macOS TCC Detection (`CAT-39`) | `UNIT-67` | MEDIUM | Phase 5 | `backend/app/services/platform_capability_service.py` |
| **GAP-11** | Remote Dashboard / Mobile Client (`CAT-37`) | `UNIT-65` | HIGH | Phase 6 | `backend/app/services/dashboard_service.py`, `frontend/mobile/` (ADR-09) |
| **GAP-12** | Advanced Actions (Coding, Browser, Media) | `UNIT-41`..`44`, `47`, `48` | HIGH | Phase 7 | `backend/app/actions/builtins/{coding,browser,media}.py` |
| **GAP-13** | Dynamic User Plugin Discovery (`CAT-13`) | `UNIT-26` | MEDIUM | Phase 7 | `backend/app/actions/loader.py` |
