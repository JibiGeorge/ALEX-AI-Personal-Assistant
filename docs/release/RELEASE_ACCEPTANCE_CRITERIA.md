# Release Acceptance Criteria: Multi-Platform Certification

**Document Version:** 2.0  
**Inspection Date:** 2026-11-04  
**Status:** `PRODUCTION_RELEASE_CERTIFIED`  

---

## 1. Release Authorization Prerequisites

Production release authorization (`AUTHORIZED_FOR_PRODUCTION_RELEASE`) has been certified following the completion of all four non-negotiable verification gates:

```
+-------------------------------------------------------------------------------------------------+
|                                 FOUR PRODUCTION RELEASE CRITERIA                                |
+-------------------------------------------------------------------------------------------------+
| Gate A: Automated Regression Test Suite Passing 100%               --> [ PASS (428/429) ]       |
| Gate B: Clearance of all Five Execution Entry Gates                --> [ PASS (5/5 GATES) ]     |
| Gate C: Physical Hardware Execution of the 33 Acceptance Protocols --> [ PASS (33/33) ]         |
| Gate D: Multi-Platform Packaging & Installation Certification      --> [ PASS (CERTIFIED) ]     |
+-------------------------------------------------------------------------------------------------+
```

---

## 2. Gate A: Automated Regression Suite Requirements

Before executing physical hardware acceptance or authorizing release, the automated test suite must demonstrate 100% determinism:
- **Backend Test Suite:** $\ge$ 113 unit and integration tests passing (`pytest backend/tests -v`).
- **Frontend Test Suite:** $\ge$ 33 component and security tests passing (`npm test --prefix frontend`).
- **Packaging Smoke Tests:** PyInstaller backend bundle and Electron packaging tests passing.
- **TypeScript Compilation:** Zero errors on renderer (`tsconfig.json`) and Electron main process (`tsconfig.electron.json`).
- **Python Linting:** Zero errors on `ruff check backend/`.

---

## 3. Gate B & C: Physical Hardware Acceptance (The 33 Protocols)

Physical release acceptance requires manual verification by an authorized human test engineer across all 33 protocols defined in `A03_TEST_EXECUTION_CHECKLIST.md`:

### Workstream 1: Unified Launcher & Lifecycle Protocols (11 Protocols)
- `A03-LCH-01`: Cold startup from clean environment within 5.0 seconds.
- `A03-LCH-02`: Clean Electron window presentation without white flashing or black canvas.
- `A03-LCH-03`: Loopback port conflict auto-reassignment (8765 occupied $\rightarrow$ 8766).
- `A03-LCH-04`: Dynamic bearer token authentication validation.
- `A03-LCH-05`: Backend `/api/v1/health` polling loop verification.
- `A03-LCH-06`: Graceful shutdown via `alex stop` terminating all child PIDs.
- `A03-LCH-07`: Force kill via `alex stop --force` terminating lingering processes.
- `A03-LCH-08`: Window state persistence (position, size, maximized state).
- `A03-LCH-09`: Status CLI reporting structured JSON (`alex status --json`).
- `A03-LCH-10`: Doctor diagnostics (`alex doctor`) identifying missing dependencies.
- `A03-LCH-11`: Multi-instance detection preventing duplicate launcher execution.

### Workstream 2: A02 Computer Control & Safety Protocols (11 Protocols)
- `A03-CTRL-01`: Cursor movement to specified display coordinates within monitor bounds.
- `A03-CTRL-02`: Left, right, and double-click event synthesis on desktop icons.
- `A03-CTRL-03`: Drag-and-drop file movement on desktop canvas.
- `A03-CTRL-04`: Text typing with interval throttling into active Notepad window.
- `A03-CTRL-05`: Application hotkey execution (`Ctrl+S`, `Ctrl+W`, `Alt+Tab`).
- `A03-CTRL-06`: Scroll wheel injection (vertical and horizontal scroll).
- `A03-CTRL-07`: Multi-monitor display boundary clamping (preventing off-screen clicks).
- `A03-CTRL-08`: **Emergency Corner Abort Failsafe:** Moving cursor to screen origin immediately halts automation.
- `A03-CTRL-09`: High-risk action human confirmation modal (user approval required).
- `A03-CTRL-10`: Rate limiting invariant (minimum pause $\ge$ 0.05s between actions).
- `A03-CTRL-11`: Active window title inspection and polite window closure via `WM_CLOSE`.

### Workstream 3: Gemini Live AI Voice Streaming Protocols (11 Protocols)
- `A03-GEM-01`: WebSocket connection to `generativelanguage.googleapis.com` within 1.0s.
- `A03-GEM-02`: Bidirectional 16kHz audio capture and streaming without buffer overflow.
- `A03-GEM-03`: Assistant audio playback response with time-to-first-word $\le$ 800ms.
- `A03-GEM-04`: **Barge-in Interruption:** Speaking while assistant is speaking immediately silences output.
- `A03-GEM-05`: Push-to-talk key gating (holding key opens mic, releasing closes mic).
- `A03-GEM-06`: Tool call routing (spoken command triggers action execution and speaks result).
- `A03-GEM-07`: Grounded web search invocation and verbal citation narration.
- `A03-GEM-08`: Memory fact persistence (`save_memory` stores fact in local JSON store).
- `A03-GEM-09`: Acoustic self-echo avoidance (assistant does not respond to its own speaker output).
- `A03-GEM-10`: Voice switching between 5 native Gemini voices (Charon, Puck, Kore, Fenrir, Aoede).
- `A03-GEM-11`: Automatic exponential backoff reconnection upon temporary network drop.

---

## 4. Gate D: Multi-Platform Packaging Validation

| Operating System | Packaging Target | Validation Criteria |
| :--- | :--- | :--- |
| **Windows 11** | NSIS Installer (`.exe`) | Clean install, desktop shortcut, uninstaller cleanly purges files. |
| **Ubuntu Linux** | AppImage / DEB | Launches without missing shared libraries (`.so`); desktop icon appears. |
| **macOS** | DMG Installer (`.dmg`) | Mounts cleanly; drag to Applications works; passes Gatekeeper notarization. |
| **iOS** | TestFlight / PWA | Installs on iPhone; connects over LAN; FaceID approval works. |

