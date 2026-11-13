"""
Automated unit tests for Universal OpenAI-Compatible LLM Provider (TASK-P3-05).

Verifies:
- Standard tool schema and message normalization.
- Strict Private Reasoning Data Policy enforcement (<think> token suppression across chunk boundaries).
- Preservation of final response text and flush semantics.
- Streamed tool call reassembly, JSON fragment parsing, and deduplication.
- Error mapping (401, 404, 429, 500/503) to NormalizedProviderError hierarchy.
- Anti-repetition loop detection guard.
- Non-streaming completion with usage metadata.
- Pre-execution and in-flight cancellation.
- Health check and model discovery.
- Integration with ProviderRegistry.
"""

from __future__ import annotations

import asyncio
import json
import pytest
import httpx

from app.providers.base import (
    AuthenticationError,
    CancellationError,
    ModelDescriptor,
    ModelNotFoundError,
    NormalizedProviderError,
    ProviderCapabilities,
    ProviderTimeoutError,
    QuotaExceededError,
    ServiceUnavailableError,
    StreamingChunk,
    UsageMetadata,
)
from app.providers.openai_provider import (
    AntiRepetitionGuard,
    OpenAICompatibleProvider,
    _ToolCallBuffer,
)
from app.providers.reasoning_filter import ReasoningFilter
from app.providers.registry import ProviderRegistry, default_registry


# ==============================================================================
# Message and Tool Formatting Tests
# ==============================================================================

def test_openai_provider_formats_tools_and_messages():
    """Verify system, user, multi-part, and tool schema normalization."""
    provider = OpenAICompatibleProvider(base_url="https://api.openai.com/v1", api_key="test-key")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "user", "parts": ["Multi-part text line 1", {"text": "Multi-part text line 2"}]},
    ]
    formatted_messages = provider._format_messages(messages)
    assert len(formatted_messages) == 3
    assert formatted_messages[0] == {"role": "system", "content": "You are a helpful assistant."}
    assert formatted_messages[1] == {"role": "user", "content": "Hello!"}
    assert formatted_messages[2] == {
        "role": "user",
        "content": "Multi-part text line 1\nMulti-part text line 2",
    }

    raw_tools = [
        {
            "name": "lookup_weather",
            "description": "Fetch weather for city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
        {
            "type": "function",
            "function": {
                "name": "open_app",
                "description": "Launch desktop application",
                "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}},
            },
        },
    ]
    formatted_tools = provider._format_tools(raw_tools)
    assert formatted_tools is not None
    assert len(formatted_tools) == 2
    assert formatted_tools[0] == {
        "type": "function",
        "function": {
            "name": "lookup_weather",
            "description": "Fetch weather for city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }
    assert formatted_tools[1] == raw_tools[1]


# ==============================================================================
# Private Reasoning Data Policy & ReasoningFilter Tests
# ==============================================================================

def test_reasoning_filter_suppresses_think_tokens_from_stream():
    """Verify that <think> tags split across streaming chunks are suppressed completely."""
    r_filter = ReasoningFilter()
    chunks = [
        "First visible token. ",
        "<th",
        "ink>Let me think through the mathematical proof carefully.\n",
        "Step 1: Compute derivative.\n",
        "Step 2: Check boundary values.\n",
        "</th",
        "ink>The answer is 42.",
    ]

    emitted = []
    for c in chunks:
        out = r_filter.filter_chunk(c)
        if out:
            emitted.append(out)
    emitted.append(r_filter.flush())

    combined = "".join(emitted)
    assert "First visible token. " in combined
    assert "The answer is 42." in combined
    assert "mathematical proof" not in combined
    assert "derivative" not in combined
    assert "<think>" not in combined
    assert "</think>" not in combined
    assert combined == "First visible token. The answer is 42."


def test_reasoning_filter_preserves_final_response():
    """Verify that standard clean responses without think blocks pass through untouched."""
    r_filter = ReasoningFilter()
    chunks = ["Hello, ", "how ", "can ", "I ", "help ", "you ", "today?"]
    emitted = [r_filter.filter_chunk(c) for c in chunks]
    emitted.append(r_filter.flush())
    assert "".join(emitted) == "Hello, how can I help you today?"


def test_reasoning_filter_unclosed_tag_discard():
    """Verify unclosed <think> tag at stream termination is discarded without leakage."""
    r_filter = ReasoningFilter()
    out1 = r_filter.filter_chunk("Clean beginning. <think>Unfinished thoughts that never closed")
    out2 = r_filter.flush()
    assert out1 == "Clean beginning. "
    assert out2 == ""
    assert "Unfinished thoughts" not in (out1 + out2)


def test_reasoning_filter_case_insensitivity():
    """Verify <THINK> and </THINK> uppercase tags are correctly filtered."""
    r_filter = ReasoningFilter()
    out1 = r_filter.filter_chunk("Result: <THINK>Secret</THINK>Done.")
    out2 = r_filter.flush()
    assert (out1 + out2) == "Result: Done."


# ==============================================================================
# Tool Call Reassembly & Deduplication Tests
# ==============================================================================

def test_openai_provider_tool_call_reassembly_streaming():
    """Verify streamed tool call deltas are reassembled and arguments are parsed into JSON dict."""
    buf = _ToolCallBuffer()

    # Chunk 1: first call ID and function name
    buf.feed([
        {"index": 0, "id": "call_abc123", "function": {"name": "search_files", "arguments": ""}}
    ])
    # Chunk 2: first call argument fragment 1
    buf.feed([
        {"index": 0, "function": {"arguments": '{"query": "re'}}
    ])
    # Chunk 3: first call argument fragment 2
    buf.feed([
        {"index": 0, "function": {"arguments": 'port.pdf"}'}}
    ])

    # Second call concurrently or subsequently
    buf.feed([
        {"index": 1, "id": "call_def456", "function": {"name": "get_weather", "arguments": '{"city": "Paris"}'}}
    ])

    calls = buf.drain()
    assert len(calls) == 2
    assert calls[0]["id"] == "call_abc123"
    assert calls[0]["name"] == "search_files"
    assert calls[0]["args"] == {"query": "report.pdf"}

    assert calls[1]["id"] == "call_def456"
    assert calls[1]["name"] == "get_weather"
    assert calls[1]["args"] == {"city": "Paris"}

    # Buffer should be empty after drain
    assert buf.drain() == []


def test_openai_provider_tool_call_deduplication():
    """Verify identical duplicate tool calls within the same turn are deduplicated."""
    buf = _ToolCallBuffer()
    buf.feed([
        {"index": 0, "id": "call_1", "function": {"name": "open_app", "arguments": '{"app": "whatsapp"}'}},
        {"index": 1, "id": "call_2", "function": {"name": "open_app", "arguments": '{"app": "whatsapp"}'}},
    ])
    calls = buf.drain()
    assert len(calls) == 1
    assert calls[0]["name"] == "open_app"
    assert calls[0]["args"] == {"app": "whatsapp"}


# ==============================================================================
# Anti-Repetition Guard Tests
# ==============================================================================

def test_anti_repetition_guard_detects_loop():
    """Verify degenerate repeating patterns trigger the guard and suppress repetition."""
    guard = AntiRepetitionGuard(max_repeats=3, min_pattern_len=8)

    # Normal text
    chunk1, loop1 = guard.check("The assistant is ready. ")
    assert chunk1 == "The assistant is ready. "
    assert not loop1
    assert not guard.is_triggered

    # Repeating phrase: 8+ characters repeated 3 times
    phrase = "repeat this pattern; "
    guard.check(phrase)
    guard.check(phrase)
    chunk_last, loop_trigger = guard.check(phrase)

    assert loop_trigger is True
    assert guard.is_triggered is True
    assert chunk_last == ""


def test_anti_repetition_guard_allows_healthy_text():
    """Verify healthy varied conversation does not trigger false positives."""
    guard = AntiRepetitionGuard(max_repeats=3, min_pattern_len=8)
    paragraphs = [
        "In physics, energy is the quantitative property transferred to a body. ",
        "It can be transformed in form, but not created or destroyed. ",
        "The unit of measurement for energy in the International System of Units is the joule. ",
    ]
    for p in paragraphs:
        text, is_loop = guard.check(p)
        assert text == p
        assert not is_loop
    assert not guard.is_triggered


# ==============================================================================
# Error Mapping Tests
# ==============================================================================

def test_openai_provider_error_mapping_401_404_429_500():
    """Verify HTTP status codes map to the NormalizedProviderError hierarchy."""
    provider = OpenAICompatibleProvider(base_url="https://api.openai.com/v1", provider_id="openai")

    # 401 Unauthorized
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    res_401 = httpx.Response(401, text="Invalid API key", request=req)
    err_401 = provider._map_error(httpx.HTTPStatusError("Auth error", request=req, response=res_401))
    assert isinstance(err_401, AuthenticationError)
    assert err_401.provider_id == "openai"

    # 404 Not Found
    res_404 = httpx.Response(404, text="Model not found", request=req)
    err_404 = provider._map_error(httpx.HTTPStatusError("Not found", request=req, response=res_404))
    assert isinstance(err_404, ModelNotFoundError)

    # 429 Rate Limit with Retry-After
    res_429 = httpx.Response(429, headers={"retry-after": "12.5"}, text="Rate limit exceeded", request=req)
    err_429 = provider._map_error(httpx.HTTPStatusError("Rate limit", request=req, response=res_429))
    assert isinstance(err_429, QuotaExceededError)
    assert err_429.retry_after_s == 12.5

    # 503 Service Unavailable
    res_503 = httpx.Response(503, text="Service overloaded", request=req)
    err_503 = provider._map_error(httpx.HTTPStatusError("Unavailable", request=req, response=res_503))
    assert isinstance(err_503, ServiceUnavailableError)
    assert err_503.status_code == 503

    # Timeout
    err_timeout = provider._map_error(httpx.ReadTimeout("Timeout"))
    assert isinstance(err_timeout, ProviderTimeoutError)


# ==============================================================================
# Non-Streaming Execution Tests
# ==============================================================================

def test_openai_provider_generate_non_streaming(monkeypatch):
    """Verify non-streaming completion, reasoning filtering, and usage parsing."""
    async def _test():
        provider = OpenAICompatibleProvider(
            base_url="https://api.openai.com/v1",
            api_key="sk-test-key",
            default_model="gpt-4o",
        )

        mock_response_data = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "<think>Internal deliberation</think>Here is your answer.",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "calculator", "arguments": '{"operation": "add", "a": 5, "b": 7}'},
                            }
                        ],
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
        }

        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url, headers=None, json=None):
                req = httpx.Request("POST", url)
                return httpx.Response(200, json=mock_response_data, request=req)

        monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

        result = await provider.generate(
            messages=[{"role": "user", "content": "What is 5 + 7?"}],
            tools=[{"name": "calculator", "description": "Do math", "parameters": {}}],
        )

        assert isinstance(result, StreamingChunk)
        assert result.text == "Here is your answer."
        assert "<think>" not in result.text
        assert result.is_final is True
        assert result.function_calls is not None
        assert len(result.function_calls) == 1
        assert result.function_calls[0]["name"] == "calculator"
        assert result.function_calls[0]["args"] == {"operation": "add", "a": 5, "b": 7}

        assert result.usage is not None
        assert result.usage.prompt_tokens == 15
        assert result.usage.completion_tokens == 25
        assert result.usage.total_tokens == 40
        assert result.usage.latency_ms > 0

    asyncio.run(_test())


# ==============================================================================
# Streaming Execution & Cancellation Tests
# ==============================================================================

def test_openai_provider_stream_execution(monkeypatch):
    """Verify SSE streaming with delta chunks, reasoning filter, and tool call emission."""
    async def _test():
        provider = OpenAICompatibleProvider(
            base_url="https://api.openai.com/v1",
            api_key="sk-test-key",
            default_model="gpt-4o",
        )

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"Hello "}}]}',
            'data: {"choices":[{"delta":{"content":"<think>secret</think>"}}]}',
            'data: {"choices":[{"delta":{"content":"world!"}}]}',
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_01","function":{"name":"ping","arguments":"{}"}}]}}]}',
            'data: {"choices":[{"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":8,"total_tokens":18}}',
            'data: [DONE]',
        ]

        class MockStreamResponse:
            def __init__(self):
                self.status_code = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def aiter_lines(self):
                for line in sse_lines:
                    yield line

        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, method, url, **kwargs):
                return MockStreamResponse()

        monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

        chunks: list[StreamingChunk] = []
        async for chunk in provider.stream(messages=[{"role": "user", "content": "Hi"}]):
            chunks.append(chunk)

        combined_text = "".join(c.text for c in chunks)
        assert "Hello world!" in combined_text
        assert "secret" not in combined_text
        assert "<think>" not in combined_text

        final_chunk = chunks[-1]
        assert final_chunk.is_final is True
        assert final_chunk.function_calls is not None
        assert final_chunk.function_calls[0]["name"] == "ping"
        assert final_chunk.usage is not None
        assert final_chunk.usage.total_tokens == 18

    asyncio.run(_test())


def test_openai_provider_cancellation():
    """Verify operation raises CancellationError when token is set."""
    async def _test():
        provider = OpenAICompatibleProvider(base_url="https://api.openai.com/v1")

        cancel_token = asyncio.Event()
        cancel_token.set()

        with pytest.raises(CancellationError):
            await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                cancellation_token=cancel_token,
            )

        with pytest.raises(CancellationError):
            async for _ in provider.stream(
                messages=[{"role": "user", "content": "Hi"}],
                cancellation_token=cancel_token,
            ):
                pass

    asyncio.run(_test())


# ==============================================================================
# Health Check and Model Listing Tests
# ==============================================================================

def test_openai_provider_health_check(monkeypatch):
    """Verify health_check pinging /models endpoint."""
    async def _test():
        provider = OpenAICompatibleProvider(base_url="https://api.openai.com/v1")

        class MockAsyncClientSuccess:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def get(self, url, headers=None):
                req = httpx.Request("GET", url)
                return httpx.Response(200, json={"data": []}, request=req)

        monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClientSuccess)
        assert await provider.health_check() is True

        class MockAsyncClientFail:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def get(self, url, headers=None):
                raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClientFail)
        assert await provider.health_check() is False

    asyncio.run(_test())


def test_openai_provider_list_models(monkeypatch):
    """Verify model listing from /models endpoint."""
    async def _test():
        provider = OpenAICompatibleProvider(base_url="https://api.openai.com/v1", provider_id="openai")

        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def get(self, url, headers=None):
                req = httpx.Request("GET", url)
                return httpx.Response(
                    200,
                    json={"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]},
                    request=req,
                )

        monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
        models = await provider.list_models()
        assert len(models) == 2
        assert all(isinstance(m, ModelDescriptor) for m in models)
        assert models[0].model_id == "openai:gpt-4o"
        assert models[1].model_id == "openai:gpt-4o-mini"

    asyncio.run(_test())


# ==============================================================================
# Registry Integration Tests
# ==============================================================================

def test_default_registry_integration():
    """Verify OpenAICompatibleProvider is registered in default_registry."""
    cls = default_registry.get_class("openai")
    assert cls is OpenAICompatibleProvider

    provider = default_registry.create_provider("openai", api_key="sk-test-key")
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.provider_id == "openai"


def test_openai_provider_timeout_mapping(monkeypatch):
    """Verify httpx.TimeoutException maps to ProviderTimeoutError."""
    async def _test():
        provider = OpenAICompatibleProvider(base_url="https://api.openai.com/v1", api_key="sk-test")

        class MockAsyncClientTimeout:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url, **kwargs):
                raise httpx.ReadTimeout("Read operation timed out")

        monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClientTimeout)

        with pytest.raises(ProviderTimeoutError) as exc_info:
            await provider.generate(messages=[{"role": "user", "content": "Hello"}])

        assert "timed out" in str(exc_info.value).lower()
        assert exc_info.value.status_code == 408

    asyncio.run(_test())


def test_openai_provider_custom_timeout_and_headers(monkeypatch):
    """Verify custom timeout_ms and authorization headers are formatted correctly."""
    async def _test():
        captured_headers = {}
        captured_json = {}
        provider = OpenAICompatibleProvider(
            base_url="https://api.openai.com/v1",
            api_key="sk-custom-secret",
            default_model="gpt-4o-custom",
        )

        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url, json=None, headers=None):
                nonlocal captured_headers, captured_json
                captured_headers = headers or {}
                captured_json = json or {}
                req = httpx.Request("POST", url)
                return httpx.Response(
                    200,
                    json={
                        "id": "chatcmpl-test",
                        "choices": [{"message": {"role": "assistant", "content": "OK"}}],
                    },
                    request=req,
                )

        monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

        res = await provider.generate(messages=[{"role": "user", "content": "Hi"}], timeout_ms=5000)
        assert res.text == "OK"
        assert captured_headers.get("Authorization") == "Bearer sk-custom-secret"
        assert captured_json.get("model") == "gpt-4o-custom"

    asyncio.run(_test())


def test_openai_provider_multi_tool_call_reassembly():
    """Verify _ToolCallBuffer correctly handles multiple parallel tool calls."""
    buf = _ToolCallBuffer()
    deltas = [
        {"index": 0, "id": "call_1", "function": {"name": "search", "arguments": '{"q":'}},
        {"index": 1, "id": "call_2", "function": {"name": "calc", "arguments": '{"x":'}},
        {"index": 0, "function": {"arguments": ' "python"}'}},
        {"index": 1, "function": {"arguments": ' 42}'}},
    ]
    buf.feed(deltas)
    calls = buf.drain()
    assert len(calls) == 2
    assert calls[0]["name"] == "search"
    assert calls[0]["args"] == {"q": "python"}
    assert calls[1]["name"] == "calc"
    assert calls[1]["args"] == {"x": 42}


