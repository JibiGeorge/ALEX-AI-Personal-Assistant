# Architectural Decision Records: Mark-LVI to Alex AI Migration

**Document Version:** 2.0 (Personal Project Governance Transition)  
**Inspection Date:** 2026-11-03  
**Status:** `OWNER_APPROVED`  
**Reference Codebase:** `Mark-LVI-main` (MARK LVI / 56)  
**Target Codebase:** `ALEX-AI-main` (Version `0.1.0`, Baseline Snapshot `SNAPSHOT_v0.1.0-20261102`)  

---

## 1. Executive Summary & Governance Policy

This document formalizes the ten Architectural Decision Records (ADRs) governing the migration from the reference prototype (`Mark-LVI-main`) to the enterprise production target (`ALEX-AI-main`).

To ensure total architectural integrity, each ADR adheres strictly to a 10-field specification:
1. **Problem:** The specific technical, architectural, or security flaw in the reference codebase.
2. **Context:** How the capability is implemented in `Mark-LVI-main` and `ALEX-AI-main`.
3. **Alternatives Considered:** Alternative approaches evaluated with architectural trade-offs.
4. **Recommended Solution:** The chosen architectural pattern and implementation design.
5. **Consequences:** Explicit positive outcomes (Pros) and trade-offs/overheads (Cons).
6. **Security Implications:** Impact on sandboxing, authentication, privilege escalation, and data privacy.
7. **Platform Implications:** Portability considerations across Windows 11, Ubuntu Linux, macOS, and iOS.
8. **Migration Dependencies:** Prerequisites, affected functional units (`UNIT-01`..`UNIT-68`), and phases.
9. **Acceptance Criteria:** Objective, verifiable conditions for marking the decision satisfied.
10. **Owner Decision Status:** Explicit authorization status under the personal project governance model (OWNER_APPROVED).

---

## 2. Architectural Decision Records (ADRs)

### ADR-01: Decoupled Three-Tier Architecture vs. Monolithic In-Process Threading

1. **Problem:** In a single-process architecture, a native C++ segmentation fault (e.g. in QtMultimedia, PyAudio, OpenCV, or ctypes), an unhandled exception in an action handler, or a Python memory leak crashes the entire application, instantly killing the GUI, the voice session, and background monitors.
2. **Context:** `Mark-LVI-main` runs PyQt6, sounddevice audio callbacks, Gemini Live WebSockets, action modules, and local web servers in a single Python process across concurrent threading workers (`main.py`). `ALEX-AI-main` is structured as three distinct tiers: Electron container, React 18 HUD, and FastAPI loopback sidecar.
3. **Alternatives Considered:**
   - *Option A (Monolithic PyQt6):* Retain Mark-LVI's single-process Python structure. (Rejected: Fatal crash risk, lack of web-standard UI tooling, difficult cross-platform bundling).
   - *Option B (Embedded Webview in Python):* Use PyWebView or PyQtWebEngine. (Rejected: Inconsistent browser engines across platforms, poor security sandboxing).
   - *Option C (Three-Tier Decoupled Architecture):* Independent Electron Shell, React SPA, and FastAPI Python sidecar. (Recommended).
4. **Recommended Solution:** Decouple Alex into three isolated processes:
   - *Desktop Shell:* Electron 33 providing native OS windowing, system tray, and secure IPC bridge.
   - *Renderer UI:* React 18, Vite, Tailwind CSS running in an isolated renderer process.
   - *Service Sidecar:* Python 3.10+ FastAPI service bound strictly to loopback `127.0.0.1`.
5. **Consequences:**
   - *Pros:* Independent crash boundaries; sidecar can restart without dropping UI; UI hot reload during development; backend sidecar can serve remote companion clients (ADR-09).
   - *Cons:* Higher baseline memory footprint (~180 MB for Electron + ~90 MB for Python sidecar vs. ~120 MB for PyQt6); requires process supervisor.
6. **Security Implications:** Enforces strict process isolation between untrusted web content and privileged OS automation primitives.
7. **Platform Implications:** Electron and Python run cross-platform on Windows 11, Ubuntu Linux, and macOS.
8. **Migration Dependencies:** Affects `UNIT-01`, `UNIT-02`, `UNIT-03`. Foundation for all subsequent phases.
9. **Acceptance Criteria:** Sidecar process crash does not crash Electron shell; launcher detects sidecar drop and triggers graceful recovery or notification within 1.0s.
10. **Owner Decision Status:**
    - Status: `OWNER_APPROVED`
    - Authority: Project Owner (Sole Decision-Maker)
    - Governance Reference: [`ARCHITECTURE_GOVERNANCE.md`](../architecture/ARCHITECTURE_GOVERNANCE.md)

---

### ADR-02: React 18 + Tailwind CSS Renderer vs. PyQt6 QPainter Software UI

1. **Problem:** PyQt6 relies on native C++ Qt bindings that must be compiled and distributed per OS architecture. Building responsive, accessible HUDs, dynamic themes, and reactive state in PyQt6 requires extensive boilerplate and custom canvas paint events.
2. **Context:** `Mark-LVI-main/ui.py` comprises 316 KB of procedural `QPainter` code, software-rendering a MediaPipe face mesh vertex-by-vertex on CPU. `ALEX-AI-main` implements a modern React 18 HUD in `frontend/src/`.
3. **Alternatives Considered:**
   - *Option A (PyQt6 QPainter):* Maintain legacy procedural QPainter canvas. (Rejected: Inflexible, no CSS styling, high CPU overhead).
   - *Option B (Flutter Desktop):* Rebuild desktop UI in Flutter. (Rejected: Additional runtime VM, complex Python FFI).
   - *Option C (React 18 + Vite + Tailwind CSS):* Modern reactive component architecture with web canvas/WebGL for avatar rendering. (Recommended).
4. **Recommended Solution:** Standardize UI on React 18 with Tailwind CSS. Port the 3D face mesh to a lightweight WebGL/Three.js or Canvas2D component (`HudAvatar.tsx`).
5. **Consequences:**
   - *Pros:* Immense web UI ecosystem, rapid component iteration, responsive layouts, CSS hardware-accelerated animations, component unit tests via Vitest.
   - *Cons:* MediaPipe 3D face mesh must be ported from NumPy software projection to WebGL shaders or Canvas2D.
6. **Security Implications:** Zero direct host access from renderer; all communication mediated by Electron ContextBridge.
7. **Platform Implications:** 100% identical rendering across Windows, macOS, Ubuntu, and mobile web browsers.
8. **Migration Dependencies:** Affects `UNIT-03`, `UNIT-04`, `UNIT-05`, `UNIT-06`.
9. **Acceptance Criteria:** React HUD maintains solid 60 FPS rendering; avatar articulates smoothly to incoming audio telemetry.
10. **Owner Decision Status:**
    - Status: `OWNER_APPROVED`
    - Authority: Project Owner (Sole Decision-Maker)
    - Governance Reference: [`ARCHITECTURE_GOVERNANCE.md`](../architecture/ARCHITECTURE_GOVERNANCE.md)

---

### ADR-03: Electron Context Isolation & Preload Allowlist vs. Unrestricted Host Access

1. **Problem:** In Mark-LVI, any script, action, or rendered page has unrestricted access to Python host primitives, arbitrary filesystem read/write, and raw shell execution. If the model fetches untrusted external web content containing prompt injection, the assistant could be coerced into executing arbitrary shell commands without isolation.
2. **Context:** `Mark-LVI-main` has zero security boundaries between UI and OS. `ALEX-AI-main` implements strict Electron sandboxing via `frontend/electron/preload.ts`.
3. **Alternatives Considered:**
   - *Option A (Node Integration Enabled):* Allow renderer to use Node.js `child_process` and `fs`. (Rejected: Severe security vulnerability; any XSS becomes remote code execution).
   - *Option B (IPC Wildcard Forwarder):* Forward raw IPC strings dynamically. (Rejected: Allows unauthorized IPC channel spoofing).
   - *Option C (Strict Context Isolation + Typed Allowlist):* `contextIsolation: true`, `nodeIntegration: false`, and explicitly typed methods on `window.alex`. (Recommended).
4. **Recommended Solution:** Enforce hardened Electron security settings:
   - `contextIsolation: true`
   - `nodeIntegration: false`
   - `sandbox: true`
   - Strictly typed `window.alex` API exposed via `contextBridge.exposeInMainWorld`.
5. **Consequences:**
   - *Pros:* Complete neutralization of renderer-based remote code execution; untrusted HTML/markdown cannot escape to the host.
   - *Cons:* Every new IPC capability requires explicit typed definitions in `preload.ts` and `main.ts`.
6. **Security Implications:** Establishes a zero-trust boundary inside the desktop container.
7. **Platform Implications:** Identical enforcement on Windows, macOS, and Linux.
8. **Migration Dependencies:** Affects `UNIT-62` (`CAT-34`). Governed under Electron Shell Freeze (requires `CR-02` for hotkeys).
9. **Acceptance Criteria:** Automated penetration test confirms `window.require`, `process`, and `child_process` are `undefined` in the renderer console.
10. **Owner Decision Status:**
    - Status: `OWNER_APPROVED`
    - Authority: Project Owner (Sole Decision-Maker)
    - Governance Reference: [`ARCHITECTURE_GOVERNANCE.md`](../architecture/ARCHITECTURE_GOVERNANCE.md)

---

### ADR-04: Dynamic Loopback Bearer Token Authentication vs. Static Open Ports

1. **Problem:** Binding an HTTP or WebSocket server to `127.0.0.1` without dynamic authentication permits any local process, background malware, or hostile browser tab (via Cross-Site Port Attacks) to send commands to the assistant sidecar.
2. **Context:** `Mark-LVI-main` uses open ports or static 4-digit PINs. `ALEX-AI-main` enforces dynamic 32-byte bearer tokens across all endpoints (`backend/app/core/auth.py`).
3. **Alternatives Considered:**
   - *Option A (Unauthenticated Loopback):* Rely solely on `127.0.0.1` binding. (Rejected: Hostile websites can execute loopback fetch requests).
   - *Option B (Static Config PIN):* Hardcode a token in `.env`. (Rejected: Static tokens leak in source control and shared environments).
   - *Option C (Ephemeral Dynamic Bearer Token):* Generate a cryptographically random 32-byte hex token on each launch and inject via process environment. (Recommended).
4. **Recommended Solution:** Unified Launcher generates `ALEX_API_KEY` (32 bytes cryptographically secure hex) at startup. Injects it into sidecar and Electron environment. All REST and WebSocket routes enforce `Authorization: Bearer <token>`.
5. **Consequences:**
   - *Pros:* Total protection against cross-site request forgery and unauthorized local software tampering.
   - *Cons:* CLI testing tools (curl, Postman) must pass the active ephemeral token.
6. **Security Implications:** Eliminates the loopback sidecar hijacking attack vector.
7. **Platform Implications:** Fully OS-agnostic.
8. **Migration Dependencies:** Affects `UNIT-57` (`CAT-30`). Verified in `backend/tests/test_api.py`.
9. **Acceptance Criteria:** Requests lacking `Authorization: Bearer <token>` return `401 Unauthorized`; WebSocket handshakes without query token are rejected with code 1008.
10. **Owner Decision Status:**
    - Status: `OWNER_APPROVED`
    - Authority: Project Owner (Sole Decision-Maker)
    - Governance Reference: [`ARCHITECTURE_GOVERNANCE.md`](../architecture/ARCHITECTURE_GOVERNANCE.md)

---

### ADR-05: OS Keyring Vault Secret Storage vs. Plaintext JSON Files

1. **Problem:** Storing user API keys (Gemini, OpenAI, Groq, ElevenLabs) in plaintext JSON files (`config/api_keys.json`) risks accidental credential leakage into Git history, backup archives, or desktop search indexes.
2. **Context:** `Mark-LVI-main` writes credentials in plaintext to `config/api_keys.json`. `ALEX-AI-main` implements `backend/app/core/keyring_vault.py`.
3. **Alternatives Considered:**
   - *Option A (Plaintext JSON/YAML):* Legacy Mark-LVI approach. (Rejected: Zero credential protection).
   - *Option B (Local AES File with Hardcoded Key):* Encrypted JSON using static app secret. (Rejected: Obfuscation only; easily reverse-engineered).
   - *Option C (Native OS Keyring Vault):* Use Python `keyring` backed by Windows Credential Manager, macOS Keychain, and Linux Secret Service. (Recommended).
4. **Recommended Solution:** Utilize `keyring` for all credential storage under the service name `alex-ai-desktop`. Fall back to encrypted user-profile file storage only if running in headless environments with explicit user warning.
5. **Consequences:**
   - *Pros:* Hardware-backed credential encryption (TPM/Secure Enclave); credentials protected by user OS login session.
   - *Cons:* Linux headless CI requires mock keyring backends (`keyrings.alt`).
6. **Security Implications:** Guarantees zero plaintext secret persistence on disk.
7. **Platform Implications:** Native support on Windows (DPAPI / Credential Manager), macOS (Keychain), Linux (SecretService / D-Bus).
8. **Migration Dependencies:** Affects `UNIT-58` (`CAT-30`). Resolves `DEF-A07-005`.
9. **Acceptance Criteria:** `config/api_keys.json` is completely eliminated; API keys are retrieved from OS Keyring via `/api/v1/settings/secrets`.
10. **Owner Decision Status:**
    - Status: `OWNER_APPROVED`
    - Authority: Project Owner (Sole Decision-Maker)
    - Governance Reference: [`ARCHITECTURE_GOVERNANCE.md`](../architecture/ARCHITECTURE_GOVERNANCE.md)

---

### ADR-06: Unified Process Supervisor CLI (`alex launch`) vs. Manual Scripts

1. **Problem:** Requiring users or testers to manually start multiple background processes (FastAPI sidecar, Vite dev server, Electron) across separate terminal windows leads to orphaned processes, port collision conflicts (e.g. port 8765 in use), and unhandled startup failures.
2. **Context:** `Mark-LVI-main` uses direct Python execution (`python main.py`). `ALEX-AI-main` implements `launcher/cli.py` (`alex launch`, `alex stop`, `alex doctor`, `alex status`).
3. **Alternatives Considered:**
   - *Option A (Batch/Bash Scripts):* Standard `.bat` or `.sh` script files. (Rejected: Fragile process management, poor error trapping, platform-specific syntax).
   - *Option B (Concurrently / NPM Script):* Run processes via Node `concurrently`. (Rejected: Cannot manage Python virtualenv activation cleanly).
   - *Option C (Python Unified Supervisor CLI):* Standalone CLI supervisor using `psutil` and `subprocess` to manage the process tree. (Recommended).
4. **Recommended Solution:** Implement a centralized CLI supervisor in `launcher/cli.py` that negotiates ports, verifies dependencies, monitors child process health, and guarantees clean tree termination on shutdown.
5. **Consequences:**
   - *Pros:* Single-command startup (`alex launch`), automated doctor diagnostics (`alex doctor`), guaranteed zero orphaned processes.
   - *Cons:* Launcher code is frozen under project governance (requires `CR-03` for Unix shell additions).
6. **Security Implications:** Restricts port binding to verified free loopback ports; generates ephemeral bearer tokens.
7. **Platform Implications:** Windows PowerShell, macOS zsh, Ubuntu bash.
8. **Migration Dependencies:** Affects `UNIT-01`, `UNIT-02`, `UNIT-60` (`CAT-01`, `CAT-32`). Gated by `CR-03`.
9. **Acceptance Criteria:** `alex launch` boots all tiers in <5.0s; `alex stop` terminates all child PIDs without leaving orphaned background services.
10. **Owner Decision Status:**
    - Status: `OWNER_APPROVED`
    - Authority: Project Owner (Sole Decision-Maker)
    - Governance Reference: [`ARCHITECTURE_GOVERNANCE.md`](../architecture/ARCHITECTURE_GOVERNANCE.md)

---

### ADR-07: Standardized Pydantic Schemas & Five-Word Outcome Contract

1. **Problem:** Mark-LVI actions return raw unvalidated strings or dictionaries. This causes runtime type errors and leads language models to hallucinate successful execution ("I clicked the button") when the underlying action actually failed or returned unverified.
2. **Context:** `Mark-LVI-main/core/outcome.py` established a 5-word contract (`done`, `unverified`, `failed`, `ask`, `started`). `ALEX-AI-main` implements strict Pydantic v2 schemas in `backend/app/actions/base.py`.
3. **Alternatives Considered:**
   - *Option A (Raw Dictionaries):* Legacy Mark-LVI approach. (Rejected: No type safety or schema validation).
   - *Option B (Generic Boolean `{ success: bool }`):* Current Alex v0.1.0 implementation. (Inadequate: Cannot differentiate between completed and unverified asynchronous operations).
   - *Option C (Unified Pydantic Schema with Five-Word Outcome Contract):* Typed `ActionOutcomeResponse` carrying `status: ToolOutcome` (`done`, `unverified`, `failed`, `ask`, `started`) and structured telemetry. (Recommended).
4. **Recommended Solution:** Unify Pydantic v2 validation with Mark-LVI's five-word outcome contract:
   ```python
   class ToolOutcome(str, Enum):
       DONE = "done"             # Action verified to have completed successfully
       UNVERIFIED = "unverified" # Request initiated, but state could not be verified
       FAILED = "failed"         # Action could not be completed
       ASK = "ask"               # Requires user clarification or approval
       STARTED = "started"       # Asynchronous process initiated cleanly; still running
   ```
   The `ActionOutcomeResponse` preserves `success: bool` as a backward-compatibility property returning `status == ToolOutcome.DONE`. `STARTED` indicates an asynchronous background operation and is **NEVER** interpreted as completed success. Callers distinguish completed from running operations using explicit semantic properties (`is_done`, `is_started`, `is_pending`).
5. **Consequences:**
   - *Pros:* Compile-time and runtime validation; LLM base prompt strictly forbids narrating success when status is `unverified` or `started`; synchronous callers never mistake a running task for a finished one.
   - *Cons:* Requires updating all existing action handlers in `backend/app/actions/builtins/`.
6. **Security Implications:** Eliminates false success reporting during safety-critical operations.
7. **Platform Implications:** Fully OS-agnostic.
8. **Migration Dependencies:** Affects `UNIT-27`, `UNIT-28` (`CAT-14`). Primary deliverable for Phase 3 (`TASK-P3-08`).
9. **Acceptance Criteria:** All action handlers return validated `ActionOutcomeResponse`; unit tests assert 100% compliance with `ToolOutcome` enum.
10. **Owner Decision Status:**
    - Status: `OWNER_APPROVED`
    - Authority: Project Owner (Sole Decision-Maker)
    - Governance Reference: [`ARCHITECTURE_GOVERNANCE.md`](../architecture/ARCHITECTURE_GOVERNANCE.md)

---

### ADR-08: Cross-Platform Hardware Abstraction Layer (HAL) for OS Primitives

1. **Problem:** Core desktop automation capabilities (window enumeration, window focus, polite closing, audio endpoint routing, and volume control) in both Mark-LVI and Alex contain hardcoded Windows Win32 ctypes calls (`user32.dll`, `pycaw`), crashing with `NotImplementedError` on macOS and Ubuntu Linux.
2. **Context:** `backend/app/services/computer_control_service.py#L296` explicitly raises `NotImplementedError` on non-Windows OS.
3. **Alternatives Considered:**
   - *Option A (Windows-Only Product Scope):* Restrict Alex to Windows 11 permanently. (Rejected: Violates cross-platform mandate).
   - *Option B (Ad-Hoc `if platform.system() == ...` Branches):* Scatter OS checks throughout services. (Rejected: Spaghetti code, unmaintainable).
   - *Option C (Formal Hardware Abstraction Layer with Swappable Adapters):* Define abstract interfaces (`WindowManagementAdapter`, `AudioEndpointAdapter`, `PlatformCapabilityAdapter`) with platform-specific driver implementations. (Recommended).
4. **Recommended Solution:** Extract all OS-specific ctypes logic into swappable HAL adapters:
   - `WindowManagementAdapter` $\rightarrow$ `Win32WindowAdapter`, `MacOSWindowAdapter` (AppleScript/Quartz), `LinuxWindowAdapter` (EWMH/wmctrl).
   - `PlatformCapabilityAdapter` $\rightarrow$ Detects Wayland restrictions and macOS TCC permissions, passing limits to LLM prompts.
5. **Consequences:**
   - *Pros:* Clean architecture, testable with mock adapters, zero regression on Windows Win32 automation.
   - *Cons:* Requires a formal Change Request (`CR-01`) to modify frozen `computer_control_service.py`.
6. **Security Implications:** Respects OS security models (macOS TCC, Wayland security boundaries) without attempting illegal bypasses.
7. **Platform Implications:** Enables full cross-platform parity on Windows 11, macOS, and Ubuntu Linux.
8. **Migration Dependencies:** Affects `UNIT-34`, `UNIT-35`, `UNIT-67` (`CAT-18`, `CAT-39`). Gated by `CR-01` (Phase 5).
9. **Acceptance Criteria:** `computer_control_service.py` executes without `NotImplementedError` on macOS and Ubuntu; Windows Win32 tests pass with 100% parity.
10. **Owner Decision Status:**
    - Status: `OWNER_APPROVED`
    - Authority: Project Owner (Sole Decision-Maker)
    - Governance Reference: [`ARCHITECTURE_GOVERNANCE.md`](../architecture/ARCHITECTURE_GOVERNANCE.md)

---

### ADR-09: Remote Mobile Strategy: Local Network Companion Client vs. On-Device Execution

1. **Problem:** Running local LLMs, speech models, or desktop automation directly on mobile devices (iOS / Android) is impossible due to iOS App Store background restrictions, thermal limits, and the Apple App Sandbox.
2. **Context:** `Mark-LVI-main` implements a local FastAPI web dashboard on port 8000 with QR-code pairing. `ALEX-AI-main` currently has zero mobile support.
3. **Alternatives Considered:**
   - *Option A (On-Device Mobile Model Execution):* Run local models via CoreML on iPhone. (Rejected: Heavy battery drain, no desktop automation capabilities).
   - *Option B (Cloud Relay Server):* Route mobile commands through a centralized SaaS cloud server. (Rejected: Violates local-first privacy, introduces monthly hosting costs).
   - *Option C (Encrypted LAN Companion Client):* Desktop sidecar acts as the local hub; smartphone connects over LAN/TLS via QR-code pairing. (Recommended).
4. **Recommended Solution:** Implement a two-tiered mobile companion architecture:
   - *Tier 1 (Mobile Web PWA):* Responsive mobile web app served by FastAPI sidecar with QR pairing for instant LAN access.
   - *Tier 2 (Native iOS Companion Client):* Swift/SwiftUI client communicating over LAN/WebSocket, supporting mobile voice streaming, memory search, and push confirmation for high-risk desktop actions.
5. **Consequences:**
   - *Pros:* Full access to desktop compute and local models from mobile; zero cloud intermediary; end-to-end local network encryption.
   - *Cons:* Smartphone must be on the same local Wi-Fi network (or connected via personal VPN like Tailscale).
6. **Security Implications:** Requires dynamic QR pairing keys (PBKDF2) and AES-256-GCM encryption on companion WebSockets to prevent LAN eavesdropping.
7. **Platform Implications:** Host: Windows/Mac/Linux. Client: iOS 16+ / Android 12+.
8. **Migration Dependencies:** Affects `UNIT-65` (`CAT-37`). Scheduled for Phase 6.
9. **Acceptance Criteria:** Scanning desktop HUD QR code on iPhone opens authenticated mobile companion; voice turn streams bi-directionally over LAN.
10. **Owner Decision Status:**
    - Status: `OWNER_APPROVED`
    - Authority: Project Owner (Sole Decision-Maker)
    - Governance Reference: [`ARCHITECTURE_GOVERNANCE.md`](../architecture/ARCHITECTURE_GOVERNANCE.md)

---

### ADR-10: Pluggable Local AI & Speech Fallback Stack vs. Cloud-Only Architecture

1. **Problem:** Relying 100% on Google Gemini cloud APIs renders the desktop assistant completely inoperative during network outages, air-gapped deployments, or API quota exhaustion (HTTP 429).
2. **Context:** `Mark-LVI-main` implements Faster-Whisper (local STT on CPU), Piper (local neural TTS on CPU), and OpenAI-compatible local LLMs (Ollama, LM Studio). `ALEX-AI-main` currently depends solely on Google Gemini.
3. **Alternatives Considered:**
   - *Option A (Cloud-Only Voice):* Retain current Gemini-only architecture. (Rejected: Vulnerable to outages, privacy concerns for sensitive environments).
   - *Option B (Heavy GPU Local Stack):* Require local CUDA GPU for Whisper and vLLM. (Rejected: Excludes standard laptop and enterprise workstation users).
   - *Option C (Lightweight CPU-Optimized Local Stack):* Faster-Whisper (int8 quantization on CPU) + Piper neural TTS (CPU optimized) + Ollama/LM Studio local LLM client. (Recommended).
4. **Recommended Solution:** Implement a pluggable local AI fallback stack:
   - *Hearing (STT):* Faster-Whisper on CPU with pre-warmed audio buffers and per-turn language detection.
   - *Thinking (LLM):* OpenAI-compatible provider interfacing with local Ollama (`127.0.0.1:11434`) and LM Studio (`127.0.0.1:1234`).
   - *Speaking (TTS):* Piper neural voice engine (~176 voices in 52 languages) and zero-dependency OS system voices (SAPI5/say/espeak).
5. **Consequences:**
   - *Pros:* Complete functional operation offline; zero telemetry leaks in air-gapped setups; absorbs cloud 429 quota exhaustion.
   - *Cons:* Requires downloading local model weights (~150 MB for Piper voice, ~140 MB for Whisper base, ~2 GB for Ollama 3B model).
6. **Security Implications:** Total data privacy: audio and conversational data never leave `127.0.0.1`.
7. **Platform Implications:** Fully supported on Windows 11, Ubuntu Linux, and macOS (Intel & Apple Silicon).
8. **Migration Dependencies:** Affects `UNIT-08`..`UNIT-19`, `UNIT-66` (`CAT-05`..`CAT-09`, `CAT-38`). Core deliverables for Phase 3 and Phase 4.
9. **Acceptance Criteria:** Disconnecting internet allows assistant to process spoken command via local Whisper $\rightarrow$ Ollama $\rightarrow$ Piper pipeline with <1.5s total turn latency.
10. **Owner Decision Status:**
    - Status: `OWNER_APPROVED`
    - Authority: Project Owner (Sole Decision-Maker)
    - Governance Reference: [`ARCHITECTURE_GOVERNANCE.md`](../architecture/ARCHITECTURE_GOVERNANCE.md)
