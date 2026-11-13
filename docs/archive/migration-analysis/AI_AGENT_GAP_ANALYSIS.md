# AI Agent and LLM Gap Analysis

## Current architecture

Mark-LVI-main centers on `JarvisLive`: Gemini Live is the default conversation path, with a model ladder/reconnect path and optional pipeline providers. Its prompt incorporates memory, and tool declarations combine inline tools, discovered action modules, and plugins. Provider mode is conditional on settings and installed integrations.

Alex separates:

- Gemini text requests and bounded in-memory conversations in `backend/app/services/conversation_service.py`.
- Gemini Live audio/WebSocket bridging in `backend/app/services/live_voice_service.py`.
- Persistent saved memory and settings in dedicated services.
- Registry-derived function declarations and Pydantic-backed `ActionExecutor`.
- A React UI and secure Electron IPC bridge, with Python FastAPI as the trusted local API.

Gemini model tool calling is implemented for text and Live paths. Declarations are generated dynamically from enabled, dependency-available actions that do not require independent confirmation. The present model-callable set is read-only `system.get_metrics` and `memory.recall`. `web.search` requires separate user approval and is therefore not disclosed to the model. Writes such as `save_memory` are similarly withheld pending an independent consent workflow.

## Gap table

| ID | Capability | Mark-LVI-main | Alex | Gap/status | Priority |
|---|---|---|---|---|---|
| AI01 | Gemini Live conversation | Default voice path, audio and model ladder | Live path, streaming audio/transcripts | Available; reconnect/resumption and action calling require real-credential verification. Partial. | P1 |
| AI02 | Text conversation/context | Integrated with live assistant/session | REST text session, bounded process memory | Separate conversation context when Live is inactive; durable transcript/session unification missing. Partial. | P1 |
| AI03 | Dynamic function/tool calling | Inline + discovered action/plugin calls | Dynamic registry declarations and execution | Safety-filtered subset only; 2 callable actions vs 25 source tools. Partial. | P0 |
| AI04 | Multi-step action loop | Returns function result to model; repeated calls possible | Text/Live tool-response loops with per-turn bound | Functional under fakes; no live Gemini tool-call smoke test or durable audit. Partial. | P1 |
| AI05 | Alternate LLMs | OpenAI-compatible provider and presets for hosted/local endpoints | Gemini-only service | Provider registry, configuration, capability normalization and fallback missing. Missing. | P1 |
| AI06 | Alternate STT/TTS | Whisper/system/Piper/ElevenLabs options, conditionally configured | Browser mic + Gemini Live audio | Standalone provider pipelines, downloads, voice capability mapping absent. Missing. | P1 |
| AI07 | Model switching/fallback | Gemini ladder and provider selection | Text model fallback/cooldowns; Live fallback list | Model fallback exists; provider selection/capability-aware model routing incomplete. Partial. | P1 |
| AI08 | Prompt and memory context | Memory prompt context and session summaries | System instruction includes bounded saved facts as data | Persistent session summaries and source-equivalent memory lifecycle absent. Partial. | P1 |
| AI09 | Memory recall | Query-oriented local tool | Read-only `memory.recall` action | Exists with literal substring search and a result cap; parity behavior not established. Partial. | P1 |
| AI10 | Memory write | Assistant tool updates local memory | UI/API CRUD, not model-callable | Consent-gated natural-language save workflow missing. Partial. | P1 |
| AI11 | Intent/model capability filtering | Provider-specific tool adaptation | One registry contract; confirmation-required actions withheld | Provider-specific function schema adaptation unavailable because alternate providers are absent. Partial. | P2 |
| AI12 | Error recovery | Live reconnect and provider fallback | Text cooldown/fallback and Live model fallback | Live recovery/resumption, unified error state and cross-provider recovery not fully equivalent. Partial. | P1 |
| AI13 | Session summaries | Save summary at assistant shutdown | Not model-callable; app lifecycle shutdown only | Summary generation and save-on-close behavior missing. Partial. | P2 |
| AI14 | Agentic coding/dev workflow | Code helper and multi-file agent can write/run/install | No sandboxed equivalent | Intentionally not migrated; implementation must wait for isolated workspace/command boundary. Missing. | P1 |

## Validation and blockers

Alex backend tests include mocked text dispatch and Live tool-response tests, and the registry excludes confirmation-gated actions. The last recorded full backend suite passed 58 tests. No real Gemini function-call session has been performed after enabling tool declarations. Historical Windows Live microphone verification predates tool calling.

Do not claim generic multi-step autonomy: the available tool set is deliberately narrow; action timeouts cannot forcibly stop a synchronous worker thread; model-generated parameters are untrusted; and there is no durable cross-action audit trail. The coding agent, shell, OS control, networked search and writes must not be added to model declarations until separate permissions and cancellation/undo design are implemented.

## Recommended sequence

1. Verify Gemini Live and text function calling with fake malformed/unknown/disabled/oversized cases and then with a user-approved real key.
2. Implement an explicit user-confirmed memory-save operation, rather than letting model output assert consent.
3. Add source-backed read-only actions in small slices; every tool must have schema, tests, timeout and structured result.
4. Design alternate provider contracts only after dependency and configuration parity is documented.
5. Defer generated-code execution until sandboxing, workspace approvals, subprocess timeouts, output limits, and cleanup tests exist.
