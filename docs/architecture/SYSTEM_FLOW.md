# Alex Desktop Assistant — System Execution & Data Flow

**Document Version:** 1.0  
**Last Updated:** 2026-11-03  
**Status:** Authoritative Architecture Reference  
**Cross-References:** [`ARCHITECTURE.md`](./ARCHITECTURE.md), [`../security/SECURITY.md`](../security/SECURITY.md), [`../api/API_REFERENCE.md`](../api/API_REFERENCE.md)

---

## 1. Overview

This document specifies the end-to-end runtime lifecycle, process execution flow, data pathways, and safety gating mechanisms of the Alex AI Desktop Assistant.

```mermaid
flowchart TD
    subgraph UI ["Frontend Renderer (React + TypeScript)"]
        HUD["HUD Avatar & Telemetry"]
        Chat["Conversation & Attachments"]
        ActionUI["Actions Panel & Forms"]
        ControlUI["Computer Control Drawer"]
    end

    subgraph Shell ["Desktop Shell (Electron)"]
        Preload["Preload ContextBridge (window.alex)"]
        MainProcess["Electron Main Process"]
    end

    subgraph Sidecar ["Backend Sidecar (Python FastAPI)"]
        AuthMiddleware["HMAC Bearer Token Auth"]
        ActionReg["Action Registry & Executor"]
        CtrlService["Computer Control Service (FROZEN)"]
        LiveService["Gemini Live Voice Service"]
        Storage["Atomic JSON Storage & Keyring"]
    end

    UI -->|"Typed IPC"| Preload
    Preload -->|"IPC Channels"| MainProcess
    MainProcess -->|"Loopback HTTP / WS (127.0.0.1)"| AuthMiddleware
    AuthMiddleware --> ActionReg
    AuthMiddleware --> CtrlService
    AuthMiddleware --> LiveService
    AuthMiddleware --> Storage
```

---

## 2. Unified Startup Orchestration Flow

The Unified Application Launcher (`alex launch` / `python -m launcher.cli launch`) enforces a health-gated sequential startup sequence to eliminate startup race conditions between tiers:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Shell
    participant Launcher as Unified Launcher CLI
    participant Backend as Python FastAPI Sidecar
    participant Frontend as Vite Dev Server
    participant Electron as Electron Desktop Shell

    User->>Launcher: alex launch
    Launcher->>Launcher: 1. Validate dependencies (Python 3.11+, Node 20+, npm)
    Launcher->>Launcher: 2. Check loopback ports (8765, 5173); reassign if occupied
    Launcher->>Backend: 3. Spawn Backend with per-run random bearer token
    loop Health Polling (up to 20s)
        Launcher->>Backend: GET http://127.0.0.1:8765/api/v1/health
        Backend-->>Launcher: HTTP 200 {status: "ok"}
    end
    Launcher->>Frontend: 4. Spawn Vite Dev Server (http://127.0.0.1:5173)
    loop Web Polling (up to 30s)
        Launcher->>Frontend: HTTP GET http://127.0.0.1:5173
        Frontend-->>Launcher: HTTP 200 OK
    end
    Launcher->>Electron: 5. Spawn Electron Window with ALEX_API_TOKEN & Ports
    Electron->>Preload: Inject window.alex contextBridge
    Launcher->>Launcher: 6. Persist PIDs, ports, and tokens to %APPDATA%/Alex/runtime.json
    Launcher-->>User: Startup Complete (Monitoring active child processes)
```

### Port Conflict Resilience
If default ports (`8765` or `5173`) are occupied, the launcher automatically scans for the next available ephemeral port, updates process arguments dynamically, and passes the resolved ports to Electron without failing startup.

### Process State Persistence
Process PIDs, assigned ports, and bearer token masks are stored in `runtime.json` under the platform user data directory (`%APPDATA%/Alex/runtime.json` on Windows, `~/.alex/runtime.json` on macOS/Linux). On launch, stale PIDs from previous crashed sessions are detected and purged.

---

## 3. Coordinated Graceful Shutdown Flow

When `alex stop`, window close, or `Ctrl+C` is received, the supervisor executes coordinated teardown:

1. **SIGTERM to Electron Shell:** Electron closes all BrowserWindow instances, flushes window state, and exits.
2. **SIGTERM to Frontend Server:** Vite development server terminates.
3. **Graceful Backend Shutdown:** FastAPI receives `SIGTERM`, triggers `@app.on_event("shutdown")`, commits in-flight atomic file writes, closes active WebSockets, and exits.
4. **Port Release Verification:** Launcher verifies loopback ports are freed within 10 seconds.
5. **Runtime State Cleanup:** `runtime.json` is safely unlinked or marked inactive.

---

## 4. Action Execution Flow

Privileged actions in Alex are strictly typed, allowlisted, and decoupled from arbitrary shell execution:

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Operator
    participant UI as React UI (Actions Page)
    participant Preload as window.alex Facade
    participant Main as Electron Main
    participant API as FastAPI Sidecar
    participant Executor as ActionExecutor

    User->>UI: Select Action & Fill Parameters
    UI->>Preload: window.alex.executeAction(actionId, params)
    Preload->>Main: IPC 'execute-action' (Sender Validated)
    Main->>Main: Validate Origin (localDevUrl / prodFile)
    Main->>API: POST /api/v1/actions/{id}/execute (HMAC Bearer Token)
    API->>Executor: Lookup Action Schema & Validate Types
    alt Requires Confirmation
        Executor-->>UI: Return Confirmation Prompt
        User->>UI: Click Explicit "Approve"
        UI->>API: POST /api/v1/actions/{id}/confirm
    end
    Executor->>Executor: Execute Concrete Handler (with Watchdog)
    Executor-->>API: Return Structured Result
    API-->>Main: HTTP 200 JSON
    Main-->>Preload: IPC Reply
    Preload-->>UI: Display Result in Actions History
```

### Action Dispatch Constraints:
- **Max 4 Executions Per Turn:** Prevents model runaway loops during multi-action tasks.
- **Pydantic Type Enforcement:** Parameters must validate against JSON schemas before dispatch.
- **Execution Watchdog:** Unresponsive handlers are cancelled after timeout (default 12 seconds).

---

## 5. Milestone A02 Computer Control Safety Gating (FROZEN)

The Computer Control subsystem ([`backend/app/services/computer_control_service.py`](../../backend/app/services/computer_control_service.py)) enforces 5 non-negotiable safety gates:

```mermaid
flowchart TD
    Proposal["AI Proposal Created<br/>(coordinate, key, or click)"] --> Gate1{"Gate 1: Master Session<br/>Permission Toggle ON?"}
    Gate1 -- No --> Reject1["Reject: HTTP 403 Forbidden"]
    Gate1 -- Yes --> Gate2{"Gate 2: Queue Cap<br/>(<= 5 proposals)?"}
    Gate2 -- No --> Reject2["Reject: Queue Full"]
    Gate2 -- Yes --> Gate3{"Gate 3: Within 5-Minute<br/>Expiry Window?"}
    Gate3 -- No --> Reject3["Reject: Proposal Expired"]
    Gate3 -- Yes --> Gate4{"Gate 4: Explicit Human<br/>One-Shot Approval?"}
    Gate4 -- No --> Reject4["Reject: Unapproved"]
    Gate4 -- Yes --> Gate5{"Gate 5: Primary Display<br/>Bounds Valid (1920x1080)?"}
    Gate5 -- No --> Reject5["Reject: Out of Bounds"]
    Gate5 -- Yes --> Execution["Execute via Win32 / PyAutoGUI<br/>(12s Watchdog Active)"]
    Execution --> Flush["Consume One-Shot Token<br/>(Replay Rejected)"]
```

### Latched Emergency Stop
Pressing the Emergency Stop button in the UI:
1. Immediately flushes all queued and pending proposals.
2. Forcibly aborts any active action at the next safe boundary.
3. Sets a **latched emergency state** that rejects all subsequent actions until explicitly re-armed by manual user action.

---

## 6. Gemini Live AI Voice Streaming Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Operator
    participant Mic as Physical Microphone (16kHz PCM)
    participant UI as React UI (Audio Visualizer)
    participant Bridge as Local Voice Service (WebSocket)
    participant Gemini as Google Gemini Live API
    participant Speaker as Stereo Playback (24kHz)

    User->>Mic: Speak Spoken Turn
    Mic->>Bridge: Stream 16kHz PCM Audio Packets
    Bridge->>Gemini: Upstream WebSocket Audio Stream
    Gemini-->>Bridge: Downstream 24kHz Audio Response
    Bridge->>Speaker: Play Spoken Audio
    Bridge->>UI: Stream Waveform Data for HUD Avatar Animation
    opt User Interrupts (Barge-In)
        User->>Mic: Speak during assistant output
        Mic->>Bridge: Detect incoming audio during playback
        Bridge->>Speaker: Immediately silence playback buffer
        Bridge->>Gemini: Send barge-in interrupt signal
    end
```
