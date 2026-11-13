# Action Migration Inventory

Updated: 2026-10-31

This inventory records every executable Mark-LVI tool discovered in `Mark-LVI-main/actions/` and `main.py`, including inline tools. It distinguishes callable tools from action support modules and from README-only plugin claims. Source paths are relative to the workspace's `Mark-LVI-main` folder.

## Browser and computer interaction

| Action ID | Action Name | Description | Category | Input Parameters (required; optional) | Dependencies | Execution Method | Original Location | Migration Status | Alex Location |
|---|---|---|---|---|---|---|---|---|---|
| `browser_control` | Browser control | Navigate/search, interact with page elements, inspect tabs and capture screenshots. Reports done/unverified/failed outcomes. | Browser | `action`; `browser, url, query, engine, selector, text, description, direction, amount, key, path, incognito, clear_first` | Playwright and/or system browser | Local UI automation and external websites | `actions/browser_control.py` | Pending; signed-in-site and screenshot scope needs policy | None |
| `computer_control` | Computer control | GUI input, screenshots, screen finding and closing a named app. Some close flows request confirmation. | Computer interaction | `action`; `app_name, confirmed, text, x, y, keys, key, direction, amount, seconds, title, description, type, field, clear_first, path` | Platform GUI automation and accessibility APIs | Local | `actions/computer_control.py` | Pending; high-risk input needs a narrow allowlist and confirmation | None |
| `computer_settings` | Computer settings | Change volume, brightness, window behavior, keyboard, dark mode, Wi-Fi and power settings. | System settings | none; `action, description, value` | Platform-specific OS APIs/commands | Local, platform-dependent | `actions/computer_settings.py` | Pending; confirmations and verified undo required | None |
| `desktop_control` | Desktop control | Wallpaper changes and desktop list/stats/organize/clean workflows. | Desktop/files | `action`; `path, url, mode` | Local filesystem and platform integrations | Local; may move/delete files or change wallpaper | `actions/desktop.py` | Pending; destructive work must be previewed and undoable | None |

## Files and development

| Action ID | Action Name | Description | Category | Input Parameters (required; optional) | Dependencies | Execution Method | Original Location | Migration Status | Alex Location |
|---|---|---|---|---|---|---|---|---|---|
| `file_controller` | File controller | List, create, read, write, delete, move, copy, rename, find and inspect files; includes desktop organization and undo tracking. | Files | `action`; `path, destination, new_name, content, name, extension, count` | Python filesystem; original undo service | Local | `actions/file_controller.py` | Pending; canonical workspace boundary, confirmation, and restore tests required | None |
| `file_processor` | File processor | Process document, image, table, code, audio, video, archive and presentation data; may write/extract files or send data to a model. | Files/media | none; `file_path, action, instruction, format, width, height, scale, quality, start, end, timestamp, column, value, condition, ascending, save, destination` | Format parsers/converters, subprocesses, `core.gemini` | Local and model/network APIs | `actions/file_processor.py` | Partial attachment-to-Gemini support exists in Alex; full processor and format parity pending | `frontend/src/App.tsx`; backend conversation service |
| `code_helper` | Code helper | Generate/edit/explain/run/build code using model assistance and local interpreters. | Development | `action`; `description, language, output_path, file_path, code, args, timeout` | `core.gemini`, local interpreters, subprocesses | Local and model API | `actions/code_helper.py` | Pending; no generated-code execution until sandbox/workspace approvals exist | None |
| `dev_agent` | Development agent | Plan multi-file projects, write code, install dependencies, launch VS Code, execute and iteratively fix code. | Development | `description`; `language, project_name, timeout` | Gemini and subprocesses/package managers | Local and model API | `actions/dev_agent.py` | Pending; broad write/execute/install behavior needs a real sandbox | None |

## Applications, media and games

| Action ID | Action Name | Description | Category | Input Parameters (required; optional) | Dependencies | Execution Method | Original Location | Migration Status | Alex Location |
|---|---|---|---|---|---|---|---|---|---|
| `open_app` | Open application | Launch a named local application; `started` is not proof that the app finished opening. | Applications | `app_name` | OS app discovery/launch APIs | Local | `actions/open_app.py` | Pending; verify process/window and protect Alex itself | None |
| `video_player` | HUD video player | Play/stop/mute/unmute local video, URL or YouTube content in the assistant display; starts muted. | Media | `action`; `source` | UI media player and YouTube resolution | Local and external media | `actions/video_player.py` | Pending; player surface, URL policy, expiry and playback tests required | None |
| `youtube_video` | YouTube video | Search/play videos, retrieve information/trending, summarize transcripts and optionally save summaries. | Media/research | none; `action, query, save, region, url` | YouTube/network, transcript and download integrations | External API/site and local UI | `actions/youtube_video.py` | Pending; provenance and scraping/transcript fallbacks need tests | None |
| `game_updater` | Game updater | List/install/update/status/schedule Steam or Epic games; optional shutdown after download. | Applications/games | none; `action, platform, game_name, app_id, hour, minute, shutdown_when_done` | Steam/Epic launchers and OS scheduler | Local and external downloads | `actions/game_updater.py` | Pending; installs, scheduling and power operations require explicit confirmations | None |

## Web and communication

| Action ID | Action Name | Description | Category | Input Parameters (required; optional) | Dependencies | Execution Method | Original Location | Migration Status | Alex Location |
|---|---|---|---|---|---|---|---|---|---|
| `web_search` | Web search | Search web/news/research/prices/compare and return answer text, optionally displayed in the UI. | Research | `query`; `mode, items, aspect` | Web search provider and Gemini | External network/API | `actions/web_search.py` | Partial: grounded Gemini modes exist; DDG fallback and original tool handoff remain | `backend/app/services/web_search_service.py` |
| `weather_report` | Weather search | Open a Google weather search for a city; does not itself fetch structured forecast data. | Research | `city` | Default browser | External website | `actions/weather_report.py` | In progress: browser search handoff exists; launch/platform verification remains | `frontend/electron/main.ts` |
| `flight_finder` | Flight finder | Build a Google Flights search and format options; Gemini may normalize dates and results may be saved/opened locally. | Travel/research | `origin, destination, date`; `return_date, passengers, cabin, save` | Gemini, browser, network and local text viewer | External website and local UI | `actions/flight_finder.py` | Pending; extracted prices cannot be represented as guaranteed current | None |
| `send_message` | Send message | Send via supported desktop messaging flow (WhatsApp/Telegram/etc.); source reports started/done/unverified/failed. | Communication | `receiver, message_text, platform` | Desktop GUI automation and installed messaging client | Local GUI with external message delivery | `actions/send_message.py` | Pending; source lacks explicit consent boundary and WhatsApp driver code is absent | None |

## Scheduling and monitoring

| Action ID | Action Name | Description | Category | Input Parameters (required; optional) | Dependencies | Execution Method | Original Location | Migration Status | Alex Location |
|---|---|---|---|---|---|---|---|---|---|
| `reminder` | Reminder | Schedule a dated notification using OS task scheduling. | Scheduling | `date, time, message` | Task Scheduler, launchd, systemd/`at`, notification APIs | Local OS scheduler | `actions/reminder.py` | Partial: persistent app-running reminders exist; OS scheduling while app is closed is pending | `backend/app/services/reminder_service.py`; `frontend/src/pages/RemindersPage.tsx` |
| `system_status` | System status | Return CPU/RAM/GPU/temperature/uptime/process metrics. | System monitoring | none | psutil, optional NVML/WMI sensors | Local | `main.py` inline tool | Partial: authenticated telemetry and alert API exist; AI tool routing and additional platform sensors pending | `backend/app/services/system_metrics_service.py` |
| `manage_monitor` | Manage topic monitor | Add/remove/list persistent topics watched for daily news changes. | Research/monitoring | `action`; `topic` | Persistent memory, DDG news integration | Local storage and external network | `main.py` inline tool; `actions/background_monitor.py` support | Pending; daily source scheduling and external-news fallback not migrated | None |
| `screen_process` | Screen/camera analysis | Capture screen or webcam and send the image to the model; camera can start a live UI stream. | Vision | `text`; `angle` | Screen/camera capture, image model, UI stream | Local capture and external model | `main.py` inline tool; `actions/screen_processor.py` support | Pending; explicit permission, capture preview and privacy controls required | None |
| `close_camera` | Close camera | Stop the active webcam stream. | Vision | none | Camera/UI stream lifecycle | Local | `main.py` inline tool | Pending | None |
| `shutdown_jarvis` | Shut down assistant | Save a session summary and terminate the application. | Application lifecycle | none | Session memory and process lifecycle | Local | `main.py` inline tool | Pending; must use orderly app lifecycle, never abrupt process exit | None |
| `save_memory` | Save memory | Persist a user-provided personal fact. | Memory | `category, key, value` | Persistent memory store | Local | `main.py` inline tool | Partial: Alex has authenticated memory CRUD; assistant tool registration and explicit consent remain | `backend/app/services/memory_service.py` |
| `recall_memory` | Recall memory | Search personal memory or list entries when query is empty. | Memory | none; `query` | Persistent memory store | Local | `main.py` inline tool | Partial: Alex has memory CRUD/context; semantic query tool is pending | `backend/app/services/memory_service.py` |
| `undo` | Undo | List undo history or revert the most recent tracked change. | Safety/undo | none; `action` | Original undo registry and action-specific restore handlers | Local; may alter filesystem/settings | `main.py` inline tool; `core/undo.py` support | Pending; only reversible, verified operations should be registered | None |

## Other dynamically loaded modules and claims

| Source area | Discovery behavior | Inventory decision |
|---|---|---|
| `core/action_loader.py` | Scans sorted `actions/*.py`, skips underscore-prefixed files, accepts module-level `TOOL` definitions and validates top-level schema shape; inline names are reserved against collisions. | Registers the 17 action modules above; it does not recursively scan nested directories. |
| `plugins/` and `core/plugin_loader.py` | Separately discovers non-underscore plugin files with `PLUGIN` metadata and `run()`; plugin calls are dispatched after inline and action handlers. | Only `_template.py` is present and skipped: zero active plugin tools. README-listed plugin features are source-missing, not actions to invent. |
| `actions/background_monitor.py`, `actions/screen_processor.py`, `actions/system_monitor.py`, `actions/proactive.py` | Imported helper services; these modules do not declare a `TOOL`. | Support code, not additional action IDs. Their behavior is accounted for under corresponding inline tools/features. |

The source discovery and execution details are in [ACTION_EXECUTION_FLOW.md](./ACTION_EXECUTION_FLOW.md). The migration state and individual test evidence are in [ACTION_MIGRATION_STATUS.md](./ACTION_MIGRATION_STATUS.md).
