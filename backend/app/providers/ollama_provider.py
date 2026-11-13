"""
Ollama Local LLM Provider.

Subclasses OpenAICompatibleProvider to connect to Ollama's local OpenAI-compatible
endpoint at http://127.0.0.1:11434/v1. Enforces strict loopback binding security,
local model discovery, and memory diagnostics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.providers.base import (
    ModelDescriptor,
    ProviderCapabilities,
    validate_base_url,
)
from app.providers.openai_provider import OpenAICompatibleProvider
from app.providers.registry import default_registry

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
MINIMUM_REQUIRED_RAM_GB = 3.0


def is_loopback_host(host: str) -> bool:
    """Verify if a hostname or IP address is strictly local loopback."""
    cleaned = host.lower().strip()
    return cleaned in ("127.0.0.1", "localhost", "::1") or cleaned.startswith("127.")


def check_host_memory_for_model(model_name: str, available_ram_gb: float) -> Tuple[bool, str]:
    """Diagnose whether available host RAM can comfortably execute the model.
    
    Prevents host thrashing on undersized local machines.
    """
    if available_ram_gb < MINIMUM_REQUIRED_RAM_GB:
        return False, f"Available RAM ({available_ram_gb:.1f} GB) is below the minimum required {MINIMUM_REQUIRED_RAM_GB:.1f} GB threshold for local inference."

    name_lower = model_name.lower()
    if "70b" in name_lower and available_ram_gb < 40.0:
        return False, f"Model {model_name} requires ~40 GB RAM; only {available_ram_gb:.1f} GB available."
    if "32b" in name_lower and available_ram_gb < 20.0:
        return False, f"Model {model_name} requires ~20 GB RAM; only {available_ram_gb:.1f} GB available."
    if "14b" in name_lower and available_ram_gb < 12.0:
        return False, f"Model {model_name} requires ~12 GB RAM; only {available_ram_gb:.1f} GB available."
    if ("8b" in name_lower or "7b" in name_lower) and available_ram_gb < 6.0:
        return False, f"Model {model_name} requires ~6 GB RAM; only {available_ram_gb:.1f} GB available."

    return True, "RAM sufficient"


class OllamaProvider(OpenAICompatibleProvider):
    """Local LLM Provider running on Ollama."""

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        default_model: str = "llama3.2:3b",
        allow_remote: bool = False,
        timeout_s: float = 60.0,
        capabilities: Optional[ProviderCapabilities] = None,
    ) -> None:
        cleaned_url = validate_base_url(base_url)
        parsed = urlparse(cleaned_url)
        host = parsed.hostname or ""

        # Enforce strict loopback binding to prevent unintended network exposure
        if not allow_remote and not is_loopback_host(host):
            raise ValueError(
                f"Ollama provider requires a loopback address (127.0.0.1 or localhost), got '{host}'. "
                f"Set allow_remote=True to connect to a remote Ollama server."
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
            api_key="",  # Local Ollama typically requires no authentication key
            default_model=default_model,
            provider_id="ollama",
            timeout_s=timeout_s,
            capabilities=caps,
            is_local=True,
        )

    async def get_ollama_version(self) -> Optional[str]:
        """Fetch Ollama daemon version via native endpoint /api/version."""
        # Derive root url without /v1
        parsed = urlparse(self._base_url)
        root_url = f"{parsed.scheme}://{parsed.netloc}"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{root_url}/api/version")
                if res.status_code == 200:
                    data = res.json()
                    return data.get("version")
        except Exception:
            return None
        return None

    async def list_models(self) -> List[ModelDescriptor]:
        """Query installed models from Ollama."""
        # Query standard /v1/models endpoint from superclass
        descriptors = await super().list_models()
        # Ensure all models are tagged with is_local=True
        for d in descriptors:
            d.is_local = True
        return descriptors


# Register Ollama in the default provider registry
default_registry.register_class("ollama", OllamaProvider)

