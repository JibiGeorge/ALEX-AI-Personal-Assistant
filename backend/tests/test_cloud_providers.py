"""
Automated unit tests for Cloud AI Providers (Groq & DeepSeek) - TASK-P3-06.

Verifies:
- Groq provider initialization with OS Keyring resolution and environment variable fallback.
- Groq streaming completion and capability configuration.
- DeepSeek provider initialization with OS Keyring resolution.
- DeepSeek reasoner isolation: extraction of reasoning_content without leaking into
  the visible user text, TTS audio stream, or conversation history.
- DeepSeek streaming with delta reasoning_content.
- Private Reasoning Data Policy adherence (<think> / <reasoning> tags filtered).
- Integration and registration in default_registry.
"""

from __future__ import annotations

import asyncio
import json
import httpx
import keyring
import pytest

from app.providers.base import (
    AuthenticationError,
    CancellationError,
    ModelDescriptor,
    NormalizedProviderError,
    StreamingChunk,
    UsageMetadata,
)
from app.providers.deepseek_provider import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEEPSEEK_KEYRING_KEY,
    DeepSeekProvider,
)
from app.providers.groq_provider import (
    DEFAULT_GROQ_BASE_URL,
    GROQ_KEYRING_KEY,
    GroqProvider,
)
from app.providers.registry import default_registry


# ==============================================================================
# Groq Provider Tests
# ==============================================================================

def test_groq_provider_initialization_with_keyring_secret(monkeypatch):
    """Verify GroqProvider resolves API key from OS Keyring under 'groq-api-key'."""
    def fake_get_password(service_name, key_name):
        if key_name == GROQ_KEYRING_KEY:
            return "gsk_test_keyring_secret_12345"
        return None

    monkeypatch.setattr(keyring, "get_password", fake_get_password)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    provider = GroqProvider()
    assert provider.provider_id == "groq"
    assert provider.base_url == DEFAULT_GROQ_BASE_URL
    assert provider._api_key == "gsk_test_keyring_secret_12345"
    assert provider.capabilities.function_calling is True
    assert provider.capabilities.streaming is True
    assert provider.capabilities.max_context_tokens == 128000


def test_groq_provider_env_var_fallback(monkeypatch):
    """Verify GroqProvider falls back to GROQ_API_KEY environment variable."""
    monkeypatch.setattr(keyring, "get_password", lambda svc, key: None)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_env_fallback_999")

    provider = GroqProvider()
    assert provider._api_key == "gsk_env_fallback_999"


def test_groq_provider_streaming_chat(monkeypatch):
    """Verify Groq streaming chat completion execution."""
    async def _test():
        provider = GroqProvider(api_key="gsk_explicit_key")

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"Fast "}}]}',
            'data: {"choices":[{"delta":{"content":"inference "}}]}',
            'data: {"choices":[{"delta":{"content":"from Groq LPU."}}]}',
            'data: {"choices":[{"finish_reason":"stop"}],"usage":{"prompt_tokens":12,"completion_tokens":6,"total_tokens":18}}',
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
        async for chunk in provider.stream(messages=[{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)

        full_text = "".join(c.text for c in chunks)
        assert full_text == "Fast inference from Groq LPU."
        assert chunks[-1].is_final is True
        assert chunks[-1].usage is not None
        assert chunks[-1].usage.total_tokens == 18

    asyncio.run(_test())


# ==============================================================================
# DeepSeek Provider Tests
# ==============================================================================

def test_deepseek_provider_initialization_with_keyring_secret(monkeypatch):
    """Verify DeepSeekProvider resolves API key from OS Keyring under 'deepseek-api-key'."""
    def fake_get_password(service_name, key_name):
        if key_name == DEEPSEEK_KEYRING_KEY:
            return "sk_deepseek_keyring_secret_abc"
        return None

    monkeypatch.setattr(keyring, "get_password", fake_get_password)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    provider = DeepSeekProvider()
    assert provider.provider_id == "deepseek"
    assert provider.base_url == DEFAULT_DEEPSEEK_BASE_URL
    assert provider._api_key == "sk_deepseek_keyring_secret_abc"
    assert provider.capabilities.max_context_tokens == 64000


def test_deepseek_reasoner_extracts_reasoning_content(monkeypatch):
    """Verify deepseek-reasoner non-streaming response extracts reasoning_content without leaking it."""
    async def _test():
        provider = DeepSeekProvider(api_key="sk_ds_test", default_model="deepseek-reasoner")

        mock_response = {
            "id": "ds-12345",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "The square root of 144 is 12.",
                        "reasoning_content": "To find sqrt(144), observe that 12 * 12 = 144. Therefore, the principal root is 12.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
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
                return httpx.Response(200, json=mock_response, request=req)

        monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

        result = await provider.generate(messages=[{"role": "user", "content": "sqrt(144)"}])

        # Verify visible response contains strictly the user-facing answer
        assert result.text == "The square root of 144 is 12."
        assert "observe that 12 * 12" not in result.text
        assert "sqrt(144)" not in result.text

        # Verify internal diagnostic accessor holds the extracted reasoning content
        assert provider.last_reasoning_content == "To find sqrt(144), observe that 12 * 12 = 144. Therefore, the principal root is 12."

    asyncio.run(_test())


def test_deepseek_reasoner_stream_isolates_reasoning_content(monkeypatch):
    """Verify deepseek-reasoner streaming isolates delta reasoning_content from visible stream chunks."""
    async def _test():
        provider = DeepSeekProvider(api_key="sk_ds_test", default_model="deepseek-reasoner")

        sse_lines = [
            'data: {"choices":[{"delta":{"reasoning_content":"Thinking: check prime factor of 21. "}}]}',
            'data: {"choices":[{"delta":{"reasoning_content":"21 = 3 * 7. "}}]}',
            'data: {"choices":[{"delta":{"content":"21 is "}}]}',
            'data: {"choices":[{"delta":{"content":"not a prime number."}}]}',
            'data: {"choices":[{"finish_reason":"stop"}],"usage":{"prompt_tokens":8,"completion_tokens":14,"total_tokens":22}}',
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
        async for chunk in provider.stream(messages=[{"role": "user", "content": "Is 21 prime?"}]):
            chunks.append(chunk)

        full_visible_text = "".join(c.text for c in chunks)
        assert full_visible_text == "21 is not a prime number."
        assert "Thinking" not in full_visible_text
        assert "prime factor" not in full_visible_text

        # Verify internal diagnostic accessor holds full aggregated reasoning content
        assert provider.last_reasoning_content == "Thinking: check prime factor of 21. 21 = 3 * 7. "

    asyncio.run(_test())


def test_deepseek_reasoning_filter_strips_inline_tags(monkeypatch):
    """Verify any inline <think> or <reasoning> tags in content delta are stripped by ReasoningFilter."""
    async def _test():
        provider = DeepSeekProvider(api_key="sk_ds_test")

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"Direct answer: "}}]}',
            'data: {"choices":[{"delta":{"content":"<reasoning>hidden calculation</reasoning>"}}]}',
            'data: {"choices":[{"delta":{"content":"verified."}}]}',
            'data: {"choices":[{"finish_reason":"stop"}]}',
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
        async for chunk in provider.stream(messages=[{"role": "user", "content": "Verify"}]):
            chunks.append(chunk)

        full_text = "".join(c.text for c in chunks)
        assert full_text == "Direct answer: verified."
        assert "hidden calculation" not in full_text
        assert "<reasoning>" not in full_text

    asyncio.run(_test())


# ==============================================================================
# Registry Integration Tests
# ==============================================================================

def test_cloud_providers_registered_in_default_registry():
    """Verify GroqProvider and DeepSeekProvider are registered and instantiable in default_registry."""
    groq_cls = default_registry.get_class("groq")
    assert groq_cls is GroqProvider

    ds_cls = default_registry.get_class("deepseek")
    assert ds_cls is DeepSeekProvider

    groq_inst = default_registry.create_provider("groq", api_key="sk_groq_test")
    assert isinstance(groq_inst, GroqProvider)
    assert groq_inst.provider_id == "groq"

    ds_inst = default_registry.create_provider("deepseek", api_key="sk_ds_test")
    assert isinstance(ds_inst, DeepSeekProvider)
    assert ds_inst.provider_id == "deepseek"

