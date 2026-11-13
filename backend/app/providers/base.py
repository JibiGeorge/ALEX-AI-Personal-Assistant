"""
AI Provider Base Abstraction Layer.

Defines the contract, capability schemas, data models, error hierarchy,
and abstract base class for all LLM providers in Alex AI Desktop Assistant.

Private Reasoning Data Policy:
In accordance with system security and privacy requirements, raw internal reasoning
tokens (<think>) are strictly forbidden from being stored or exposed. StreamingChunk
strictly excludes any raw chain-of-thought fields. Operational audit metadata
is captured in UsageMetadata.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field


def redact_secret(secret: Optional[str]) -> str:
    """Mask sensitive tokens/keys for logging and operational display.
    
    Returns:
        Empty string if secret is None, empty, or whitespace-only.
        '***' if secret is 6 characters or shorter.
        Masked string retaining only the last 4 characters if longer.
    """
    if not secret:
        return ""
    stripped = secret.strip()
    if not stripped:
        return ""
    if len(stripped) <= 6:
        return "***"
    return f"{'*' * (len(stripped) - 4)}{stripped[-4:]}"


def validate_base_url(url: str) -> str:
    """Validate base URL endpoint to prevent malformed URLs and SSRF vulnerabilities.
    
    Rejects:
        - Non-HTTP/HTTPS schemes
        - Missing hostnames
        - Cloud metadata service IPs (e.g., 169.254.169.254)
    
    Returns:
        Cleaned URL string without trailing slashes.
    """
    if not url or not isinstance(url, str):
        raise ValueError("Base URL must be a non-empty string")
    
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}': only HTTP and HTTPS are permitted")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    # Block cloud instance metadata IP to prevent SSRF
    if hostname.lower() in ("169.254.169.254", "metadata.google.internal", "instance-data"):
        raise ValueError(f"Access to metadata endpoint '{hostname}' is blocked for security")
    
    return cleaned.rstrip("/")


class ProviderCapabilities(BaseModel):
    """Capabilities and limits declared by an AI provider or model."""
    model_config = ConfigDict(extra="forbid")

    vision: bool = False
    function_calling: bool = True
    streaming: bool = True
    native_audio: bool = False
    live_bidirectional: bool = False
    max_context_tokens: int = 8192
    supports_system_prompt: bool = True
    max_tools: Optional[int] = None
    tool_format: Optional[str] = "openai"  # "openai", "gemini", "anthropic"


class UsageMetadata(BaseModel):
    """Operational audit metadata for provider execution.
    
    Captures latency, token usage, tool interactions, and error telemetry.
    Strictly excludes raw chain-of-thought or internal reasoning text.
    """
    model_config = ConfigDict(extra="forbid")

    provider_id: str = ""
    model_id: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    fallback_reason: Optional[str] = None
    tool_invocation: Optional[str] = None
    tool_outcome: Optional[str] = None
    error_category: Optional[str] = None


class StreamingChunk(BaseModel):
    """Single incremental generation chunk emitted during streaming or full generation.
    
    Strictly complies with the Private Reasoning Data Policy:
    Contains NO raw reasoning text or chain-of-thought fields.
    """
    model_config = ConfigDict(extra="forbid")

    text: str = ""
    function_calls: Optional[List[Dict[str, Any]]] = None
    is_final: bool = False
    usage: Optional[UsageMetadata] = None


class ModelDescriptor(BaseModel):
    """Metadata describing an available model provided by an engine."""
    model_config = ConfigDict(extra="forbid")

    model_id: str
    display_name: str
    provider_name: str
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)
    context_window: int = 8192
    is_local: bool = False


# ─────────────────────────────────────────────────────────────────────────────
#  Normalized Error Hierarchy
# ─────────────────────────────────────────────────────────────────────────────

class NormalizedProviderError(Exception):
    """Base exception for normalized provider errors across different vendor APIs."""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        retryable: bool = False,
        provider_id: str = "",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.provider_id = provider_id
        self.original_error = original_error

    def __str__(self) -> str:
        provider_tag = f"[{self.provider_id}] " if self.provider_id else ""
        return f"{provider_tag}{self.message} (HTTP {self.status_code}, retryable={self.retryable})"


class AuthenticationError(NormalizedProviderError):
    """Provider authentication failed (e.g. invalid API key, expired token, 401/403). Non-retryable."""
    def __init__(
        self,
        message: str = "Authentication failed",
        provider_id: str = "",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            retryable=False,
            provider_id=provider_id,
            original_error=original_error,
        )


class QuotaExceededError(NormalizedProviderError):
    """Provider quota or rate limit exceeded (HTTP 429). Retryable with backoff."""
    def __init__(
        self,
        message: str = "Rate limit or quota exceeded",
        provider_id: str = "",
        retry_after_s: Optional[float] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            status_code=429,
            retryable=True,
            provider_id=provider_id,
            original_error=original_error,
        )
        self.retry_after_s = retry_after_s


class ServiceUnavailableError(NormalizedProviderError):
    """Provider backend service temporarily unavailable (HTTP 500/502/503). Retryable."""
    def __init__(
        self,
        message: str = "Provider service unavailable",
        status_code: int = 503,
        provider_id: str = "",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            retryable=True,
            provider_id=provider_id,
            original_error=original_error,
        )


class ModelNotFoundError(NormalizedProviderError):
    """Requested model not found on provider (HTTP 404). Non-retryable."""
    def __init__(
        self,
        message: str = "Requested model not found",
        provider_id: str = "",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            status_code=404,
            retryable=False,
            provider_id=provider_id,
            original_error=original_error,
        )


class ProviderTimeoutError(NormalizedProviderError):
    """Provider request timed out (HTTP 408 / 504). Retryable."""
    def __init__(
        self,
        message: str = "Provider request timed out",
        status_code: int = 408,
        provider_id: str = "",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            retryable=True,
            provider_id=provider_id,
            original_error=original_error,
        )


class CancellationError(NormalizedProviderError):
    """Provider operation was cancelled via cancellation token (HTTP 499). Non-retryable."""
    def __init__(
        self,
        message: str = "Provider operation cancelled by client",
        provider_id: str = "",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            status_code=499,
            retryable=False,
            provider_id=provider_id,
            original_error=original_error,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Abstract LLM Provider Base Class
# ─────────────────────────────────────────────────────────────────────────────

class LLMProvider(ABC):
    """Abstract base class for all LLM providers in Alex AI Desktop Assistant."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier of the provider (e.g. 'gemini', 'ollama', 'lm_studio', 'openai')."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Declared capabilities and constraints of this provider."""
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelDescriptor]:
        """Query or return the list of models supported and currently available."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Lightweight connectivity/readiness ping to verify provider is healthy."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_ms: int = 30000,
        cancellation_token: Optional[asyncio.Event] = None,
    ) -> StreamingChunk:
        """Execute a single-turn completion call.
        
        Args:
            messages: Normalized conversation turns.
            tools: Optional tool/function schemas.
            timeout_ms: Maximum execution time in milliseconds.
            cancellation_token: Event to signal early termination.
            
        Returns:
            Final StreamingChunk with aggregated text and usage metadata.
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_ms: int = 30000,
        cancellation_token: Optional[asyncio.Event] = None,
    ) -> AsyncIterator[StreamingChunk]:
        """Stream response chunks incrementally.
        
        Args:
            messages: Normalized conversation turns.
            tools: Optional tool/function schemas.
            timeout_ms: Maximum execution time in milliseconds.
            cancellation_token: Event to signal early termination.
            
        Yields:
            StreamingChunk instances as generated.
        """
        pass
