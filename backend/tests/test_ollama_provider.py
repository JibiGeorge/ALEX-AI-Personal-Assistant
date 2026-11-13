"""
Automated unit tests for Ollama Local LLM Provider.

Verifies:
- Detection of running Ollama service on port 11434
- Listing and mapping installed local models
- Offline chat completion execution
- Strict loopback security enforcement (refusal of non-loopback addresses without allow_remote=True)
- Streaming chat completion with Private Reasoning Data Policy (<think> token stripping)
- Host RAM diagnostics and threshold checks
- REST diagnostic API endpoint /api/v1/system/engines/ollama
"""

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.base import (
    ModelDescriptor,
    ModelNotFoundError,
    ProviderTimeoutError,
    QuotaExceededError,
    ServiceUnavailableError,
)
from app.providers.ollama_provider import (
    OllamaProvider,
    check_host_memory_for_model,
    is_loopback_host,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Loopback Security Enforcement
# ─────────────────────────────────────────────────────────────────────────────

def test_is_loopback_host():
    assert is_loopback_host("127.0.0.1") is True
    assert is_loopback_host("localhost") is True
    assert is_loopback_host("::1") is True
    assert is_loopback_host("127.0.0.2") is True
    assert is_loopback_host("192.168.1.50") is False
    assert is_loopback_host("api.external.com") is False


def test_ollama_loopback_security_enforcement():
    # Loopback addresses succeed
    p1 = OllamaProvider(base_url="http://127.0.0.1:11434/v1")
    assert p1.base_url == "http://127.0.0.1:11434/v1"

    p2 = OllamaProvider(base_url="http://localhost:11434/v1")
    assert "localhost" in p2.base_url

    # Non-loopback addresses must be rejected by default
    with pytest.raises(ValueError, match="requires a loopback address"):
        OllamaProvider(base_url="http://192.168.1.100:11434/v1")

    with pytest.raises(ValueError, match="requires a loopback address"):
        OllamaProvider(base_url="http://remote.lan:11434/v1")

    # Non-loopback allowed only when allow_remote=True
    p3 = OllamaProvider(base_url="http://192.168.1.100:11434/v1", allow_remote=True)
    assert p3.base_url == "http://192.168.1.100:11434/v1"


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Host RAM Diagnostics
# ─────────────────────────────────────────────────────────────────────────────

def test_check_host_memory_for_model():
    # Insufficient system RAM (< 3.0 GB)
    ok, msg = check_host_memory_for_model("llama3.2:3b", available_ram_gb=2.5)
    assert not ok
    assert "below the minimum" in msg

    # 70B model requires ~40 GB RAM
    ok, msg = check_host_memory_for_model("llama3.3:70b", available_ram_gb=16.0)
    assert not ok
    assert "requires ~40 GB" in msg

    # 70B model with 64 GB RAM is OK
    ok, msg = check_host_memory_for_model("llama3.3:70b", available_ram_gb=64.0)
    assert ok

    # 8B model with 4 GB RAM fails
    ok, msg = check_host_memory_for_model("llama3.1:8b", available_ram_gb=4.0)
    assert not ok
    assert "requires ~6 GB" in msg

    # 3B model with 8 GB RAM succeeds
    ok, msg = check_host_memory_for_model("llama3.2:3b", available_ram_gb=8.0)
    assert ok


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Service Detection & Health Check
# ─────────────────────────────────────────────────────────────────────────────

def test_ollama_detects_running_service_on_11434():
    async def _test():
        provider = OllamaProvider()

        # Mock online service
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_res = httpx.Response(200, json={"data": []})
            mock_get.return_value = mock_res
            assert await provider.health_check() is True

        # Mock offline / connection refused service
        with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
            assert await provider.health_check() is False

    asyncio.run(_test())


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Listing Installed Models
# ─────────────────────────────────────────────────────────────────────────────

def test_ollama_lists_installed_models():
    async def _test():
        provider = OllamaProvider()

        mock_payload = {
            "data": [
                {"id": "llama3.2:3b"},
                {"id": "qwen2.5:7b"},
            ]
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            req = httpx.Request("GET", "http://127.0.0.1:11434/v1/models")
            mock_res = httpx.Response(200, json=mock_payload, request=req)
            mock_get.return_value = mock_res

            models = await provider.list_models()
            assert len(models) == 2
            assert models[0].model_id == "ollama:llama3.2:3b"
            assert models[0].is_local is True
            assert models[0].provider_name == "ollama"

            assert models[1].model_id == "ollama:qwen2.5:7b"
            assert models[1].is_local is True

    asyncio.run(_test())


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Chat Completion Execution (Generate)
# ─────────────────────────────────────────────────────────────────────────────

def test_ollama_executes_chat_completion_mock():
    async def _test():
        provider = OllamaProvider(default_model="llama3.2:3b")

        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Hello! I am running locally on Ollama.",
                        "role": "assistant",
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 8,
                "total_tokens": 20,
            },
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            req = httpx.Request("POST", "http://127.0.0.1:11434/v1/chat/completions")
            mock_res = httpx.Response(200, json=mock_response_data, request=req)
            mock_post.return_value = mock_res

            chunk = await provider.generate(
                messages=[{"role": "user", "content": "Hello from tests"}]
            )

            assert chunk.is_final is True
            assert chunk.text == "Hello! I am running locally on Ollama."
            assert chunk.usage is not None
            assert chunk.usage.provider_id == "ollama"
            assert chunk.usage.total_tokens == 20

    asyncio.run(_test())


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Streaming & Private Reasoning Data Policy (<think> Filtering)
# ─────────────────────────────────────────────────────────────────────────────

def test_ollama_streaming_and_think_token_filtering():
    async def _test():
        provider = OllamaProvider(default_model="deepseek-r1:8b")

        sse_lines = [
            'data: {"choices": [{"delta": {"content": "<think>Analyzing user query"}}, {"finish_reason": null}]}',
            'data: {"choices": [{"delta": {"content": "... and finding safe response</think>Here is your answer."}}, {"finish_reason": null}]}',
            'data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}',
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
            chunks = []
            async for chunk in provider.stream(
                messages=[{"role": "user", "content": "What is 2+2?"}]
            ):
                chunks.append(chunk)

            assembled_text = "".join(c.text for c in chunks)
            # Must strictly exclude <think> tags and all content inside them!
            assert "<think>" not in assembled_text
            assert "</think>" not in assembled_text
            assert "Analyzing user query" not in assembled_text
            assert "Here is your answer." in assembled_text
            assert chunks[-1].is_final is True

    asyncio.run(_test())


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Diagnostics Endpoint /api/v1/system/engines/ollama
# ─────────────────────────────────────────────────────────────────────────────

def test_ollama_diagnostics_endpoint(tmp_path):
    app = create_app(data_dir=tmp_path, api_token="test-token")
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    # Mock provider calls inside the endpoint
    with patch.object(OllamaProvider, "health_check", return_value=True), \
         patch.object(OllamaProvider, "get_ollama_version", return_value="0.3.12"), \
         patch.object(OllamaProvider, "list_models", return_value=[
             ModelDescriptor(
                 model_id="ollama:llama3.2:3b",
                 display_name="llama3.2:3b",
                 provider_name="ollama",
                 is_local=True,
             )
         ]):
        res = client.get("/api/v1/system/engines/ollama", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["engine"] == "ollama"
        assert data["running"] is True
        assert data["version"] == "0.3.12"
        assert len(data["models"]) == 1
        assert data["ram_diagnostics"]["min_required_gb"] == 3.0
