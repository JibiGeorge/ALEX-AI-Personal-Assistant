# Alex Desktop Assistant — Security Architecture & Policy Guide

**Document Version:** 1.0  
**Last Updated:** 2026-11-03  
**Status:** Authoritative Security Specification  
**Cross-References:** [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md), [`../architecture/SYSTEM_FLOW.md`](../architecture/SYSTEM_FLOW.md), [`../api/API_REFERENCE.md`](../api/API_REFERENCE.md)

---

## 1. Security Architecture Overview

Alex enforces a defense-in-depth security model across its three execution tiers:
1. **Unprivileged Renderer Tier:** React UI isolated in a sandboxed WebContents.
2. **Desktop Broker Tier:** Electron main process enforcing origin validation and IPC allowlisting.
3. **Privileged Backend Tier:** Python sidecar enforcing token authentication, filesystem sandboxing, and safety watchdogs.

```text
+---------------------------------------------------------------------------------------+
|                                SECURITY TRUST BOUNDARIES                              |
+---------------------------------------------------------------------------------------+
|  [UNTRUSTED] React Renderer                                                           |
|    - nodeIntegration: false, contextIsolation: true                                   |
|    - Strict Content Security Policy (CSP)                                             |
|         │                                                                             |
|         ▼ (Allowlisted window.alex ContextBridge IPC)                                 |
|  [BROKER] Electron Main Process                                                       |
|    - Origin checking: isAllowedDevOrigin (127.0.0.1:5173 only)                        |
|    - IPC sender validation & protocol gating                                          |
|    - Generates 32-byte cryptographically secure random bearer token                   |
|         │                                                                             |
|         ▼ (Authenticated Loopback HTTP / WebSocket: 127.0.0.1 only)                   |
|  [PRIVILEGED] Python / FastAPI Sidecar                                                |
|    - Constant-time HMAC bearer token comparison on all requests                       |
|    - OS Credential Manager integration (keyring) — zero plaintext secrets             |
|    - Private workspace sandboxing & symlink/traversal rejection                       |
|    - Computer Control safety subsystem: 5 gates, emergency stop, 12s watchdog        |
+---------------------------------------------------------------------------------------+
```

---

## 2. Desktop Shell & IPC Hardening

### A. Context Isolation & Node Integration
The Electron BrowserWindow is configured with strict isolation:
```typescript
webPreferences: {
  nodeIntegration: false,
  contextIsolation: true,
  sandbox: true,
  preload: path.join(__dirname, "preload.js")
}
```
The renderer cannot access `process`, `require`, `fs`, `child_process`, or Node.js internal modules.

### B. Typed Preload Facade
The preload script exposes only explicit, allowlisted methods via `contextBridge.exposeInMainWorld("alex", ...)`:
- No generic `ipcRenderer.send` or event listener hooks are exposed to the DOM.
- Every IPC handler in `main.ts` validates `event.senderFrame` origin before dispatch.

### C. Origin & Navigation Hardening
Renderer navigation is guarded by strict origin allowlists in `main.ts`:
- **Development:** `isAllowedDevOrigin` accepts only `http://127.0.0.1:5173/` or `http://localhost:5173/`.
- **Production:** Accepts only canonical packaged file URLs (`file://.../dist/index.html`).
- External hyperlinks (`target="_blank"` or clicked URLs) are intercepted and opened in the user's default browser via `shell.openExternal`, never inside the Electron window.

---

## 3. Sidecar Authentication & Network Security

### A. Loopback Binding Only
The FastAPI sidecar binds exclusively to IPv4 loopback (`127.0.0.1`). It never binds to `0.0.0.0` or external network interfaces, preventing remote network access.

### B. Per-Run Bearer Token Authentication
At startup, Electron generates a 32-byte cryptographically secure random token (`ALEX_API_TOKEN`) and injects it into the backend environment.
- Every HTTP request must supply `Authorization: Bearer <token>`.
- Every WebSocket connection must supply `?token=<token>`.
- The FastAPI middleware validates the token using constant-time comparison (`secrets.compare_digest`) to prevent timing side-channel attacks. Unauthenticated requests return `HTTP 401 Unauthorized`.

### C. Bearer Token Masking
Bearer tokens are strictly masked to `****` in terminal outputs, `--json` status outputs, and application logs. Plaintext tokens are never written to disk or logged.

---

## 4. Credential Management (Zero Plaintext Secrets)

Alex integrates with the OS Credential Manager via the Python `keyring` library:
- **Windows:** Windows Credential Manager (`win32cred`).
- **macOS:** Apple Keychain.
- **Linux:** SecretService API.

### Credential Handling Rules:
1. Google Gemini API keys are retrieved on demand from `keyring.get_password("alex", "gemini_api_key")`.
2. API keys are **never** returned in GET API responses (routes return `{configured: true/false}`).
3. API keys are **never** written to git repositories, test logs, screenshots, or error traces.
4. If keyring is unavailable, keys are not silently written to plaintext config files.

---

## 5. Milestone A02 Computer Control Safety Invariants (FROZEN)

The Computer Control safety subsystem ([`backend/app/services/computer_control_service.py`](../../backend/app/services/computer_control_service.py)) is under a permanent governance freeze and enforces:

1. **Master Session Permission Gate:** Default state is strictly **OFF**. All automation actions return `HTTP 403 Forbidden` until explicitly enabled by the human operator via the UI toggle.
2. **Queue Cap:** Maximum of 5 pending proposals in the queue at any time.
3. **Five-Minute Proposal TTL:** Proposals auto-expire after 300 seconds (5 minutes). Expired proposals cannot be executed.
4. **One-Shot Execution Token:** Each proposal receives a single-use token consumed upon execution. Replay attempts are rejected.
5. **Coordinate & Display Bounds Validation:** Coordinates must reside strictly within primary monitor bounds (e.g. `0 <= x <= 1920`, `0 <= y <= 1080`). Negative or out-of-screen coordinates are rejected.
6. **Hotkey Whitelist Enforcement:** Only a finite whitelist of safe keys and modifier combinations is permitted. Arbitrary system chord injection is blocked.
7. **Text Injection Cap:** Typed strings are capped at 2,000 characters; control characters are sanitized.
8. **Latched Emergency Stop:** Emergency Stop flushes all pending proposals, aborts active execution, and latches into an emergency state requiring manual UI re-arming.
9. **12-Second Execution Watchdog:** Any automation action running longer than 12 seconds is forcibly terminated.
10. **Win32 Process Ancestry Protection:** Polite `WM_CLOSE` termination checks process PID trees, shielding Alex and its parent launcher from termination.

---

## 6. Filesystem Sandboxing & Scoped Workspace

The workspace filesystem manager ([`backend/app/services/file_workspace_service.py`](../../backend/app/services/file_workspace_service.py)) enforces:
- **Private Sandbox:** All file operations are confined strictly to `data_dir/workspace`.
- **Path Traversal Defense:** `..` directory traversal sequences and absolute root escapes are rejected with `HTTP 400 Bad Request`.
- **Symlink & Hardlink Rejection:** Symlinks and hardlinks targeting outside the workspace are rejected.
- **Ten-Entry Undo Journal:** Bounded 10-entry rollback journal for reversible workspace file operations.

---

## 7. Compliance & Enterprise Security Boundary

- **Zero AppLocker / Policy Bypasses:** Alex strictly forbids bypassing corporate Active Directory Group Policy Objects, AppLocker, or Software Restriction Policies.
- **Honest Environmental Halting:** When operating on restricted enterprise hosts, testing cleanly stops under `BLOCKED_BY_ENVIRONMENT`. No administrative workarounds or privilege escalation scripts are permitted.
