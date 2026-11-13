"""
Desktop environment built-in action handlers (TASK-GAP-06 / GAP-06).

Exposes 'desktop.environment' for wallpaper setting, desktop organization,
hygiene archiving, listing, and storage statistics.
"""

from __future__ import annotations

import logging

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse
from app.schemas.desktop_environment import DesktopActionParameters
from app.services.desktop_environment_service import DesktopEnvironmentService

logger = logging.getLogger(__name__)


def register_desktop_environment_actions(
    registry: ActionRegistry,
    desktop_service: DesktopEnvironmentService,
) -> None:
    """Register desktop hygiene and wallpaper management actions with the ActionRegistry."""

    def handle_desktop(params: DesktopActionParameters) -> ActionOutcomeResponse:
        return desktop_service.execute(params)

    registry.register(
        ActionDefinition(
            action_id="desktop.environment",
            name="Desktop hygiene and wallpaper manager",
            description=(
                "Manage desktop wallpaper, sort loose files into categorized folders, "
                "archive clutter, or inspect desktop storage statistics."
            ),
            category="system",
            parameters=DesktopActionParameters,
            handler=handle_desktop,
            timeout_seconds=30.0,
            requires_confirmation=False,
        )
    )

