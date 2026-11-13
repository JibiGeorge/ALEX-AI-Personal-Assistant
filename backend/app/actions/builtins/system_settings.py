"""
System settings built-in action handlers (TASK-GAP-02 / GAP-02).

Exposes 'system.setting' action for hardware macros:
volume, brightness, Wi-Fi toggle, screen locking, and system utilities.
"""

from __future__ import annotations

import logging

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse
from app.schemas.system_settings import SystemSettingParameters
from app.services.system_settings_service import SystemSettingsService

logger = logging.getLogger(__name__)


def register_system_settings_actions(
    registry: ActionRegistry,
    settings_service: SystemSettingsService,
) -> None:
    """Register system hardware settings macros with the ActionRegistry."""

    def handle_setting(params: SystemSettingParameters) -> ActionOutcomeResponse:
        return settings_service.execute(params)

    registry.register(
        ActionDefinition(
            action_id="system.setting",
            name="Adjust system settings and hardware controls",
            description=(
                "Control hardware volume (up, down, mute, level), screen brightness, "
                "toggle Wi-Fi, lock display/session, or open system preferences."
            ),
            category="system",
            parameters=SystemSettingParameters,
            handler=handle_setting,
            timeout_seconds=30.0,
            requires_confirmation=False,
        )
    )

