# Alex Desktop Assistant — API & IPC Reference

**Document Version:** 1.0  
**Last Updated:** 2026-11-03  
**Status:** Authoritative Interface Reference  
**Cross-References:** [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md), [`../security/SECURITY.md`](../security/SECURITY.md)

---

## 1. Overview & Authentication

Alex provides two primary interface layers:
1. **Authenticated Loopback REST & WebSocket API:** Hosted by the Python FastAPI sidecar on `127.0.0.1:8765`.
2. **Typed Electron Preload IPC Bridge:** Exposed to the React renderer via `window.alex`.

### Sidecar Authentication
All REST endpoints require the HTTP Authorization header:
```http
Authorization: Bearer <ALEX_API_TOKEN>
```
WebSocket endpoints require the token as a query parameter:
```text
ws://127.0.0.1:8765/api/v1/voice/live?token=<ALEX_API_TOKEN>
```
Unauthenticated or invalid requests return `HTTP 401 Unauthorized`.

---

## 2. System & Platform Endpoints

### `GET /api/v1/health`
Health check endpoint used by the Unified Launcher startup orchestrator.
- **Auth:** Not required (open on loopback).
- **Response:**
  ```json
  {
    "status": "ok",
    "version": "0.1.0",
    "timestamp": "2026-11-03T12:00:00Z"
  }
  ```

### `GET /api/v1/system/metrics`
Retrieves live hardware telemetry from `psutil`.
- **Response:**
  ```json
  {
    "cpu_percent": 12.4,
    "memory_percent": 48.2,
    "memory_used_mb": 7820,
    "memory_total_mb": 16384,
    "network_sent_kbps": 14.2,
    "network_recv_kbps": 82.5,
    "uptime_seconds": 18420,
    "process_count": 240
  }
  ```

### `GET /api/v1/system/alerts`
Returns active threshold alerts (CPU >90%, RAM >90%, GPU >95%, Temp >85°C) with cooldown state.

### `GET /api/v1/platform/capabilities`
Reports honest platform capability matrix (Win32 window controls, screen capture, audio devices, Gemini Live readiness).

### `GET /api/v1/briefing`
Returns structured proactive startup briefing aggregating greeting, identity memories, pending reminders, and hardware status.

---

## 3. Settings & Credentials Endpoints

### `GET /api/v1/settings`
Retrieves user preferences and credential configuration status.
- **Security Invariant:** Never returns stored API keys.
- **Response:**
  ```json
  {
    "assistant_name": "Alex",
    "user_name": "Operator",
    "accent_color": "#00f0ff",
    "voice_name": "Aoede",
    "hud_style": "avatar",
    "gemini_api_key_configured": true
  }
  ```

### `PUT /api/v1/settings`
Updates preferences and securely stores API key in the OS Credential Manager via `keyring`.

---

## 4. Categorized Memory Endpoints

Alex organizes persistent facts across 6 fixed categories: `identity`, `preferences`, `projects`, `relationships`, `wishes`, and `notes`.

- `GET /api/v1/memory`: List all memories grouped by category.
- `GET /api/v1/memory/{category}`: List facts in a specific category.
- `POST /api/v1/memory`: Upsert a key-value fact (`{category, key, value}`).
- `DELETE /api/v1/memory/{category}/{key}`: Delete a specific memory fact.
- `GET /api/v1/memory/search?q={query}`: Case-insensitive relevance-scored search across keys and values.

---

## 5. Desktop Reminders Endpoints

- `GET /api/v1/reminders`: List all pending and due reminders.
- `POST /api/v1/reminders`: Create a reminder with target ISO datetime and message.
- `DELETE /api/v1/reminders/{id}`: Cancel a pending reminder.
- `POST /api/v1/reminders/{id}/acknowledge`: Mark a reminder delivered with active user acknowledgment.

---

## 6. Actions Registry Endpoints

- `GET /api/v1/actions`: Discover registered typed actions with Pydantic JSON schemas.
- `POST /api/v1/actions/{id}/execute`: Execute action with validated arguments. Max 4 executions per turn.

### Key Builtin Action Contracts
- `vision.capture`: Acquires desktop screenshots (source: `"screen"`) or live webcam frames (source: `"camera"` via OpenCV `cv2`). Supports optional base64 encoding (`include_base64: true`) or direct filesystem persistence (`output_path`).
- `files.*`: Scoped private workspace filesystem CRUD with 10-entry rollback journal.
- `system.*`: Telemetry and hardware state introspection.

---

## 7. Computer Control Endpoints (FROZEN)

Subsystem enforces the 5 mandatory safety gates:
- `GET /api/v1/computer-control/state`: Returns session toggle state (`true`/`false`), active queue, and emergency stop latch status.
- `POST /api/v1/computer-control/permission`: Toggle master session permission (default `false`).
- `POST /api/v1/computer-control/proposals/{id}/approve`: Explicit human one-shot approval of a pending proposal.
- `POST /api/v1/computer-control/proposals/{id}/reject`: Reject and purge a pending proposal.
- `POST /api/v1/computer-control/emergency-stop`: Immediate abort, queue flush, and emergency state latch.
- `POST /api/v1/computer-control/re-arm`: Manual operator re-arming after emergency stop.

---

## 8. Gemini Live Streaming WebSocket

### `WS /api/v1/voice/live?token=<TOKEN>`
Establishes bidirectional real-time audio pipeline:
- **Client -> Server:** 16 kHz 16-bit mono PCM audio packets or typed text turns.
- **Server -> Client:** 24 kHz audio chunks, waveform visualization data, and mid-stream tool call proposal cards.
- **Barge-In:** Server detects client audio during assistant speech and immediately silences downstream audio output.

---

## 9. Electron Preload IPC Bridge (`window.alex`)

The renderer accesses desktop capabilities strictly through the typed `window.alex` object:

```typescript
interface AlexBridge {
  executeAction(actionId: string, params: Record<string, unknown>): Promise<ActionResult>;
  openExternal(url: string): Promise<void>;
  getScreenSources(): Promise<DesktopCapturerSource[]>;
  captureScreen(sourceId: string): Promise<string>; // returns base64 thumbnail
  getPlatform(): Promise<"win32" | "darwin" | "linux">;
  createShortcut(): Promise<{ success: boolean; path?: string }>;
  setLoginItem(enabled: boolean): Promise<boolean>;
  getBackendPort(): Promise<number>;
  getApiToken(): Promise<string>;
}
```

