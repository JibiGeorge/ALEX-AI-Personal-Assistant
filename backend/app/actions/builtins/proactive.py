from __future__ import annotations

import time
from typing import Any

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, done
from app.schemas.proactive import ProactiveCheckParams, ProactiveCheckResponse
from app.services.proactive_service import ProactiveEngine


def register_proactive_actions(
    registry: ActionRegistry,
    proactive_engine: ProactiveEngine,
) -> None:
    def proactive_check_handler(params: ProactiveCheckParams) -> ActionOutcomeResponse:
        now = time.monotonic()
        ref_speech = (
            now - params.last_user_speech_seconds_ago
            if params.last_user_speech_seconds_ago is not None
            else None
        )

        should = params.force or proactive_engine.should_trigger(ref_speech)
        if not should:
            data = ProactiveCheckResponse(
                triggered=False,
                reason="Silence duration or check-in cooldown threshold not yet reached",
            )
            return done(
                action="conversation.proactive_check",
                data=data.model_dump(),
                message="Proactive check-in deferred (silence gate/cooldown active)",
            )

        prompt, period, focus_idx = proactive_engine.build_prompt()
        proactive_engine.mark_triggered()

        data = ProactiveCheckResponse(
            triggered=True,
            reason="Proactive criteria met" if not params.force else "Forced trigger",
            prompt=prompt,
            period=period,
            focus_index=focus_idx,
        )
        return done(
            action="conversation.proactive_check",
            data=data.model_dump(),
            message=f"Proactive check-in generated for {period} (focus #{focus_idx})",
        )

    registry.register(
        ActionDefinition(
            action_id="conversation.proactive_check",
            name="Proactive Conversation Check-In",
            description="Evaluates idle silence and builds a time-aware, non-repetitive contextual prompt for unprompted conversational check-ins.",
            category="conversation",
            parameters=ProactiveCheckParams,
            handler=proactive_check_handler,
            requires_confirmation=False,
            timeout_seconds=5.0,
        )
    )

