"""
Universal OpenAI-Compatible LLM Provider.

Interfaces with any vendor or local server implementing the OpenAI /v1/chat/completions
and /v1/models specifications (e.g. Ollama, LM Studio, Groq, DeepSeek, OpenAI).
Includes streaming support, tool call reassembly & deduplication, anti-repetition detection,
and strict Private Reasoning Data Policy enforcement via ReasoningFilter.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.providers.base import (
    AuthenticationError,
    CancellationError,
    LLMProvider,
    ModelDescriptor,
    ModelNotFoundError,
    NormalizedProviderError,
    ProviderCapabilities,
    ProviderTimeoutError,
    QuotaExceededError,
    ServiceUnavailableError,
    StreamingChunk,
    UsageMetadata,
    redact_secret,
    validate_base_url,
)
from app.providers.reasoning_filter import ReasoningFilter

logger = logging.getLogger(__name__)


class _ToolCallBuffer:
    """Reassembles fragmented tool calls emitted during SSE streaming and deduplicates repeats."""

    def __init__(self) -> None:
        self._slots: Dict[int, Dict[str, str]] = {}

    def feed(self, deltas: List[Dict[str, Any]]) -> None:
        for d in deltas or []:
            idx = d.get("index", 0)
            slot = self._slots.setdefault(idx, {"id": "", "name": "", "args": ""})
            if d.get("id"):
                slot["id"] = d["id"]
            fn = d.get("function") or {}
            if fn.get("name"):
                slot["name"] += fn["name"]
            if fn.get("arguments"):
                slot["args"] += fn["arguments"]

    def drain(self) -> List[Dict[str, Any]]:
        calls = []
        seen_signatures = set()
        for idx in sorted(self._slots.keys()):
            slot = self._slots[idx]
            if not slot["name"]:
                continue
            raw_args = slot["args"].strip() or "{}"
            try:
                parsed_args = json.loads(raw_args)
            except Exception:
                if "{" in raw_args and "}" in raw_args:
                    try:
                        parsed_args = json.loads(raw_args[raw_args.find("{"):raw_args.rfind("}") + 1])
                    except Exception:
                        parsed_args = {}
                else:
                    parsed_args = {"value": raw_args}
            if not isinstance(parsed_args, dict):
                parsed_args = {"value": parsed_args}

            sig = (slot["name"], json.dumps(parsed_args, sort_keys=True))
            if sig in seen_signatures:
                logger.warning("Deduplicating repeated tool call in same turn: %s", slot["name"])
                continue
            seen_signatures.add(sig)

            calls.append({
                "id": slot["id"] or f"call_{idx}",
                "name": slot["name"],
                "args": parsed_args,
            })
        self._slots.clear()
        return calls


class AntiRepetitionGuard:
    """Detects degenerate repetition loops in streamed text chunks.
    
    If a generated substring of sufficient length repeats consecutively
    beyond max_repeats, the guard flags repetition and suppresses the duplicate loop.
    """

    def __init__(self, max_repeats: int = 3, min_pattern_len: int = 8) -> None:
        self.max_repeats = max_repeats
        self.min_pattern_len = min_pattern_len
        self._full_text: str = ""
        self._triggered: bool = False

    def check(self, chunk: str) -> tuple[str, bool]:
        """Check chunk against historical text. Returns (allowed_chunk, is_repeating)."""
        if self._triggered or not chunk:
            return "", self._triggered

        self._full_text += chunk
        total_len = len(self._full_text)

        # Scan for repeating suffix patterns
        max_scan = min(300, total_len // self.max_repeats)
        for p_len in range(self.min_pattern_len, max_scan + 1):
            pattern = self._full_text[-p_len:]
            repeats = 0
            pos = total_len
            while pos >= p_len and self._full_text[pos - p_len:pos] == pattern:
                repeats += 1
                pos -= p_len
                if repeats >= self.max_repeats:
                    self._triggered = True
                    logger.warning("Anti-repetition guard detected degenerate loop for pattern %r (%d times)", pattern, repeats)
                    return "", True

        return chunk, False

    @property
    def is_triggered(self) -> bool:
        return self._triggered


class OpenAICompatibleProvider(LLMProvider):
    """Universal OpenAI-compatible chat completion provider."""

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: Optional[str] = None,
        default_model: str = "gpt-4o",
        provider_id: str = "openai",
        timeout_s: float = 60.0,
        capabilities: Optional[ProviderCapabilities] = None,
        is_local: bool = False,
    ) -> None:
        self._base_url = validate_base_url(base_url)
        self._api_key = api_key or ""
        self._default_model = default_model
        self._provider_id = provider_id
        self._timeout_s = timeout_s
        self._is_local = is_local
        self._capabilities = capabilities or ProviderCapabilities(
            vision=True,
            function_calling=True,
            streaming=True,
            max_context_tokens=128000,
        )

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    @property
    def base_url(self) -> str:
        return self._base_url

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _map_error(self, exc: Exception) -> NormalizedProviderError:
        """Map httpx errors and HTTP status codes to NormalizedProviderError hierarchy."""
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            msg = exc.response.text or str(exc)
            if code in (401, 403):
                return AuthenticationError(f"Authentication failed: {msg}", provider_id=self._provider_id, original_error=exc)
            if code == 404:
                return ModelNotFoundError(f"Model or endpoint not found: {msg}", provider_id=self._provider_id, original_error=exc)
            if code == 429:
                retry_after: Optional[float] = None
                raw_header = exc.response.headers.get("retry-after")
                if raw_header:
                    try:
                        retry_after = float(raw_header)
                    except ValueError:
                        pass
                return QuotaExceededError(f"Rate limit exceeded: {msg}", provider_id=self._provider_id, retry_after_s=retry_after, original_error=exc)
            if code in (500, 502, 503, 504):
                return ServiceUnavailableError(f"Service unavailable (HTTP {code}): {msg}", status_code=code, provider_id=self._provider_id, original_error=exc)
            return NormalizedProviderError(f"HTTP {code} error: {msg}", status_code=code, provider_id=self._provider_id, original_error=exc)

        if isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError)):
            return ProviderTimeoutError(f"Request to {self._provider_id} timed out", provider_id=self._provider_id, original_error=exc)

        return ServiceUnavailableError(f"Network error connecting to {self._provider_id}: {exc}", provider_id=self._provider_id, original_error=exc)

    async def health_check(self) -> bool:
        """Ping provider by querying /models."""
        endpoint = f"{self._base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(endpoint, headers=self._headers())
                return res.status_code == 200
        except Exception as exc:
            logger.debug("Health check failed for %s: %s", self._provider_id, exc)
            return False

    async def list_models(self) -> List[ModelDescriptor]:
        """Fetch available models from /v1/models endpoint."""
        endpoint = f"{self._base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                res = await client.get(endpoint, headers=self._headers())
                if res.status_code >= 400:
                    res.raise_for_status()
                data = res.json()
        except Exception as exc:
            logger.warning("Failed to list models from %s: %s", self._provider_id, exc)
            raise self._map_error(exc)

        items = data.get("data", []) if isinstance(data, dict) else []
        models: List[ModelDescriptor] = []
        for item in items:
            m_id = item.get("id") or item.get("name")
            if m_id:
                models.append(
                    ModelDescriptor(
                        model_id=f"{self._provider_id}:{m_id}" if not m_id.startswith(f"{self._provider_id}:") else m_id,
                        display_name=str(m_id),
                        provider_name=self._provider_id,
                        capabilities=self._capabilities,
                        is_local=self._is_local,
                    )
                )
        return models

    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize messages into standard OpenAI chat completion shape."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # If parts format (Gemini style) is passed, adapt it
            if "parts" in msg and not content:
                parts = msg["parts"]
                text_parts = []
                for p in parts:
                    if isinstance(p, str):
                        text_parts.append(p)
                    elif isinstance(p, dict) and "text" in p:
                        text_parts.append(p["text"])
                content = "\n".join(text_parts)
            formatted.append({"role": role, "content": content})
        return formatted

    def _format_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """Normalize tools into standard OpenAI chat completion function tool schema."""
        if not tools:
            return None
        formatted: List[Dict[str, Any]] = []
        for t in tools:
            if not isinstance(t, dict):
                continue
            if t.get("type") == "function" and isinstance(t.get("function"), dict):
                formatted.append(t)
            elif "name" in t:
                params = t.get("parameters") or t.get("parameters_schema") or {"type": "object", "properties": {}}
                formatted.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": params,
                    },
                })
            else:
                formatted.append(t)
        return formatted if formatted else None

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_ms: int = 30000,
        cancellation_token: Optional[asyncio.Event] = None,
    ) -> StreamingChunk:
        """Execute a non-streaming completion call."""
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
            raw_tool_calls = msg.get("tool_calls")
            if raw_tool_calls:
                buf = _ToolCallBuffer()
                buf.feed([{"index": i, **tc} for i, tc in enumerate(raw_tool_calls)])
                calls = buf.drain()
                if calls:
                    function_calls = calls

        # Apply Private Reasoning Data Policy filter to remove any <think> blocks
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
        """Stream chunks via SSE, filtering <think> tokens, guarding against loops, and reassembling tool calls."""
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

                            # Capture usage if provided in chunk
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
                            content_delta = delta.get("content") or ""
                            tool_deltas = delta.get("tool_calls")
                            if tool_deltas:
                                tool_buffer.feed(tool_deltas)

                            finish_reason = choices[0].get("finish_reason")
                            is_final = finish_reason is not None

                            # Apply Private Reasoning Data Policy filter
                            filtered_text = r_filter.filter_chunk(content_delta)
                            if is_final:
                                filtered_text += r_filter.flush()

                            # Apply Anti-Repetition Guard
                            safe_text, is_loop = anti_rep.check(filtered_text)
                            if is_loop:
                                is_final = True

                            # If anything to emit
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

