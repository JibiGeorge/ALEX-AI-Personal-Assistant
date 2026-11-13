"""
Automated unit tests for AI Provider Base Abstraction Layer and Registry.

Tests:
- Abstract base class contract enforcement
- Pydantic v2 schemas and validation
- Strict enforcement of Private Reasoning Data Policy (no <think> or raw thought fields)
- Normalized error hierarchy, status codes, and retryability
- Secret redaction and base URL SSRF validation
- Mock provider execution: generate, stream, timeouts, and cancellation tokens
- ProviderRegistry lifecycle, discovery, health checking, and credential resolution
"""

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional
import pytest
from pydantic import ValidationError

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
from app.providers.registry import ProviderRegistry


# ─────────────────────────────────────────────────────────────────────────────
#  Mock Provider Implementation for Testing
# ─────────────────────────────────────────────────────────────────────────────

class MockProvider(LLMProvider):
    def __init__(
        self,
        provider_id: str = "mock_provider",
        healthy: bool = True,
        models: Optional[List[ModelDescriptor]] = None,
        caps: Optional[ProviderCapabilities] = None,
    ):
        self._provider_id = provider_id
        self._healthy = healthy
        self._caps = caps or ProviderCapabilities()
        self._models = models or [
            ModelDescriptor(
                model_id=f"{provider_id}-model-1",
                display_name="Mock Model 1",
                provider_name=provider_id,
                capabilities=self._caps,
            )
        ]

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._caps

    async def list_models(self) -> List[ModelDescriptor]:
        if not self._healthy:
            raise ServiceUnavailableError("Mock provider is offline", provider_id=self._provider_id)
        return list(self._models)

    async def health_check(self) -> bool:
        if not self._healthy:
            return False
        return True

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_ms: int = 30000,
        cancellation_token: Optional[asyncio.Event] = None,
    ) -> StreamingChunk:
        if cancellation_token and cancellation_token.is_set():
            raise CancellationError("Cancelled before generation", provider_id=self._provider_id)

        timeout_sec = timeout_ms / 1000.0
        try:
            async def _run():
                # Simulate light work
                await asyncio.sleep(0.01)
                if cancellation_token and cancellation_token.is_set():
                    raise CancellationError("Cancelled during generation", provider_id=self._provider_id)
                return StreamingChunk(
                    text="Mock generated response",
                    is_final=True,
                    usage=UsageMetadata(
                        provider_id=self._provider_id,
                        model_id=self._models[0].model_id,
                        prompt_tokens=10,
                        completion_tokens=5,
                        total_tokens=15,
                        latency_ms=10.0,
                    ),
                )

            return await asyncio.wait_for(_run(), timeout=timeout_sec)
        except asyncio.TimeoutError as exc:
            raise ProviderTimeoutError("Mock provider timed out", provider_id=self._provider_id, original_error=exc)

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_ms: int = 30000,
        cancellation_token: Optional[asyncio.Event] = None,
    ) -> AsyncIterator[StreamingChunk]:
        tokens = ["Hello", " from", " mock", " provider!"]
        for i, token in enumerate(tokens):
            if cancellation_token and cancellation_token.is_set():
                raise CancellationError("Cancelled during streaming", provider_id=self._provider_id)
            await asyncio.sleep(0.005)
            is_final = (i == len(tokens) - 1)
            usage = None
            if is_final:
                usage = UsageMetadata(
                    provider_id=self._provider_id,
                    model_id=self._models[0].model_id,
                    prompt_tokens=8,
                    completion_tokens=len(tokens),
                    total_tokens=8 + len(tokens),
                    latency_ms=20.0,
                )
            yield StreamingChunk(
                text=token,
                is_final=is_final,
                usage=usage,
            )


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Capabilities & Data Models
# ─────────────────────────────────────────────────────────────────────────────

def test_provider_capabilities_defaults_and_validation():
    caps = ProviderCapabilities()
    assert caps.vision is False
    assert caps.function_calling is True
    assert caps.streaming is True
    assert caps.native_audio is False
    assert caps.live_bidirectional is False
    assert caps.max_context_tokens == 8192
    assert caps.supports_system_prompt is True
    assert caps.max_tools is None
    assert caps.tool_format == "openai"

    # Extra fields must be forbidden
    with pytest.raises(ValidationError):
        ProviderCapabilities(unknown_cap=True)


def test_model_descriptor_validation():
    desc = ModelDescriptor(
        model_id="test-model",
        display_name="Test Model",
        provider_name="test_provider",
        context_window=16384,
        is_local=True,
    )
    assert desc.model_id == "test-model"
    assert desc.display_name == "Test Model"
    assert desc.provider_name == "test_provider"
    assert desc.context_window == 16384
    assert desc.is_local is True
    assert desc.capabilities.function_calling is True

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        ModelDescriptor(
            model_id="test",
            display_name="Test",
            provider_name="p",
            invalid_prop="bad",
        )


def test_private_reasoning_data_policy_enforcement():
    """Verify that StreamingChunk strictly prohibits raw reasoning/thought fields."""
    chunk = StreamingChunk(text="Visible answer", is_final=True)
    assert chunk.text == "Visible answer"
    assert chunk.is_final is True
    assert chunk.function_calls is None
    assert chunk.usage is None

    # Verify no 'thought', 'think', or 'thought_log' attributes exist
    assert not hasattr(chunk, "thought")
    assert not hasattr(chunk, "think")
    assert not hasattr(chunk, "thought_log")

    # Extra fields like thought or think MUST raise ValidationError
    with pytest.raises(ValidationError):
        StreamingChunk(text="Visible", thought="internal secret reasoning")  # type: ignore

    with pytest.raises(ValidationError):
        StreamingChunk(text="Visible", think="raw think block")  # type: ignore

    # Verify UsageMetadata holds operational audit metadata only
    usage = UsageMetadata(
        provider_id="groq",
        model_id="llama-3.3-70b",
        prompt_tokens=100,
        completion_tokens=25,
        total_tokens=125,
        latency_ms=145.2,
        fallback_reason="Gemini 429 quota exhaustion",
        tool_invocation="weather_lookup",
        tool_outcome="DONE",
        error_category=None,
    )
    assert usage.provider_id == "groq"
    assert usage.fallback_reason == "Gemini 429 quota exhaustion"
    assert usage.tool_outcome == "DONE"

    # Extra fields on UsageMetadata are also forbidden
    with pytest.raises(ValidationError):
        UsageMetadata(provider_id="groq", raw_thoughts="prohibited")  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Error Hierarchy
# ─────────────────────────────────────────────────────────────────────────────

def test_normalized_error_hierarchy():
    # Base error
    base_err = NormalizedProviderError("General error", status_code=500, retryable=False, provider_id="test")
    assert isinstance(base_err, Exception)
    assert base_err.status_code == 500
    assert not base_err.retryable
    assert base_err.provider_id == "test"
    assert "General error" in str(base_err)

    # AuthenticationError
    auth_err = AuthenticationError("Bad API key", provider_id="openai")
    assert isinstance(auth_err, NormalizedProviderError)
    assert auth_err.status_code == 401
    assert auth_err.retryable is False
    assert auth_err.provider_id == "openai"

    # QuotaExceededError
    quota_err = QuotaExceededError("Rate limit", provider_id="gemini", retry_after_s=5.5)
    assert isinstance(quota_err, NormalizedProviderError)
    assert quota_err.status_code == 429
    assert quota_err.retryable is True
    assert quota_err.retry_after_s == 5.5

    # ServiceUnavailableError
    svc_err = ServiceUnavailableError("503 Backend down", provider_id="groq")
    assert isinstance(svc_err, NormalizedProviderError)
    assert svc_err.status_code == 503
    assert svc_err.retryable is True

    # ModelNotFoundError
    model_err = ModelNotFoundError("Model xyz not found", provider_id="ollama")
    assert isinstance(model_err, NormalizedProviderError)
    assert model_err.status_code == 404
    assert model_err.retryable is False

    # ProviderTimeoutError
    orig = TimeoutError("Socket timeout")
    timeout_err = ProviderTimeoutError("Deadline exceeded", provider_id="lm_studio", original_error=orig)
    assert isinstance(timeout_err, NormalizedProviderError)
    assert timeout_err.status_code == 408
    assert timeout_err.retryable is True
    assert timeout_err.original_error is orig

    # CancellationError
    cancel_err = CancellationError("Client abort", provider_id="mock")
    assert isinstance(cancel_err, NormalizedProviderError)
    assert cancel_err.status_code == 499
    assert cancel_err.retryable is False


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Helpers (redact_secret & validate_base_url)
# ─────────────────────────────────────────────────────────────────────────────

def test_redact_secret():
    assert redact_secret(None) == ""
    assert redact_secret("") == ""
    assert redact_secret("   ") == ""
    assert redact_secret("short") == "***"
    assert redact_secret("123456") == "***"
    assert redact_secret("sk-123456789") == "********6789"
    assert redact_secret("AIzaSyAbcdEfgh123456") == "****************3456"


def test_validate_base_url():
    # Valid endpoints
    assert validate_base_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434"
    assert validate_base_url("http://localhost:1234/v1/") == "http://localhost:1234/v1"
    assert validate_base_url("https://api.openai.com/v1") == "https://api.openai.com/v1"

    # Invalid empty or non-string
    with pytest.raises(ValueError, match="non-empty string"):
        validate_base_url("")

    # Invalid schemes
    with pytest.raises(ValueError, match="Invalid URL scheme"):
        validate_base_url("ftp://example.com/api")

    with pytest.raises(ValueError, match="Invalid URL scheme"):
        validate_base_url("file:///etc/passwd")

    # Missing host
    with pytest.raises(ValueError, match="missing hostname"):
        validate_base_url("http://")

    # SSRF protection against metadata endpoints
    with pytest.raises(ValueError, match="blocked for security"):
        validate_base_url("http://169.254.169.254/latest/meta-data")

    with pytest.raises(ValueError, match="blocked for security"):
        validate_base_url("http://metadata.google.internal/computeMetadata/v1")


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Abstract LLMProvider Contract
# ─────────────────────────────────────────────────────────────────────────────

def test_cannot_instantiate_abstract_provider():
    class IncompleteProvider(LLMProvider):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider()  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Provider Execution (Generate, Stream, Cancellation, Timeouts)
# ─────────────────────────────────────────────────────────────────────────────

def test_mock_provider_generate_success():
    async def _test():
        provider = MockProvider()
        assert provider.provider_id == "mock_provider"

        chunk = await provider.generate(messages=[{"role": "user", "content": "hi"}])
        assert chunk.is_final is True
        assert chunk.text == "Mock generated response"
        assert chunk.usage is not None
        assert chunk.usage.total_tokens == 15

    asyncio.run(_test())


def test_mock_provider_stream_success():
    async def _test():
        provider = MockProvider()
        chunks = []
        async for chunk in provider.stream(messages=[{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

        assert len(chunks) == 4
        full_text = "".join(c.text for c in chunks)
        assert full_text == "Hello from mock provider!"
        assert chunks[-1].is_final is True
        assert chunks[-1].usage is not None
        assert chunks[-1].usage.total_tokens == 12

    asyncio.run(_test())


def test_mock_provider_generate_timeout():
    async def _test():
        provider = MockProvider()
        # Force timeout with 1 ms
        with pytest.raises(ProviderTimeoutError) as exc_info:
            await provider.generate(messages=[{"role": "user", "content": "hi"}], timeout_ms=1)
        assert exc_info.value.retryable is True
        assert exc_info.value.provider_id == "mock_provider"

    asyncio.run(_test())


def test_mock_provider_cancellation_during_generation():
    async def _test():
        provider = MockProvider()
        cancel_token = asyncio.Event()
        cancel_token.set()  # Pre-cancelled

        with pytest.raises(CancellationError) as exc_info:
            await provider.generate(
                messages=[{"role": "user", "content": "hi"}],
                cancellation_token=cancel_token,
            )
        assert exc_info.value.status_code == 499
        assert exc_info.value.retryable is False

    asyncio.run(_test())


def test_mock_provider_cancellation_during_streaming():
    async def _test():
        provider = MockProvider()
        cancel_token = asyncio.Event()

        received = []
        with pytest.raises(CancellationError):
            async for chunk in provider.stream(
                messages=[{"role": "user", "content": "hi"}],
                cancellation_token=cancel_token,
            ):
                received.append(chunk)
                # Cancel after first chunk
                cancel_token.set()

        assert len(received) == 1
        assert received[0].text == "Hello"

    asyncio.run(_test())


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: ProviderRegistry
# ─────────────────────────────────────────────────────────────────────────────

def test_provider_registry_lifecycle_and_discovery():
    async def _test():
        registry = ProviderRegistry(service_name="AlexTest")

        # Registration of non-provider raises TypeError
        with pytest.raises(TypeError):
            registry.register_class("bad", object)  # type: ignore

        with pytest.raises(TypeError):
            registry.register_instance(object())  # type: ignore

        # Register class
        registry.register_class("mock_cls", MockProvider)
        assert "mock_cls" in registry.list_providers()
        assert registry.get_class("mock_cls") is MockProvider

        # Dynamic instantiation
        instance = registry.create_provider("mock_cls", provider_id="dynamic_mock")
        assert instance.provider_id == "dynamic_mock"
        assert registry.get_provider("dynamic_mock") is instance
        assert "dynamic_mock" in registry.list_active_providers()

        # Register pre-built instance
        static_p = MockProvider(provider_id="static_mock")
        registry.register_instance(static_p)
        assert registry.get_provider("static_mock") is static_p

        # Unregister
        registry.unregister("static_mock")
        assert registry.get_provider("static_mock") is None

        # Clear
        registry.clear()
        assert registry.list_providers() == []
        assert registry.list_active_providers() == []

    asyncio.run(_test())


def test_provider_registry_health_and_model_aggregation():
    async def _test():
        registry = ProviderRegistry(service_name="AlexTest")

        p1 = MockProvider(provider_id="healthy_p", healthy=True)
        p2 = MockProvider(provider_id="failing_p", healthy=False)

        registry.register_instance(p1)
        registry.register_instance(p2)

        # Health check
        health_results = await registry.check_all_health()
        assert health_results["healthy_p"] is True
        assert health_results["failing_p"] is False

        # List all models
        models_dict = await registry.list_all_models()
        assert len(models_dict["healthy_p"]) == 1
        assert models_dict["healthy_p"][0].model_id == "healthy_p-model-1"
        # Failing provider should return empty list gracefully without throwing
        assert models_dict["failing_p"] == []

    asyncio.run(_test())


def test_provider_registry_credential_resolution(monkeypatch):
    registry = ProviderRegistry(service_name="AlexTest")

    # Test environment variable resolution
    monkeypatch.setenv("TEST_AI_KEY", "env-secret-key-12345")
    resolved_env = registry.resolve_credential("key_name", env_var="TEST_AI_KEY")
    assert resolved_env == "env-secret-key-12345"

    # Test missing env falls back to keyring
    monkeypatch.delenv("TEST_AI_KEY", raising=False)
    monkeypatch.setattr("keyring.get_password", lambda svc, key: "keyring-secret-key-999")
    resolved_keyring = registry.resolve_credential("gemini-api-key", env_var="NON_EXISTENT_ENV")
    assert resolved_keyring == "keyring-secret-key-999"

    # Test key not found in either
    monkeypatch.setattr("keyring.get_password", lambda svc, key: None)
    assert registry.resolve_credential("unknown-key") is None

    # Test keyring exception handled gracefully
    def _exploding_keyring(svc, key):
        raise RuntimeError("Keyring locked or inaccessible")

    monkeypatch.setattr("keyring.get_password", _exploding_keyring)
    assert registry.resolve_credential("key_name") is None


def test_provider_registry_empty_edge_cases():
    async def _test():
        registry = ProviderRegistry(service_name="AlexEmpty")
        assert await registry.check_all_health() == {}
        assert await registry.list_all_models() == {}

        with pytest.raises(KeyError, match="No provider class registered"):
            registry.create_provider("nonexistent")

        # Unregistering nonexistent provider is a safe no-op
        registry.unregister("nonexistent")

    asyncio.run(_test())

