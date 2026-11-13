# Milestone A08 – External Workstation Readiness Checklist

**Document Version:** 1.0  
**Milestone:** A08 – External Workstation Readiness & Runtime Execution Gate  
**Target Application Version:** `0.1.0`  
**Approved Baseline Snapshot:** `SNAPSHOT_v0.1.0-20261102`  
**Authoritative References:**  
- [`Alex/docs/A07_FINAL_DOCUMENTATION_AUDIT.md`](./A07_FINAL_DOCUMENTATION_AUDIT.md)  
- [`Alex/docs/A08_EXECUTION_ENTRY_CRITERIA.md`](./A08_EXECUTION_ENTRY_CRITERIA.md)  
- [`Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`](./external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md)  

> [!IMPORTANT]
> **Mandatory Human-Execution Notice:**  
> This checklist must be executed and filled out by an **authorized human test engineer** directly on the physical target workstation before any physical runtime acceptance testing begins.  
> Do not execute or simulate this checklist in automated CI/CD runners, virtual background sessions, or domain-restricted environments.

---

## 1. Workstation & Tester Metadata

| Field | Description / Instruction | Tester Entry |
|---|---|---|
| **Workstation Hostname / ID** | Host machine network name (e.g., `STANDALONE-WIN11-01`) | `___________________________` |
| **Domain Enrollment Status** | Standalone / Workgroup / Domain Joined | `___________________________` |
| **Physical Location** | Physical laboratory / test bench location | `___________________________` |
| **Assigned Tester Name** | Full name of authorized QA test engineer | `___________________________` |
| **Tester Security Role** | Authorized Desktop QA Engineer | `___________________________` |
| **Readiness Audit Date** | Date and local timestamp of audit execution | `___________________________` |

---

## 2. 12-Point Workstation Readiness Checklist

Each check must be empirically validated on the target machine. Check `[X]` for PASS, leave blank or mark `[FAIL]` if unfulfilled.

### A. Operating System & Execution Permissions
- [ ] **Check 1: Windows Version and Architecture (64-bit)**  
  *Command:* `powershell.exe -Command "[System.Environment]::OSVersion.VersionString; [System.Environment]::Is64BitOperatingSystem"`  
  *Requirement:* Windows 10 (22H2+) or Windows 11 (23H2/24H2), 64-bit architecture.  
  *Recorded Output:* `___________________________________________________`

- [ ] **Check 2: Interactive Win32 Desktop Session**  
  *Command:* `powershell.exe -Command "(Get-Process -Id $PID).SessionId"`  
  *Requirement:* Output must be `1` (or greater), confirming an interactive console session with window station `winsta0\default`. Must NOT be Session 0 (service session).  
  *Recorded Session ID:* `______`

- [ ] **Check 3: Process Execution & Group Policy Verification**  
  *Command:* `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Write-Host 'Execution Allowed'"`  
  *Requirement:* Returns `Execution Allowed` with exit code 0. Must NOT produce "This program is blocked by group policy".  
  *Observed Result:* `___________________________________________________`

### B. Runtime Environment & Toolchain
- [ ] **Check 4: Python 3.11+ Compatibility**  
  *Command:* `python --version`  
  *Requirement:* Python 3.11.x (or compatible 3.12.x 64-bit). Virtual environment activation must succeed.  
  *Recorded Version:* `Python __________________`

- [ ] **Check 5: Node.js & npm Compatibility**  
  *Command:* `node --version; npm --version`  
  *Requirement:* Node.js >= 18.0.0 (v20 LTS recommended), npm >= 9.0.0.  
  *Recorded Versions:* `Node: ____________ / npm: ____________`

### C. Physical Hardware Peripherals
- [ ] **Check 6: Physical Display & Resolution**  
  *Verification:* Physical monitor connected via HDMI/DisplayPort running at minimum 1920x1080 resolution. Display scaling set to 100% recommended for PyAutoGUI coordinate mapping.  
  *Recorded Display Spec:* `Resolution: __________ x __________ @ Scale: ______%`

- [ ] **Check 7: Physical Keyboard & Hardware Mouse**  
  *Verification:* Physical USB/Bluetooth keyboard and mouse connected and operational.  
  *Observed Devices:* `___________________________________________________`

- [ ] **Check 8: Physical Microphone (16kHz PCM)**  
  *Verification:* Physical microphone or headset attached and set as Default Recording Device in Windows Sound Settings (`mmsys.cpl`). Voice input meter registers active sound levels.  
  *Device Name:* `___________________________________________________`

- [ ] **Check 9: Physical Stereo Speakers / Headphones**  
  *Verification:* Physical speakers or headphones attached and set as Default Playback Device. Test chime audible.  
  *Device Name:* `___________________________________________________`

### D. Network Egress & Credential Security
- [ ] **Check 10: Gemini Live HTTPS / WSS Egress**  
  *Command:* `curl -I https://generativelanguage.googleapis.com`  
  *Requirement:* HTTP response received (HTTP 200 or 404/400 without TLS interception or connection reset). Port 443 egress open.  
  *Recorded Status:* `___________________________________________________`

- [ ] **Check 11: Dedicated Gemini API Key Provisioned in OS Credential Store**  
  *Command:* `powershell.exe -Command "python -c 'import keyring; print(bool(keyring.get_password(\"alex\", \"gemini_api_key\")))'"`  
  *Requirement:* Output must be `True`. Key must be stored via `alex config` or keyring, NEVER stored in plaintext scripts or repo files.  
  *Keyring Verified:* `[ ] YES`

### E. Repository Baseline & Git Provenance
- [ ] **Check 12: Repository Baseline & 40-Character Commit SHA**  
  *Command:* `git status; git rev-parse HEAD`  
  *Requirement:* Clean working tree matching `SNAPSHOT_v0.1.0-20261102`. Record exact 40-character hex commit SHA below.  
  *Recorded 40-Char SHA:* `________________________________________`  
  *Working Tree Status:* `[ ] CLEAN (0 Uncommitted Changes)`

---

## 3. Evidence Storage & Sanitization Protocol

Prior to testing, the tester must confirm understanding of evidence handling requirements:

1. **Evidence Directory:** All physical test artifacts (logs, screenshots, audio samples) must be saved into:  
   `Alex/docs/external-acceptance/evidence/`
2. **Redaction Mandate:**  
   - Zero Gemini API keys (`AIzaSy...`) in logs or screenshots.
   - Zero bearer tokens in terminal outputs (must display `****`).
   - Personal directories or sensitive corporate paths sanitized.
3. **Authenticity Commitment:**  
   - No mock audio, synthetic keystrokes, or simulated screenshots.
   - Genuine physical artifacts only.

*Tester Acknowledgment:*  
`[ ] I confirm that all evidence collected will be genuine, unsimulated, and sanitized of credentials.`

---

## 4. Formal Workstation Suitability Determination

Based on the empirical audit of the 12 items above, select the authoritative determination:

- [ ] **`SUITABLE_FOR_TESTING`**  
  *Criteria:* All 12 checks evaluated as PASS. Workstation is fully equipped, unrestricted, and approved for Phase 4 execution entry.
- [ ] **`PARTIALLY_SUITABLE`**  
  *Criteria:* Core launcher and GUI checks pass, but audio hardware or Gemini key is absent. Restricts execution to Workstream 1 only.
- [ ] **`BLOCKED_BY_ENVIRONMENT`**  
  *Criteria:* Workstation security policy blocks process spawning, session is non-interactive, or critical prerequisites fail. Testing MUST HALT.

---

## 5. Tester Attestation Signature

```
========================================================================================
                 WORKSTATION READINESS ATTESTATION CERTIFICATE
========================================================================================
  Workstation ID:            ___________________________
  Audit Outcome:             [ ] SUITABLE   [ ] PARTIALLY SUITABLE   [ ] BLOCKED
  Date of Audit:             ___________________________
  Authorized Tester Name:    ___________________________
  Authorized Tester Signature: ___________________________
========================================================================================
```

