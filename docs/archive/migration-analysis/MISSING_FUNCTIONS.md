# Function-Level Gap Analysis

This report tracks **20 workflow/function groups** (`G01-G20`) rather than listing every private helper in two differently structured codebases. Each row describes source behavior, the closest real Alex implementation, the gap, and a traceable acceptance target. Action tool entrypoints are separately tracked in [ACTION_COMPARISON.md](./ACTION_COMPARISON.md); do not add them a second time to the project feature denominator.

| ID | Source function/module behavior | Alex equivalent | Gap / classification | Priority |
|---|---|---|---|---|
| G01 | `main.py` startup: configure key/settings, initialize UI and `JarvisLive` | Electron `main.ts`, Python `app/main.py` | Different runtime and startup sequence; sidecar lifecycle exists but full reconnect/summary cleanup parity is not demonstrated. Partial. | P1 |
| G02 | `core/action_loader.py`: scan sorted top-level action modules, validate `TOOL`, skip invalid imports | `app/actions/action_registry.py`, explicit `main.py` registration | Registry is explicit and safer but does not discover source modules dynamically. Partial by design. | P1 |
| G03 | `core/plugin_loader.py`: discover plugins, settings, dispatch | No third-party plugin loader | No plugin module lifecycle/configuration. Source checkout has no active plugin modules; framework parity only. | P2 |
| G04 | `main.py` Gemini Live connect/reconnect/model ladder | `services/live_voice_service.py` | Live connection, fallback and streamed audio exist; reconnect/resumption and live tool-call verification remain. Partial. | P1 |
| G05 | `core/llm_client.py`, `core/gemini.py`, `providers/`: provider selection and capability-aware LLM | `services/conversation_service.py`, `web_search_service.py` | Gemini-only text/Live paths and model fallback; no provider registry or alternate adapter parity. Missing/partial. | P1 |
| G06 | `main.py` inline tool dispatch and action/plugin handlers | `ActionExecutor.execute`, text/Live dispatch | Strict registry and Pydantic validation cover only registered actions. No source action coverage broadly; confirmation is independent. Partial. | P0 |
| G07 | `core/confirm.py`: UI approval gate with expiry and handler opt-in | Action API/UI `confirmed` gate | Explicit gate exists for registered actions; no general human-confirmation model for unmigrated OS/file/message actions. Partial. | P0 |
| G08 | `core/undo.py`: bounded stack and registered reversal callbacks | No equivalent action undo service | No reversible operation provenance or undo API/UI. Missing. | P0 |
| G09 | `memory/memory_manager.py`, `main.py`: load, search, save and session summary | `MemoryService`, memory routes/UI, `memory.recall` | Persistent categorized CRUD/context exist; session summary, full source query behavior and model-approved writes remain. Partial. | P1 |
| G10 | `memory/config_manager.py`: persistent app settings and API keys | `SettingsService`, credential store, settings routes | Alex has settings and OS keyring; provider/plugin/device configuration differs. Secret-store migration has not been compared by round-trip regression. Partial. | P1 |
| G11 | `core/audio_devices.py`: enumerate/select/test audio devices | Browser `MediaDevices` UI and persisted IDs | Browser-scoped device view is not platform backend selection; hotplug/name/device-route parity needs hardware testing. Partial. | P1 |
| G12 | `core/hotkey.py`, `core/wake_word.py`, `core/echo.py`: PTT/wake/sleep/echo | Renderer focused Ctrl+Space gate | No global PTT, wake-word lifecycle, local wake model, or self-echo guard. Partial. | P1 |
| G13 | `main.py`, `actions/screen_processor.py`: screen/camera capture, analysis, stop | None | No screen/camera capture, privacy flow, vision model request, or camera-stop control. Missing. | P0 |
| G14 | `actions/reminder.py`: native OS scheduling | `ReminderService`, API/UI, renderer polling | Persistent reminders deliver only while Alex is open; no OS scheduler adapter or closed-app delivery. Partial. | P1 |
| G15 | `actions/background_monitor.py`, `actions/proactive.py`: topic schedule, duplicate suppression, proactive briefings/check-ins | `SystemMonitorService` | Metric alerts are not news/topic monitoring or proactive session behavior. Partial. | P2 |
| G16 | OS action handlers: app launch, settings, keys/mouse, power | Electron shortcut/startup APIs and URL opening | No allowlisted installed-app/OS-setting/input adapter, action verification, undo or model-callable operation. Partial/missing. | P0 |
| G17 | File/action handlers: CRUD, organize, search, undo, format processing | `FileAttachment`, attachment validation and Gemini request | Selected attachment analysis only; no path-bounded management, output workflow, archive extraction or undo. Partial. | P0 |
| G18 | `actions/web_search.py`, weather, flight, YouTube and messaging integrations | `WebSearchService`, weather browser handoff, Gemini chat | Grounded web search is partial; weather semantics differ; flight/video/transcript/messaging workflows absent. Partial/missing/mismatch. | P1 |
| G19 | `dashboard/server.py`: pairing, LAN routes, remote commands/audio/file upload | No remote dashboard | Missing transport, pairing and remote-client workflows. Missing. | P2 |
| G20 | `ui.py`: Qt HUD, menus/settings, status, chat, overlay and interactions | React `App`, pages/components, Electron shell | Core HUD and major pages exist; source visual details/native overlays and several feature controls missing. Partial. | P2 |

## Function and method comparison notes

- **Inputs and outputs:** Alex uses typed API/Pydantic models for settings, reminders, memory, attachments, search and actions. Source tool schemas are JSON declarations and handlers do not consistently enforce those schemas at runtime. Exact field-by-field compatibility is not established for unmigrated tools.
- **Errors:** Alex centralizes API auth, storage/credential errors, model fallback and action result statuses. Source uses UI/activity/log callbacks and tool-specific outcomes. No broad cross-project error-message regression suite exists.
- **Side effects:** Source actions may change files/settings, launch programs, send messages, execute code, install packages, or schedule shutdown. Alex intentionally omits most such handlers rather than exposing unsafe generic access.
- **Return shape:** Alex action results are structured `{action_id,status,data,message,error,execution_time}`; source tool results are converted to function response text/objects in dispatcher branches. User-visible response parity has not been tested end-to-end.
- **Execution sequence:** Alex text and Live paths now advertise registry-derived tools and feed validated execution responses to Gemini. Tool declarations omit actions requiring independent confirmation; model output never grants consent.

## Function-level acceptance testing

For each G group, record source observable behavior (where the source can run), Alex output/error/side-effect, and platform constraints. Use mocks for external calls and hardware-independent logic; use user-approved isolated Windows hardware checks for real audio, camera, OS settings, file writes, messaging, and process effects. Never test destructive operations against real user data.
