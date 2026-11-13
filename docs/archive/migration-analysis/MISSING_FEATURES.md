# Missing and Incomplete Features

Assessment date: 2026-10-31. This is a gap index, not an implementation request. Unique feature IDs and status counts are defined in [PROJECT_COMPARISON_REPORT.md](./PROJECT_COMPARISON_REPORT.md); detailed action parameters/effects are in [ACTION_COMPARISON.md](./ACTION_COMPARISON.md).

## Missing or changed source features

| ID | Feature | Classification | Source evidence | Alex evidence / gap | Priority |
|---|---|---|---|---|---|
| A01 | Browser automation: navigation, page interaction, tabs, screenshots | `MISSING` | `actions/browser_control.py` | External URL handoff is not browser automation. | P1 |
| A02 | Computer GUI control | `MISSING` | `actions/computer_control.py` | No registered GUI input/control action. | P0 |
| A03 | OS computer settings | `MISSING` | `actions/computer_settings.py` | Assistant configuration is not OS setting control; no platform adapter. | P1 |
| A04 | Desktop wallpaper and file organization | `MISSING` | `actions/desktop.py` | Electron shell does not implement wallpaper/organization behavior. | P1 |
| A05 | General filesystem management | `PARTIALLY_IMPLEMENTED` | `actions/file_controller.py` | User-selected chat attachments do not provide safe local CRUD/search/move/undo. | P0 |
| A06 | Format-aware document/media processor | `PARTIALLY_IMPLEMENTED` | `actions/file_processor.py` | Bounded allowlisted attachment analysis is present; conversion, extraction, transforms, output workflows, and corpus parity are not. | P1 |
| A07 | Code generation/edit/run helper | `PARTIALLY_IMPLEMENTED` | `actions/code_helper.py` | Code attachment analysis exists; code helper and execution do not. | P1 |
| A08 | Multi-file development agent | `MISSING` | `actions/dev_agent.py` | No agent/workspace execution workflow. | P1 |
| A09 | Flight finder | `MISSING` | `actions/flight_finder.py` | No flight search or result workflow. | P2 |
| A10 | Steam/Epic game updater | `MISSING` | `actions/game_updater.py` | No launcher/update/scheduling integration. | P2 |
| A11 | Open installed application | `MISSING` | `actions/open_app.py` | Validated URL opening is not local app discovery/launch or process verification. | P1 |
| A12 | OS-scheduled reminders | `PARTIALLY_IMPLEMENTED` | `actions/reminder.py` | Persistent in-app reminders deliver only while Alex is running; no OS scheduler; not model-callable. | P1 |
| A13 | Weather reporting | `BEHAVIOUR_MISMATCH` | `actions/weather_report.py` | Alex opens a weather search URL; source action is described in the source audit as retrieving a live report. Verify exact source outputs before any parity claim. | P2 |
| A14 | HUD video playback controls | `MISSING` | `actions/video_player.py` | Video attachments are not a media-player surface. | P2 |
| A15 | YouTube search/play/info/transcript summary | `MISSING` | `actions/youtube_video.py` | No YouTube workflow. | P2 |
| A16 | Web search/news/research/price/compare | `PARTIALLY_IMPLEMENTED` | `actions/web_search.py` | Grounded Gemini search exists; DDG fallback and original invocation/result behavior are absent. User confirmation prevents model invocation. | P1 |
| A17 | External messaging | `MISSING` | `actions/send_message.py` | Chat sends to Gemini; no external messaging client/recipient verification/consent workflow. | P1 |
| A18 | System status | `PARTIALLY_IMPLEMENTED` | inline `system_status` in `main.py` | `system.get_metrics` is real, but sensor/process parity and cross-platform readings are incomplete. | P1 |
| A19 | Screen/webcam vision | `MISSING` | inline `screen_process`; `actions/screen_processor.py` | System metrics process count is not screen capture or vision; no screen/camera workflow. | P0 |
| A20 | Close camera | `MISSING` | inline `close_camera` in `main.py` | No camera stream to close. | P1 |
| A21 | Persistent topic monitoring | `MISSING` | inline `manage_monitor`; `actions/background_monitor.py` | System-alert polling is different from configurable daily topic monitoring. | P2 |
| A22 | Assistant shutdown with summary | `PARTIALLY_IMPLEMENTED` | inline `shutdown_jarvis` in `main.py` | App lifecycle stops the sidecar; no model-callable summary-then-assistant-exit tool. | P2 |
| A23 | Assistant-triggered save memory | `PARTIALLY_IMPLEMENTED` | inline `save_memory` | UI/API memory writes exist; tool calling is intentionally withheld pending an independent consent flow. | P1 |
| A24 | Assistant-triggered memory recall | `PARTIALLY_IMPLEMENTED` | inline `recall_memory` | Read-only `memory.recall` is registered and model-callable; matching/limits and behavior parity need validation. | P1 |
| A25 | Undo/revert action | `MISSING` | inline `undo`; `core/undo.py` | No Alex undo registry or reversible action records. | P0 |

## Subsystem gaps

| ID | Subsystem | Classification | Gap | Priority |
|---|---|---|---|---|
| S01 | Application startup and shutdown | `PARTIALLY_IMPLEMENTED` | Electron/Python startup exists, but full source setup, reconnect, failure cleanup, session summary and parity lifecycle evidence are incomplete. | P1 |
| S02 | Voice/audio/session controls | `PARTIALLY_IMPLEMENTED` | Gemini Live and focused PTT/device settings exist; alternate pipelines, wake word, global hotkey, echo handling, reconnect/resumption and platform coverage are incomplete. | P1 |
| S03 | Alternate provider pipeline | `MISSING` | No provider registry/pipeline parity for alternate LLM, STT and TTS backends. | P1 |
| S04 | Phone dashboard | `MISSING` | No paired LAN dashboard, remote command/audio/file workflow. | P2 |
| S05 | Plugin system | `PARTIALLY_IMPLEMENTED` | Alex has explicit built-in action registration, not source plugin discovery/configuration. Source contains no active plugin modules, so README-only claimed plugins are excluded. | P2 |
| S06 | HUD/avatar fidelity | `PARTIALLY_IMPLEMENTED` | Animated cyan face/HUD is present; original face mesh, expressions, visemes and synchronized lip-sync remain. | P2 |
| S07 | Monitoring and proactive behavior | `PARTIALLY_IMPLEMENTED` | System alerts exist; topic watch scheduler, proactive check-ins, startup briefings and session summaries are not equivalent. | P2 |
| S08 | Persistent memory subsystem | `PARTIALLY_IMPLEMENTED` | Categorized CRUD/context exist; legacy import, source-specific search and assistant-triggered write/undo parity remain. | P1 |
| S09 | Configuration and optional capabilities | `PARTIALLY_IMPLEMENTED` | Settings and OS key storage exist; provider/device/plugin/setup configuration and full OS capability checks remain. | P1 |

## Explicit exclusions and uncertainty

- Source README plugin claims are **not** counted as features available in the source checkout. `plugins/` contains only `_template.py`, which the loader skips.
- The 25 tools are source-declared callable surfaces. Runtime availability can be lower because action discovery imports modules and can skip failures or apply provider capability filtering.
- Similar labels are not treated as equivalent functionality. For example, external URL opening does not satisfy browser automation; chat attachments do not satisfy file management; process count does not satisfy screen/process inspection.
- No destructive source action was executed for this comparison.
