# Formal Implementation Change Request Register

**Document Version:** 1.1 (Reconciled Governance & Conflict Analysis)  
**Inspection Date:** 2026-11-03  
**Status:** `ACTIVE_CHANGE_REQUEST_REGISTER`  
**Reference Codebase:** `Mark-LVI-main` (MARK LVI / 56)  
**Target Codebase:** `ALEX-AI-main` (Version `0.1.0`, Baseline Snapshot `SNAPSHOT_v0.1.0-20261102`)  

---

## 1. Change Control Policy for Frozen Components

Under project governance rules, several core modules are subject to strict implementation freezes:
- **Milestone A02 Computer Control Implementation (`backend/app/services/computer_control_service.py`)**
- **Unified Launcher Implementation (`launcher/cli.py`)**
- **Electron Shell Main Process (`frontend/electron/main.ts`)**
- **Application Baseline (`0.1.0` / `SNAPSHOT_v0.1.0-20261102`)**

No engineer or agent may modify these files without a formal Change Request (CR) explicitly authorized by the project owner. 

This document provides complete, line-level conflict analyses and implementation specifications for `CR-01`, `CR-02`, and `CR-03`.

---

## 2. Proposed Change Requests

### `CR-01`: Decouple Window Management from `computer_control_service.py` into Swappable HAL Adapters

#### 1. Conflict Analysis Against Existing Freeze
- **Frozen Component:** Milestone A02 Computer Control (`backend/app/services/computer_control_service.py`).
- **Nature of Freeze:** Frozen following A02 security hardening to preserve coordinate bounding, rate limiting, watchdog timers, approval queues, and 32 passing unit tests.
- **Conflict Assessment:** The file currently contains Windows Win32 ctypes calls hardcoded in the main class body. Attempting to call `list_windows()`, `focus_window()`, or `close_app()` on macOS or Ubuntu Linux raises `NotImplementedError`. This creates a direct blocker for cross-platform parity (`UNIT-35`).
- **Justification for Exception:** Refactoring window management into a swappable adapter does NOT modify any safety invariants, coordinate validation rules, or approval gates. It isolates the platform-dependent Win32 code behind an abstract interface and enables macOS and Linux drivers.

#### 2. Exact Affected Files and Line Numbers
- **Primary Target File:** `backend/app/services/computer_control_service.py`
  - Lines 295–305: `@staticmethod def _require_windows()`
  - Lines 306–343: `@classmethod def _windows(cls)` (EnumWindows Win32 ctypes loop)
  - Lines 344–353: `def active_window(self)` (GetForegroundWindow)
  - Lines 358–376: `def focus_window(self, title: str)` (ShowWindow, SetForegroundWindow)
  - Lines 378–435: `def close_app(self, application: str)` (PostMessage WM_CLOSE)
- **New Files to Introduce:**
  - `backend/app/services/adapters/base.py` (Abstract `WindowManagementAdapter` interface)
  - `backend/app/services/adapters/win32_window_adapter.py` (Drop-in extraction of lines 295–435)
  - `backend/app/services/adapters/macos_window_adapter.py` (AppleScript / Quartz driver)
  - `backend/app/services/adapters/linux_window_adapter.py` (EWMH / `wmctrl` driver)

#### 3. Required Behavior
1. Define abstract base class `WindowManagementAdapter` with methods:
   - `list_windows() -> list[dict[str, object]]`
   - `active_window() -> dict[str, object] | None`
   - `focus_window(title: str) -> dict[str, object]`
   - `close_app(application: str) -> dict[str, object]`
2. In `ComputerControlService.__init__()`, inject the appropriate adapter based on `platform.system()`:
   - Windows $\rightarrow$ `Win32WindowAdapter`
   - Darwin $\rightarrow$ `MacOSWindowAdapter`
   - Linux $\rightarrow$ `LinuxWindowAdapter`
3. Forward `active_window()`, `list_windows()`, `focus_window()`, and `close_app()` calls to the injected adapter.

#### 4. Security Impact Assessment
- **Coordinate Clamping:** Untouched. Mouse and keyboard bounds checking remain enforced by `ComputerControlService`.
- **Approval Gate:** Untouched. Irreversible operations (`close_app`, window manipulation) still require cryptographic approval tokens.
- **Privilege Escalation:** Zero risk. Adapters run within the unprivileged user session and cannot elevate permissions.

#### 5. Backward Compatibility Guarantee
- 100% byte-for-byte behavioral parity on Windows 11.
- All existing return payload structures (`window_id`, `title`, `process_id`, `application`) remain identical.
- Zero breaking changes to `ComputerControlService` public API.

#### 6. Regression Test Suite
- Run all 32 existing unit tests in `backend/tests/test_computer_control_service.py`.
- Run mock adapter tests verifying injection on non-Windows platforms.
- Windows smoke test: Verify polite close of a test Notepad window via `WM_CLOSE`.

#### 7. Acceptance Criteria
- `test_computer_control_service.py` passes 32/32 tests with zero regressions.
- Calling `list_windows()` on macOS returns active Quartz window list instead of `NotImplementedError`.
- Calling `list_windows()` on Ubuntu returns active EWMH window list instead of `NotImplementedError`.

#### 8. Owner Authorization Status
- **Status:** `FROZEN_PENDING_OWNER_EXCEPTION`
- **Authorization Authority:** Project Owner (Sole Decision-Maker)
- **Gated Execution:** Phase 5 Implementation.

---

### `CR-02`: Add Global Shortcut IPC Registration to `frontend/electron/main.ts`

#### 1. Conflict Analysis Against Existing Freeze
- **Frozen Component:** Electron Shell Main Process (`frontend/electron/main.ts`).
- **Nature of Freeze:** Frozen to preserve Electron context isolation, sandboxing invariants, and secure IPC boundaries.
- **Conflict Assessment:** Currently, push-to-talk (`Ctrl+Space`) only triggers when the Electron window has active keyboard focus (`frontend/src/App.tsx`). When the user is working in another desktop application (e.g. Word, Browser, IDE), the assistant cannot be summoned via hotkey (`UNIT-21`).
- **Justification for Exception:** Registering a global shortcut via Electron's official `globalShortcut` API is standard practice for desktop assistants. It requires adding ~15 lines of declarative IPC event forwarding without modifying context isolation or renderer privileges.

#### 2. Exact Affected Files and Line Numbers
- **Primary Target File:** `frontend/electron/main.ts`
  - Lines 1–13: Import list (Add `globalShortcut` to `electron` imports).
  - Lines 150–220: `app.whenReady()` lifecycle block (Register `CommandOrControl+Space`).
  - Lines 300–350: App termination cleanup (Add `globalShortcut.unregisterAll()`).
- **Secondary Target File:** `frontend/electron/preload.ts`
  - Expose `onPushToTalk: (callback: (active: boolean) => void) => () => void` in `window.alex`.

#### 3. Required Behavior
1. In `main.ts`, on `app.whenReady()`:
   ```typescript
   globalShortcut.register("CommandOrControl+Space", () => {
     if (mainWindow) {
       mainWindow.webContents.send("alex:push-to-talk", { active: true });
     }
   });
   ```
2. In `main.ts`, on `app.on("will-quit")`:
   ```typescript
   globalShortcut.unregisterAll();
   ```
3. In `frontend/src/hooks/useLiveVoice.ts`, listen for `alex:push-to-talk` and open the Web Audio stream.

#### 4. Security Impact Assessment
- **Context Isolation:** Untouched (`contextIsolation: true` remains enforced).
- **Node Integration:** Untouched (`nodeIntegration: false` remains enforced).
- **Preload Allowlist:** Scoped strictly to read-only push-to-talk event listener. Renderer cannot register arbitrary system hotkeys.

#### 5. Backward Compatibility Guarantee
- Does not affect existing UI mouse-click voice activation.
- Falls back gracefully if OS denies global shortcut registration (e.g. hotkey conflict with OS spotlight).

#### 6. Regression Test Suite
- Vitest renderer tests in `frontend/src/__tests__/`.
- Electron startup and IPC handshake tests.
- Verify shortcut does not interfere with system-reserved shortcuts (e.g. Win+L).

#### 7. Acceptance Criteria
- Pressing `Ctrl+Space` (or `Cmd+Space` on macOS) while third-party app is focused activates microphone and unminimizes Alex HUD.
- Exiting application cleanly unregisters the shortcut without leaving system hooks.

#### 8. Owner Authorization Status
- **Status:** `FROZEN_PENDING_OWNER_EXCEPTION`
- **Authorization Authority:** Project Owner (Sole Decision-Maker)
- **Gated Execution:** Phase 4 Implementation.

---

### `CR-03`: Extend Unified Launcher for macOS/Linux Bash Shell Compatibility

#### 1. Conflict Analysis Against Existing Freeze
- **Frozen Component:** Unified CLI Launcher (`launcher/cli.py`).
- **Nature of Freeze:** Frozen following Milestone A01 to stabilize the multi-process supervision and port conflict engine.
- **Conflict Assessment:** While `launcher/cli.py` is written in Python, its subshell process invocation currently assumes Windows executable paths (`Scripts\python.exe`, PowerShell `.ps1` build scripts). On macOS and Linux, the launcher fails to locate Unix virtual environment paths (`bin/python`) or execute build scripts (`UNIT-01`).
- **Justification for Exception:** Adding POSIX-compliant path resolution and bash shell script dispatch enables the launcher to run seamlessly on macOS and Ubuntu Linux without altering the process supervision, port negotiation, or health polling logic.

#### 2. Exact Affected Files and Line Numbers
- **Primary Target File:** `launcher/cli.py`
  - Lines 120–180: Virtual environment discovery (`_find_venv_python()`)
  - Lines 310–380: `handle_launch()` process spawning logic
  - Lines 212–280: `handle_doctor()` toolchain detection
- **New Scripts to Introduce:**
  - `scripts/build-backend.sh` (POSIX equivalent of `scripts/build-backend.ps1`)
  - `scripts/package-electron.sh` (POSIX packaging script)

#### 3. Required Behavior
1. In `launcher/cli.py`, make Python executable detection cross-platform:
   ```python
   def _get_venv_python(venv_dir: Path) -> Path:
       if platform.system() == "Windows":
           return venv_dir / "Scripts" / "python.exe"
       return venv_dir / "bin" / "python"
   ```
2. Support detecting `.sh` scripts on POSIX hosts while retaining `.ps1` / `.bat` scripts on Windows.
3. Handle POSIX process signals (`SIGTERM`, `SIGINT`) alongside Windows `CTRL_C_EVENT`.

#### 4. Security Impact Assessment
- **Loopback Token Injection:** Untouched. 32-byte dynamic bearer token generation remains enforced.
- **Subprocess Isolation:** Commands are executed strictly without `shell=True` to prevent command injection vulnerabilities.

#### 5. Backward Compatibility Guarantee
- 100% preservation of Windows PowerShell execution paths and commands.
- Zero change to command-line interface syntax (`alex launch`, `alex stop`, `alex doctor`).

#### 6. Regression Test Suite
- Run `backend/tests/test_launcher.py` on Windows, macOS, and Linux runners.
- Verify `alex doctor` detects dependencies accurately on all three platforms.

#### 7. Acceptance Criteria
- `alex launch` successfully discovers virtual environment and launches sidecar and Electron on macOS and Ubuntu Linux.
- `alex stop` terminates all child processes cleanly on POSIX platforms using `SIGTERM`.

#### 8. Owner Authorization Status
- **Status:** `FROZEN_PENDING_OWNER_EXCEPTION`
- **Authorization Authority:** Project Owner (Sole Decision-Maker)
- **Gated Execution:** Phase 5 Implementation.
