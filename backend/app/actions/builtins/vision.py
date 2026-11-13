"""
Vision built-in action handlers (TASK-GAP-07 / GAP-07).

Exposes 'vision.capture' for capturing video frames from webcams or desktop screens.
"""

from __future__ import annotations

import logging

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse
from app.schemas.vision import VisionCaptureParameters
from app.services.vision_service import VisionService

logger = logging.getLogger(__name__)


def register_vision_actions(
    registry: ActionRegistry,
    vision_service: VisionService,
) -> None:
    """Register vision capture actions with the ActionRegistry."""

    def handle_capture(params: VisionCaptureParameters) -> ActionOutcomeResponse:
        return vision_service.execute(params)

    registry.register(
        ActionDefinition(
            action_id="vision.capture",
            name="Capture visual frame from webcam or screen",
            description="Captures an image frame from the user's webcam or desktop display.",
            category="vision",
            parameters=VisionCaptureParameters,
            handler=handle_capture,
            timeout_seconds=20.0,
            requires_confirmation=False,
        )
    )

