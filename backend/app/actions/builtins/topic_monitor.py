"""
Topic Monitor built-in action handlers (GAP-11).

Exposes 'topic.monitor' for user-configured background topic news tracking.
"""

from __future__ import annotations

import logging

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse
from app.schemas.topic_monitor import TopicMonitorParameters
from app.services.topic_monitor_service import TopicMonitorService

logger = logging.getLogger(__name__)


def register_topic_monitor_actions(
    registry: ActionRegistry,
    monitor_service: TopicMonitorService,
) -> None:
    """Register topic news monitor actions with the ActionRegistry."""

    def handle_topic_monitor(params: TopicMonitorParameters) -> ActionOutcomeResponse:
        return monitor_service.execute(params)

    registry.register(
        ActionDefinition(
            action_id="topic.monitor",
            name="Track background topic news with daily headline monitoring",
            description="Monitors user-configured topics for breaking news headlines via DuckDuckGo, alerting when new stories appear.",
            category="search",
            parameters=TopicMonitorParameters,
            handler=handle_topic_monitor,
            timeout_seconds=30.0,
            requires_confirmation=False,
        )
    )

