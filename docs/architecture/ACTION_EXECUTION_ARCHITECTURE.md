# Action Execution Architecture & Tool Lifecycle

**Document Version:** 1.0  
**Inspection Date:** 2026-11-03  
**Status:** `ACTIVE_ARCHITECTURE_SPECIFICATION`  

---

## 1. Architectural Overview

The Action Execution Engine is the subsystem that empowers Alex to interact with the host operating system, analyze documents, drive browsers, execute code, and manage user preferences.

To maintain security, predictability, and user trust, the action engine enforces four foundational invariants:
1. **Empirical Verification:** A tool answers with what it observed rather than what it attempted.
2. **Standardized Five-Word Outcome Contract:** Every tool outcome maps strictly to one of five words (`done`, `unverified`, `failed`, `ask`, `started`).
3. **Safety & Human Confirmation Gating:** High-risk or irreversible operations (shutdown, restart, file deletion, computer control) require explicit human approval.
4. **Reversibility & Undo Logging:** State-changing file operations and system settings modifications push reversible records onto a multi-level undo stack.

```mermaid
graph TD
    subgraph "AI Model Dispatch"
        CALL["Model Function Call: name + arguments"]
    end

    subgraph "Action Discovery & Registry"
        REG["Action Registry (Builtins + Plugins)"]
        DECL["TOOL Dictionary Declaration<br>• name & description<br>• parameters schema (Pydantic)<br>• handler callable<br>• tier ('core' | 'extra')<br>• brief (short description)"]
        REG <--> DECL
    end

    CALL --> REG

    subgraph "Validation & Execution Lifecycle"
        SCHEMA_VAL["Pydantic Argument Validation"]
        RISK_GATE{"Risk Evaluation Gate"}
        CONFIRM["Human Confirmation Modal (UI)"]
        EXEC["Handler Execution via Signature Introspection"]
        VERIFY["Post-Execution Empirical OS Verification"]
        OUTCOME["Five-Word Outcome Categorization"]
        UNDO_LOG["Undo Stack Recording"]
    end

    REG --> SCHEMA_VAL
    SCHEMA_VAL --> RISK_GATE
    RISK_GATE -->|High Risk (Power, Control)| CONFIRM
    CONFIRM -->|User Approves| EXEC
    RISK_GATE -->|Low Risk (Read, Search)| EXEC
    EXEC --> VERIFY
    VERIFY --> OUTCOME
    OUTCOME --> UNDO_LOG

    subgraph "Model Return"
        RESULT["Structured ActionOutcomeResponse<br>status: done | unverified | failed | ask | started"]
    end

    OUTCOME --> RESULT
```

---

## 2. Standardized Five-Word Outcome Contract

In typical AI agents, tools report boolean return codes or generic status messages. This frequently causes the model to announce false successes (e.g. reporting "Opened Spotify" when the application failed to start or was never installed).

Alex enforces the **Five-Word Outcome Contract** across all action handlers:

| Outcome Word | Semantic Definition | Spoken Rule for Model |
| :--- | :--- | :--- |
| **`done`** | The operation completed successfully and its effect was **empirically observed** in the operating system (e.g. process verified in process table, volume verified via audio readback). | The model announces success normally. |
| **`unverified`** | The command was dispatched to the OS, but its outcome could not be verified (e.g. blind keystrokes sent to an external window). | **The model MUST NOT claim success.** It must explicitly state that the action was attempted but could not be confirmed. |
| **`failed`** | The operation did not execute or encountered an error. A detailed error reason is provided in the data payload. | The model explains the exact failure reason to the user. |
| **`ask`** | The operation was halted because taking action without user clarification would have been a destructive guess. | The model presents the question or confirmation prompt to the user. |
| **`started`** | A long-running asynchronous operation was initiated; the final outcome will arrive separately via an event or notification. | The model acknowledges that the operation has begun. |

---

## 3. Dynamic Action Discovery & Introspection Dispatch

Actions in Alex self-describe using a standardized `TOOL` dictionary:
```python
TOOL = {
    "name": "open_app",
    "description": "Opens an installed desktop application or raises its window if already running.",
    "parameters": OpenAppParams.model_json_schema(),
    "handler": open_app_handler,
    "tier": "core",           # "core" (always kept) or "extra" (culled on small models)
    "brief": "Launch or raise an application.", # Short description for 8B models
    "behavior": "BLOCKING",   # "BLOCKING" or "NON_BLOCKING"
    "scheduling": "WHEN_IDLE" # "WHEN_IDLE" | "SILENT" | "INTERRUPT"
}
```

### Signature Introspection & Dependency Injection
When `ActionExecutor` invokes a handler, it inspects the handler's signature using Python `inspect.signature()` and injects only the context objects requested by that specific handler:
- `parameters`: The validated Pydantic parameter model.
- `speak`: A callable allowing the action to speak an instant acknowledgment.
- `player`: The HUD media player controller.
- `session_memory`: Active in-memory session facts.

---

## 4. Multi-Level Undo Stack (`core/undo.py`)

Alex tracks state mutations so the user can say "Undo that" or click the Undo button in the HUD.

### Reversible Action Handlers:
1. **File Operations:**
   - When a file is created $\rightarrow$ undo deletes the created file.
   - When a file is renamed $\rightarrow$ undo restores the original filename.
   - When a file is moved $\rightarrow$ undo moves it back to source directory.
   - When a file is deleted $\rightarrow$ files are moved to OS Recycle Bin/Trash via `send2trash`, enabling full recovery.
2. **System Settings:**
   - When output volume is modified $\rightarrow$ undo restores the previous volume percentage.
   - When wallpaper is changed $\rightarrow$ undo restores the previous wallpaper path.

---

## 5. Dangerous Action Protection & Process Tree Immunity

To prevent the assistant from terminating itself, closing critical system services, or breaking active tests:
- **Process Immunity Guard:** Any tool that drives window closing (`close_app`) or process killing audits the target PID against a three-layer immunity check:
  1. Is the target PID equal to `os.getpid()` (the Alex backend sidecar)?
  2. Does the target PID belong to the parent process tree (the Unified Launcher or Electron shell)?
  3. Does the target executable share the same binary path as the active interpreter?
- If any check matches, the action is **immediately rejected with an error**: *"Refused to terminate the assistant's own process tree."*

