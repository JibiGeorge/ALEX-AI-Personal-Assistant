"""
LM Studio Local LLM Provider.

Subclasses OpenAICompatibleProvider to connect to LM Studio's local OpenAI-compatible
server at http://127.0.0.1:1234/v1. Enforces strict loopback security, local model discovery,
and token streaming with low first-chunk latency.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.providers.base import (
    ModelDescriptor,
    ProviderCapabilities,
    validate_base_url,
)
from app.providers.ollama_provider import is_loopback_host
from app.providers.openai_provider import OpenAICompatibleProvider
from app.providers.registry import default_registry

logger = logging.getLogger(__name__)

DEFAULT_LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"


class LMStudioProvider(OpenAICompatibleProvider):
    """Local LLM Provider interfacing with LM Studio local inference server."""

    def __init__(
        self,
        base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
        default_model: str = "local-model",
        allow_remote: bool = False,
        timeout_s: float = 60.0,
        capabilities: Optional[ProviderCapabilities] = None,
    ) -> None:
        cleaned_url = validate_base_url(base_url)
        parsed = urlparse(cleaned_url)
        host = parsed.hostname or ""

        # Enforce loopback binding security to prevent unintentional network exposure
        if not allow_remote and not is_loopback_host(host):
            raise ValueError(
                f"LM Studio provider requires a loopback address (127.0.0.1 or localhost), got '{host}'. "
                f"Set allow_remote=True to connect to a remote LM Studio server."
            )

        caps = capabilities or ProviderCapabilities(
            vision=False,
            function_calling=True,
            streaming=True,
            native_audio=False,
            live_bidirectional=False,
            max_context_tokens=8192,
            max_tools=12,
            tool_format="openai",
        )

        super().__init__(
            base_url=cleaned_url,
            api_key="",  # Local LM Studio requires no authentication key
            default_model=default_model,
            provider_id="lm_studio",
            timeout_s=timeout_s,
            capabilities=caps,
            is_local=True,
        )

    async def list_models(self) -> List[ModelDescriptor]:
        """Fetch models currently loaded and available in LM Studio."""
        descriptors = await super().list_models()
        for d in descriptors:
            d.is_local = True
            d.provider_name = "lm_studio"
        return descriptors

    async def get_active_model(self) -> Optional[str]:
        """Fetch the first active/loaded model identifier from LM Studio, if any."""
        try:
            models = await self.list_models()
            if models:
                return models[0].model_id
        except Exception as exc:
            logger.debug("Could not resolve active model from LM Studio: %s", exc)
        return None


# Register LM Studio provider in the default provider registry
default_registry.register_class("lm_studio", LMStudioProvider)
default_registry.register_class("lmstudio", LMStudioProvider)

