"""
Messaging built-in action handlers (TASK-GAP-05 / GAP-05).

Exposes 'message.send' for automated message dispatch across WhatsApp, Telegram,
Signal, Discord, and Instagram.
"""

from __future__ import annotations

import logging

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse
from app.schemas.messaging import SendMessageParameters
from app.services.messaging_service import MessagingService

logger = logging.getLogger(__name__)


def register_messaging_actions(
    registry: ActionRegistry,
    messaging_service: MessagingService,
) -> None:
    """Register messaging actions with the ActionRegistry."""

    def handle_send_message(params: SendMessageParameters) -> ActionOutcomeResponse:
        return messaging_service.execute(params)

    registry.register(
        ActionDefinition(
            action_id="message.send",
            name="Send message via WhatsApp or Telegram",
            description="Send a message to a recipient contact via WhatsApp, Telegram, Signal, Discord, or Instagram.",
            category="communication",
            parameters=SendMessageParameters,
            handler=handle_send_message,
            timeout_seconds=30.0,
            requires_confirmation=True,
        )
    )

