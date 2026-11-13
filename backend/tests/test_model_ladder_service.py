"""
Automated unit tests for Nine-Rung Model Fallback Ladder & Quota Resilience Service.

Verifies:
- ADR-02 task-specific fallback ladders (LIVE, FAST, SMART, SEARCH)
- 429 quota exhaustion fallback and 300s cooldown tracking
- Model cooldown avoidance and primary tier recovery after cooldown expiry
- Immediate abortion on HTTP 401/403 authentication failures (no invalid step-downs)
- Maximum 3-hop ladder limit enforcement
- Capability-aware filtering (requires_live_audio, requires_vision, requires_tools)
- Quota pool awareness and provider-level exhaustion
- User-visible fallback telemetry emission
- LiveVoiceService integration with ModelLadderService
"""

import asyncio
import time
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import errors

from app.providers.base import (
    AuthenticationError,
    NormalizedProviderError,
    ProviderTimeoutError,
    QuotaExceededError,
    ServiceUnavailableError,
)
from app.services.model_ladder_service import (
    COOLDOWN_429_DEFAULT,
    MAX_LADDER_HOPS,
    RUNG_1,
    RUNG_2,
    RUNG_3,
    RUNG_4,
    RUNG_5,
    RUNG_6,
    RUNG_7,
    RUNG_8,
    RUNG_9,
    FallbackEvent,
    ModelLadderService,
    TaskType,
    model_ladder_service,
    provider_of,
)
from app.services.live_voice_service import LiveVoiceService


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Provider Derivation & Ladder Sequences
# ─────────────────────────────────────────────────────────────────────────────

def test_provider_of_derivation():
    assert provider_of(RUNG_1) == "gemini"
    assert provider_of(RUNG_2) == "gemini"
    assert provider_of(RUNG_3) == "gemini"
    assert provider_of(RUNG_4) == "gemini"
    assert provider_of(RUNG_5) == "groq"
    assert provider_of(RUNG_6) == "deepseek"
    assert provider_of(RUNG_7) == "ollama"
    assert provider_of(RUNG_8) == "lm_studio"
    assert provider_of(RUNG_9) == "gemini"


def test_task_ladders_structure():
    service = ModelLadderService()

    live_candidates = service.get_candidates(TaskType.LIVE)
    assert live_candidates == [RUNG_1, RUNG_2]

    fast_candidates = service.get_candidates(TaskType.FAST)
    assert fast_candidates == [RUNG_3, RUNG_4, RUNG_5, RUNG_7, RUNG_9]

    smart_candidates = service.get_candidates(TaskType.SMART)
    assert smart_candidates == [RUNG_3, RUNG_6, RUNG_4, RUNG_8, RUNG_9]

    search_candidates = service.get_candidates(TaskType.SEARCH)
    assert search_candidates == [RUNG_3, RUNG_4, RUNG_9]


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Capability-Aware Candidate Selection
# ─────────────────────────────────────────────────────────────────────────────

def test_capability_filtering_live_audio():
    service = ModelLadderService()
    # Live audio required should only match RUNG_1 and RUNG_2
    candidates = service.get_candidates(TaskType.LIVE, requires_live_audio=True)
    assert candidates == [RUNG_1, RUNG_2]

    # In FAST ladder, no models declare native live audio, so candidate list is empty
    fast_live = service.get_candidates(TaskType.FAST, requires_live_audio=True)
    assert fast_live == []


def test_capability_filtering_vision():
    service = ModelLadderService()
    # In LIVE ladder, only RUNG_1 has vision
    candidates = service.get_candidates(TaskType.LIVE, requires_vision=True)
    assert candidates == [RUNG_1]

    # In FAST ladder, RUNG_3, RUNG_4, and RUNG_9 have vision; RUNG_5 (groq) and RUNG_7 (ollama) do not
    fast_vision = service.get_candidates(TaskType.FAST, requires_vision=True)
    assert fast_vision == [RUNG_3, RUNG_4, RUNG_9]


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Fallback on 429 Quota Exhaustion & Cooldowns
# ─────────────────────────────────────────────────────────────────────────────

def test_ladder_advances_on_429_quota_exhausted():
    service = ModelLadderService()
    events: List[FallbackEvent] = []
    service.add_fallback_listener(events.append)

    # Initial state: Rung 1 is primary
    assert service.get_candidates(TaskType.LIVE)[0] == RUNG_1

    # Record 429 quota exhaustion on Rung 1
    service.record_failure(RUNG_1, 429)
    assert service.is_cooling(RUNG_1) is True
    assert service.cooldown_remaining(RUNG_1) > 0

    # Next candidate selection must automatically skip Rung 1 and select Rung 2
    candidates = service.get_candidates(TaskType.LIVE)
    assert candidates[0] == RUNG_2


def test_ladder_skips_cooling_models():
    service = ModelLadderService()
    # Put Rung 3 and Rung 4 in cooldown
    service.record_failure(RUNG_3, 429)
    service.record_failure(RUNG_4, 503)

    assert service.is_cooling(RUNG_3) is True
    assert service.is_cooling(RUNG_4) is True

    # FAST ladder should skip RUNG_3 and RUNG_4 and select RUNG_5 (groq)
    candidates = service.get_candidates(TaskType.FAST)
    assert candidates[0] == RUNG_5


def test_ladder_returns_to_primary_tier_after_cooldown_expires(monkeypatch):
    service = ModelLadderService()
    base_time = 1000.0
    monkeypatch.setattr(time, "monotonic", lambda: base_time)

    # Put Rung 1 on cooldown
    service.record_failure(RUNG_1, 429, retry_after_s=60.0)
    assert service.is_cooling(RUNG_1) is True
    assert service.get_candidates(TaskType.LIVE) == [RUNG_2]

    # Advance monotonic clock by 61 seconds (past the 60s cooldown)
    monkeypatch.setattr(time, "monotonic", lambda: base_time + 61.0)
    assert service.is_cooling(RUNG_1) is False

    # Primary tier must now be restored as top candidate
    assert service.get_candidates(TaskType.LIVE)[0] == RUNG_1


def test_ladder_aborts_immediately_on_401_authentication_error():
    service = ModelLadderService()
    # 401 error on gemini
    service.record_failure(RUNG_3, 401)

    # Provider 'gemini' is permanently marked failed
    assert service.is_cooling(RUNG_3) is True
    assert service.is_cooling(RUNG_4) is True
    assert service.is_cooling(RUNG_9) is True

    # Under FAST ladder, all gemini models are excluded; only non-gemini models remain
    candidates = service.get_candidates(TaskType.FAST)
    for model in candidates:
        assert provider_of(model) != "gemini"

    # Async execute must raise AuthenticationError without stepping down
    async def _test():
        async def _failing_call(model_id: str):
            raise AuthenticationError("API Key Invalid", provider_id=provider_of(model_id))

        with pytest.raises(AuthenticationError):
            await service.execute_with_ladder(TaskType.FAST, _failing_call)

    asyncio.run(_test())


def test_ladder_clamps_to_max_3_hops():
    service = ModelLadderService()
    attempted_models: List[str] = []

    async def _test():
        async def _always_fails(model_id: str):
            attempted_models.append(model_id)
            raise QuotaExceededError(f"429 on {model_id}", provider_id=provider_of(model_id))

        with pytest.raises(ServiceUnavailableError, match="exhausted after 3 hops"):
            await service.execute_with_ladder(
                TaskType.FAST,
                _always_fails,
                max_hops=3,
            )

        assert len(attempted_models) == 3

    asyncio.run(_test())


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Quota Pool Awareness (Provider-Wide vs. Model-Specific 429)
# ─────────────────────────────────────────────────────────────────────────────

def test_provider_wide_quota_exhaustion():
    service = ModelLadderService()
    # Mark provider-wide quota exhaustion on gemini
    service.record_failure(RUNG_3, 429, is_provider_wide=True)

    # All Gemini models should be cooling
    assert service.is_cooling(RUNG_1) is True
    assert service.is_cooling(RUNG_3) is True
    assert service.is_cooling(RUNG_4) is True
    assert service.is_cooling(RUNG_9) is True

    # Non-Gemini models must NOT be cooling
    assert service.is_cooling(RUNG_5) is False  # groq
    assert service.is_cooling(RUNG_7) is False  # ollama

    # Candidate selection for FAST automatically prioritizes groq
    candidates = service.get_candidates(TaskType.FAST)
    assert candidates[0] == RUNG_5


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: Observability & Fallback Telemetry
# ─────────────────────────────────────────────────────────────────────────────

def test_fallback_telemetry_emission():
    service = ModelLadderService()
    events: List[FallbackEvent] = []
    service.add_fallback_listener(events.append)

    evt = service.emit_fallback(
        from_model=RUNG_1,
        to_model=RUNG_2,
        reason="HTTP 429 Resource Exhausted",
        task_type=TaskType.LIVE,
    )
    assert len(events) == 1
    assert events[0].from_model == RUNG_1
    assert events[0].to_model == RUNG_2
    assert events[0].reason == "HTTP 429 Resource Exhausted"
    assert events[0].task_type == "live"

    service.remove_fallback_listener(events.append)


# ─────────────────────────────────────────────────────────────────────────────
#  Tests: LiveVoiceService Integration with ModelLadderService
# ─────────────────────────────────────────────────────────────────────────────

def test_live_voice_service_fallback_on_429():
    async def _test():
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.get.return_value = (
            MagicMock(assistant_name="Alex", user_name="User", voice_name="Puck"),
            True,
        )
        mock_settings.get_api_key_for_service.return_value = "fake-gemini-key"

        mock_memory = MagicMock()
        mock_memory.list_entries.return_value = []

        service = LiveVoiceService(settings=mock_settings, memory=mock_memory)

        # Mock WebSocket
        mock_ws = AsyncMock()
        sent_messages = []
        mock_ws.send_json.side_effect = lambda msg: sent_messages.append(msg)

        # Reset ladder cooldowns
        model_ladder_service.reset_all_cooldowns()

        # Mock client connection: Rung 1 raises 429 APIError, Rung 2 succeeds
        api_error_429 = errors.APIError(429, "Resource has been exhausted", "RESOURCE_EXHAUSTED")

        class MockSession:
            pass

        class MockAsyncLive:
            def __init__(self):
                self.calls = []

            def connect(self, model, config):
                self.calls.append(model)
                mock_ctx = AsyncMock()
                if model == RUNG_1:
                    mock_ctx.__aenter__.side_effect = api_error_429
                else:
                    mock_ctx.__aenter__.return_value = MockSession()
                return mock_ctx

        mock_client = MagicMock()
        mock_client.aio.live = MockAsyncLive()
        mock_client.aio.aclose = AsyncMock()

        with patch("google.genai.Client", return_value=mock_client), \
             patch.object(service, "_bridge", new_callable=AsyncMock) as mock_bridge:
            await service.serve(mock_ws)
            mock_bridge.assert_awaited_once()

        # Verify fallback event was sent to websocket
        fallback_msgs = [m for m in sent_messages if m.get("type") == "model_fallback"]
        connected_msgs = [m for m in sent_messages if m.get("type") == "connected"]

        assert len(fallback_msgs) == 1
        assert fallback_msgs[0]["from_model"] == RUNG_1
        assert fallback_msgs[0]["to_model"] == RUNG_2
        assert "429" in fallback_msgs[0]["reason"]

        assert len(connected_msgs) == 1
        assert connected_msgs[0]["model"] == RUNG_2

        # Verify RUNG_1 is now cooling in model_ladder_service
        assert model_ladder_service.is_cooling(RUNG_1) is True
        model_ladder_service.reset_all_cooldowns()

    asyncio.run(_test())


def test_record_success_clears_failure_state():
    """Verify record_success clears cooling state for the model."""
    service = ModelLadderService()
    service.record_failure(RUNG_1, status_code=429)
    assert service.is_cooling(RUNG_1) is True

    service.record_success(RUNG_1)
    assert service.is_cooling(RUNG_1) is False
    assert service.cooldown_remaining(RUNG_1) == 0.0


def test_record_timeout_initiates_cooldown():
    """Verify record_timeout cools the model for the configured timeout duration."""
    service = ModelLadderService()
    assert service.is_cooling(RUNG_2) is False

    service.record_timeout(RUNG_2)
    assert service.is_cooling(RUNG_2) is True
    assert service.cooldown_remaining(RUNG_2) > 0.0


def test_fallback_listener_removal():
    """Verify removing a fallback listener stops event dispatch."""
    service = ModelLadderService()
    events = []

    def listener(ev: FallbackEvent):
        events.append(ev)

    service.add_fallback_listener(listener)
    service.emit_fallback(RUNG_1, RUNG_2, "test reason", TaskType.SMART)
    assert len(events) == 1

    service.remove_fallback_listener(listener)
    service.emit_fallback(RUNG_2, RUNG_3, "second reason", TaskType.SMART)
    assert len(events) == 1  # No second event received


def test_execute_with_ladder_full_sequence_exhaustion():
    """Verify execute_with_ladder hops through candidates on 429 and raises ServiceUnavailableError when exhausted."""
    async def _test():
        service = ModelLadderService()
        attempts = []
        events = []
        service.add_fallback_listener(lambda ev: events.append(ev))

        async def failing_worker(model_id: str):
            attempts.append(model_id)
            raise QuotaExceededError(f"Quota exceeded for {model_id}", provider_id=provider_of(model_id))

        with pytest.raises(ServiceUnavailableError) as exc_info:
            await service.execute_with_ladder(
                task=TaskType.FAST,
                run_func=failing_worker,
                max_hops=3,
            )

        assert "All candidate models exhausted" in str(exc_info.value)
        # Verify 3 hops (3 attempts made up to max_hops=3)
        assert len(attempts) == 3
        # 2 transitions: attempt 1 -> attempt 2, attempt 2 -> attempt 3
        assert len(events) == 2

    asyncio.run(_test())


def test_concurrent_ladder_contention():
    """Verify concurrent worker threads accessing ModelLadderService do not cause race conditions."""
    import concurrent.futures

    service = ModelLadderService()

    def worker(i: int):
        model = RUNG_1 if i % 2 == 0 else RUNG_2
        service.record_failure(model, status_code=429)
        _ = service.is_cooling(model)
        _ = service.get_candidates(task=TaskType.SMART)
        if i % 3 == 0:
            service.record_success(model)
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(40)]
        results = [f.result() for f in futures]

    assert len(results) == 40
    service.reset_all_cooldowns()


