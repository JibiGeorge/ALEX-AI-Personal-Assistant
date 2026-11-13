"""
Automated unit tests for LM Studio Local LLM Provider.

Verifies:
- Active server detection on port 1234
- Listing and mapping installed / loaded local models
- Low-latency SSE streaming chat completion execution
- Strict loopback security enforcement (refusal of non-loopback addresses without allow_remote=True)
- Streaming chat completion with Private Reasoning Data Policy (<think> token stripping)
- REST diagnostic API endpoint /api/v1/system/engines/lmstudio
"""

import asyncio
import json
import time
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.base import (
    ModelDescriptor,
    NormalizedProviderError,
    ProviderCapabilities,
    StreamingChunk,
    UsageMetadata,
)
from app.providers.lm_studio_provider import (
    DEFAULT_LM_STUDIO_BASE_URL,
    LMStudioProvider,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Loopback Security Enforcement
# ─────────────────────────────────────────────────────────────────────────────

def test_lm_studio_loopback_security_enforcement():
    # Loopback addresses succeed
    p1 = LMStudioProvider(base_url="http://127.0.0.1:1234/v1")
    assert p1.base_url == "http://127.0.0.1:1234/v1"

    p2 = LMStudioProvider(base_url="http://localhost:1234/v1")
    assert "localhost" in p2.base_url

    # Non-loopback addresses must be rejected by default
    with pytest.raises(ValueError, match="requires a loopback address"):
        LMStudioProvider(base_url="http://192.168.1.200:1234/v1")

    with pytest.raises(ValueError, match="requires a loopback address"):
        LMStudioProvider(base_url="http://lmstudio.remote.lan:1234/v1")

    # Non-loopback allowed only when allow_remote=True
    p3 = LMStudioProvider(base_url="http://192.168.1.200:1234/v1", allow_remote=True)
    assert p3.base_url == "http://192.168.1.200:1234/v1"


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Active Server Detection & Health Check
# ─────────────────────────────────────────────────────────────────────────────

def test_lm_studio_detects_active_server():
    async def _test():
        provider = LMStudioProvider()

        # Mock online service
        with patch("httpx.AsyncClient.get") as mock_get:
            req = httpx.Request("GET", "http://127.0.0.1:1234/v1/models")
            mock_res = httpx.Response(200, json={"data": []}, request=req)
            mock_get.return_value = mock_res
            assert await provider.health_check() is True

        # Mock offline / connection refused service
        with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
            assert await provider.health_check() is False

    asyncio.run(_test())


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Model Listing & Active Model Resolution
# ─────────────────────────────────────────────────────────────────────────────

def test_lm_studio_lists_models():
    async def _test():
        provider = LMStudioProvider()

        mock_payload = {
            "data": [
                {"id": "meta-llama-3.1-8b-instruct"},
                {"id": "mistral-7b-instruct-v0.3"},
            ]
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            req = httpx.Request("GET", "http://127.0.0.1:1234/v1/models")
            mock_res = httpx.Response(200, json=mock_payload, request=req)
            mock_get.return_value = mock_res

            models = await provider.list_models()
            assert len(models) == 2
            assert models[0].model_id == "lm_studio:meta-llama-3.1-8b-instruct"
            assert models[0].is_local is True
            assert models[0].provider_name == "lm_studio"

            assert models[1].model_id == "lm_studio:mistral-7b-instruct-v0.3"
            assert models[1].is_local is True

            active_model = await provider.get_active_model()
            assert active_model == "lm_studio:meta-llama-3.1-8b-instruct"

    asyncio.run(_test())


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Low-Latency Token Streaming & Private Reasoning Filter
# ─────────────────────────────────────────────────────────────────────────────

def test_lm_studio_executes_streaming_chat():
    async def _test():
        provider = LMStudioProvider(default_model="meta-llama-3.1-8b-instruct")

        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}, "finish_reason": null}]}',
            'data: {"choices": [{"delta": {"content": " from"}, "finish_reason": null}]}',
            'data: {"choices": [{"delta": {"content": " <think>internal secret</think>LM"}, "finish_reason": null}]}',
            'data: {"choices": [{"delta": {"content": " Studio!"}, "finish_reason": null}]}',
            'data: {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16}}',
            "data: [DONE]",
        ]

        class MockStreamResponse:
            def __init__(self):
                self.status_code = 200

            async def aiter_lines(self):
                for line in sse_lines:
                    yield line

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        class MockAsyncClient:
            def stream(self, *args, **kwargs):
                return MockStreamResponse()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch("httpx.AsyncClient", return_value=MockAsyncClient()):
            chunks: list[StreamingChunk] = []
            async for chunk in provider.stream(
                messages=[{"role": "user", "content": "Say hello"}]
            ):
                chunks.append(chunk)

            assert len(chunks) > 0
            assembled_text = "".join(c.text for c in chunks)
            assert assembled_text == "Hello from LM Studio!"
            assert "<think>" not in assembled_text
            assert "internal secret" not in assembled_text
            assert chunks[-1].is_final is True
            assert chunks[-1].usage is not None
            assert chunks[-1].usage.total_tokens == 16

    asyncio.run(_test())


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Diagnostics Endpoint /api/v1/system/engines/lmstudio
# ─────────────────────────────────────────────────────────────────────────────

def test_lm_studio_diagnostics_endpoint(tmp_path):
    app = create_app(data_dir=tmp_path, api_token="test-token")
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    # Mock provider calls inside the endpoint
    with patch.object(LMStudioProvider, "health_check", return_value=True), \
         patch.object(LMStudioProvider, "get_active_model", return_value="lm_studio:local-model"), \
         patch.object(LMStudioProvider, "list_models", return_value=[
             ModelDescriptor(
                 model_id="lm_studio:local-model",
                 display_name="local-model",
                 provider_name="lm_studio",
                 is_local=True,
             )
         ]):
        res = client.get("/api/v1/system/engines/lmstudio", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["engine"] == "lm_studio"
        assert data["running"] is True
        assert data["active_model"] == "lm_studio:local-model"
        assert len(data["models"]) == 1
        assert data["ram_diagnostics"]["min_required_gb"] == 3.0

