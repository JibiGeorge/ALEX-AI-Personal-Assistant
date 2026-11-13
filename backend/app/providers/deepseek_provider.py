"""
DeepSeek Cloud AI Provider.

Cloud inference provider interfacing with DeepSeek API at https://api.deepseek.com/v1,
supporting deepseek-chat (DeepSeek-V3) and deepseek-reasoner (DeepSeek-R1).
Credentials are automatically resolved from OS Keyring under 'deepseek-api-key'
with environment variable fallback 'DEEPSEEK_API_KEY'.

Strictly enforces the Private Reasoning Data Policy:
Extracts and isolates reasoning_content from deepseek-reasoner without leaking
internal chain-of-thought into the speech pipeline, React HUD transcript, or persistent history.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.providers.base import (
    CancellationError,
    NormalizedProviderError,
    ProviderCapabilities,
    StreamingChunk,
    UsageMetadata,
    validate_base_url,
)
from app.providers.openai_provider import (
    AntiRepetitionGuard,
    OpenAICompatibleProvider,
    _ToolCallBuffer,
)
from app.providers.reasoning_filter import ReasoningFilter
from app.providers.registry import default_registry

logger = logging.getLogger(__name__)

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_KEYRING_KEY = "deepseek-api-key"
DEEPSEEK_ENV_VAR = "DEEPSEEK_API_KEY"


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek Cloud LLM Provider with reasoning model isolation."""

    def __init__(
        self,
        base_url: str = DEFAULT_DEEPSEEK_BASE_URL,
        api_key: Optional[str] = None,
        default_model: str = DEFAULT_DEEPSEEK_MODEL,
        provider_id: str = "deepseek",
        timeout_s: float = 60.0,
        capabilities: Optional[ProviderCapabilities] = None,
    ) -> None:
        resolved_key = api_key or default_registry.resolve_credential(
            DEEPSEEK_KEYRING_KEY, env_var=DEEPSEEK_ENV_VAR
        ) or ""

        deepseek_caps = capabilities or ProviderCapabilities(
            vision=False,
            function_calling=True,
            streaming=True,
            max_context_tokens=64000,
            tool_format="openai",
        )

        super().__init__(
            base_url=base_url,
            api_key=resolved_key,
            default_model=default_model,
            provider_id=provider_id,
            timeout_s=timeout_s,
            capabilities=deepseek_caps,
            is_local=False,
        )
        self._last_reasoning_content: str = ""

    @property
    def last_reasoning_content(self) -> str:
        """Internal diagnostic accessor for isolated reasoning content."""
        return self._last_reasoning_content

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_ms: int = 30000,
        cancellation_token: Optional[asyncio.Event] = None,
    ) -> StreamingChunk:
        """Execute non-streaming completion, isolating any reasoning_content from user-visible text."""
        self._last_reasoning_content = ""
        if cancellation_token and cancellation_token.is_set():
            raise CancellationError("Operation cancelled before execution", provider_id=self._provider_id)

        timeout_sec = min(timeout_ms / 1000.0, self._timeout_s)
        endpoint = f"{self._base_url}/chat/completions"

        payload: Dict[str, Any] = {
            "model": self._default_model,
            "messages": self._format_messages(messages),
            "stream": False,
        }
        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            payload["tools"] = formatted_tools

        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                res = await client.post(endpoint, headers=self._headers(), json=payload)
                if res.status_code >= 400:
                    res.raise_for_status()
                data = res.json()
        except Exception as exc:
            raise self._map_error(exc)

        latency_ms = (time.monotonic() - start_time) * 1000.0

        choices = data.get("choices", [])
        raw_text = ""
        function_calls: Optional[List[Dict[str, Any]]] = None

        if choices:
            msg = choices[0].get("message", {})
            raw_text = msg.get("content") or ""
            # Extract and isolate reasoning_content if emitted by deepseek-reasoner
            self._last_reasoning_content = msg.get("reasoning_content") or ""

            raw_tool_calls = msg.get("tool_calls")
            if raw_tool_calls:
                buf = _ToolCallBuffer()
                buf.feed([{"index": i, **tc} for i, tc in enumerate(raw_tool_calls)])
                calls = buf.drain()
                if calls:
                    function_calls = calls

        # Apply Private Reasoning Data Policy filter to remove any <think> blocks from content
        r_filter = ReasoningFilter()
        visible_text = r_filter.filter_chunk(raw_text) + r_filter.flush()

        usage_info = data.get("usage", {})
        usage = UsageMetadata(
            provider_id=self._provider_id,
            model_id=self._default_model,
            prompt_tokens=usage_info.get("prompt_tokens", 0),
            completion_tokens=usage_info.get("completion_tokens", 0),
            total_tokens=usage_info.get("total_tokens", 0),
            latency_ms=latency_ms,
        )

        return StreamingChunk(
            text=visible_text,
            function_calls=function_calls,
            is_final=True,
            usage=usage,
        )

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_ms: int = 30000,
        cancellation_token: Optional[asyncio.Event] = None,
    ) -> AsyncIterator[StreamingChunk]:
        """Stream chunks via SSE, isolating reasoning_content and suppressing <think> tokens."""
        self._last_reasoning_content = ""
        if cancellation_token and cancellation_token.is_set():
            raise CancellationError("Streaming cancelled before execution", provider_id=self._provider_id)

        timeout_sec = min(timeout_ms / 1000.0, self._timeout_s)
        endpoint = f"{self._base_url}/chat/completions"

        payload: Dict[str, Any] = {
            "model": self._default_model,
            "messages": self._format_messages(messages),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            payload["tools"] = formatted_tools

        start_time = time.monotonic()
        r_filter = ReasoningFilter()
        anti_rep = AntiRepetitionGuard()
        tool_buffer = _ToolCallBuffer()
        accumulated_usage: Optional[UsageMetadata] = None

        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                async with client.stream("POST", endpoint, headers=self._headers(), json=payload) as response:
                    if response.status_code != 200:
                        await response.aread()
                        response.raise_for_status()

                    async for line in response.aiter_lines():
                        if cancellation_token and cancellation_token.is_set():
                            raise CancellationError("Streaming cancelled by client", provider_id=self._provider_id)

                        clean_line = line.strip()
                        if not clean_line or clean_line.startswith(":"):
                            continue
                        if clean_line == "data: [DONE]":
                            break

                        if clean_line.startswith("data: "):
                            raw_json = clean_line[6:].strip()
                            try:
                                chunk_data = json.loads(raw_json)
                            except json.JSONDecodeError:
                                continue

                            usage_dict = chunk_data.get("usage")
                            if usage_dict:
                                accumulated_usage = UsageMetadata(
                                    provider_id=self._provider_id,
                                    model_id=self._default_model,
                                    prompt_tokens=usage_dict.get("prompt_tokens", 0),
                                    completion_tokens=usage_dict.get("completion_tokens", 0),
                                    total_tokens=usage_dict.get("total_tokens", 0),
                                    latency_ms=(time.monotonic() - start_time) * 1000.0,
                                )

                            choices = chunk_data.get("choices", [])
                            if not choices:
                                continue

                            delta = choices[0].get("delta", {})

                            # Intercept and isolate reasoning_content delta
                            reasoning_delta = delta.get("reasoning_content")
                            if reasoning_delta:
                                self._last_reasoning_content += reasoning_delta

                            content_delta = delta.get("content") or ""
                            tool_deltas = delta.get("tool_calls")
                            if tool_deltas:
                                tool_buffer.feed(tool_deltas)

                            finish_reason = choices[0].get("finish_reason")
                            is_final = finish_reason is not None

                            # Apply Private Reasoning Data Policy filter on visible content
                            filtered_text = r_filter.filter_chunk(content_delta)
                            if is_final:
                                filtered_text += r_filter.flush()

                            # Apply Anti-Repetition Guard
                            safe_text, is_loop = anti_rep.check(filtered_text)
                            if is_loop:
                                is_final = True

                            if safe_text or is_final:
                                calls = tool_buffer.drain() if is_final else None
                                yield StreamingChunk(
                                    text=safe_text,
                                    function_calls=calls if calls else None,
                                    is_final=is_final,
                                    usage=accumulated_usage if is_final else None,
                                )
                            if is_loop:
                                logger.info("Ending stream early due to anti-repetition guard trigger.")
                                break
        except Exception as exc:
            if isinstance(exc, NormalizedProviderError):
                raise
            raise self._map_error(exc)

