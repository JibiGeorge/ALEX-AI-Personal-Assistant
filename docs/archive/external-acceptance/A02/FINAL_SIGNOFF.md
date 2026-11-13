# A02 – Milestone Acceptance Certificate & Final Sign-Off

**Milestone Target:** A02 – Computer Control Completion & Parity  
**Target Application:** Alex (Modernized Architecture)  
**Reference Baseline:** `Mark-LVI-main` (Read-only reference baseline)  
**Current Milestone Acceptance Decision:** **`NOT ACCEPTED`** (Frozen pending external tester execution)

---

## 1. Acceptance Criteria Checklist

The authorized signatory must verify each of the following 5 criteria before issuing an acceptance decision:

| # | Criterion | Verification Evidence Location | Required State | Signatory Check |
|---|---|---|---|---|
| **1** | **Physical Desktop Runtime Execution** | [`WINDOWS_DESKTOP_RESULTS.md`](./WINDOWS_DESKTOP_RESULTS.md)<br>`evidence/desktop/smoke_stdout.txt` | All 8 tests (TC-A02-01 to TC-A02-08) passed on live Windows desktop session without mock substitution. | `[ ] PASS` |
| **2** | **Live Gemini End-to-End Workflow** | [`GEMINI_INTEGRATION_RESULTS.md`](./GEMINI_INTEGRATION_RESULTS.md)<br>`evidence/gemini/` | Natural-language prompt created proposal; displayed in Controls UI; zero pre-approval input; manual approval executed action; result returned to model. | `[ ] PASS` |
| **3** | **Security & Negative Controls** | [`SECURITY_VERIFICATION.md`](./SECURITY_VERIFICATION.md)<br>`evidence/security/` | Direct bypass blocked; proposal rejection works; 300s TTL expires; parameter tampering rejected; duplicate approval denied; emergency stop latches. | `[ ] PASS` |
| **4** | **Evidence Integrity & Completeness** | `Alex/docs/external-acceptance/A02/evidence/` | All required terminal stdout logs, UI screenshots, and execution traces are attached in repository. | `[ ] PASS` |
| **5** | **Zero Secret Disclosure** | Global repository check | No real API keys, bearer tokens, or personal identifiers are present in logs or screenshots. Keys masked as `AIzaSy...****`. | `[ ] PASS` |

---

## 2. Formal Decision Rules

In strict adherence to the project charter:

* **ACCEPTED:**  
  *Marked only when all 5 criteria above are verified PASS with physical evidence by an authorized tester.*
* **NOT ACCEPTED:**  
  *Maintained whenever physical desktop verification is incomplete, live Gemini verification is missing, evidence is absent, or tester sign-off is incomplete.*
* **BLOCKED BY ENVIRONMENT:**  
  *Assigned when host security restrictions (e.g. Group Policy) or missing credentials prevent physical execution.*

---

## 3. Current Milestone Decision

### Status: **`NOT ACCEPTED`**

**Justification:**  
On the development runner, physical desktop interaction was blocked by Windows Group Policy (`This program is blocked by group policy`) and live Gemini turns could not be executed without production API credentials. In accordance with strict audit rules, automated unit tests and mock implementations cannot be substituted for live physical execution. The implementation is **frozen** and awaiting authorized external testing.

---

## 4. Authorized Sign-Off Block

*(To be signed by the authorized external tester upon completion of all physical tests)*

| Field | Record |
|---|---|
| **Authorized Tester Name** | ____________________________________________________ |
| **Professional Title / Role** | ____________________________________________________ |
| **Organization / Team** | ____________________________________________________ |
| **Workstation OS & Build** | ____________________________________________________ |
| **Test Execution Date** | ____________________________________________________ |
| **Final Audit Verdict** | `[ ] ACCEPTED` &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; `[ ] NOT ACCEPTED` |
| **Authorized Signature** | ____________________________________________________ |

---

## 5. Post-Acceptance Transition Actions

When the sign-off block above is completed with a verdict of `ACCEPTED`:
1. Commit the evidence files into `Alex/docs/external-acceptance/A02/evidence/`.
2. Update Section H of [`Alex/docs/A02_COMPLETION_AUDIT.md`](../../A02_COMPLETION_AUDIT.md) to **`ACCEPTED`**.
3. Update [`Alex/docs/ACTION_MIGRATION_STATUS.md`](../../ACTION_MIGRATION_STATUS.md) and [`Alex/docs/FEATURE_MIGRATION_STATUS.md`](../../FEATURE_MIGRATION_STATUS.md) `computer_control` status to **`Complete`**.
4. Update [`Alex/docs/IMPLEMENTATION_ROADMAP.md`](../../IMPLEMENTATION_ROADMAP.md) to clear the A02 dependency barrier, unlocking Phase 1 work.

