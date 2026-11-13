# Consolidated Blocker Register: Technical, Environmental & Governance

**Document Version:** 1.0  
**Inspection Date:** 2026-11-03  
**Status:** `ACTIVE_BLOCKER_REGISTER`  

---

## 1. Blocker Taxonomy & Executive Summary

This register consolidates all active blockers preventing full migration completion, cross-platform certification, or physical release authorization.

Blockers are strictly classified into nine distinct categories to prevent confusing operating system environmental limitations with application software defects:

```
========================================================================================
                               BLOCKER REGISTER SUMMARY
========================================================================================
  Category                                 Count   Status
----------------------------------------------------------------------------------------
  1. External Provisioning Blockers:         1     OPEN (Standalone Win11 pending)
  2. Operating System & Hardware Blockers:   3     OPEN (Win32 station, Mic/Speaker, GPO)
  3. Network & Credential Blockers:          2     OPEN (Gemini Keyring, WSS Proxy)
  4. Cross-Platform Architectural Blockers:  2     OPEN (Wayland input, macOS TCC)
  5. Application Implementation Blockers:    0     CLEAN (148 tests pass)
  6. Migration Feature Parity Blockers:      3     IN PROGRESS (Local AI, TTS, Docs)
  7. Security & Licensing Blockers:          0     CLEAN (CC BY-NC 4.0 compliant)
  8. Automated Testing Blockers:             0     CLEAN (100% deterministic pass)
  9. Physical Acceptance Blockers:           1     OPEN (33 protocols gated)
----------------------------------------------------------------------------------------
  Total Active Critical/High Blockers:      12 Blockers Documented
========================================================================================
```

---

## 2. Exhaustive Blocker Inventory

### 2.1 External Provisioning & Hardware Blockers

#### `BLK-ENV-001` (`DEF-A07-001`): Enterprise Active Directory AppLocker Restricts Child Shell Instantiation
- **Category:** Environment & Operating System Security Policy
- **Severity:** CRITICAL \| **Status:** OPEN
- **Affected Features:** All 33 physical acceptance protocols (`A03-LCH`, `A03-CTRL`, `A03-GEM`).
- **Evidence:** Executing `powershell.exe` on corporate domain host throws: `This program is blocked by group policy.`
- **Root Cause:** Test runner is enrolled in an enterprise Active Directory domain enforcing AppLocker path rules.
- **Impact:** Unified Launcher and Electron cannot spawn child processes.
- **Required Action:** Allocate a dedicated, standalone, non-domain-joined Windows 11 workstation.
- **Dependencies:** Physical hardware procurement / IT allocation.
- **Owner:** IT Operations / QA Infrastructure Lead.
- **Exit Criteria:** Standalone Windows 11 workstation verified non-domain joined; child process execution unrestricted.

#### `BLK-ENV-002` (`DEF-A07-002`): Headless Runner Context Lacks Interactive Win32 Desktop Station
- **Category:** Display & Window Management
- **Severity:** CRITICAL \| **Status:** OPEN
- **Affected Features:** Electron GUI rendering and A02 Computer Control (`A03-CTRL-01..11`).
- **Evidence:** PyAutoGUI throws display bounds errors; Tkinter/Electron fails to allocate window station.
- **Root Cause:** Background automation service runs in Session 0 without an interactive desktop station (`winsta0\default`).
- **Impact:** Synthetic clicks, mouse movement, window activation, and coordinate checks fail.
- **Required Action:** Log into an interactive Windows 11 desktop console session with a physical monitor at 1920x1080 resolution.
- **Owner:** QA Test Engineer.
- **Exit Criteria:** Active interactive user session (Session ID $\ge$ 1) verified with 1920x1080 canvas at 100% DPI.

#### `BLK-ENV-003` (`DEF-A07-003`): Absence of Physical Multimedia Audio Hardware
- **Category:** Peripheral Audio Hardware
- **Severity:** CRITICAL \| **Status:** OPEN
- **Affected Features:** Gemini Live Voice (`A03-GEM-01..11`) and Audio Devices (`CAT-11`).
- **Evidence:** Web Audio API / PyAudio cannot open 16kHz PCM audio input/output streams.
- **Root Cause:** Headless runner lacks physical microphone and speaker audio endpoints.
- **Impact:** Bidirectional voice streaming cannot initialize or be verified.
- **Required Action:** Attach physical USB microphone and stereo speakers/headphones to the test workstation.
- **Owner:** QA Test Engineer.
- **Exit Criteria:** Hardware audio devices enumerated and responsive in Windows Sound Settings.

---

### 2.2 Network & Credential Blockers

#### `BLK-NET-001` (`DEF-A07-004`): Enterprise Network Proxy Blocks Outbound WSS to Gemini Live
- **Category:** Network Infrastructure & TLS Inspection
- **Severity:** HIGH \| **Status:** OPEN
- **Affected Features:** Gemini Live Voice (`CAT-04`, `A03-GEM-01..11`).
- **Evidence:** WebSocket connection to `generativelanguage.googleapis.com:443` fails TLS handshake or is intercepted.
- **Root Cause:** Corporate egress proxy performing TLS interception without custom root certificates in Python trust store.
- **Impact:** Live voice streaming fails on connection attempt.
- **Required Action:** Provide direct, unobstructed outbound HTTPS and WSS access to `generativelanguage.googleapis.com` on port 443.
- **Owner:** Network Administrator / QA Engineer.
- **Exit Criteria:** Direct WSS handshake succeeds with valid Google TLS certificate.

#### `BLK-CRED-001` (`DEF-A07-005`): Absence of Live Gemini API Credentials in OS Keyring
- **Category:** Credential Storage
- **Severity:** HIGH \| **Status:** OPEN
- **Affected Features:** Live Voice and Gemini Grounded Search (`CAT-04`, `CAT-23`).
- **Evidence:** `keyring.get_password("Alex", "gemini-api-key")` returns `None`.
- **Root Cause:** Production API keys intentionally excluded from git-tracked workspace to prevent credential leakage.
- **Impact:** Live voice sessions and grounded search cannot establish authenticated sessions.
- **Required Action:** Securely provision dedicated Google Gemini API test key into the OS Keyring via `alex config` or Windows Credential Manager.
- **Owner:** Authorized Human QA Engineer.
- **Exit Criteria:** Keyring returns valid configured key; first-run authentication succeeds.

---

### 2.3 Cross-Platform & Architectural Blockers

#### `BLK-PLAT-001`: Wayland Desktop Security Model Blocks Synthetic Input on Modern Ubuntu
- **Category:** Cross-Platform Architecture / Linux Compositor
- **Severity:** HIGH \| **Status:** OPEN (Mitigated via X11 recommendation)
- **Affected Features:** Computer Control (`CAT-15`, `CAT-16`) on Ubuntu 22.04 / 24.04 LTS.
- **Evidence:** Under Wayland, `pyautogui.click()` and `pyautogui.write()` return without moving cursor or typing.
- **Root Cause:** Wayland protocol security architecture deliberately prohibits cross-application synthetic input injection.
- **Impact:** Autonomous desktop computer control cannot operate on standard Wayland sessions.
- **Required Action:** Implement Wayland detection in `platform_capability_service.py` to inform LLM prompt honestly; instruct user to select "Ubuntu on Xorg" for full automation.
- **Owner:** Linux Platform Engineer.
- **Exit Criteria:** Assistant informs user honestly of Wayland restriction; full automation verified under Xorg session.

#### `BLK-PLAT-002`: macOS TCC Permissions Block Input and Display Capture until User Grant
- **Category:** Cross-Platform Architecture / macOS Security
- **Severity:** HIGH \| **Status:** OPEN
- **Affected Features:** Computer Control (`CAT-15`) and Vision (`CAT-17`) on macOS Sonoma/Sequoia.
- **Evidence:** Synthetic mouse clicks and screen capture return empty data without error until Accessibility and Screen Recording permissions are enabled.
- **Root Cause:** macOS TCC framework mandates explicit user opt-in in System Settings.
- **Impact:** Alex cannot control desktop or see screen until user manually grants permissions.
- **Required Action:** Implement TCC permission auditor; display in-app onboarding wizard guiding user to System Settings.
- **Owner:** macOS Platform Engineer.
- **Exit Criteria:** Onboarding wizard accurately detects TCC status and guides user to successful grant.

---

### 2.4 Migration Feature Parity Blockers

#### `BLK-MIG-001`: Absence of Local LLM Provider & Tool Budget Engine in Alex
- **Category:** Migration Feature Parity
- **Severity:** HIGH \| **Status:** OPEN (Phase 3 Delivery)
- **Affected Features:** Local AI (`CAT-06`), Multi-Provider (`CAT-07`), Offline Operation.
- **Evidence:** Backend sidecar contains zero OpenAI-compatible HTTP clients or tool slicing logic.
- **Impact:** Assistant is 100% dependent on Google Gemini cloud API; cannot run offline on Ollama or LM Studio.
- **Required Action:** Execute `TASK-P3-02` and `TASK-P3-03` to implement `OpenAICompatibleProvider` and `ToolBudgetManager`.
- **Owner:** Backend AI Engineer.
- **Exit Criteria:** Ollama model executes local tools with tool descriptions under 9,000 characters.

#### `BLK-MIG-002`: Absence of Local Offline Speech Recognition (Whisper) & Neural Synthesis (Piper)
- **Category:** Migration Feature Parity
- **Severity:** HIGH \| **Status:** OPEN (Phase 4 Delivery)
- **Affected Features:** Offline STT (`CAT-08`), Offline TTS (`CAT-09`), Multi-Language Voice.
- **Evidence:** No local audio transcription or speech synthesis packages in `backend/requirements.txt`.
- **Impact:** User cannot converse with assistant when disconnected from cloud API.
- **Required Action:** Execute `TASK-P4-01` and `TASK-P4-02` to implement `LocalSpeechService` with `faster-whisper` and `piper-tts`.
- **Owner:** Audio & Speech Engineer.
- **Exit Criteria:** Fully offline spoken conversation executes with under 1.5s total turn latency on CPU.

#### `BLK-MIG-003`: Hardcoded Windows-Only Window Management in Computer Control
- **Category:** Cross-Platform Architecture
- **Severity:** HIGH \| **Status:** OPEN (Phase 5 Delivery)
- **Affected Features:** Window Management (`CAT-18`) on macOS and Ubuntu.
- **Evidence:** `backend/app/services/computer_control_service.py#L296` explicitly raises `NotImplementedError` on non-Windows.
- **Impact:** `focus_window()` and `close_app()` crash on macOS and Linux.
- **Required Action:** Execute `TASK-P5-01..03` to introduce swappable `WindowManagementAdapter` interface with macOS AppleScript and Linux wmctrl backends.
- **Owner:** Systems Engineer.
- **Exit Criteria:** "Open Spotify" and "Close Spotify" work cleanly on Windows, macOS, and Ubuntu X11.

---

### 2.5 Physical Acceptance Blocker

#### `BLK-ACC-001`: Physical Desktop Acceptance Protocol Execution Gated by Five Entry Criteria
- **Category:** Release Acceptance Governance
- **Severity:** CRITICAL \| **Status:** OPEN (Gated)
- **Affected Features:** All 33 Physical Acceptance Protocols (`A03-LCH`, `A03-CTRL`, `A03-GEM`).
- **Evidence:** Current physical score is `0/33` (0 Passed, 0 Failed, 33 Blocked by Environment). Current status: `NOT_AUTHORIZED_FOR_RELEASE`.
- **Root Cause:** All five execution entry gates remain closed pending physical workstation provisioning and human tester assignment.
- **Impact:** Release hold remains active.
- **Required Action:** Complete Actions 1 through 9 in `docs/release/RELEASE_STATUS.md`; obtain formal Five-Gate clearance.
- **Owner:** Project Owner.
- **Exit Criteria:** All 33 physical acceptance protocols pass with empirical evidence on target hardware; release authorization granted.

