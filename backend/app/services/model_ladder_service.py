"""
Nine-Rung Model Fallback Ladder & Quota Resilience Service.

Implements the multi-provider 9-rung Model Fallback Ladder defined in ADR-02,
providing task-specific fallback ladders (FAST, SMART, SEARCH, LIVE),
dynamic cooldown tracking (429, 404, 500-504), capability-aware candidate selection,
quota pool awareness, and user-visible fallback observability.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, Iterable, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from app.providers.base import (
    AuthenticationError,
    NormalizedProviderError,
    ProviderCapabilities,
    ProviderTimeoutError,
    QuotaExceededError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

# Maximum model hops per turn before terminating with error
MAX_LADDER_HOPS = 3

# Cooldown default durations (seconds)
COOLDOWN_429_DEFAULT = 300.0        # 5 minutes
COOLDOWN_404 = 21600.0             # 6 hours
COOLDOWN_5XX = 1800.0              # 30 minutes
COOLDOWN_TIMEOUT = 1800.0          # 30 minutes


class TaskType(str, Enum):
    """Specific task-oriented ladder modes."""
    LIVE = "live"       # Full-duplex live audio websocket session
    FAST = "fast"       # Short classification, fast extraction, low-latency UI turns
    SMART = "smart"     # Deep reasoning, long document synthesis, complex planning
    SEARCH = "search"   # Grounded web search and information retrieval


# ─────────────────────────────────────────────────────────────────────────────
#  Authoritative Nine Rung Identifiers
# ─────────────────────────────────────────────────────────────────────────────
# Flagged runtime model assumptions (subject to capability probing):
RUNG_1 = "models/gemini-3.1-flash-live-preview"              # Primary Multimodal Live WSS
RUNG_2 = "models/gemini-2.5-flash-native-audio-preview-12-2025" # Secondary Native Audio Live WSS
RUNG_3 = "gemini-2.5-flash"                                 # Primary Fast REST Reasoning & Tools
RUNG_4 = "gemini-2.5-flash-lite"                            # Ultra-Fast REST Fallback
RUNG_5 = "groq:llama-3.3-70b-versatile"                     # Cloud High-Speed Backup
RUNG_6 = "deepseek:deepseek-chat"                           # Deep Reasoning Backup
RUNG_7 = "ollama:llama3.2:3b"                               # Local Offline Primary
RUNG_8 = "lm_studio:local-model"                            # Local Offline Secondary
RUNG_9 = "gemini-1.5-flash"                                 # Emergency Cloud Survival Rung

NINE_RUNGS: Tuple[str, ...] = (
    RUNG_1, RUNG_2, RUNG_3, RUNG_4, RUNG_5, RUNG_6, RUNG_7, RUNG_8, RUNG_9
)

# Base capabilities declared for the 9 rungs
_DEFAULT_RUNGS_CAPABILITIES: Dict[str, ProviderCapabilities] = {
    RUNG_1: ProviderCapabilities(
        live_bidirectional=True,
        native_audio=True,
        vision=True,
        function_calling=True,
        streaming=True,
        max_context_tokens=128000,
    ),
    RUNG_2: ProviderCapabilities(
        live_bidirectional=True,
        native_audio=True,
        vision=False,
        function_calling=True,
        streaming=True,
        max_context_tokens=64000,
    ),
    RUNG_3: ProviderCapabilities(
        live_bidirectional=False,
        native_audio=False,
        vision=True,
        function_calling=True,
        streaming=True,
        max_context_tokens=1048576,
    ),
    RUNG_4: ProviderCapabilities(
        live_bidirectional=False,
        native_audio=False,
        vision=True,
        function_calling=True,
        streaming=True,
        max_context_tokens=1048576,
    ),
    RUNG_5: ProviderCapabilities(
        live_bidirectional=False,
        native_audio=False,
        vision=False,
        function_calling=True,
        streaming=True,
        max_context_tokens=128000,
    ),
    RUNG_6: ProviderCapabilities(
        live_bidirectional=False,
        native_audio=False,
        vision=False,
        function_calling=True,
        streaming=True,
        max_context_tokens=64000,
    ),
    RUNG_7: ProviderCapabilities(
        live_bidirectional=False,
        native_audio=False,
        vision=False,
        function_calling=True,
        streaming=True,
        max_context_tokens=8192,
    ),
    RUNG_8: ProviderCapabilities(
        live_bidirectional=False,
        native_audio=False,
        vision=False,
        function_calling=True,
        streaming=True,
        max_context_tokens=8192,
    ),
    RUNG_9: ProviderCapabilities(
        live_bidirectional=False,
        native_audio=False,
        vision=True,
        function_calling=True,
        streaming=True,
        max_context_tokens=1048576,
    ),
}

# Task-specific ordered model sequences
_LADDERS: Dict[TaskType, Tuple[str, ...]] = {
    TaskType.LIVE: (RUNG_1, RUNG_2),
    TaskType.FAST: (RUNG_3, RUNG_4, RUNG_5, RUNG_7, RUNG_9),
    TaskType.SMART: (RUNG_3, RUNG_6, RUNG_4, RUNG_8, RUNG_9),
    TaskType.SEARCH: (RUNG_3, RUNG_4, RUNG_9),
}


def provider_of(model_id: str) -> str:
    """Extract vendor/provider identifier from model ID for quota pooling and authentication."""
    if model_id.startswith("groq:"):
        return "groq"
    if model_id.startswith("deepseek:"):
        return "deepseek"
    if model_id.startswith("ollama:"):
        return "ollama"
    if model_id.startswith("lm_studio:"):
        return "lm_studio"
    return "gemini"


class FallbackEvent(BaseModel):
    """Structured telemetry emitted during model fallback."""
    from_model: str
    to_model: str
    reason: str
    task_type: str
    timestamp: float = Field(default_factory=time.time)


class ModelLadderService:
    """Unified Ladder State Machine, Cooldown Tracker, and Fallback Orchestrator."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._model_cooldown_until: Dict[str, float] = {}
        self._provider_auth_failed: Set[str] = set()
        self._provider_quota_exhausted_until: Dict[str, float] = {}
        self._capabilities: Dict[str, ProviderCapabilities] = dict(_DEFAULT_RUNGS_CAPABILITIES)
        self._fallback_listeners: List[Callable[[FallbackEvent], None]] = []

    def add_fallback_listener(self, listener: Callable[[FallbackEvent], None]) -> None:
        """Register a callback for fallback observability events."""
        with self._lock:
            if listener not in self._fallback_listeners:
                self._fallback_listeners.append(listener)

    def remove_fallback_listener(self, listener: Callable[[FallbackEvent], None]) -> None:
        """Unregister a fallback event listener."""
        with self._lock:
            if listener in self._fallback_listeners:
                self._fallback_listeners.remove(listener)

    def emit_fallback(self, from_model: str, to_model: str, reason: str, task_type: TaskType) -> FallbackEvent:
        """Create and broadcast a fallback telemetry event."""
        event = FallbackEvent(
            from_model=from_model,
            to_model=to_model,
            reason=reason,
            task_type=task_type.value,
        )
        logger.info(
            "Model fallback triggered [%s]: %s -> %s (Reason: %s)",
            task_type.value, from_model, to_model, reason
        )
        with self._lock:
            listeners = list(self._fallback_listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                logger.warning("Fallback listener raised error: %s", exc)
        return event

    def is_cooling(self, model_id: str) -> bool:
        """Check if a specific model or its parent provider is currently in cooldown."""
        with self._lock:
            now = time.monotonic()
            provider = provider_of(model_id)

            if provider in self._provider_auth_failed:
                return True

            provider_until = self._provider_quota_exhausted_until.get(provider, 0.0)
            if provider_until > now:
                return True

            model_until = self._model_cooldown_until.get(model_id, 0.0)
            return model_until > now

    def cooldown_remaining(self, model_id: str) -> float:
        """Seconds remaining in cooldown, or 0.0 if active and healthy."""
        with self._lock:
            now = time.monotonic()
            provider = provider_of(model_id)

            if provider in self._provider_auth_failed:
                return float("inf")

            provider_remaining = self._provider_quota_exhausted_until.get(provider, 0.0) - now
            model_remaining = self._model_cooldown_until.get(model_id, 0.0) - now
            remaining = max(0.0, provider_remaining, model_remaining)
            return remaining

    def record_failure(
        self,
        model_id: str,
        status_code: int,
        retry_after_s: Optional[float] = None,
        is_provider_wide: bool = False,
    ) -> None:
        """Record model/provider failure and calculate cooldown duration based on status code.
        
        Rules:
        - 401/403: Provider marked as AUTHENTICATION_FAILED. Fatal for all models under that key.
        - 429: Cooldown = retry_after_s or 300s.
        - 404: Cooldown = 21,600s (6h).
        - 500, 502, 503, 504: Cooldown = 1,800s (30m).
        """
        now = time.monotonic()
        provider = provider_of(model_id)

        with self._lock:
            if status_code in (401, 403):
                self._provider_auth_failed.add(provider)
                logger.error("Provider '%s' authentication failed (HTTP %s); marked invalid", provider, status_code)
                return

            if status_code == 429:
                duration = retry_after_s if (retry_after_s and retry_after_s > 0) else COOLDOWN_429_DEFAULT
                if is_provider_wide:
                    self._provider_quota_exhausted_until[provider] = now + duration
                    logger.warning("Provider '%s' project quota exhausted (HTTP 429) for %.1fs", provider, duration)
                else:
                    self._model_cooldown_until[model_id] = now + duration
                    logger.warning("Model '%s' quota exceeded (HTTP 429) for %.1fs", model_id, duration)
                return

            if status_code in (404, 1007, 1008):
                self._model_cooldown_until[model_id] = now + COOLDOWN_404
                logger.warning("Model '%s' returned %s (policy/not found); quarantined for 6h", model_id, status_code)
                return

            if status_code in (500, 502, 503, 504):
                self._model_cooldown_until[model_id] = now + COOLDOWN_5XX
                logger.warning("Model '%s' returned HTTP %s; cooling for 30m", model_id, status_code)
                return

    def record_timeout(self, model_id: str) -> None:
        """Record request timeout for a model."""
        with self._lock:
            self._model_cooldown_until[model_id] = time.monotonic() + COOLDOWN_TIMEOUT
            logger.warning("Model '%s' timed out; cooling for 30m", model_id)

    def record_success(self, model_id: str) -> None:
        """Reset cooldown state on successful operation."""
        provider = provider_of(model_id)
        with self._lock:
            self._model_cooldown_until.pop(model_id, None)
            self._provider_quota_exhausted_until.pop(provider, None)
            self._provider_auth_failed.discard(provider)

    def reset_all_cooldowns(self) -> None:
        """Clear all active cooldowns and authentication failure states."""
        with self._lock:
            self._model_cooldown_until.clear()
            self._provider_quota_exhausted_until.clear()
            self._provider_auth_failed.clear()

    def get_candidates(
        self,
        task: TaskType = TaskType.FAST,
        requires_live_audio: bool = False,
        requires_vision: bool = False,
        requires_tools: bool = False,
        requires_streaming: bool = False,
    ) -> List[str]:
        """Return available candidate models matching the required capability profile and not in cooldown.
        
        If all candidates are cooling, returns cooling candidates in order of shortest remaining cooldown.
        """
        ladder = _LADDERS.get(task, _LADDERS[TaskType.FAST])

        def _matches(model: str) -> bool:
            caps = self._capabilities.get(model)
            if not caps:
                return True
            if requires_live_audio and not (caps.live_bidirectional or caps.native_audio):
                return False
            if requires_vision and not caps.vision:
                return False
            if requires_tools and not caps.function_calling:
                return False
            if requires_streaming and not caps.streaming:
                return False
            return True

        matching = [m for m in ladder if _matches(m)]

        with self._lock:
            now = time.monotonic()
            # Clean expired cooldowns
            self._model_cooldown_until = {
                m: u for m, u in self._model_cooldown_until.items() if u > now
            }
            self._provider_quota_exhausted_until = {
                p: u for p, u in self._provider_quota_exhausted_until.items() if u > now
            }

            available = [m for m in matching if not self.is_cooling(m)]
            if available:
                return available

            # If all matching models are in cooldown, sort by remaining cooldown time
            # but completely exclude hard authentication failures
            active_auth_candidates = [
                m for m in matching if provider_of(m) not in self._provider_auth_failed
            ]
            if not active_auth_candidates:
                return []

            return sorted(active_auth_candidates, key=self.cooldown_remaining)

    async def execute_with_ladder(
        self,
        task: TaskType,
        run_func: Callable[[str], Coroutine[Any, Any, Any]],
        requires_live_audio: bool = False,
        requires_vision: bool = False,
        requires_tools: bool = False,
        requires_streaming: bool = False,
        max_hops: int = MAX_LADDER_HOPS,
    ) -> Any:
        """Execute an asynchronous operation against the model ladder, automatically falling back on failure.
        
        Limits hops to at most `max_hops` (default: 3).
        """
        candidates = self.get_candidates(
            task=task,
            requires_live_audio=requires_live_audio,
            requires_vision=requires_vision,
            requires_tools=requires_tools,
            requires_streaming=requires_streaming,
        )

        if not candidates:
            raise ServiceUnavailableError("No available models matching capability profile", provider_id=task.value)

        last_error: Optional[Exception] = None
        hops = 0

        for i, model in enumerate(candidates):
            if hops >= max_hops:
                logger.warning("Reached maximum ladder hops (%d); aborting fallback", max_hops)
                break

            hops += 1
            try:
                result = await run_func(model)
                self.record_success(model)
                return result
            except NormalizedProviderError as exc:
                last_error = exc
                self.record_failure(model, exc.status_code)
                if isinstance(exc, AuthenticationError):
                    # Fatal error: do not step down under broken authentication
                    logger.error("Authentication error on model %s; aborting ladder", model)
                    raise

                if i + 1 < len(candidates) and hops < max_hops:
                    next_model = candidates[i + 1]
                    self.emit_fallback(model, next_model, str(exc), task)
                continue
            except Exception as exc:
                last_error = exc
                logger.warning("Unhandled error on model %s: %s", model, exc)
                self.record_failure(model, 500)
                if i + 1 < len(candidates) and hops < max_hops:
                    next_model = candidates[i + 1]
                    self.emit_fallback(model, next_model, str(exc), task)
                continue

        raise ServiceUnavailableError(
            f"All candidate models exhausted after {hops} hops: {last_error}",
            provider_id=task.value,
            original_error=last_error,
        )


# Global singleton instance
model_ladder_service = ModelLadderService()

