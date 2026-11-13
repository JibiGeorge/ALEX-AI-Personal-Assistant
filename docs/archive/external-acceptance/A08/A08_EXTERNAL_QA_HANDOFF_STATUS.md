# Milestone A08 – External QA Handoff & Provisioning Status

**Document Version:** 1.0  
**Milestone:** A08 – External Workstation Provisioning Coordination & Controlled QA Execution  
**Handoff Date:** 2026-11-03T13:36:00+05:30  
**Application Name:** Alex AI Desktop Assistant  
**Application Version:** `0.1.0`  
**Approved Baseline Identifier:** `SNAPSHOT_v0.1.0-20261102`  
**Current Release Status:** `NOT_AUTHORIZED_FOR_RELEASE` (Release Hold Active)  
**Physical Acceptance Status:** `0/33` (0 Passed, 0 Failed, 33 Blocked by Environment)  
**Execution Authorization:** `BLOCKED_BY_ENVIRONMENT`  
**Authoritative References:**  
- [`Alex/docs/A08_FINAL_GOVERNANCE_REVIEW.md`](./A08_FINAL_GOVERNANCE_REVIEW.md)  
- [`Alex/docs/A08_EXECUTION_ENTRY_CRITERIA.md`](./A08_EXECUTION_ENTRY_CRITERIA.md)  
- [`Alex/docs/A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md`](./A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md)  
- [`Alex/docs/A08_EXTERNAL_QA_HANDOFF.md`](./A08_EXTERNAL_QA_HANDOFF.md)  
- [`Alex/docs/external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md`](./external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md)  
- [`Alex/docs/external-acceptance/A03_TESTER_SIGNOFF.md`](./external-acceptance/A03_TESTER_SIGNOFF.md)  

---

## 1. Executive Summary & Handoff Objective

This document establishes the definitive operational handoff package for external workstation provisioning and controlled physical acceptance execution.

With documentation review and handoff preparation complete, the project transitions from documentation governance to awaiting genuine external hardware allocation and physical test execution.

---

## 2. Nine Outstanding Human Actions

Execution of the 33 physical acceptance protocols is strictly gated. The following nine sequential human actions must be completed by an authorized human test engineer on the physical target host. None of these actions may be simulated, automated, or presumed complete without empirical evidence:

```
+-------------------------------------------------------------------------------------------------+
|                               NINE OUTSTANDING HUMAN ACTIONS MATRIX                             |
+-------------------------------------------------------------------------------------------------+
| Action 1: Provision Separate Suitable Windows 11 Workstation        --> [ PENDING ]             |
| Action 2: Complete 12-Item Workstation Readiness Audit Checklist    --> [ PENDING ]             |
| Action 3: Clone Authoritative Repository from Remote Git Origin     --> [ PENDING ]             |
| Action 4: Query and Document Actual 40-Character Git Commit SHA     --> [ PENDING ]             |
| Action 5: Provision Dedicated Gemini Test API Key in OS Keyring     --> [ PENDING ]             |
| Action 6: Verify Network Connectivity & Outbound TLS 443 Egress    --> [ PENDING ]             |
| Action 7: Confirm Interactive Display, Mouse, Keyboard & Audio I/O  --> [ PENDING ]             |
| Action 8: Formally Assign Authorized Human Test Engineer by Name    --> [ PENDING ]             |
| Action 9: Obtain Five-Gate Clearance to Begin the 33 Protocols      --> [ PENDING ]             |
+-------------------------------------------------------------------------------------------------+
```

### Action 1: Provision a Separate Suitable Windows 11 Workstation
- **Requirement:** Secure a standalone, physical Windows 11 64-bit computer (Build 23H2 or 24H2) outside enterprise Active Directory Group Policy and AppLocker restrictions.
- **Evidence Required:** Hostname, OS version, domain status recorded in the audit certificate.
- **Status:** **PENDING**.

### Action 2: Verify All 12 Readiness Checklist Items
- **Requirement:** Physically execute and document every check in [`A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md`](./A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md).
- **Evidence Required:** Fully completed and signed readiness checklist with empirical command outputs.
- **Status:** **PENDING**.

### Action 3: Clone the Authoritative Repository
- **Requirement:** Clone the authoritative project repository directly from the remote Git origin onto the target Windows machine.
- **Evidence Required:** Working tree cloned cleanly without local modifications.
- **Status:** **PENDING**.

### Action 4: Record the Actual 40-Character Git Commit SHA
- **Requirement:** Execute `git rev-parse HEAD` on the target machine and confirm the commit matches `SNAPSHOT_v0.1.0-20261102`.
- **Evidence Required:** Actual 40-character hexadecimal commit SHA documented in the audit log.
- **Status:** **PENDING**.

### Action 5: Provision Gemini Credentials Securely
- **Requirement:** Store a dedicated, active, billed Google Gemini API test key in the Windows Credential Manager using `keyring` / `alex config`. Never place keys in plaintext files, scripts, or environment variables.
- **Evidence Required:** Output from `python -c "import keyring; print(bool(keyring.get_password('alex', 'gemini_api_key')))"` returning `True`.
- **Status:** **PENDING**.

### Action 6: Verify Network Connectivity
- **Requirement:** Confirm unobstructed outbound TLS 443 HTTPS and WSS egress to `generativelanguage.googleapis.com` without corporate TLS interception.
- **Evidence Required:** Successful HTTPS connection response and verified WebSocket handshake.
- **Status:** **PENDING**.

### Action 7: Confirm Required Physical Hardware
- **Requirement:** Verify interactive Win32 desktop session (`winsta0\default`, Session ID >= 1), physical 1920x1080 display at 100% scaling, hardware mouse, physical keyboard, physical 16kHz PCM audio microphone, and stereo playback speakers.
- **Evidence Required:** Windows Sound Settings verification and active display resolution confirmation.
- **Status:** **PENDING**.

### Action 8: Assign an Authorized Human Tester
- **Requirement:** Designate an authorized human desktop QA engineer by full name and role to conduct physical testing and sign the evaluation certificates.
- **Evidence Required:** Tester name, title, and organization recorded in governance documentation.
- **Status:** **PENDING**.

### Action 9: Obtain Formal Approval to Begin the 33 Protocols
- **Requirement:** Formally verify that all five gates in [`A08_EXECUTION_ENTRY_CRITERIA.md`](./A08_EXECUTION_ENTRY_CRITERIA.md) evaluate to `PASS` before launching `alex launch` or executing any desktop automation.
- **Evidence Required:** Completed Five-Gate Authorization Clearance signed by the assigned tester.
- **Status:** **PENDING**.

---

## 3. Strict Execution Directives

During external execution, the test engineer must strictly adhere to the following non-negotiable rules:
1. **Zero Simulation:** Do not simulate hardware, network connectivity, API responses, user approval, or physical execution.
2. **Zero Policy Bypass:** Do not attempt AppLocker bypasses, privilege escalation, or unauthorized registry tampering.
3. **Preserve Protocol IDs:** Execute all 33 protocols from [`A03_TEST_EXECUTION_CHECKLIST.md`](./external-acceptance/A03_TEST_EXECUTION_CHECKLIST.md) using their original IDs (`A03-LCH-01..11`, `A03-CTRL-01..11`, `A03-GEM-01..11`).
4. **Accurate Protocol Statuses:** Any test blocked by environmental issues must remain `BLOCKED_BY_ENVIRONMENT`. A blocked test must **never** be marked as `PASS`.
5. **Sanitization Mandate:** Sanitize all screenshots and logs. Never commit raw API keys or plain tokens to source control.
6. **Implementation Freezes:** Do not alter application code in `backend/`, `frontend/`, `launcher/`, or `Mark-LVI-main`.

---

## 4. Current Milestone & Governance State

```
========================================================================================
                      EXTERNAL QA HANDOFF FINAL STATUS MATRIX
========================================================================================
  A08 Documentation & Handoff Preparation: COMPLETE
  External Workstation Provisioning:       PENDING
  Authoritative Git Commit SHA:            UNVERIFIED (Pending remote clone)
  Five Entry Gates Status:                 ALL 5 GATES CLOSED
  Execution Authorization:                 BLOCKED_BY_ENVIRONMENT
  Physical Acceptance Protocols:           0/33 (0 Passed, 0 Failed, 33 Blocked)
  Application Code Defects:                0 Identified in Executed Tests
  Environmental Blockers:                  5 Active Release Blockers (DEF-A07-001..005)
  Production Release Status:               NOT_AUTHORIZED_FOR_RELEASE
========================================================================================
```

---

## 5. Transition Mandate & Next Milestone Trigger

> [!IMPORTANT]
> **No Further Documentation Milestones:**  
> Milestone A08 documentation and handoff preparation is formally **COMPLETE**.  
> **No further documentation-only milestones should be initiated after this correction.**  
> The next milestone must be triggered strictly by actual external workstation provisioning, verified five-gate clearance, and authorized human execution of the existing 33 acceptance protocols on target hardware.

