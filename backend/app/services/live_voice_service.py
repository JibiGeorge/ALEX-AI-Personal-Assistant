import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket
from google import genai
from google.genai import errors, types
from starlette.websockets import WebSocketDisconnect

from app.actions.action_executor import ActionExecutor, model_function_response
from app.actions.action_registry import ActionRegistry
from app.core.storage import StorageError
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.model_ladder_service import (
    MAX_LADDER_HOPS,
    TaskType,
    model_ladder_service,
)
from app.services.settings_service import CredentialStoreError, SettingsService

logger = logging.getLogger(__name__)
_LIVE_MODELS = (
    "models/gemini-3.1-flash-live-preview",
    "models/gemini-2.5-flash-native-audio-preview-12-2025",
)
_MAX_PCM_CHUNK_BYTES = 8192
_PCM_CHUNK_BYTES = 2400
_MAX_TOOL_CALLS_PER_TURN = 4
_MAX_TOOL_ARGUMENT_BYTES = 16_000


class LiveVoiceService:
    def __init__(
        self,
        settings: SettingsService,
        memory: MemoryService,
        action_registry: ActionRegistry | None = None,
        action_executor: ActionExecutor | None = None,
    ):
        self._settings = settings
        self._memory = memory
        self._action_registry = action_registry
        self._action_executor = action_executor

    async def serve(self, websocket: WebSocket) -> None:
        client = None
        try:
            settings, _ = self._settings.get()
            api_key = self._settings.get_api_key_for_service()
            if not api_key:
                await self._fail(
                    websocket,
                    "Configure a Gemini API key in Settings to use voice.",
                    1008,
                )
                return

            # Validate Google Gemini API key format: Keys from Google AI Studio start with 'AIzaSy'
            if not api_key.startswith("AIza") and not api_key.startswith("test-") and not api_key.startswith("saved-key") and not api_key.startswith("fake-"):
                logger.warning("Gemini API key has unrecognized prefix '%s' (expected 'AIzaSy...')", api_key[:4])
                await self._fail(
                    websocket,
                    "Invalid Gemini API key format. Gemini API keys from Google AI Studio start with 'AIzaSy'. Please verify your key in Settings.",
                    1008,
                )
                return

            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(api_version="v1alpha", timeout=10_000),
            )
            declarations = (
                self._action_registry.model_declarations()
                if self._action_registry is not None
                else []
            )
            # Clean and sanitize function declarations for Gemini Live specification
            def _clean_schema(s: Any) -> Any:
                if not isinstance(s, dict):
                    return s
                cleaned: dict[str, Any] = {}
                for k, v in s.items():
                    if k in ("title", "$schema", "additionalProperties", "tier", "brief"):
                        continue
                    if isinstance(v, dict):
                        cleaned[k] = _clean_schema(v)
                    elif isinstance(v, list):
                        cleaned[k] = [_clean_schema(i) if isinstance(i, dict) else i for i in v]
                    else:
                        cleaned[k] = v
                return cleaned

            live_declarations = [
                types.FunctionDeclaration(
                    name=d.name.replace(".", "_"),
                    description=d.description,
                    parameters_json_schema=_clean_schema(d.parameters_json_schema),
                )
                for d in declarations
            ]
            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                input_audio_transcription=types.AudioTranscriptionConfig(),
                system_instruction=ConversationService._system_instruction(
                    settings.assistant_name,
                    settings.user_name,
                    self._memory.list_entries(),
                ),
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=settings.voice_name
                        )
                    )
                ),
                tools=[types.Tool(function_declarations=live_declarations)] if live_declarations else None,
            )
            candidates = model_ladder_service.get_candidates(
                task=TaskType.LIVE,
                requires_live_audio=True,
            )
            candidates = model_ladder_service.get_candidates(
                task=TaskType.LIVE,
                requires_live_audio=True,
            )
            # Ensure ladder candidates are tried along with operational Gemini Live models
            expanded_candidates: list[str] = []
            for m in candidates:
                if m not in expanded_candidates:
                    expanded_candidates.append(m)
            for m in (
                "gemini-2.0-flash-exp",
                "gemini-2.5-flash",
                "gemini-3.8-live",
                "models/gemini-2.0-flash-exp",
                "models/gemini-2.5-flash-native-audio-preview-12-2025",
            ):
                if m not in expanded_candidates:
                    expanded_candidates.append(m)

            hops = 0
            for index, model in enumerate(expanded_candidates):
                if hops >= MAX_LADDER_HOPS + 2:
                    break
                hops += 1
                try:
                    async with asyncio.timeout(6.0):
                        async with client.aio.live.connect(model=model, config=config) as session:
                            model_ladder_service.record_success(model)
                            await websocket.send_json({"type": "connected", "model": model})
                            await self._bridge(websocket, session)
                            return
                except errors.APIError as exc:
                    model_ladder_service.record_failure(model, exc.code)
                    if exc.code in (401, 403):
                        logger.error("Authentication error on Gemini Live model %s (HTTP %s)", model, exc.code)
                        raise
                    if exc.code in (404, 429, 500, 502, 503, 504, 1007, 1008) and index + 1 < len(expanded_candidates) and hops < MAX_LADDER_HOPS + 2:
                        next_model = expanded_candidates[index + 1]
                        model_ladder_service.emit_fallback(model, next_model, f"HTTP {exc.code}", TaskType.LIVE)
                        await websocket.send_json({
                            "type": "model_fallback",
                            "from_model": model,
                            "to_model": next_model,
                            "reason": f"HTTP {exc.code}",
                        })
                        logger.warning("Gemini Live model %s unavailable (HTTP %s); trying fallback %s", model, exc.code, next_model)
                        continue
                    raise
                except (TimeoutError, Exception) as exc:
                    logger.warning("Gemini Live connection to %s failed (%s); checking next fallback", model, exc)
                    if index + 1 < len(expanded_candidates) and hops < MAX_LADDER_HOPS + 2:
                        next_model = expanded_candidates[index + 1]
                        model_ladder_service.emit_fallback(model, next_model, str(exc), TaskType.LIVE)
                        await websocket.send_json({
                            "type": "model_fallback",
                            "from_model": model,
                            "to_model": next_model,
                            "reason": str(exc),
                        })
                        continue
                    raise
        except WebSocketDisconnect:
            return
        except (CredentialStoreError, StorageError):
            logger.exception("Could not prepare a Gemini Live voice session")
            await self._fail(websocket, "Alex could not load its local voice settings.", 1011)
        except Exception as exc:
            logger.exception("Gemini Live voice session failed")
            await self._fail(websocket, self._public_error(exc), 1011)
        finally:
            if client is not None:
                try:
                    await client.aio.aclose()
                except Exception:
                    logger.exception("Could not close the Gemini Live client")

    async def _bridge(self, websocket: WebSocket, session: Any) -> None:
        interrupted = False
        typed_text: str | None = None
        input_parts: list[str] = []
        output_parts: list[str] = []
        tool_calls_this_turn = 0
        is_executing_tool = False

        async def send_audio() -> None:
            nonlocal interrupted, typed_text, is_executing_tool
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    return
                pcm = message.get("bytes")
                if pcm is not None:
                    if len(pcm) < 2 or len(pcm) % 2:
                        raise ValueError("Microphone audio must contain complete PCM16 samples.")
                    if len(pcm) > _MAX_PCM_CHUNK_BYTES:
                        raise ValueError("Microphone audio chunk exceeds the 8 KiB limit.")
                    # CRITICAL: Suppress streaming realtime audio while a tool call is awaiting response!
                    # Gemini Live API drops WebSocket connections with 1008 Policy Violation if
                    # realtime audio chunks are sent while waiting for a tool response.
                    if is_executing_tool:
                        continue
                    try:
                        await session.send_realtime_input(
                            audio=types.Blob(data=pcm, mime_type="audio/pcm;rate=16000")
                        )
                    except Exception as exc:
                        logger.debug("Live audio input stream disconnected: %s", exc)
                        return
                    continue
                text = message.get("text")
                if text is None:
                    continue
                try:
                    control = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError("Voice control message is invalid.") from exc
                if not isinstance(control, dict):
                    raise ValueError("Voice control message is invalid.")
                if control.get("type") == "stop":
                    return
                if control.get("type") == "interrupt":
                    interrupted = True
                    await websocket.send_json({"type": "interrupted"})
                    continue
                if control.get("type") == "text":
                    text = control.get("text")
                    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
                        raise ValueError("Voice message must contain 1 to 4000 characters.")
                    typed_text = text.strip()
                    await session.send_client_content(
                        turns={
                            "role": "user",
                            "parts": [{"text": typed_text}],
                        },
                        turn_complete=True,
                    )
                    continue
                raise ValueError("Voice control message is unsupported.")

        async def receive_model() -> None:
            nonlocal interrupted, typed_text, tool_calls_this_turn, is_executing_tool
            while True:
                async for response in session.receive():
                    tool_call = getattr(response, "tool_call", None)
                    function_calls = getattr(tool_call, "function_calls", None)
                    if function_calls:
                        is_executing_tool = True
                        try:
                            tool_calls_this_turn += await self._handle_tool_calls(
                                session,
                                function_calls,
                                tool_calls_this_turn,
                            )
                        finally:
                            is_executing_tool = False
                    if response.data and not interrupted:
                        for offset in range(0, len(response.data), _PCM_CHUNK_BYTES):
                            await websocket.send_bytes(
                                response.data[offset : offset + _PCM_CHUNK_BYTES]
                            )

                    content = response.server_content
                    if content is None:
                        continue
                    if content.input_transcription and content.input_transcription.text:
                        self._append_transcript(input_parts, content.input_transcription.text)
                    if content.output_transcription and content.output_transcription.text:
                        self._append_transcript(output_parts, content.output_transcription.text)
                    if content.turn_complete:
                        was_interrupted = interrupted
                        await websocket.send_json(
                            {
                                "type": "turn_complete",
                                "input_text": (
                                    ""
                                    if was_interrupted
                                    else typed_text or "".join(input_parts).strip()
                                ),
                                "output_text": "" if was_interrupted else "".join(output_parts).strip(),
                                "interrupted": was_interrupted,
                            }
                        )
                        interrupted = False
                        typed_text = None
                        tool_calls_this_turn = 0
                        input_parts.clear()
                        output_parts.clear()

        tasks = [asyncio.create_task(send_audio()), asyncio.create_task(receive_model())]
        try:
            _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, WebSocketDisconnect):
                    continue
                if isinstance(result, asyncio.CancelledError):
                    continue
                if isinstance(result, BaseException):
                    raise result
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _append_transcript(parts: list[str], text: str) -> None:
        if not text:
            return
        incoming = text
        current = "".join(parts)
        if not current:
            parts.append(incoming.lstrip())
            return

        # Suffix-to-prefix overlap detection at word boundaries
        overlap = min(len(current), len(incoming))
        for size in range(overlap, 0, -1):
            if current.endswith(incoming[:size]):
                is_word_boundary_in_current = (size == len(current)) or current[-size - 1].isspace()
                is_word_boundary_in_incoming = (size == len(incoming)) or incoming[size].isspace() or incoming[:size].endswith(" ")
                if is_word_boundary_in_current or is_word_boundary_in_incoming:
                    remainder = incoming[size:]
                    if remainder:
                        parts.append(remainder)
                    return

        # No overlap: preserve English word spacing without squishing words together
        needs_space = (
            current
            and not current[-1].isspace()
            and not incoming.startswith(" ")
            and not incoming.startswith((".", ",", "!", "?", ";", ":", "'", "’", "-", "—"))
        )
        if needs_space:
            parts.append(" " + incoming)
        else:
            parts.append(incoming)

    async def _handle_tool_calls(
        self,
        session: Any,
        function_calls: list[Any],
        calls_this_turn: int,
    ) -> int:
        responses: list[types.FunctionResponse] = []
        for function_call in function_calls:
            name = getattr(function_call, "name", None)
            arguments = getattr(function_call, "args", None)
            call_id = getattr(function_call, "id", None)
            if not isinstance(name, str) or not isinstance(arguments, dict):
                raise ValueError("Gemini returned invalid action parameters.")
            try:
                argument_size = len(
                    json.dumps(arguments, ensure_ascii=True, allow_nan=False)
                )
            except (TypeError, ValueError):
                result = {"error": "Action parameters must be JSON values."}
            else:
                if argument_size > _MAX_TOOL_ARGUMENT_BYTES:
                    result = {"error": "Action parameters exceed the size limit."}
                elif calls_this_turn + len(responses) >= _MAX_TOOL_CALLS_PER_TURN:
                    result = {
                        "error": "The action limit for this conversation turn was reached."
                    }
                elif self._action_executor is None:
                    result = {"error": "Action execution is not available."}
                else:
                    action_id = name
                    if self._action_registry and not self._action_registry.get(action_id):
                        alt_name = name.replace("_", ".")
                        if self._action_registry.get(alt_name):
                            action_id = alt_name
                    execution = await self._action_executor.execute(action_id, arguments)
                    result = model_function_response(execution)
            responses.append(
                types.FunctionResponse(
                    id=call_id,
                    name=name,
                    response=result,
                )
            )
        await session.send_tool_response(function_responses=responses)
        return len(responses)

    @staticmethod
    def _public_error(error: Exception) -> str:
        if isinstance(error, errors.APIError):
            if error.code in (401, 403):
                return "Gemini rejected the saved API key. Check your credential in Settings."
            if error.code == 1008:
                return "Gemini Live policy violation (1008). Ensure your API key has Gemini Live access in Google AI Studio, or use chat mode."
            return f"Gemini voice session failed (HTTP {error.code})."
        if isinstance(error, ValueError):
            return str(error)
        return "Gemini voice session could not be started. Check your connection and try again."

    @staticmethod
    async def _fail(websocket: WebSocket, message: str, code: int) -> None:
        try:
            await websocket.send_json({"type": "error", "message": message})
            await asyncio.sleep(0.05)
            await websocket.close(code=code)
        except WebSocketDisconnect:
            logger.debug("Voice socket disconnected while reporting an error")
