# Alex – Failure Recovery & Edge-Case Acceptance Protocols

**Document:** `FAILURE_RECOVERY_TESTS.md`  
**Purpose:** Test instructions and recovery verification for 10 specific failure scenarios (`TC-FAIL-01` to `TC-FAIL-10`).

---

## 1. Overview & Verification Objective

A production desktop launcher must fail safely, clean up child processes on any abort, report accurate diagnostics, and never leave orphaned processes running in the background.

The tester will simulate or execute each failure condition and verify:
1. Terminal error message is clear and specifies the failing component.
2. The launcher exits with code `1` (or `0` on user-initiated close).
3. Any started child processes (`python.exe`, `node.exe`, `electron.exe`) are terminated.
4. Temporary runtime state is cleaned up.

---

## 2. Test Execution Protocols

### TC-FAIL-01: Existing Session Protection Guard
* **Scenario:** A user attempts to launch Alex while an existing instance is already running.
* **Procedure:**
  1. Start Alex in Terminal A: `alex launch`.
  2. While running, open Terminal B and execute: `alex launch`.
* **Expected Result:**
  * Terminal B halts at Step 0:
    ```text
    ! An active Alex session was detected (PID 12345).
    i Use 'alex status' to view services, or 'alex stop' before launching.
    i To override this check, run 'alex launch --force'.
    ```
  * Terminal B exits with code `1`.
  * The running instance in Terminal A continues running undisturbed.

---

### TC-FAIL-02 & TC-FAIL-03: Backend Startup Failure & Health Timeout
* **Scenario:** The backend fails to start or fails to report healthy on `/api/v1/health` within 25 seconds.
* **Procedure (Automated simulation):**
  Run the automated regression test:
  ```cmd
  backend\.venv\Scripts\python.exe -m pytest backend\tests\test_launcher.py -k "health_failure"
  ```
* **Expected Result:**
  * Launcher detects timeout; halts at Step 2.
  * Outputs: `[FAIL] Backend failed health check`.
  * Displays captured stderr logs from backend.
  * Terminates the backend process tree; clears state; exits code `1`.
  * Frontend and Electron are never spawned.

---

### TC-FAIL-04: Frontend Readiness Failure
* **Scenario:** The React/Vite development server fails to start or fails readiness check within 30 seconds.
* **Procedure (Automated simulation):**
  Run the automated regression test:
  ```cmd
  backend\.venv\Scripts\python.exe -m pytest backend\tests\test_launcher.py -k "frontend_readiness"
  ```
* **Expected Result:**
  * Launcher halts at Step 3: `[FAIL] Frontend failed readiness check`.
  * Captures Vite log output.
  * Automatically invokes `backend.stop()` to prevent leaving an orphaned backend running.
  * Exits code `1`.

---

### TC-FAIL-05: Electron Immediate Crash Recovery
* **Scenario:** Electron process crashes or is terminated immediately upon startup.
* **Procedure (Automated simulation):**
  Run the automated regression test:
  ```cmd
  backend\.venv\Scripts\python.exe -m pytest backend\tests\test_launcher.py -k "electron_failure"
  ```
* **Expected Result:**
  * Launcher detects `not electron.is_alive()` at Step 4.
  * Outputs: `[FAIL] Electron window exited unexpectedly`.
  * Tears down both the frontend Vite server and backend sidecar cleanly.
  * Exits code `1`.

---

### TC-FAIL-06: Backend Port Conflict & Auto-Reassignment
* **Scenario:** Port 8765 is already occupied by another application.
* **Procedure:**
  1. Open a temporary PowerShell window and occupy port 8765:
     ```powershell
     $listener = [System.Net.Sockets.TcpListener]8765
     $listener.Start()
     ```
  2. In another terminal, run: `alex launch`.
  3. Observe terminal output.
  4. Stop the TCP listener: `$listener.Stop()`.
* **Expected Result:**
  * Launcher detects busy port 8765.
  * Prints warning: `! Backend port 8765 is busy. Automatically reassigning to available port 8766.`
  * Successfully binds backend to 8766.
  * Passes `ALEX_BACKEND_PORT=8766` to Electron.
  * All services reach healthy state on port 8766.

---

### TC-FAIL-07: Frontend Port Conflict & Auto-Reassignment
* **Scenario:** Port 5173 is already occupied by another application.
* **Procedure:**
  1. Occupy port 5173 using a TCP listener.
  2. Run `alex launch`.
* **Expected Result:**
  * Launcher prints warning: `! Frontend port 5173 is busy. Automatically reassigning to available port 5174.`
  * Starts Vite on port 5174 and configures `ALEX_FRONTEND_URL=http://127.0.0.1:5174/`.
  * Electron loads `http://127.0.0.1:5174/` successfully.

---

### TC-FAIL-08: Missing Dependencies Detection
* **Scenario:** Python package or virtual environment is missing.
* **Procedure:**
  Execute launcher with an invalid Python path:
  ```cmd
  set ALEX_PYTHON=invalid_python_path
  alex launch
  ```
* **Expected Result:**
  * Launcher pre-flight halts at Step 1: `[FAIL] Environment validation failed`.
  * Reports actionable remediation command; exits code `1`.
  * `set ALEX_PYTHON=` to restore.

---

### TC-FAIL-09: User Interruption via `Ctrl+C`
* **Scenario:** User presses `Ctrl+C` in the terminal while Alex is running.
* **Procedure:**
  1. Start Alex via `alex launch`.
  2. Once summary table appears, press `Ctrl + C`.
* **Expected Result:**
  * Terminal catches SIGINT gracefully:
    ```text
    i Stopping Alex application services...
    ✔ Successfully stopped all Alex processes.
    ```
  * Backend, Frontend, and Electron process trees are all terminated.
  * `tasklist` confirms no lingering processes.

---

### TC-FAIL-10: Closing the Electron Application Window
* **Scenario:** User clicks the close button (`X`) on the Alex desktop window.
* **Procedure:**
  1. Start Alex via `alex launch`.
  2. Click the `X` button in the top right corner of the Alex window.
* **Expected Result:**
  * Launcher supervision detects window close:
    ```text
    i Electron desktop window was closed by the user.
    i Stopping Alex application services...
    ✔ Successfully stopped all Alex processes.
    ```
  * Launcher exits with code `0`.
  * Frontend and Backend processes terminate cleanly.

---

## 3. Results Recording Sheet

| Test ID | Failure Scenario Induction | Date Tested | Actual Observed Recovery | Status |
|---|---|---|---|---|
| **TC-FAIL-01** | Dual launch collision | *(Date)* | Stopped at step 0; PID warning; exit 1 | `[  ] PASS  [  ] FAIL` |
| **TC-FAIL-02** | Backend startup crash | *(Date)* | Step 2 caught error; cleaned up; exit 1 | `[  ] PASS  [  ] FAIL` |
| **TC-FAIL-03** | Backend health timeout | *(Date)* | Health timed out; stderr dumped; exit 1 | `[  ] PASS  [  ] FAIL` |
| **TC-FAIL-04** | Frontend readiness failure | *(Date)* | Step 3 timeout; backend stopped; exit 1 | `[  ] PASS  [  ] FAIL` |
| **TC-FAIL-05** | Electron early exit | *(Date)* | Dead PID detected; services stopped; exit 1 | `[  ] PASS  [  ] FAIL` |
| **TC-FAIL-06** | Backend port 8765 busy | *(Date)* | Auto-reassigned to 8766; services online | `[  ] PASS  [  ] FAIL` |
| **TC-FAIL-07** | Frontend port 5173 busy | *(Date)* | Auto-reassigned to 5174; services online | `[  ] PASS  [  ] FAIL` |
| **TC-FAIL-08** | Missing dependency preflight | *(Date)* | Step 1 halted; clear remedy printed; exit 1 | `[  ] PASS  [  ] FAIL` |
| **TC-FAIL-09** | Ctrl+C terminal interrupt | *(Date)* | SIGINT caught; all processes killed cleanly | `[  ] PASS  [  ] FAIL` |
| **TC-FAIL-10** | Electron window closed (X) | *(Date)* | Window exit detected; clean shutdown; exit 0 | `[  ] PASS  [  ] FAIL` |

