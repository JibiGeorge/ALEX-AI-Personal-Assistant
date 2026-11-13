from __future__ import annotations

import asyncio
import time
from datetime import date, datetime
from unittest.mock import MagicMock
import pytest

from app.actions.action_executor import ActionExecutor
from app.actions.action_registry import ActionRegistry
from app.actions.builtins.proactive import register_proactive_actions
from app.schemas.memory import MemoryEntry
from app.schemas.proactive import ProactiveCheckParams
from app.services.proactive_service import ProactiveEngine


def test_proactive_engine_silence_and_cooldown_gates():
    engine = ProactiveEngine(min_silence_secs=60, check_cooldown=120)

    # 1. User spoke just now -> should not trigger
    engine.record_user_activity()
    assert engine.should_trigger() is False

    # 2. User spoke 30 seconds ago (< 60s silence) -> should not trigger
    now = time.monotonic()
    assert engine.should_trigger(last_user_speech=now - 30) is False

    # 3. User spoke 70 seconds ago (> 60s silence) and cooldown never fired -> should trigger
    assert engine.should_trigger(last_user_speech=now - 70) is True

    # 4. Mark triggered -> sets cooldown
    engine.mark_triggered()
    # Now silence is still 70s, but cooldown (120s) is active -> should not trigger
    assert engine.should_trigger(last_user_speech=now - 70) is False


def test_proactive_engine_time_periods():
    engine = ProactiveEngine()

    _, morning_p, _ = engine.build_prompt(now_dt=datetime(2026, 11, 5, 9, 0, 0))
    assert morning_p == "morning"

    _, afternoon_p, _ = engine.build_prompt(now_dt=datetime(2026, 11, 5, 14, 0, 0))
    assert afternoon_p == "afternoon"

    _, evening_p, _ = engine.build_prompt(now_dt=datetime(2026, 11, 5, 19, 30, 0))
    assert evening_p == "evening"

    _, night_p, _ = engine.build_prompt(now_dt=datetime(2026, 11, 5, 2, 0, 0))
    assert night_p == "late night"


def test_proactive_engine_focus_rotation():
    engine = ProactiveEngine()

    prompt0, _, idx0 = engine.build_prompt()
    assert idx0 == 0
    assert "active projects or goals" in prompt0

    engine.mark_triggered()
    prompt1, _, idx1 = engine.build_prompt()
    assert idx1 == 1
    assert "wellbeing" in prompt1

    engine.mark_triggered()
    prompt2, _, idx2 = engine.build_prompt()
    assert idx2 == 2
    assert "genuinely interesting" in prompt2

    engine.mark_triggered()
    prompt3, _, idx3 = engine.build_prompt()
    assert idx3 == 0


def test_proactive_engine_context_formatting():
    mock_mem = MagicMock()
    mock_mem.list_entries.return_value = [
        MemoryEntry(
            category="projects",
            key="thesis",
            value="Quantum computing algorithms",
            updated=date.today(),
        )
    ]

    engine = ProactiveEngine(memory_service=mock_mem)
    prompt, _, _ = engine.build_prompt(
        monitors=["SpaceX Starship", "Gemini 3"],
        recent_turns=["User: What is the weather?", "Alex: It's sunny and 22C."],
    )

    assert "[PROACTIVE_CHECK]" in prompt
    assert "Quantum computing algorithms" in prompt
    assert "SpaceX Starship, Gemini 3" in prompt
    assert "What is the weather?" in prompt


def test_action_conversation_proactive_check():
    registry = ActionRegistry()
    engine = ProactiveEngine(min_silence_secs=60, check_cooldown=120)
    register_proactive_actions(registry, engine)

    executor = ActionExecutor(registry)

    async def _test():
        # When user was active 10s ago, action defers
        res = await executor.execute(
            "conversation.proactive_check",
            {"last_user_speech_seconds_ago": 10},
        )
        assert res.status == "success"
        assert res.data["outcome_status"] == "done"
        assert res.data["triggered"] is False
        assert "deferred" in res.message

        # When force is true, action triggers immediately
        res_forced = await executor.execute(
            "conversation.proactive_check",
            {"force": True},
        )
        assert res_forced.status == "success"
        assert res_forced.data["outcome_status"] == "done"
        assert res_forced.data["triggered"] is True
        assert "[PROACTIVE_CHECK]" in res_forced.data["prompt"]

    asyncio.run(_test())
