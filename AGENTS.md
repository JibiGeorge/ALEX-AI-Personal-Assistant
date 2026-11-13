# Project-Level AI Instructions: Alex AI Desktop Assistant

**Project Governance Model:** Personal Owner-Controlled Governance  
**Sole Decision-Maker:** Project Owner  
**Repository:** `ALEX-AI-main`  
**Application Version:** `0.1.0`  
**Baseline Snapshot:** `SNAPSHOT_v0.1.0-20261102`  

---

## 1. Project Ownership & Governance Mandate

1. **Personal Project:** Alex is a personal AI desktop assistant project owned, directed, and managed by a single project owner. It is not an enterprise or organization-managed project.
2. **Sole Authorization Authority:** The project owner is the sole final decision-maker for all architectural, implementation, release, and governance decisions.
3. **Zero External Approvals:** Do **NOT** introduce, require, or wait for external stakeholder approvals, approval committees, enterprise sign-off gates, or multi-person signatures (e.g., Technical Architect, Security Lead, QA Lead, Release Manager).
4. **Owner Direct Authorization:** The project owner authorizes work directly. Record authorization decisions and dates in [`docs/architecture/ARCHITECTURE_GOVERNANCE.md`](docs/architecture/ARCHITECTURE_GOVERNANCE.md).

---

## 2. Personal Project Status Lifecycle Model

All phases, tasks, and change requests must use the standard 8-state governance lifecycle:

| Status | Meaning | Permitted AI Action |
| :--- | :--- | :--- |
| `PLANNED` | Work is identified but technical specifications are not finalized. | Scoping, planning, analysis only. |
| `READY_FOR_IMPLEMENTATION` | Scope, technical approach, tests, and boundaries are fully defined. | Awaiting project owner authorization. |
| `OWNER_AUTHORIZED` | Project owner has explicitly authorized active development. | Begin active implementation of authorized scope. |
| `IN_PROGRESS` | Implementation is underway within the authorized scope. | Code modification within scope boundaries. |
| `TESTING` | Implementation complete; tests and verification underway. | Run automated tests, regression suites. |
| `COMPLETED` | Implementation and required verification are complete. | Document results, close phase gate. |
| `BLOCKED` | Work cannot proceed because of an identified blocker. | Report blocker, halt implementation. |
| `FROZEN` | Changes are prohibited unless owner authorizes an exception. | Strictly do NOT touch. Read-only. |

---

## 3. Phase Authorization Workflow

For every development phase, AI agents and engineers must adhere to the following 11-step process:

1. **Define Objectives & Scope:** Document target capabilities, boundaries, and deliverables.
2. **Identify Affected Components:** List all files to be created, modified, or tested.
3. **Document Implementation Boundaries:** Ensure isolation from frozen components.
4. **Identify Security & Compatibility Risks:** Document threat mitigations and platform portability.
5. **Define Acceptance Criteria:** Establish verifiable, objective test criteria.
6. **Set Status to `READY_FOR_IMPLEMENTATION`:** Stage specifications for owner review.
7. **Wait for Project Owner Authorization:** Do not implement until owner sets status to `OWNER_AUTHORIZED`.
8. **Implement Authorized Scope:** Implement only the defined scope without creep or unauthorized modifications.
9. **Run Relevant Tests:** Execute existing regression test suites and new unit/integration tests.
10. **Report Actual Results:** Report real test outputs, pass/fail counts, and remaining blockers honestly.
11. **Mark Phase `COMPLETED`:** Transition status to `COMPLETED` only after all acceptance criteria are proven satisfied.

---

## 4. Frozen Components & Invariants

The following components are marked `FROZEN` and must **NEVER** be modified without an explicit change authorization record approved by the project owner:

- **Milestone A02 Computer Control:** `backend/app/services/computer_control_service.py` (`FROZEN`)
- **Unified Launcher:** `launcher/cli.py` (`FROZEN`)
- **Electron Shell Main Process:** `frontend/electron/main.ts` (`FROZEN`)
- **Reference Codebase:** `Mark-LVI-main/` (`READ_ONLY` — strictly read-only reference prototype)

### Change Requests (CR-01, CR-02, CR-03)
- Proposed modifications to frozen files are documented in [`docs/planning/CHANGE_REQUESTS.md`](docs/planning/CHANGE_REQUESTS.md).
- They remain `FROZEN_PENDING_OWNER_EXCEPTION` and are NOT authorized by Phase 3 authorization.
- The project owner may personally authorize an exception for `CR-02` (Phase 4) or `CR-01` / `CR-03` (Phase 5).

---

## 5. Security & Privacy Invariants

1. **Zero Plaintext Secrets:** All API keys and credentials must be retrieved via `keyring_vault.py` (OS Keyring). Never persist secrets in JSON files, code, or logs.
2. **Private Reasoning Data Policy:** Raw internal reasoning (`<think>` tokens) must:
   - NEVER be exposed in the React HUD.
   - NEVER be sent to TTS or audio output.
   - NEVER be stored in primary conversation history.
   - NEVER be stored in a raw chain-of-thought persistence mechanism (e.g. `thought_log` is prohibited).
   - Only operational audit metadata (provider, model, latency, tokens, error category) may be retained.
3. **Tool Outcome Safety:**
   - Five outcomes: `DONE`, `UNVERIFIED`, `FAILED`, `ASK`, `STARTED`.
   - `STARTED` indicates asynchronous background execution and is **NEVER** interpreted as completed success (`success: bool == (status == ToolOutcome.DONE)`).

