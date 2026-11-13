"""
Groq Cloud AI Provider.

Ultra-low latency inference provider interfacing with Groq's LPUs via
the OpenAI-compatible endpoint at https://api.groq.com/openai/v1.
Credentials are automatically resolved from OS Keyring under 'groq-api-key'
with environment variable fallback 'GROQ_API_KEY'.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.providers.base import ProviderCapabilities, validate_base_url
from app.providers.openai_provider import OpenAICompatibleProvider
from app.providers.registry import default_registry

logger = logging.getLogger(__name__)

DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_KEYRING_KEY = "groq-api-key"
GROQ_ENV_VAR = "GROQ_API_KEY"


class GroqProvider(OpenAICompatibleProvider):
    """Ultra-low latency LLM provider powered by Groq LPUs."""

    def __init__(
        self,
        base_url: str = DEFAULT_GROQ_BASE_URL,
        api_key: Optional[str] = None,
        default_model: str = DEFAULT_GROQ_MODEL,
        provider_id: str = "groq",
        timeout_s: float = 30.0,
        capabilities: Optional[ProviderCapabilities] = None,
    ) -> None:
        resolved_key = api_key or default_registry.resolve_credential(
            GROQ_KEYRING_KEY, env_var=GROQ_ENV_VAR
        ) or ""

        groq_caps = capabilities or ProviderCapabilities(
            vision=False,
            function_calling=True,
            streaming=True,
            max_context_tokens=128000,
            tool_format="openai",
        )

        super().__init__(
            base_url=base_url,
            api_key=resolved_key,
            default_model=default_model,
            provider_id=provider_id,
            timeout_s=timeout_s,
            capabilities=groq_caps,
            is_local=False,
        )

