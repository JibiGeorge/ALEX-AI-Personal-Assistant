# Milestone A08 – Physical Execution Entry Criteria

**Document Version:** 1.0  
**Milestone:** A08 – External Workstation Readiness & Runtime Execution Gate  
**Target Application Version:** `0.1.0`  
**Approved Baseline:** `SNAPSHOT_v0.1.0-20261102`  
**Authoritative References:**  
- [`Alex/docs/A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md`](./A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md)  
- [`Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`](./external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md)  
- [`Alex/docs/A07_FINAL_DOCUMENTATION_AUDIT.md`](./A07_FINAL_DOCUMENTATION_AUDIT.md)  

---

## 1. Executive Summary & Purpose

This document establishes the **Mandatory Entry Criteria Gates** that must be fully satisfied before any physical runtime execution begins for Milestone A08.

Under the project governance framework:
> *"A08 physical execution must not begin until all mandatory prerequisites are satisfied. Once suitable hardware is available, use the existing authoritative checklist `A03_TEST_EXECUTION_CHECKLIST.md` to execute all 33 existing protocols: `A03-LCH-01` through `A03-LCH-11`, `A03-CTRL-01` through `A03-CTRL-11`, and `A03-GEM-01` through `A03-GEM-11`. Do not create replacement acceptance criteria or weaken existing safety requirements."*

---

## 2. Five Mandatory Execution Entry Gates

Physical execution of the 33 acceptance protocols is strictly gated behind 5 sequential, non-negotiable verification gates. All 5 gates must evaluate to **`OPEN / SATISFIED`** before launching `alex launch` or executing any desktop automation.

```
+-------------------------------------------------------------------------------+
|                        MILESTONE A08 ENTRY CRITERIA GATES                      |
+-------------------------------------------------------------------------------+
|  GATE 1: Workstation Suitability Gate        --> [ SUITABLE_FOR_TESTING ]     |
|  GATE 2: Baseline Integrity Gate            --> [ SNAPSHOT_v0.1.0-20261102 ]  |
|  GATE 3: Credential & Network Security Gate --> [ Keyring Valid / TLS Open ]  |
|  GATE 4: Hardware & Multimedia Peripheral Gate --> [ 1080p / Mic / Speakers ] |
|  GATE 5: Governance & Tester Authority Gate --> [ Authorized Tester Assigned] |
+-------------------------------------------------------------------------------+
```

---

### Gate 1: Workstation Suitability Gate
- **Requirement:** An authorized human tester must execute [`A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md`](./A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md) on the target host.
- **Entry Condition:** The formal suitability determination must be **`SUITABLE_FOR_TESTING`** (all 12 prerequisite checks marked PASS).
- **Hard Stop Condition:** If the outcome is `BLOCKED_BY_ENVIRONMENT` or `PARTIALLY_SUITABLE` (for full suite), entry is **DENIED**. No execution may proceed.

### Gate 2: Repository Baseline Integrity Gate
- **Requirement:** The repository must be cloned from the authoritative origin repository onto the target host.
- **Entry Condition:**
  1. Working tree is clean (`git status` shows zero uncommitted changes).
  2. The exact 40-character Git commit SHA is queried (`git rev-parse HEAD`) and documented in the test log.
  3. Codebase contents match `SNAPSHOT_v0.1.0-20261102` (Application Version `0.1.0`).
  4. Implementation freezes across Computer Control, Unified Launcher, and `Mark-LVI-main` are 100% intact.
- **Hard Stop Condition:** If any file diff exists or code has been altered, entry is **DENIED**.

### Gate 3: Credential & Network Security Gate
- **Requirement:** Secure provisioning of cloud credentials and network connectivity.
- **Entry Condition:**
  1. A dedicated, active, billed Google Gemini API test key is stored in the Windows Credential Manager via `keyring` / `alex config`.
  2. Zero plaintext credentials exist in shell scripts, environment variables, or repo files.
  3. Direct outbound TLS 443 egress to `generativelanguage.googleapis.com` is verified without connection drops.
- **Hard Stop Condition:** If credentials are missing or proxy blocks WSS handshakes, Workstream 3 entry is **DENIED**.

### Gate 4: Hardware & Multimedia Peripheral Gate
- **Requirement:** Physical human-interactive testing peripherals attached and operational.
- **Entry Condition:**
  1. Interactive Win32 session running (Session ID >= 1) with window station `winsta0\default`.
  2. Physical 1920x1080 display active (scaling set to 100%).
  3. Physical mouse and keyboard connected.
  4. Physical 16kHz PCM audio microphone verified active in Windows Sound Settings.
  5. Physical stereo playback speakers or headphones connected and audible.
- **Hard Stop Condition:** If execution is running in Session 0, via SSH/background daemon, or lacks audio peripherals, entry is **DENIED**.

### Gate 5: Governance & Tester Authority Gate
- **Requirement:** QA execution governance authorization.
- **Entry Condition:**
  1. An authorized human QA test engineer is assigned by name.
  2. Evidence directory `Alex/docs/external-acceptance/evidence/` is created and write-accessible.
  3. Tester affirms zero fabrication, zero policy bypass, and mandatory redaction rules.
- **Hard Stop Condition:** Automated agents or unauthorized personnel must NOT attempt physical desktop acceptance.

---

## 3. Protocol Execution Mandate (The 33 Authoritative Protocols)

Once all 5 Entry Gates are satisfied, testing must strictly execute the existing protocols in [`A03_TEST_EXECUTION_CHECKLIST.md`](./external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md):

### Workstream 1: Unified Launcher and Electron Shell (11 Protocols)
- `A03-LCH-01`: System Diagnostics (`alex doctor`)
- `A03-LCH-02`: Standard Sequential Startup (`alex launch`)
- `A03-LCH-03`: Port Conflict Fallback (Ports 8765/5173 occupied)
- `A03-LCH-04`: Headless Mode Execution (`alex launch --headless`)
- `A03-LCH-05`: Process Status & Token Masking (`alex status --json`)
- `A03-LCH-06`: Coordinated Graceful Shutdown (`alex stop`)
- `A03-LCH-07`: Restart Orchestration (`alex restart`)
- `A03-LCH-08`: Electron Dev/Prod Origin Isolation
- `A03-LCH-09`: Electron IPC Security Bridge (`window.alex`)
- `A03-LCH-10`: Corrupt Runtime State Recovery (`runtime.json`)
- `A03-LCH-11`: Rapid Stop/Start Stress Sequence

### Workstream 2: Milestone A02 Computer Control Safety Subsystem (11 Protocols)
- `A03-CTRL-01`: Session Permission Gate Toggle (Default OFF)
- `A03-CTRL-02`: Proposal Queue Cap (Max 5) & 5-Min Expiration
- `A03-CTRL-03`: One-Shot Execution Token Enforcement
- `A03-CTRL-04`: Coordinate Bounds Validation (Reject out-of-screen)
- `A03-CTRL-05`: Hotkey Whitelist Enforcement
- `A03-CTRL-06`: Text Injection Cap (2000 chars) & Sanitization
- `A03-CTRL-07`: Win32 Window Enumeration & Target Focus (`SetForegroundWindow`)
- `A03-CTRL-08`: Polite Window Close (`WM_CLOSE` to disposable window)
- `A03-CTRL-09`: Latched Emergency Stop Abort (Immediate queue flush)
- `A03-CTRL-10`: 12-Second Watchdog Execution Timeout
- `A03-CTRL-11`: End-to-End Physical Smoke Script (`$env:ALEX_ENABLE_DESKTOP_SMOKE="1"`)

### Workstream 3: Gemini Live AI Voice Integration (11 Protocols)
- `A03-GEM-01`: Live Audio Pipeline Initialization (16kHz in / 24kHz out)
- `A03-GEM-02`: Microphone Audio Capture & Ingestion (PCM stream)
- `A03-GEM-03`: Bi-Directional Speech Interaction
- `A03-GEM-04`: Barge-In Interrupt Handling
- `A03-GEM-05`: Voice Tool Proposal Triggering
- `A03-GEM-06`: Voice Tool Proposal Human Approval Card
- `A03-GEM-07`: Live Session Disconnect & Auto-Reconnect
- `A03-GEM-08`: Keyring Credential Loading & Masking
- `A03-GEM-09`: Audio Latency & Jitter Measurement (<1500ms)
- `A03-GEM-10`: Non-Streaming Fallback Inspection
- `A03-GEM-11`: End-to-End Multimodal Task Flow

---

## 4. Preservation of Safety Controls

Under no circumstances may an external tester:
1. Modify safety limits (e.g. increase watchdog timeout beyond 12s, allow arbitrary hotkeys, or bypass the 5-proposal limit).
2. Execute Computer Control actions without explicit manual renderer approval.
3. Disable latched emergency stop state without manual UI re-arming.
4. Modify application source code to pass a test.

---

## 5. Defect & Blocker Escalation Protocol

If any protocol fails during physical execution:
1. Immediately capture relevant terminal logs, error dialog screenshots, and system metrics.
2. Mark the specific protocol outcome as `FAIL` or `BLOCKED_BY_ENVIRONMENT`.
3. If an unhandled crash or safety failure occurs, **halt testing immediately**.
4. Log the defect in the A08 Defect Register and escalate to the Release Acceptance Coordinator for triage.

