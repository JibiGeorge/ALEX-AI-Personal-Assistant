# Alex – Unified Launcher Lifecycle Execution Guide

**Document:** `LAUNCHER_EXECUTION_GUIDE.md`  
**Purpose:** Step-by-step instructions and evidence capture requirements for Category A tests (`TC-LCH-01` to `TC-LCH-08`).

---

## 1. Overview & Preparation

The tester will execute the full lifecycle of the Alex unified launcher across 6 operational phases:
1. System diagnostic validation (`alex doctor`).
2. Complete full-stack startup (`alex launch`).
3. Real-time service monitoring (`alex status` and `alex status --json`).
4. Headless development mode (`alex launch --no-electron`).
5. Application restart (`alex restart`).
6. Orderly application termination (`alex stop`).

All console logs and diagnostic transcripts must be captured and saved under [`evidence/launcher/`](./evidence/launcher/).

---

## 2. Test Execution Protocols

### TC-LCH-01: System Diagnostic Validation
* **Objective:** Verify environment runtimes, virtual environment, dependencies, loopback ports, and OS credential store.
* **Command:**
  ```cmd
  alex doctor --verbose > docs\external-acceptance\unified-startup\evidence\launcher\doctor_stdout.txt 2>&1
  ```
  *(Display on console and save output)*
* **Expected Result:**
  * Terminal displays ASCII banner and 10 individual diagnostic checks.
  * All 10 checks evaluate to `[PASS]` (or acceptable `[WARN]` on transient ports).
  * Overall exit code is `0`.

---

### TC-LCH-02: Complete Full-Stack Launch
* **Objective:** Verify end-to-end launch of Python FastAPI backend, React/Vite dev server, and Electron desktop window.
* **Command:**
  ```cmd
  alex launch
  ```
* **Step-by-Step Expected Sequence:**
  1. `[1/5] Validating environment & dependencies... [OK]`
  2. `[2/5] Starting Python FastAPI backend (127.0.0.1:8765)... [OK]  http://127.0.0.1:8765`
     * Backend health endpoint `http://127.0.0.1:8765/api/v1/health` reports status `ready`.
  3. `[3/5] Starting React/Vite frontend (127.0.0.1:5173)... [OK]  http://127.0.0.1:5173/`
     * Vite frontend server responds with HTTP 200.
  4. `[4/5] Compiling and launching Electron desktop window... [OK]  PID <pid>`
     * `tsc -p tsconfig.electron.json` compiles main process.
     * Electron GUI window opens (1180x800).
     * Electron detects launcher environment (`ALEX_MANAGED_BY_LAUNCHER=1`) and attaches to existing backend on port 8765 without spawning a second backend.
  5. `[5/5] Verifying end-to-end system connectivity... [OK]`
  6. **Summary Table Rendered:**
     ```text
      ────────────────────────────────────────────────────────────────────────
       Service          Status     Port      PID       Target
      ────────────────────────────────────────────────────────────────────────
       Backend API      ONLINE     8765      12345     http://127.0.0.1:8765
       Frontend UI      ONLINE     5173      23456     http://127.0.0.1:5173/
       Electron App     ONLINE     -         34567     Desktop Window
      ────────────────────────────────────────────────────────────────────────
       ✔ Startup completed in X.XXs.
       Press Ctrl+C to stop all services cleanly.
     ```
* **Evidence to Capture:**
  * Save console output to [`evidence/launcher/launch_stdout.txt`](./evidence/launcher/).
  * Verify PIDs using `tasklist | findstr /i "python node electron"`.

---

### TC-LCH-03 & TC-LCH-04: Service Status Monitoring & JSON Sanitization
* **Objective:** While Alex is running from TC-LCH-02, open a second terminal window and inspect service health and JSON formatting.
* **Commands:**
  ```cmd
  alex status
  alex status --json > docs\external-acceptance\unified-startup\evidence\launcher\status_json.txt
  ```
* **Expected Result for `alex status`:**
  * Displays active uptime counter (`Uptime: HH:MM:SS`).
  * Table reports `ONLINE` status, ports, and live PIDs matching the launch process.
* **Expected Result for `alex status --json`:**
  * Valid JSON structure containing `launcher_pid`, `status: "running"`, `backend`, `frontend`, and `electron`.
  * **Critical Security Invariant:** The backend bearer token must be masked as `****` or `xxxx...****`. No plaintext authentication token is exposed.

---

### TC-LCH-05: Headless Development Launch
* **Objective:** Verify starting the backend API and web frontend in isolation without launching the Electron window.
* **Command:**
  ```cmd
  alex launch --no-electron
  ```
* **Expected Result:**
  * Step sequence adjusts to `[1/4]` through `[4/4]`.
  * Starts Backend (port 8765) and Frontend (port 5173).
  * Skips Electron compilation and window spawning.
  * Browser navigation to `http://127.0.0.1:5173/` displays the Alex web interface.
* **Evidence to Capture:**
  * Save console output to [`evidence/launcher/launch_no_electron.txt`](./evidence/launcher/).

---

### TC-LCH-06 & TC-LCH-07: Graceful Application Shutdown & Force Cleanup
* **Objective:** Verify stopping running services gracefully from the command line.
* **Commands:**
  ```cmd
  alex stop
  alex stop --force
  ```
* **Expected Result for `alex stop`:**
  * Issues graceful HTTP POST `/api/v1/shutdown` to backend.
  * Terminates Vite and Electron child process trees.
  * Cleans up `%APPDATA%\Alex\runtime.json` state file.
  * Prints: `✔ Successfully stopped all Alex processes.`
  * Verifying with `alex status` confirms `STOPPED (No active services running)`.
  * Verifying with `tasklist` confirms no orphaned `python.exe` or `electron.exe` processes remain.
* **Expected Result for `alex stop --force`:**
  * Confirms forceful tree kill when processes do not respond within timeout.
* **Evidence to Capture:**
  * Save output to [`evidence/launcher/stop_stdout.txt`](./evidence/launcher/).

---

### TC-LCH-08: Application Stack Restart
* **Objective:** Verify seamless restart of all services without port collisions or orphaned processes.
* **Command:**
  ```cmd
  alex restart
  ```
* **Expected Result:**
  * Gracefully terminates the running session.
  * Clears runtime state and waits 1.0 second.
  * Relaunches Backend, Frontend, and Electron window.
  * Returns fresh PIDs and healthy status summary table.
* **Evidence to Capture:**
  * Save output to [`evidence/launcher/restart_stdout.txt`](./evidence/launcher/).

---

## 3. Results Recording Sheet

The tester must record the empirical result for each Category A test below:

| Test ID | Command | Date Tested | Actual Terminal Output / Logs | Tester Observed Status |
|---|---|---|---|---|
| **TC-LCH-01** | `alex doctor --verbose` | *(Date)* | All 10 checks passed | `[  ] PASS  [  ] FAIL` |
| **TC-LCH-02** | `alex launch` | *(Date)* | 5/5 steps completed; table rendered; window opened | `[  ] PASS  [  ] FAIL` |
| **TC-LCH-03** | `alex status` | *(Date)* | Status ONLINE, PIDs accurate, uptime tracking | `[  ] PASS  [  ] FAIL` |
| **TC-LCH-04** | `alex status --json` | *(Date)* | JSON valid; bearer token masked as `****` | `[  ] PASS  [  ] FAIL` |
| **TC-LCH-05** | `alex launch --no-electron` | *(Date)* | Backend & Vite online; Electron skipped | `[  ] PASS  [  ] FAIL` |
| **TC-LCH-06** | `alex stop` | *(Date)* | Graceful shutdown; no orphaned processes | `[  ] PASS  [  ] FAIL` |
| **TC-LCH-07** | `alex stop --force` | *(Date)* | Force termination cleanly kills process trees | `[  ] PASS  [  ] FAIL` |
| **TC-LCH-08** | `alex restart` | *(Date)* | Orderly stop followed by clean fresh launch | `[  ] PASS  [  ] FAIL` |

