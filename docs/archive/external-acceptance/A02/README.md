# A02 – External Acceptance Repository & Evidence Index

**Target Milestone:** A02 – Computer Control Parity & Security Architecture  
**Authoritative Acceptance Guide:** [`Alex/docs/A02_EXTERNAL_ACCEPTANCE_GUIDE.md`](../../A02_EXTERNAL_ACCEPTANCE_GUIDE.md)  
**Authoritative Completion Audit:** [`Alex/docs/A02_COMPLETION_AUDIT.md`](../../A02_COMPLETION_AUDIT.md)  
**Implementation State:** **FROZEN**  
**Current Milestone Acceptance Decision:** **`NOT ACCEPTED`**

---

## 1. Overview & Purpose

This repository organizes the verifiable runtime evidence, tester environment specifications, execution transcripts, and formal sign-off documents required to transition milestone **A02 (Computer Control)** from `NOT ACCEPTED` to `ACCEPTED`.

In strict adherence to the project audit rules:
- **Zero Mock Substitution:** Mocks and automated unit tests prove logic correctness, but cannot substitute for physical hardware interaction.
- **No Policy Bypass:** Never circumvent host security controls (such as Windows Software Restriction Policies or AppLocker).
- **No Secret Storage:** Never record real Gemini API keys, bearer tokens, or personal identifiers in any evidence file or transcript.
- **Unambiguous Status:** Until physical desktop execution and live Gemini turns are verified on an authorized, unrestricted Windows machine, the decision must remain **`NOT ACCEPTED`**.

---

## 2. Evidence Repository Structure

```text
Alex/docs/external-acceptance/A02/
├── README.md                      # This index and handoff instructions
├── TESTER_INFORMATION.md          # Tester environment, OS build, and configuration
├── WINDOWS_DESKTOP_RESULTS.md     # Test logs for mouse, typing, scroll, screenshot, close
├── GEMINI_INTEGRATION_RESULTS.md  # Live speech/text proposal, approval, and execution turns
├── SECURITY_VERIFICATION.md       # Negative security tests (tamper, replay, stop, TTL)
├── FINAL_SIGNOFF.md               # Formal acceptance decision and authorized sign-off
└── evidence/
    ├── desktop/                   # Raw console logs and optional screenshots of desktop smoke
    ├── gemini/                    # Transcripts and UI screenshots of Gemini proposals
    └── security/                  # Evidence of emergency stop latching and rejection logs
```

---

## 3. Evidence Collection Workflow for Authorized Testers

1. **Step 1: Record Tester Environment:**  
   Fill out [`TESTER_INFORMATION.md`](./TESTER_INFORMATION.md) with workstation OS details, display resolution/scaling, Python version, and network check.
2. **Step 2: Execute Physical Windows Desktop Tests:**  
   Follow Part 1 of [`A02_EXTERNAL_ACCEPTANCE_GUIDE.md`](../../A02_EXTERNAL_ACCEPTANCE_GUIDE.md). Run `manual_computer_control_smoke.py` and `manual_computer_control_close_smoke.py`. Save console stdout to `evidence/desktop/smoke_stdout.txt` and complete [`WINDOWS_DESKTOP_RESULTS.md`](./WINDOWS_DESKTOP_RESULTS.md).
3. **Step 3: Execute Live Gemini End-to-End Workflow:**  
   Follow Part 2 of [`A02_EXTERNAL_ACCEPTANCE_GUIDE.md`](../../A02_EXTERNAL_ACCEPTANCE_GUIDE.md). Perform natural language turns with real Gemini credentials. Save masked transcripts to `evidence/gemini/` and complete [`GEMINI_INTEGRATION_RESULTS.md`](./GEMINI_INTEGRATION_RESULTS.md).
4. **Step 4: Execute Negative Security Tests:**  
   Verify parameter tampering rejection, proposal expiration, duplicate approval denial, and emergency stop latching. Record results in [`SECURITY_VERIFICATION.md`](./SECURITY_VERIFICATION.md).
5. **Step 5: Complete Final Sign-Off:**  
   When all 12 acceptance criteria pass and evidence is committed, fill out the signature block in [`FINAL_SIGNOFF.md`](./FINAL_SIGNOFF.md) and update [`A02_COMPLETION_AUDIT.md`](../../A02_COMPLETION_AUDIT.md) to **`ACCEPTED`**.

