# Backend Gap Analysis

## Architecture comparison

| Concern | Mark-LVI-main | Alex | Gap |
|---|---|---|---|
| Application | Python/Qt `main.py` and `ui.py` | Electron main + Python FastAPI sidecar | Major framework redesign; preserve behavior across IPC boundary. |
| API | Live Gemini session and optional dashboard FastAPI | Authenticated loopback REST + WebSocket | Core service transport exists; remote dashboard routes absent. |
| Action dispatch | Inline tools, action loader, plugin loader | Explicit typed `ActionRegistry` / `ActionExecutor` | Safer centralized contract; most source handlers are not registered. |
| Persistence | JSON config/memory and action-specific persistence | JSON document store, credential store, settings/memory/reminder services | Current services exist; migration/import and data-format regression are incomplete. |
| Long-running work | Async live loop, schedulers/monitoring, OS jobs | Live websocket, app-polled reminders/alerts | No native reminder scheduler, daily topic watcher, or proactive service parity. |
| OS integrations | GUI, file, app, settings, power, browser actions | Shortcuts/login startup, external URL and process metrics | Most local OS operation adapters absent. |
| Errors/logging | UI/activity callbacks and module-specific handling | Structured Python logging, HTTP errors, typed action statuses | Better centralization in Alex; no cross-project failure compatibility tests. |

## API/service gaps

| ID | Source behavior | Alex status and evidence | Priority |
|---|---|---|---|
| BE01 | OS settings, volume/brightness/Wi-Fi/power adapters | No equivalent action service; assistant settings routes are different. | P1 |
| BE02 | GUI input and app discovery/control | Not registered or implemented as a controlled service. | P0 |
| BE03 | File CRUD, organization, reversible operations | Attachment validation/forwarding exists, not file management. | P0 |
| BE04 | Format-specific processing and archive workflows | Gemini attachment path only; no complete parser/converter/action pipeline. | P1 |
| BE05 | Native reminder scheduling | In-app persistent service/due delivery exists only while app runs. | P1 |
| BE06 | Daily topic monitoring and proactive engine | Metric threshold service exists, but no topic scheduler/proactive check-in. | P2 |
| BE07 | Screen/webcam capture/analysis and stop controls | No capture service or camera lifecycle. | P0 |
| BE08 | Browser automation | Default URL launch only; no browser session, origin policy, DOM interaction or screenshot service. | P1 |
| BE09 | Messaging and recipient verification | No external channel adapter. | P1 |
| BE10 | Video/YouTube/flight/game integrations | No corresponding APIs/services; attachment support is not playback/research integration. | P2 |
| BE11 | Alternate provider integrations | Gemini-specific services only; no provider registry or STT/TTS adapters. | P1 |
| BE12 | Paired remote phone dashboard | No LAN server, pair-token workflow, or mobile API. | P2 |
| BE13 | Reversible actions and durable audit | Bounded in-memory action history exists; no general undo or persistent audit. | P0 |

## Existing Alex backend capabilities

Alex already has authenticated FastAPI routes and services for health, metrics/alerts, settings and credential status, memory, reminders, text conversation, grounded web search and action discovery/execution/history. Gemini Live is served over an authenticated loopback WebSocket. Action schemas are validated with Pydantic, and confirmation-gated web search is rejected without separate confirmation.

## Startup, failure, and lifecycle

The desktop starts the Python sidecar on loopback with an API token; routes enforce token authentication. Electron owns the lifecycle and requests backend shutdown during app exit. Historical packaged smoke evidence says the bundled sidecar starts and unauthenticated health returns 401. The comparison has not exercised startup failures, abrupt Electron termination, websocket cleanup under backend failure, clean-install behavior, or platform-specific process cleanup beyond recorded automated tests.

## Source-side safety findings to avoid copying

- `code_helper` and `dev_agent` can run local generated code and install dependencies without a sandbox.
- Archive extraction calls `shutil.unpack_archive` with no visible destination-entry validation in the audited path.
- `game_updater` can schedule system shutdown after downloads without an observed independent confirmation gate.
- Desktop organization has file moves without universal undo coverage.
- Phone dashboard defaults to `0.0.0.0` and plain HTTP unless configured otherwise; source warns commands are unencrypted in default HTTP.

The Alex migration should implement safer, explicitly approved behavior rather than preserve unsafe mechanics.
