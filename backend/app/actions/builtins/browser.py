"""
Browser automation built-in action handlers (TASK-GAP-01 / GAP-01).

Exposes 'browser.control' for web navigation, search, and Playwright DOM automation.
"""

from __future__ import annotations

import logging

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse
from app.schemas.browser_control import BrowserControlParameters
from app.services.browser_control_service import BrowserControlService

logger = logging.getLogger(__name__)


def register_browser_actions(
    registry: ActionRegistry,
    browser_service: BrowserControlService,
) -> None:
    """Register browser navigation and automation actions with the ActionRegistry."""

    def handle_control(params: BrowserControlParameters) -> ActionOutcomeResponse:
        return browser_service.execute(params)

    registry.register(
        ActionDefinition(
            action_id="browser.control",
            name="Browser navigation and automation",
            description="Open URLs, launch browsers, search the web, and perform interactive web automation.",
            category="automation",
            parameters=BrowserControlParameters,
            handler=handle_control,
            timeout_seconds=60.0,
            requires_confirmation=True,
        )
    )

