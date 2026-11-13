# Existing Architecture: Mark LVI

## Context

The supplied Mark-LVI-main checkout is a Python desktop application, not a web or Electron project. The following reflects the implementation in `../../Mark-LVI-main/`; it does not treat the README's absent plugin files as implemented functionality.

## Component view

```text
python main.py
  ├─ PyQt6 UI (ui.py) ── callbacks/signals ── JarvisLive (main.py)
  │      ├─ setup, chat/activity, avatar, input, settings, media, confirmations
  │      └─ UI workers for slower setup/settings operations
  ├─ asyncio session and audio loops
  │      ├─ Gemini Live (default) OR providers/ PipelineEngine
  │      ├─ action registry (actions/*.py TOOL declarations)
  │      ├─ plugin registry (plugins/*.py PLUGIN declarations; template only here)
  │      ├─ memory/config, undo and confirmation
  │      └─ monitoring/proactive/wake-word and optional dashboard jobs
  └─ OS APIs, subprocesses and third-party integrations

Optional LAN dashboard:
  phone HTML/JS ── HTTP(S), WebSocket ── FastAPI/uvicorn in the same process
                                      └─ queued commands/audio/events ── JarvisLive
```

## Runtime and ownership

| Component | Current owner / boundary | Lifecycle |
|---|---|---|
| Application | `main.py` | Creates the GUI/session and coordinates startup, reconnect and shutdown. |
| Desktop UI | `JarvisUI` and related PyQt widgets in `ui.py` | Runs on the Qt UI thread; callbacks cross to session work through thread-safe loop scheduling and Qt signals/workers. |
| Conversation | `JarvisLive` | Owns an async session, audio queues, transcript/viseme state, reconnect signaling and runtime capability selection. |
| Default model session | Gemini Live SDK | Bidirectional audio/text, tool calls, output audio, turn completion and session-resumption data. |
| Alternative engine | `providers/engine_pipeline.py` | STT → LLM → TTS; emits Live-shaped events and asynchronously handles tool-result follow-ups. Optional and lazy-loaded. |
| Action execution | `core/action_loader.py` registry | Discovers module-level `TOOL` dicts, validates names/schema/handlers, dispatches handlers with only the declared context arguments. |
| Plugins | `core/plugin_loader.py` registry | Discovers `PLUGIN` declarations and checks enabled state from config; concrete plugins are absent in this checkout. |
| Persistence | `memory/config_manager.py`, `memory/memory_manager.py` | Reads/writes local JSON files; there is no database abstraction. |
| Remote service | `dashboard/server.py` | FastAPI/uvicorn server with static clients, auth/session state, WebSocket and upload endpoints. It is optional and shares process state. |

## Request and event flow

### Main conversation

1. UI setup gathers a Gemini key and preferences.
2. `JarvisLive` loads identity and the system prompt, the memory prompt core, detected platform limits and registered tool declarations.
3. The engine is selected from config. Gemini Live is the default; provider modules are imported on demand when an alternate is selected.
4. The microphone supplies mono 16 kHz PCM. The session returns 24 kHz mono audio, transcripts, tool calls and turn state.
5. Output transcription feeds the activity view and transcript-aware avatar mouth; PCM is queued for playback. The self-echo guard compares input with recent output.
6. Tool calls route to inline session tools, action handlers or plugins. Non-blocking Live actions may schedule their response according to the declared policy.
7. The result is sent to the model, while proactive/monitoring tasks may inject events into the same session.
8. Reconnects preserve context where the engine supports it; wake word, voice and device changes alter session state according to their respective rules.

### Configuration and persistence

- `config/api_keys.json` contains the key, identity, voice, audio, UI, feature, provider, plugin and dashboard preferences.
- `memory/long_term.json` stores categorized facts, monitor state and session summaries. The prompt receives a bounded selection plus a key index; recall searches local data.
- Undo and confirmation queues are process-local. They are not durable across restarts.

### Remote dashboard

The dashboard serves its own static phone client from FastAPI. A short-lived pairing key creates an authenticated session; the client may retain a device token. WebSocket connections deliver updates and phone audio; command, wake, file and upload APIs feed the assistant. Dashboard control is not Electron IPC and must not be reused as the renderer-to-Python protocol without redesign.

## Cross-cutting conventions

- Tool/action handlers generally accept a parameter dictionary and optional runtime context.
- Tool schemas use Gemini's uppercase type names; provider code translates them for OpenAI-compatible/Anthropic interfaces and budgets declarations for smaller local models.
- `core/outcome.py` wraps `done`, `unverified`, `failed`, `ask` and `started` results, including untrusted external content.
- Optional/heavy imports are often delayed to first use; `core/lazyimport.py` and `providers/registry.py` support that.
- Platform support is detected separately and communicated to both UI and model to avoid false claims on Wayland or permission-restricted macOS.

## Boundary map for Alex

| Existing concern | Alex boundary |
|---|---|
| Qt UI and control callbacks | React renderer; window management and OS dialogs remain in Electron main. |
| `JarvisLive` orchestration | Backend application services and explicit session lifecycle manager. |
| Action/plugin dispatch | Python modules behind typed service interfaces; each privileged action allowlisted and tested. |
| JSON config and memory | Versioned Pydantic schemas plus repository abstraction; explicit file location and atomic writes. |
| Dashboard/remote auth | Separate optional feature and API contract, not renderer authority. |
| Audio/model providers | Provider interfaces and adapters; no provider secret sent to renderer. |
| `print`/GUI log | Python structured logging plus typed event stream delivered through IPC. |

## Known mismatches and caveats

- The README's tree lists many plugin files not present in the current checkout.
- The dashboard's server commentary says eight-character pairing codes while its static login form accepts six characters.
- Older MARK XL-era `core/installer.py`, `core/llm_client.py`, `core/stt.py` and `core/tts.py` coexist with the newer provider architecture; source references must determine which remain active.
- There is no checked-in build, packaging or full application test harness to use as an architecture contract.
