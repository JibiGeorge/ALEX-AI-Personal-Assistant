# Alex – Unified Launcher & Electron Runtime Final Acceptance Sign-Off

**Milestone:** Unified Launcher CLI & Electron Desktop Runtime Stabilization  
**Authoritative Reference:** [`Alex/docs/UNIFIED_STARTUP_RUNTIME_ACCEPTANCE.md`](../../UNIFIED_STARTUP_RUNTIME_ACCEPTANCE.md)  
**Package:** `Alex/docs/external-acceptance/unified-startup/`  
**Current Status:** **`BLOCKED_BY_ENVIRONMENT`**  

---

## 1. Formal Decision Rules

In accordance with Alex engineering governance and audit requirements:

* **ACCEPTED:**  
  All 40 mandatory test cases (`TC-LCH-01` through `TC-LCH-08`, `TC-ELC-01` through `TC-ELC-06`, `TC-SEC-01` through `TC-SEC-10`, `TC-FAIL-01` through `TC-FAIL-10`, and `TC-GEM-01` through `TC-GEM-06`) have been physically executed on an authorized, unrestricted Windows workstation, all 40 evaluate to `PASS`, and verifiable console logs, transcripts, and screenshots are committed under `evidence/`.
* **NOT ACCEPTED:**  
  One or more mandatory test cases evaluate to `FAIL`, a reproducible defect or crash occurs, or security controls are bypassed.
* **BLOCKED_BY_ENVIRONMENT:**  
  Required physical hardware runtime tests could not be executed due to machine policy, software restriction policy, credential absence, or infrastructure barriers.

---

## 2. Mandatory Acceptance Criteria Checklist

### Category A: Unified Launcher Lifecycle
- [ ] **TC-LCH-01:** System diagnostic check (`alex doctor --verbose`) verifies all 10 checks.
- [ ] **TC-LCH-02:** Full-stack startup (`alex launch`) starts Backend, Frontend, and Electron window.
- [ ] **TC-LCH-03:** Status command (`alex status`) accurately reports PIDs, ports, and uptime.
- [ ] **TC-LCH-04:** JSON status (`alex status --json`) masks backend bearer token as `****`.
- [ ] **TC-LCH-05:** Headless mode (`alex launch --no-electron`) runs Backend and Frontend without GUI.
- [ ] **TC-LCH-06:** Graceful stop (`alex stop`) shuts down all process trees via HTTP shutdown.
- [ ] **TC-LCH-07:** Force stop (`alex stop --force`) reliably terminates lingering processes.
- [ ] **TC-LCH-08:** Restart command (`alex restart`) stops active session and relaunches cleanly.

### Category B: Electron Desktop Runtime
- [ ] **TC-ELC-01:** Window opens at 1180x800 with dark theme and renders holographic HUD.
- [ ] **TC-ELC-02:** Context bridge exposes `window.alex`; `require`/`process`/`ipcRenderer` are undefined.
- [ ] **TC-ELC-03:** Live host metrics update; settings persist across restart.
- [ ] **TC-ELC-04:** Production build loads `dist/index.html` via canonical `file://` URL without errors.
- [ ] **TC-ELC-05:** Startup error dialog displays exact failing subsystem (`stepDescription`).
- [ ] **TC-ELC-06:** Exactly one Python backend process exists (no duplicate spawned by Electron).

### Category C: Security & Sender Validation
- [ ] **TC-SEC-01:** Exact loopback development origin (`http://127.0.0.1:5173/`) is permitted.
- [ ] **TC-SEC-02:** Subdomain spoofing attempts (`127.0.0.1:5173.attacker.com`) are blocked.
- [ ] **TC-SEC-03:** Unauthorized external protocols and ports are rejected.
- [ ] **TC-SEC-04:** Production canonical file path matching `dist/index.html` is permitted.
- [ ] **TC-SEC-05:** Arbitrary local file URLs (`file:///etc/passwd`, `calc.exe`) are blocked.
- [ ] **TC-SEC-06:** Child iframe IPC invocations (`senderFrame !== mainFrame`) throw `"Untrusted IPC sender"`.
- [ ] **TC-SEC-07:** Window open requests (`window.open`) are denied by `setWindowOpenHandler`.
- [ ] **TC-SEC-08:** Navigation to unauthorized origins is prevented by `will-navigate`.
- [ ] **TC-SEC-09:** Plaintext bearer tokens and API keys never appear in terminal output or JSON status.
- [ ] **TC-SEC-10:** Media permissions are restricted strictly to audio from trusted windows.

### Category D: Failure Recovery & Edge Cases
- [ ] **TC-FAIL-01:** Second launch attempt while active is blocked with PID warning.
- [ ] **TC-FAIL-02:** Backend spawn error halts launch cleanly at Step 2 with exit code 1.
- [ ] **TC-FAIL-03:** Backend health timeout after 25s dumps stderr logs and terminates backend.
- [ ] **TC-FAIL-04:** Frontend readiness timeout after 30s dumps Vite logs and terminates backend.
- [ ] **TC-FAIL-05:** Electron early exit terminates frontend and backend cleanly.
- [ ] **TC-FAIL-06:** Occupied backend port 8765 auto-reassigns to 8766.
- [ ] **TC-FAIL-07:** Occupied frontend port 5173 auto-reassigns to 5174.
- [ ] **TC-FAIL-08:** Missing dependency halts launch at Step 1 with actionable remedy.
- [ ] **TC-FAIL-09:** `Ctrl+C` terminal interrupt cleanly terminates all child process trees.
- [ ] **TC-FAIL-10:** Closing Electron desktop window cleanly terminates all background services.

### Category E: Live Gemini AI Integration
- [ ] **TC-GEM-01:** Key stored in OS credential store; availability verified without printing key.
- [ ] **TC-GEM-02:** Live REST chat turn produces natural language response from `gemini-2.5-flash`.
- [ ] **TC-GEM-03:** Live voice session establishes WebSocket connection with real-time audio playback.
- [ ] **TC-GEM-04:** Computer control action proposal requires manual human approval click in Controls drawer.
- [ ] **TC-GEM-05:** Missing and invalid API keys display polite UI error banner; backend process does not crash.
- [ ] **TC-GEM-06:** Zero plaintext API keys or bearer tokens exist in any logs or network captures.

---

## 3. Required Evidence Artifacts Audit

Confirm all required evidence files are present in the repository prior to final sign-off:

| Evidence File Path | Purpose | Verified Present |
|---|---|---|
| `evidence/launcher/doctor_stdout.txt` | Complete stdout from `alex doctor --verbose` | [ ] |
| `evidence/launcher/launch_stdout.txt` | Complete stdout from `alex launch` | [ ] |
| `evidence/launcher/status_json.txt` | Sanitized output from `alex status --json` | [ ] |
| `evidence/launcher/stop_stdout.txt` | Clean shutdown output from `alex stop` | [ ] |
| `evidence/electron/dev_window_hud.png` | Screenshot of running Electron HUD in dev mode | [ ] |
| `evidence/electron/devtools_console.txt` | DevTools console checks confirming context isolation | [ ] |
| `evidence/electron/prod_window.png` | Screenshot of running Electron in production mode | [ ] |
| `evidence/security/security_test_stdout.txt` | Test suite output from `electron-security.test.ts` | [ ] |
| `evidence/failures/` | Recovery logs for port collisions and interruptions | [ ] |
| `evidence/gemini/rest_turn_chat.png` | Screenshot of completed live Gemini REST chat turn | [ ] |
| `evidence/gemini/rest_transcript.txt` | Masked transcript of conversation turn | [ ] |
| `evidence/gemini/live_voice_session.png` | Screenshot of active bidirectional voice session | [ ] |
| `evidence/gemini/tool_proposal_approval.png`| Screenshot of human approval requirement in Controls drawer | [ ] |
| `evidence/gemini/credential_error_banner.png`| Screenshot of missing/invalid API key error handling | [ ] |

---

## 4. Formal Acceptance Sign-Off Certificate

### Final Acceptance Decision:
```text
[   ] ACCEPTED               (All 40 criteria verified with committed empirical evidence)
[   ] NOT ACCEPTED           (Defects or test failures encountered)
[ X ] BLOCKED_BY_ENVIRONMENT (Runner Software Restriction Policy blocks live terminal subshells)
```

### Authorized External Tester Sign-Off:
* **Tester Name:** _______________________________________
* **Title / Organization:** _______________________________________
* **Workstation Hostname / OS Build:** _______________________________________
* **Tester Signature:** _______________________________________
* **Date:** ________________________

### Lead Architect Review & Status Transition:
* **Architect Name:** Antigravity AI Assistant / Engineering Lead
* **Decision:** `BLOCKED_BY_ENVIRONMENT` (Execution attempted on 2026-11-01T22:48:50+05:30; blocked by Active Directory SRP/AppLocker on `powershell.exe`).
* **Audit Logs:** [`evidence/failures/host_policy_blocker.txt`](./evidence/failures/host_policy_blocker.txt), [`evidence/launcher/execution_attempt.log`](./evidence/launcher/execution_attempt.log).
* **Transition Authorizing Milestone Acceptance:** Requires unblocked physical execution by an authorized tester on an unrestricted workstation.
* **Date:** 2026-11-01

