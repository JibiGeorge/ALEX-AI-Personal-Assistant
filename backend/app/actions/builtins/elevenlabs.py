"""
ElevenLabs built-in action handlers (TASK-GAP-08 / GAP-08).

Exposes 'elevenlabs.synthesize' for multilingual neural speech synthesis.
"""

from __future__ import annotations

import logging

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse
from app.schemas.elevenlabs import ElevenLabsSynthesizeParameters
from app.services.elevenlabs_service import ElevenLabsService

logger = logging.getLogger(__name__)


def register_elevenlabs_actions(
    registry: ActionRegistry,
    elevenlabs_service: ElevenLabsService,
) -> None:
    """Register ElevenLabs synthesis actions with the ActionRegistry."""

    def handle_synthesize(params: ElevenLabsSynthesizeParameters) -> ActionOutcomeResponse:
        return elevenlabs_service.execute(params)

    registry.register(
        ActionDefinition(
            action_id="elevenlabs.synthesize",
            name="Synthesize speech with ElevenLabs multilingual neural voice",
            description="Converts text into high-quality multilingual speech using ElevenLabs API.",
            category="speech",
            parameters=ElevenLabsSynthesizeParameters,
            handler=handle_synthesize,
            timeout_seconds=30.0,
            requires_confirmation=False,
        )
    )

