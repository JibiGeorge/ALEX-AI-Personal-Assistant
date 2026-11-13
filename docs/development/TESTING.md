# Alex Desktop Assistant — Testing Guide

**Document Version:** 2.0  
**Last Updated:** 2026-11-13  
**Status:** Authoritative Quality Assurance Reference  
**Cross-References:** [`./SETUP.md`](./SETUP.md), [`./DEVELOPMENT_GUIDE.md`](./DEVELOPMENT_GUIDE.md), [`../release/RELEASE_STATUS.md`](../release/RELEASE_STATUS.md)

---

## 1. Quality Assurance Architecture

Alex employs a strict two-tier testing methodology:
1. **Automated Offline Testing:** Deterministic unit, integration, and security tests that run without external network egress or physical peripherals.
2. **Physical Runtime Acceptance Testing:** End-to-end hardware-in-the-loop verification on dedicated Windows 11 target hardware with physical peripherals and live credentials.

> [!IMPORTANT]
> **No Mock Equivalence:** Automated test success validates code correctness, but cannot substitute for physical acceptance. Hardware capabilities (Win32 window APIs, physical display coordinates, 16kHz PCM audio capture, and barge-in audio playback) require empirical physical execution on target hardware.

---

## 2. Automated Test Inventory

The established automated test baseline comprises:

| Scope | Framework | Collected | Passed | Skipped | Failed | Notes |
|---|---|:---:|:---:|:---:|:---:|---|
| **Backend Unit & Service Suites** | `pytest tests/` | 519 | 518 | 1 | 0 | 34 suites covering AI ladder, actions, services, HAL, and vision |
| **Frontend Component & Security Suites** | `vitest run` | 183 | 183 | 0 | 0 | 25 suites covering unified HUD, floating workspace, avatar, and security |
| **Core Application Baseline** | Subtotal | **702** | **701** | **1** | **0** | **Mandatory Automated Quality Gate (100% Determinism)** |
| **Supplemental Packaging Suite** | `node:test` | 3 | 2 | 1 | 0 | 1 Unix executable bit test skipped |
| **Combined All Suites** | Total | **705** | **703** | **2** | **0** | Packaging segregated from core baseline |

---

## 3. Running Automated Backend Tests

Backend tests are located in `backend/tests/` and execute via `pytest`:

```bash
# Activate virtual environment
# Windows: .\backend\.venv\Scripts\Activate.ps1
# macOS/Linux: source backend/.venv/bin/activate

cd backend
pytest tests/
```

### Specific Module Test Execution
```bash
# Test API routes and authentication middleware
pytest tests/test_api.py

# Test Computer Control safety mechanisms (32 unit tests)
pytest tests/test_computer_control_service.py

# Test Scoped Workspace filesystem security and 10-entry undo
pytest tests/test_file_workspace_service.py

# Test Unified Launcher CLI and process supervisor (22 unit tests)
pytest tests/test_launcher.py

# Test Platform capability and briefing aggregation
pytest tests/test_platform_capability_service.py tests/test_briefing_service.py

# Test Vision Service & OpenCV frame capture (7 unit tests)
pytest tests/test_vision_service.py
```

---

## 4. Running Automated Frontend Tests

Frontend tests are located in `frontend/src/` and execute via `Vitest`:

```bash
cd frontend
npm test
```

### Key Frontend Test Suites
- `App.test.tsx`: Verifies unified continuous HUD layout, minimal System Monitor, and controls drawers (17 tests).
- `HUDWorkspaceWindow.test.tsx`: Verifies independent floating workspace window controls, minimize/restore, and content container (10 tests).
- `HUDWorkspace.test.tsx`: Verifies universal content viewer integration (YouTube, Music, PDF, Docs, Images, Browser) (5 tests).
- `VoiceControlledWorkspace.test.tsx`: Verifies hands-free voice-controlled workspace commands (8 tests).
- `HudAvatar.test.tsx`: Verifies dynamic avatar positioning (centered in normal mode, bottom-right in active workspace) (11 tests).
- `electron-security.test.ts`: Verifies `isAllowedDevOrigin`, canonical production file checks, and IPC channel allowlisting (10 tests).
- `ComputerControlPage.test.tsx`: Verifies master session permission toggle default OFF, proposal card review, and emergency stop latch controls.
- `ConversationPage.test.tsx`: Verifies unified typed/voice chat turn rendering and attachment bounds.
- `SettingsPage.test.tsx`: Verifies API key input masking (never displaying stored key in plaintext).

---

## 5. Physical Runtime Acceptance Protocols (Milestone A03–A08)

Physical acceptance requires an authorized human QA engineer on an unrestricted Windows 11 workstation executing all 33 protocols from [`../archive/external-acceptance/A03/A03_TEST_EXECUTION_CHECKLIST.md`](../archive/external-acceptance/A03/A03_TEST_EXECUTION_CHECKLIST.md):

- **Workstream 1 (Unified Launcher & Electron Shell):** Protocols `A03-LCH-01` through `A03-LCH-11`.
- **Workstream 2 (A02 Computer Control Safety Subsystem):** Protocols `A03-CTRL-01` through `A03-CTRL-11`.
- **Workstream 3 (Gemini Live AI Voice Integration):** Protocols `A03-GEM-01` through `A03-GEM-11`.

### Current Physical Acceptance Score
- **Passed:** `0`
- **Failed:** `0`
- **Blocked by Environment:** `33` (`0/33`)
- **Execution Authorization:** `BLOCKED_BY_ENVIRONMENT`

See [`../release/RELEASE_STATUS.md`](../release/RELEASE_STATUS.md) for active environmental blockers and prerequisites.

