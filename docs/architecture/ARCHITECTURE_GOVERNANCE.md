# Architecture Governance & Owner Authorization Register

**Document Version:** 2.0 (Personal Project Governance Transition)  
**Inspection Date:** 2026-11-03  
**Status:** `READY_FOR_IMPLEMENTATION`  
**Reference Review:** [`FORMAL_ARCHITECTURE_REVIEW.md`](FORMAL_ARCHITECTURE_REVIEW.md)  
**Target Milestone:** Phase 3 Authorization Entry Gate  
**Target Project:** `ALEX-AI-main` (Alex AI Desktop Assistant, Version `0.1.0`, Baseline Snapshot `SNAPSHOT_v0.1.0-20261102`)  
**Reference Codebase:** `Mark-LVI-main` (MARK LVI / 56)  
**Current Acceptance:** Physical Acceptance `0/33` (Environment Blocked)  
**Execution Authorization:** `BLOCKED_BY_ENVIRONMENT`  
**Production Release Status:** `NOT_AUTHORIZED_FOR_RELEASE`  

---

## 1. Personal Project Governance Model

Alex is a personal AI assistant project owned, directed, and managed by a single project owner.

### 1.1 Core Ownership Principles
1. **Single Project Owner:** The project owner is the sole final decision-maker for all architectural, implementation, release, and governance decisions.
2. **Zero External Bureaucracy:** No external stakeholder approvals, approval committees, enterprise sign-off gates, or multi-person signature registers are required.
3. **Engineering Integrity Preserved:** Removing external stakeholder sign-offs does not weaken engineering discipline, architectural rigour, code quality, or system safety. All Architecture Decision Records (ADRs), security controls, automated test suites, and audit trails remain strictly maintained.

### 1.2 Personal Project Status Lifecycle Model
Every phase, component, and change request is tracked under the following 8-state governance lifecycle:

| Status | Meaning |
| :--- | :--- |
| `PLANNED` | Work is identified and scoped conceptually, but technical specifications are not yet finalized. |
| `READY_FOR_IMPLEMENTATION` | Scope, technical contracts, interfaces, tests, and risks are fully defined and ready for owner authorization. |
| `OWNER_AUTHORIZED` | The project owner has explicitly authorized active development and implementation to commence. |
| `IN_PROGRESS` | Implementation and engineering work is actively underway within the authorized scope. |
| `TESTING` | Implementation is complete; automated tests, regression tests, and verification checks are underway. |
| `COMPLETED` | Implementation, test coverage, and all acceptance criteria are fully satisfied and documented. |
| `BLOCKED` | Work cannot proceed due to an identified technical, dependency, or environmental blocker. |
| `FROZEN` | Changes to the component are strictly prohibited unless the project owner explicitly authorizes a documented exception. |

### 1.3 Personal Phase Authorization Workflow
For every development phase, the project adheres to the following 11-step engineering process:
1. **Define Objectives & Scope:** Explicitly list target capabilities and deliverables.
2. **Identify Affected Components:** Detail all files to be created or modified.
3. **Document Implementation Boundaries:** Isolate changes from frozen components.
4. **Identify Security & Compatibility Risks:** Document threat mitigations and platform portability.
5. **Define Acceptance Criteria:** Establish verifiable, objective exit gates.
6. **Set Status to `READY_FOR_IMPLEMENTATION`:** Stage technical specifications for owner review.
7. **Await Project Owner Authorization:** Implementation may not commence until the owner sets status to `OWNER_AUTHORIZED`.
8. **Implement Authorized Scope:** Implement only the defined scope without creep or unauthorized modifications.
9. **Run Relevant Automated Tests:** Execute existing regression test suites and new unit/integration tests.
10. **Report Actual Results & Blockers:** Document test execution metrics, any test failures, and remaining blockers honestly.
11. **Mark Phase `COMPLETED`:** Transition status to `COMPLETED` only after all acceptance criteria are proven satisfied.

---

## 2. Architectural Decision Records (ADRs) Summary

All ten Architectural Decision Records in [`MIGRATION_DECISIONS.md`](../migration/MIGRATION_DECISIONS.md) have been formally validated against the technical criteria (*Correctness, Three-Tier Compatibility, Mark-LVI Parity, Security, Cross-Platform Support, Performance, Backward Compatibility, Testing*):

| ADR ID | Decision Title | Technical Review Verdict | Governance Status |
| :--- | :--- | :--- | :---: |
| **ADR-01** | Decoupled Three-Tier Architecture | Verified process isolation between Electron, React, and FastAPI. Sidecar watchdog auto-restart added to Phase 3 criteria. | `OWNER_APPROVED` |
| **ADR-02** | React 18 + Tailwind CSS Renderer | Verified reactive HUD. Avatar MediaPipe 3D mesh porting verified for Phase 4 using Canvas2D/WebGL (<5% CPU target). | `OWNER_APPROVED` |
| **ADR-03** | Electron Context Isolation & Preload | Verified `contextIsolation: true`, `nodeIntegration: false`. RCE vulnerability neutralized. | `OWNER_APPROVED` |
| **ADR-04** | Dynamic Loopback Bearer Authentication | Verified 32-byte ephemeral hex token. Loopback vs. LAN contradiction resolved via dual-gate authentication design. | `OWNER_APPROVED` |
| **ADR-05** | OS Keyring Vault Secret Storage | Verified complete elimination of plaintext JSON. Structured namespacing `alex-ai:<provider>` verified. | `OWNER_APPROVED` |
| **ADR-06** | Unified Process Supervisor CLI | Verified multi-process supervision and clean tree shutdown. Gated by CR-03 for POSIX paths. | `OWNER_APPROVED` |
| **ADR-07** | Standardized Outcome Contract | Verified 5-word contract (`done`, `unverified`, `failed`, `ask`, `started`) with Pydantic v2. `success` property strictly `DONE` (never True for `STARTED`). | `OWNER_APPROVED` |
| **ADR-08** | Cross-Platform HAL for OS Primitives | Verified swappable adapter design for windowing, audio, and TCC. Gated by CR-01 for Phase 5. | `OWNER_APPROVED` |
| **ADR-09** | Remote Mobile Companion Client Strategy | Verified encrypted LAN/TLS companion architecture; QR code PBKDF2 pairing without third-party cloud servers. | `OWNER_APPROVED` |
| **ADR-10** | Pluggable Local AI & Speech Fallback Stack | Verified offline resilience (Whisper + Piper + Ollama/LM Studio). Pre-flight doctor checks 3 GB RAM availability. | `OWNER_APPROVED` |

---

## 3. Frozen Components & Change Request (CR) Control

### 3.1 Frozen Components Invariant
The following components are marked `FROZEN` to preserve baseline stability and safety invariants:
- **Milestone A02 Computer Control Implementation (`backend/app/services/computer_control_service.py`):** `FROZEN`
- **Unified Launcher Implementation (`launcher/cli.py`):** `FROZEN`
- **Electron Shell Main Process (`frontend/electron/main.ts`):** `FROZEN`
- **Reference Codebase (`Mark-LVI-main`):** `READ_ONLY`

No engineer or agent may modify frozen components without an explicit Change Request authorized by the project owner.

### 3.2 Change Request Register
Proposed modifications to frozen components are formally analyzed in [`CHANGE_REQUESTS.md`](../planning/CHANGE_REQUESTS.md) and gated for future phases:

| CR ID | Target Component | Purpose & Scope | Target Phase | Status |
| :--- | :--- | :--- | :---: | :---: |
| **`CR-01`** | `computer_control_service.py` (L295–435) | Extract Win32 ctypes into swappable `WindowManagementAdapter` interface for macOS & Linux support. | Phase 5 | `FROZEN_PENDING_OWNER_EXCEPTION` |
| **`CR-02`** | `frontend/electron/main.ts` (L150–220) | Register `CommandOrControl+Space` global shortcut for system-wide push-to-talk. | Phase 4 | `FROZEN_PENDING_OWNER_EXCEPTION` |
| **`CR-03`** | `launcher/cli.py` (L120–180, L310–380) | Add POSIX virtualenv path detection (`bin/python`) and `.sh` build script execution for macOS & Linux. | Phase 5 | `FROZEN_PENDING_OWNER_EXCEPTION` |

> [!NOTE]
> **Owner Exception Rule:**  
> The project owner may personally authorize an exception to modify a frozen component by recording an explicit authorization decision prior to entering Phase 4 (`CR-02`) or Phase 5 (`CR-01`, `CR-03`). Phase 3 requires zero freeze exceptions.

---

## 4. Phase 3 Technical Scope & Readiness

### 4.1 Implementation Scope Verification
Review of implementation specifications in [`PHASE_3_IMPLEMENTATION_BREAKDOWN.md`](../planning/PHASE_3_IMPLEMENTATION_BREAKDOWN.md):

| Scope ID | Task Scope | Readiness Checklist & Technical Contract | Status |
| :--- | :--- | :--- | :---: |
| `TASK-P3-01` | Provider Abstraction (`base.py`, `registry.py`) | `LLMProvider` abstract base class, `ProviderCapabilities`, `StreamingChunk`, `UsageMetadata` (operational audit only), `NormalizedProviderError`. | `READY_FOR_IMPLEMENTATION` |
| `TASK-P3-02` | 9-Rung Model Fallback Ladder | Capability-aware fallback specified; runtime validation requirements documented; unsubstantiated quota-pool claims retracted. | `READY_FOR_IMPLEMENTATION` |
| `TASK-P3-03` | Ollama Local LLM (`127.0.0.1:11434`) | Loopback binding verified; model discovery via `/api/tags` specified; >=3GB RAM limit warnings mapped. | `READY_FOR_IMPLEMENTATION` |
| `TASK-P3-04` | LM Studio Local LLM (`127.0.0.1:1234`) | Loopback binding verified; streaming token parsing defined; first-token latency target <50ms. | `READY_FOR_IMPLEMENTATION` |
| `TASK-P3-05` | OpenAI-Compatible API Provider | Standard `/v1/chat/completions` client; streaming thought filter strips `<think>` tokens; strict private reasoning data policy enforced. | `READY_FOR_IMPLEMENTATION` |
| `TASK-P3-06` | Cloud Providers (Groq & DeepSeek) | Keyring secret storage verified; rate-limit fallback mapped to Model Ladder. | `READY_FOR_IMPLEMENTATION` |
| `TASK-P3-07` | Dynamic Tool Budgeting Engine | Dual budgeting (clamped to 9,000 chars and max 12 tools for 8B models) verified; priority ranking defined. | `READY_FOR_IMPLEMENTATION` |
| `TASK-P3-08` | Five-Word Outcome Contract | `ToolOutcome` enum (`done`, `unverified`, `failed`, `ask`, `started`) defined; `success: bool` returns True ONLY for `DONE` (`STARTED` is never completed success). | `READY_FOR_IMPLEMENTATION` |
| `TASK-P3-09` | Deep Document Parsing Action | PDF, DOCX, XLSX, PPTX parsers specified; 25 MB file size and workspace sandboxing verified. | `READY_FOR_IMPLEMENTATION` |

---

### 4.2 Model Ladder Validation Requirements & Quota Policy
1. **Policy: No Unsubstantiated Quota-Pool Independence Claims:**
   - Do not claim model availability or quota-pool independence without empirical evidence.
   - Models within the same Google Gemini provider share API project quota, billing tier limits, and organizational rate limits (RPM/TPM/RPD) unless proven isolated via multi-tenant runtime telemetry.
   - If project-wide quota depletion occurs, falling back to other models under the same provider key will fail with repeated 429 errors; the ladder must detect provider-level quota exhaustion and prioritize cross-provider cloud (Groq/DeepSeek) or local offline inference (Ollama/LM Studio).
2. **Capability-Aware Fallback Selection:**
   - Fallback candidate selection must dynamically match the *Capability Profile* required by the active turn:
     - `requires_live_audio`: Full-duplex live audio stream (`/api/v1/voice/live`) requires models declaring `live_bidirectional` or native audio. If live audio models are exhausted, the system cannot drop into a text-only REST model without triggering the Speech Adapter Handshake (Faster-Whisper STT + Piper TTS) to preserve spoken conversation.
     - `requires_tools`: Models must declare verified function calling support (`capabilities.function_calling is True`). Models lacking function-calling capabilities or unable to parse budgeted schemas must be excluded from candidate filtering.
     - `requires_streaming`: SSE / WebSocket chunking must be supported.
     - `requires_vision`: Turns containing image or screen frames require `capabilities.vision is True`.
3. **Explicit Runtime Validation Requirements:**
   - **Model Availability:** Probed at startup via `list_models()` / `/v1/models` (cached 6 hours); 404 sets cooldown to 6 hours.
   - **Provider Authentication:** Probed via lightweight credential ping using OS Keyring. If HTTP 401/403 is received, the provider is marked `AUTHENTICATION_FAILED`. This is fatal for all models under that credential; the ladder bypasses all rungs under that provider without attempting subsequent models with the same broken key.
   - **Streaming Support:** Validated during session handshake (<1,500ms initial chunk latency).
   - **Tool-Calling Compatibility:** Verified against declared tool schema dialects (Gemini vs. OpenAI) and schema budget constraints (`TASK-P3-07`).
   - **Multimodal / Audio Capabilities:** Verified against declared provider capabilities.
   - **Quota & Rate-Limit Behavior:** Inspect HTTP 429 response headers (`Retry-After`, `x-ratelimit-reset`). Detect project-wide vs. model-specific limits.
   - **Provider-Specific Cooldowns:** Dynamic tracker maintaining state per (provider, model):
     - 429: Provider-specified `Retry-After` if present, else default 300s.
     - 404: 21,600s (6h).
     - 500/502/503/504: 1,800s (30m) with 1 immediate backoff retry (1.0s).
     - 401/403: Quarantined indefinitely until user updates API keys in settings.
   - **Conversation Continuity During Fallback:** Normalized conversation history transferred across provider dialects; in-flight partial output discarded; maximum 3 hops per turn; non-disruptive telemetry emitted to frontend.
4. **Flagged Runtime Model Assumptions:**
   - `models/gemini-3.1-flash-live-preview`: Preview model tag from Mark-LVI prototype. **FLAGGED:** Must be dynamically probed via live WebSocket handshake at runtime; if unverified or unavailable, the ladder must advance cleanly to verified rungs without failing session establishment. Do NOT silently delete or replace.
   - `models/gemini-2.5-flash-native-audio-preview-12-2025`: Date-versioned snapshot (`preview-12-2025`). **FLAGGED:** Subject to vendor deprecation and retirement. Provider registry must probe model availability before hardcoding.
   - `groq:llama-3.3-70b-versatile` & `deepseek:deepseek-chat`: Cloud provider endpoint IDs. **FLAGGED:** Rely on external provider service availability, valid user API keys retrieved strictly from OS Keyring (`keyring_vault.py`), and unblocked outbound network egress.
   - `ollama:llama3.2:3b` & `lm_studio:local-model`: Local inference servers (`127.0.0.1:11434` and `127.0.0.1:1234`). **FLAGGED:** Assumes local daemon is running and model weights are pre-pulled; requires $\ge$ 3 GB available host RAM to prevent system thrashing.

---

### 4.3 Private Reasoning Data Policy
In accordance with system security and privacy requirements, the following policies are strictly enforced for internal reasoning tokens (`<think>`):
1. **No HUD Exposure:** Raw internal reasoning must **NEVER** be exposed in the React HUD (neither in the chat transcript nor in collapsible disclosure widgets).
2. **No Audio/TTS Output:** Raw internal reasoning must **NEVER** be sent to TTS or audio output. `reasoning_filter.py` intercepts chunks across token boundaries and strips all reasoning blocks before speech synthesis.
3. **No History Inclusion:** Raw internal reasoning must **NOT** be included in primary conversation history (`ConversationMessage.content`).
4. **Prohibition of Raw Chain-of-Thought Persistence:** Do **NOT** introduce a raw chain-of-thought persistence mechanism such as `thought_log`. Persisting internal model reasoning blocks on disk or in database records is strictly prohibited.
5. **Operational Audit Metadata Only:** The system retains **ONLY** structured operational audit metadata:
   - Provider identifier (`provider_id`)
   - Model identifier (`model_id`)
   - Execution latency (`latency_ms`)
   - Token usage (`prompt_tokens`, `completion_tokens`, `total_tokens`)
   - Fallback reason (`fallback_reason`)
   - Tool invocation name (`tool_invocation`)
   - Tool outcome status (`tool_outcome`)
   - Error category (`error_category`)

---

### 4.4 Tool Outcome Compatibility & `STARTED` Handling
To prevent dangerous scenarios where background or unverified actions are prematurely reported as complete:
1. **Preserve the Five Outcomes:**
   - `ToolOutcome.DONE`: Action verified to have completed successfully.
   - `ToolOutcome.UNVERIFIED`: Request initiated, but state could not be verified.
   - `ToolOutcome.FAILED`: Action could not be completed.
   - `ToolOutcome.ASK`: Requires user clarification or approval.
   - `ToolOutcome.STARTED`: Asynchronous process initiated cleanly; currently running in the background.
2. **`STARTED` Is Never Completed Success:**
   - The backward-compatibility property `success: bool` evaluates to `True` **ONLY** when `status == ToolOutcome.DONE`.
   - `success` returns `False` for `STARTED`, `UNVERIFIED`, `FAILED`, and `ASK`.
3. **Explicit State Inspection Properties:**
   - `is_done: bool` $\rightarrow$ `self.status == ToolOutcome.DONE` (verified completion).
   - `is_started: bool` $\rightarrow$ `self.status == ToolOutcome.STARTED` (operation running in background).
   - `is_pending: bool` $\rightarrow$ `self.status in (ToolOutcome.STARTED, ToolOutcome.UNVERIFIED)` (non-terminal).
   - `requires_clarification: bool` $\rightarrow$ `self.status == ToolOutcome.ASK` (interactive input needed).
   - `is_failed: bool` $\rightarrow$ `self.status == ToolOutcome.FAILED` (execution error).
4. **How Existing Callers Distinguish Completed vs. Running Operations:**
   - **Synchronous Callers & Tests:** Checking `response.success` evaluates to `True` strictly when the operation reached verified completion (`DONE`). If an action returns `STARTED`, `success` is `False`, ensuring existing sync callers do not mistake a running operation for a finished one.
   - **Asynchronous Callers & Supervisors:** Inspect `response.status == ToolOutcome.STARTED` (or `response.is_started`). The tracking metadata in `data` (`job_id`, `pid`, or `task_token`) is used to await/poll completion events via WebSocket (`/api/v1/jobs/{job_id}/events`).
   - **LLM Orchestration Layer:** Prompts strictly instruct the model that `STARTED` means an asynchronous task is running in the background and must **NOT** be reported as finished or successful.
   - **Preserve Safety:** Does not weaken existing safety bounds, coordinate clamping, or confirmation gates.

---

## 5. Project Owner Authorization Record

This register records the direct authorization decisions made by the project owner.

### Phase 3 Authorization Entry Gate
- **Target Phase:** Phase 3 — Core AI Providers & Operational Actions (`TASK-P3-01` through `TASK-P3-09`)
- **Authorization Authority:** Project Owner (Sole Decision-Maker)
- **Current Technical Status:** `OWNER_AUTHORIZED`
- **Owner Decision:** `[X] OWNER_AUTHORIZED`
- **Authorization Date:** `2026-11-03`
- **Authorized Scope:**
  - `TASK-P3-01`: Provider Abstraction Layer (`backend/app/providers/base.py`, `registry.py`)
  - `TASK-P3-02`: Nine-Rung Model Fallback Ladder (`backend/app/services/model_ladder_service.py`)
  - `TASK-P3-03`: Ollama Local LLM Integration (`backend/app/providers/ollama_provider.py`)
  - `TASK-P3-04`: LM Studio Local LLM Integration (`backend/app/providers/lm_studio_provider.py`)
  - `TASK-P3-05`: OpenAI-Compatible API Provider (`backend/app/providers/openai_provider.py`, `reasoning_filter.py`)
  - `TASK-P3-06`: Cloud Providers Integration (`groq_provider.py`, `deepseek_provider.py`)
  - `TASK-P3-07`: Dynamic Tool Budgeting Engine (`backend/app/providers/schema_budget.py`)
  - `TASK-P3-08`: Standardized Five-Word Outcome Contract (`backend/app/actions/base.py`)
  - `TASK-P3-09`: Deep Document Parsing Action (`backend/app/actions/builtins/documents.py`)
- **Directives & Conditions:**
  - Preserves frozen components: `computer_control_service.py`, `launcher/cli.py`, `main.ts`.
  - Phase 3 does not modify frozen files and requires zero freeze exceptions.
  - Implement scopes sequentially according to the priority ladder, starting with `TASK-P3-01`.

---

## 6. Current Project Restrictions & Governance Invariants

The following technical restrictions remain active and are preserved under owner-controlled governance:

1. **Frozen Components:**
   - Milestone A02 Computer Control (`computer_control_service.py`): `FROZEN`
   - Unified Launcher (`launcher/cli.py`): `FROZEN`
   - Electron Shell Main Process (`frontend/electron/main.ts`): `FROZEN`
2. **Reference Project Integrity:**
   - `Mark-LVI-main/` remains strictly `READ_ONLY`.
3. **Change Requests Separation:**
   - `CR-01`, `CR-02`, and `CR-03` remain separate change requests requiring explicit owner authorization records prior to Phase 4 or Phase 5.
4. **Physical Acceptance & Environment:**
   - Physical acceptance testing remains `0/33` (environment-blocked).
   - Execution authorization remains `BLOCKED_BY_ENVIRONMENT`.
   - Production release remains `NOT_AUTHORIZED_FOR_RELEASE`.
   - Application version `0.1.0` and snapshot `SNAPSHOT_v0.1.0-20261102` remain unchanged.

