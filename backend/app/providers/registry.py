"""
AI Provider Registry.

Manages registration, discovery, dynamic instantiation, credential resolution,
health verification, and model aggregation across all supported AI providers.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Type

import keyring

from app.providers.base import (
    LLMProvider,
    ModelDescriptor,
    NormalizedProviderError,
    redact_secret,
)

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_NAME = "Alex"


class ProviderRegistry:
    """Central registry and lifecycle manager for LLM providers."""

    def __init__(self, service_name: str = DEFAULT_SERVICE_NAME) -> None:
        self.service_name = service_name
        self._classes: Dict[str, Type[LLMProvider]] = {}
        self._instances: Dict[str, LLMProvider] = {}

    def register_class(self, provider_id: str, provider_cls: Type[LLMProvider]) -> None:
        """Register a provider class for dynamic instantiation."""
        if not issubclass(provider_cls, LLMProvider):
            raise TypeError(f"Provider class {provider_cls.__name__} must inherit from LLMProvider")
        self._classes[provider_id.lower()] = provider_cls
        logger.debug("Registered provider class for '%s': %s", provider_id, provider_cls.__name__)

    def register_instance(self, provider: LLMProvider) -> None:
        """Register an active, pre-configured provider instance."""
        if not isinstance(provider, LLMProvider):
            raise TypeError(f"Instance must be an LLMProvider, got {type(provider).__name__}")
        pid = provider.provider_id.lower()
        self._instances[pid] = provider
        logger.debug("Registered provider instance for '%s'", pid)

    def get_provider(self, provider_id: str) -> Optional[LLMProvider]:
        """Retrieve an active provider instance by ID."""
        return self._instances.get(provider_id.lower())

    def get_class(self, provider_id: str) -> Optional[Type[LLMProvider]]:
        """Retrieve a registered provider class by ID."""
        return self._classes.get(provider_id.lower())

    def list_providers(self) -> List[str]:
        """List all registered provider IDs (instances and classes)."""
        all_ids = set(self._instances.keys()) | set(self._classes.keys())
        return sorted(all_ids)

    def list_active_providers(self) -> List[str]:
        """List provider IDs that currently have instantiated objects."""
        return sorted(self._instances.keys())

    def unregister(self, provider_id: str) -> None:
        """Unregister a provider instance and class if present."""
        pid = provider_id.lower()
        self._instances.pop(pid, None)
        self._classes.pop(pid, None)

    def clear(self) -> None:
        """Clear all registered instances and classes (useful for testing)."""
        self._instances.clear()
        self._classes.clear()

    def resolve_credential(self, key_name: str, env_var: Optional[str] = None) -> Optional[str]:
        """Resolve a secret credential from OS Keyring with optional environment variable fallback.
        
        Credentials are never persisted in plaintext.
        """
        if env_var:
            env_val = os.environ.get(env_var)
            if env_val and env_val.strip():
                return env_val.strip()

        try:
            stored = keyring.get_password(self.service_name, key_name)
            if stored and stored.strip():
                return stored.strip()
        except Exception as exc:
            logger.warning("Keyring lookup for '%s' failed: %s", key_name, exc)
            return None

        return None

    def create_provider(self, provider_name: str, **kwargs: Any) -> LLMProvider:
        """Instantiate a registered provider class and register it as an active instance."""
        name = provider_name.lower()
        cls = self._classes.get(name)
        if not cls:
            raise KeyError(f"No provider class registered for '{provider_name}'")

        try:
            instance = cls(**kwargs)
            self.register_instance(instance)
            return instance
        except Exception as exc:
            logger.error("Failed to instantiate provider '%s': %s", provider_name, exc)
            raise

    async def check_all_health(self) -> Dict[str, bool]:
        """Check health status across all active provider instances concurrently.
        
        Failures in one provider do not impact checks of other providers.
        """
        results: Dict[str, bool] = {}
        if not self._instances:
            return results

        async def _check(pid: str, provider: LLMProvider) -> tuple[str, bool]:
            try:
                healthy = await provider.health_check()
                return pid, bool(healthy)
            except Exception as exc:
                logger.warning("Health check failed for provider '%s': %s", pid, exc)
                return pid, False

        tasks = [_check(pid, inst) for pid, inst in self._instances.items()]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, tuple):
                pid, status = item
                results[pid] = status
            elif isinstance(item, Exception):
                logger.error("Unexpected error in health check task: %s", item)

        return results

    async def list_all_models(self) -> Dict[str, List[ModelDescriptor]]:
        """Collect available models from all active provider instances concurrently.
        
        If a provider fails or is unreachable, an empty list is recorded for it
        and an error is logged, without failing other providers.
        """
        results: Dict[str, List[ModelDescriptor]] = {}
        if not self._instances:
            return results

        async def _fetch_models(pid: str, provider: LLMProvider) -> tuple[str, List[ModelDescriptor]]:
            try:
                models = await provider.list_models()
                return pid, models
            except Exception as exc:
                logger.warning("Failed to list models for provider '%s': %s", pid, exc)
                return pid, []

        tasks = [_fetch_models(pid, inst) for pid, inst in self._instances.items()]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, tuple):
                pid, models = item
                results[pid] = models
            elif isinstance(item, Exception):
                logger.error("Unexpected error in model listing task: %s", item)

        return results


# Global singleton instance
default_registry = ProviderRegistry()
