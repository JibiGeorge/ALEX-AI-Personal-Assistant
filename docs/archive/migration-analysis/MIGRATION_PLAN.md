# Migration Plan: Mark LVI to Alex

## Guardrails

- `../../Mark-LVI-main/` is the read-only source of truth and must remain unchanged.
- Migrate implementation-backed behavior, not filenames or README promises.
- The checkout lacks many README-listed plugin files; those features remain source-missing until the original implementations are provided or scope is explicitly narrowed.
- Do not reintroduce arbitrary generated Python execution. Privileged actions require typed inputs, scoped paths, observable outcomes and user confirmation where appropriate.
- Maintain parity evidence per feature; do not mark a feature migrated because a UI control or endpoint exists.

## Architecture target

```text
Electron main + secure preload
  └─ allowlisted IPC only
       └─ Python FastAPI sidecar bound to 127.0.0.1
            ├─ versioned Pydantic API
            ├─ services / feature modules / integrations
            ├─ local repositories for config and memory
            └─ structured logs and event stream
```

Renderer has `contextIsolation: true`, `nodeIntegration: false`, a restrictive Content Security Policy and typed `contextBridge` APIs. The Electron main process owns backend startup/stop and calls its loopback API using a one-run random bearer secret; the secret is never sent to the renderer. Validate IPC origin, sender, method and payload. Backend binds loopback only for desktop mode, uses bounded request sizes/timeouts, and reports ready only after health checks.

## Sequential stages and exit criteria

### Stage 1 — Analyze source (complete)
- Inspect source tree, entry points, action/provider implementations, persistence, setup and UI/dashboard surfaces.
- Record README/source discrepancies and missing plugin files.
- **Exit:** analysis has evidence-backed source inventory and known gaps.

### Stage 2 — Analysis documentation (complete before implementation)
- Create `CODEBASE_ANALYSIS.md`, `EXISTING_ARCHITECTURE.md`, `FEATURE_INVENTORY.md`, `DEPENDENCY_ANALYSIS.md` and this plan.
- **Exit:** required docs exist before the new runtime code is written.

### Stage 3 — Independent Alex project structure (complete)
- Create project root, backend package/test configuration, Electron/React TypeScript renderer, scripts, docs, environment example and ignore rules.
- Keep all generated paths and user data under Alex's own app-data area.
- **Exit:** independent development tree and setup instructions; original remains untouched.

### Stage 4 — Python backend foundation (implemented; Windows tests pass)
- Environment-based settings, Pydantic request/response types, structured logging, FastAPI lifespan, authenticated health, settings, memory and shutdown endpoints are implemented.
- JSON persistence uses atomic writes; API and storage tests cover validation, persistence and error responses.
- **Exit:** unit/API tests and a packaged Windows sidecar startup/authentication/shutdown test pass; other OS checks remain.

### Stage 5 — Electron + React foundation (implemented; renderer tests/build pass)
- Secure BrowserWindow defaults, preload allowlist, sender/input validation, typed renderer API, React navigation and error/loading states are implemented.
- Settings, secure API-key configuration and categorized memory are available in the renderer.
- **Exit:** Vitest and TypeScript/Vite builds pass; live Electron IPC behavior and other OS checks remain.

### Stage 6 — Incremental feature migration (started)
Recommended order:
1. Settings/configuration and memory viewing/editing (local and bounded).
2. **Initial text conversation/model adapter implemented:** authenticated text turns, bounded session context, saved-memory context, REST model fallback, and process-local cooldowns are implemented. Tiered one-shot calls, provider adapters and tool dispatch remain.
3. Gemini Live voice and shared typed turns are implemented and Windows-tested; audio-device selection and focused-window push-to-talk are implemented with automated tests. Global push-to-talk, wake word, reconnect/resumption and cross-platform session validation remain.
4. Screen/camera and avatar presentation.
5. Low-risk lookup and content features: web search, weather page launch, YouTube info/summary.
6. Filesystem/document processing with path policies, size limits and undo.
7. OS automation, app/window control and messaging with confirmation and observable outcomes.
8. Reminder API/UI implemented for app-running delivery; OS scheduler lifecycle, system alerts, and proactive/topic scheduler remain.
9. Optional providers and the authenticated LAN dashboard.
10. Media display and platform-specific packaging.
- **Exit per slice:** behavior-focused tests, documented limitations and migration-status update.

### Stage 7 — Electron/backend integration (Windows packaged sidecar smoke passed; installer lifecycle pending)
- Electron main starts the development or packaged Python sidecar, waits for authenticated readiness, and routes allowlisted IPC through a per-run token.
- Shutdown requests are authenticated with bounded process termination as fallback.
- Windows packaged-app smoke confirms the bundled sidecar starts and rejects an unauthenticated health request (HTTP 401). Authenticated desktop development and real Gemini Live/microphone playback have also passed.
- **Exit:** clean-install installer/uninstaller, graceful packaged-app shutdown, startup failure UX, and macOS/Linux lifecycle checks remain.

### Stage 8 — Functional, regression and platform tests
- Compare every source-backed feature against the inventory; test at least Windows and add macOS/Linux checks for platform code.
- Exercise clean install, missing credentials, offline/timeout, cancellation, permissions, upgrades and packaged app.
- **Exit:** no unaccounted source-backed features; unresolved differences have explicit status and user-facing impact.

### Stage 9 — Stabilize and optimize
- Measure startup, audio latency, memory, sidecar lifecycle, renderer responsiveness and packaging footprint.
- **Exit:** no silent success-shaped failures; performance budgets recorded.

### Stage 10 — Documentation and release (Windows installer generated; release validation pending)
- Finish architecture, development, build/deploy and migration status docs; package backend with Electron Builder.
- An unsigned Windows NSIS installer was generated; code signing, clean-machine install/run validation and per-OS installers remain.
- **Exit:** clean machine install/run/build validation for supported OS targets.

## Migration decisions and risks

| Decision / risk | Plan |
|---|---|
| Source behavior currently co-located in Qt/main loop | Split by backend service and typed events; preserve event order and explicit session lifecycle. |
| Direct desktop privileges | Keep in Python; expose only small, validated operations; confirmation required for irreversible effects. |
| JSON persistence and existing user data | Add schema version and import/export path; never write into Mark LVI's data directory by default. |
| Missing plugin implementations | Keep flagged source-missing; do not invent integrations or declare them complete. |
| External services/model quotas | Make provider/key state explicit, enforce timeouts and report provider/network errors. |
| Cross-platform differences | Add per-OS adapters and platform tests; detect capabilities rather than claiming universal support. |
| Packaged Python sidecar | Build per OS/architecture; verify child process readiness, logs, restart and clean exit. |

## Current migration state

The independent project structure, Python/Electron foundations, reference-inspired HUD, animated welcome, live host telemetry, settings/memory dialogs and Gemini chat with bounded attachments are implemented. Gemini Live voice and shared typed turns passed a Windows real-credential/microphone smoke test; packaged Windows sidecar startup and auth-boundary smoke tests also passed. Feature parity remains substantially incomplete: original actions/plugins, remote dashboard, automation, and other listed features remain pending or source-missing. Feature completion is tracked separately in [FEATURE_MIGRATION_STATUS.md](./FEATURE_MIGRATION_STATUS.md).
