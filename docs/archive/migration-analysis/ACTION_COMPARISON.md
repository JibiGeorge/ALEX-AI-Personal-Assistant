# Action Comparison: Mark-LVI-main vs Alex

There are 25 executable tool declarations in the supplied Mark-LVI source: eight inline tools in `main.py` plus 17 action modules with `TOOL` definitions. Helper modules under `actions/` are not counted as separate tools. Each row is a unique action feature ID; details are not repeated in other inventories.

| ID | Source action | Source purpose / inputs | Alex implementation and model execution | Classification | Priority |
|---|---|---|---|---|---|
| A01 | `browser_control` | Browser navigation, page interaction, tabs/screenshots; action and optional target/browser fields. `actions/browser_control.py` | No browser automation. `openExternal` is a browser handoff only. | `MISSING` | P1 |
| A02 | `computer_control` | GUI input, screenshots, screen finding, app closing; action-specific coordinates/text/keys. `actions/computer_control.py` | No corresponding action or controlled GUI surface. | `MISSING` | P0 |
| A03 | `computer_settings` | Volume/brightness/window/keyboard/dark-mode/Wi-Fi/power; action/description/value. `actions/computer_settings.py` | No OS settings action. Alex settings configure Alex itself. | `MISSING` | P1 |
| A04 | `desktop_control` | Wallpaper and desktop list/stats/organize/clean; action/path/url/mode. `actions/desktop.py` | Desktop app shell only; no desktop organization/wallpaper operations. | `MISSING` | P1 |
| A05 | `file_controller` | Local list/create/read/write/delete/move/copy/rename/find/organize with some undo; `actions/file_controller.py` | Attachment flow only; no file CRUD, canonical boundary, previews or undo. | `PARTIALLY_IMPLEMENTED` | P0 |
| A06 | `file_processor` | Document/image/table/code/audio/video/archive/presentation processing; `actions/file_processor.py` | User-selected MIME allowlist (8 MiB) can be analyzed by Gemini; no comparable processing/conversion/extraction outputs. | `PARTIALLY_IMPLEMENTED` | P1 |
| A07 | `code_helper` | Generate/edit/explain/run/build local code; `actions/code_helper.py` | Code attachment analysis is generic; no coding action. Deliberately no generated execution. | `PARTIALLY_IMPLEMENTED` | P1 |
| A08 | `dev_agent` | Multi-file project generation, dependency installation, launch and iterative fixes; `actions/dev_agent.py` | No workspace agent. Unsafe subprocess behavior is not migrated. | `MISSING` | P1 |
| A09 | `flight_finder` | Flight search and formatting; origin/destination/date and optional travel/save fields; `actions/flight_finder.py` | No flight workflow. | `MISSING` | P2 |
| A10 | `game_updater` | Steam/Epic list/install/update/schedule and optional shutdown; `actions/game_updater.py` | No launcher integration. Source shutdown-on-download is high risk and lacks a visible confirmation call in audited path. | `MISSING` | P2 |
| A11 | `open_app` | Launch named local app; `app_name`. `actions/open_app.py` | Opens validated external URLs only; does not discover/launch installed applications or verify a process. | `MISSING` | P1 |
| A12 | `reminder` | Schedule native notification by date/time/message; `actions/reminder.py` | Persistent UI/API; due notifications are delivered while Alex is running. No native OS scheduler, closed-app delivery, or model-callable reminder. | `PARTIALLY_IMPLEMENTED` | P1 |
| A13 | `weather_report` | Source handler reports current weather for `city`; `actions/weather_report.py` | Opens a Google weather search page, not structured weather data. The behavior materially differs. Confirm exact source integration at runtime before specifying parity. | `BEHAVIOUR_MISMATCH` | P2 |
| A14 | `video_player` | HUD play/stop/mute/unmute video from source; `actions/video_player.py` | No player page/action. Video attachment support is not playback. | `MISSING` | P2 |
| A15 | `youtube_video` | Search/play/info/trending/transcript summary; `actions/youtube_video.py` | No YouTube-specific action or workflow. | `MISSING` | P2 |
| A16 | `web_search` | Web/news/research/prices/compare; query/mode/items/aspect; `actions/web_search.py` | Grounded Gemini search API/UI exists and `web.search` is registered, but it requires explicit user confirmation and is not exposed to model tool calling. DDG fallback and full source handoff differ. | `PARTIALLY_IMPLEMENTED` | P1 |
| A17 | `send_message` | Send to verified receiver/platform; `actions/send_message.py` | Chat only sends to Gemini. No external messaging integration, verified recipient, or send-consent dialog. Source WhatsApp driver also appears absent. | `MISSING` | P1 |
| A18 | `system_status` | Current system/hardware information; inline `main.py` tool | `system.get_metrics` is registered and model-callable. GPU/temperature may be unavailable; source tool name/output parity is not demonstrated. | `PARTIALLY_IMPLEMENTED` | P1 |
| A19 | `screen_process` | Capture/analyze screen or webcam; inline `main.py`, `actions/screen_processor.py` | No screen/camera capture. Host process count is not screen or process inspection. | `MISSING` | P0 |
| A20 | `close_camera` | Stop webcam feed; inline `main.py` tool | Camera capture is absent, so no camera lifecycle control exists. | `MISSING` | P1 |
| A21 | `manage_monitor` | Add/remove/list watched topics; inline `main.py` tool | No topic monitor records or management UI; metric alerts are a different feature. | `MISSING` | P2 |
| A22 | `shutdown_jarvis` | Save summary/goodbye and stop assistant; inline `main.py` tool | Electron app lifecycle stops the sidecar, but there is no corresponding assistant action or summary-before-exit flow. | `PARTIALLY_IMPLEMENTED` | P2 |
| A23 | `save_memory` | Save categorized fact; inline `main.py` tool | Memory UI/API CRUD exists; no model-callable write because user consent is not separately confirmed. | `PARTIALLY_IMPLEMENTED` | P1 |
| A24 | `recall_memory` | Query local memory; inline `main.py` tool | Registered read-only `memory.recall`, callable from Gemini text and Live; literal substring matching and result bound need parity checks. | `PARTIALLY_IMPLEMENTED` | P1 |
| A25 | `undo` | List/revert supported changes; inline `main.py`, `core/undo.py` | No undo service/registry. | `MISSING` | P0 |

## Alex target implementation/evidence paths

Paths are relative to the `Alex/` project root. `None` means no equivalent handler is registered; the cited registry or feature surface is evidence that the adjacent capability is different, not a migrated implementation.

| ID | Alex target file(s) or absence evidence |
|---|---|
| A01 | `frontend/electron/main.ts` (validated external URL opening only); no browser automation service. |
| A02 | `backend/app/main.py`, `backend/app/actions/action_registry.py` (no computer-control registration). |
| A03 | `backend/app/api/routes.py` (Alex settings API, not OS settings); no OS settings action. |
| A04 | `frontend/electron/main.ts` (desktop shortcut/lifecycle only); no wallpaper/desktop-file service. |
| A05 | `backend/app/schemas/conversation.py`, `frontend/src/App.tsx` (selected attachments only); no local file-management service. |
| A06 | `backend/app/services/conversation_service.py`, `backend/app/schemas/conversation.py` (attachment analysis only). |
| A07 | `frontend/src/App.tsx` (code attachment support only); no code-helper action or runner. |
| A08 | `backend/app/main.py`, `backend/app/actions/action_registry.py` (no development-agent registration). |
| A09 | No Alex flight-service or action registration. |
| A10 | No Alex game-launcher service or action registration. |
| A11 | `frontend/electron/main.ts` (external URL launch, not installed-app launch). |
| A12 | `backend/app/services/reminder_service.py`, `backend/app/api/routes.py`, `frontend/src/pages/RemindersPage.tsx`. |
| A13 | `frontend/src/pages/WebSearchPage.tsx`, `frontend/electron/main.ts` (weather-search URL handoff). |
| A14 | `backend/app/schemas/conversation.py` (video attachment MIME only); no player surface. |
| A15 | No Alex YouTube action/service/page. |
| A16 | `backend/app/actions/builtins/search.py`, `backend/app/services/web_search_service.py`; confirmation required. |
| A17 | `backend/app/api/routes.py` (Gemini conversation route only); no external messaging adapter. |
| A18 | `backend/app/actions/builtins/system.py`, `backend/app/services/system_metrics_service.py`. |
| A19 | `backend/app/services/system_metrics_service.py` (aggregate process count only); no capture service. |
| A20 | `frontend/src/hooks/useLiveVoice.ts` (voice requests video disabled); no camera lifecycle service. |
| A21 | `backend/app/services/system_monitor_service.py` (hardware alert monitoring, not topic monitoring). |
| A22 | `backend/app/api/routes.py`, `frontend/electron/main.ts` (sidecar lifecycle shutdown, not assistant tool). |
| A23 | `backend/app/services/memory_service.py`, `backend/app/api/routes.py` (user-facing CRUD only; no model-write tool). |
| A24 | `backend/app/actions/builtins/memory.py` (read-only model-callable recall). |
| A25 | No Alex undo service or registered action. |

## Callable/execution evidence

- **Original:** declarations in source `main.py` and action module `TOOL` objects are sent into model sessions after loader/provider filtering. Source action handler arguments are not uniformly Pydantic-validated.
- **Alex registry:** startup registers `system.get_metrics`, `memory.recall`, and confirmation-gated `web.search` (`backend/app/main.py`). API tests cover discovery, metrics execution, memory recall, confirmation rejection, invalid parameters, and disabling.
- **Gemini:** text and Live tool calling use registry-generated function declarations. Only enabled, available actions without independent confirmation are included. Current callable set is `system.get_metrics` and `memory.recall`; network search and memory writes are withheld from model calls.
- **Execution validation:** Alex backend suite last passed 58 tests, including fake Gemini tool responses and Live declaration construction. This does not constitute a real-credential tool call or source-vs-Alex regression.

## Safety and migration notes

Do not directly re-enable the source's arbitrary path, GUI automation, package install, generated code execution, messaging, power, or broad browser actions. Equivalent Alex implementations must use narrow schemas, least privilege, preview/confirmation, action-specific undo/cancellation, audit records, and explicit capability reporting. Source behavior itself has gaps: `game_updater` can schedule shutdown without an observed independent confirmation call, desktop organization is not generally undoable, and local generated-code execution is not sandboxed.
