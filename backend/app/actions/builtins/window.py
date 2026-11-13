"""
Window management built-in action handlers (TASK-P5-01 / TASK-P5-02 / TASK-P5-03).

Exposes 'window.list', 'window.active', 'window.focus', and 'window.close'
actions for cross-platform desktop window management.
"""

from __future__ import annotations

import logging
from pydantic import BaseModel, ConfigDict, Field

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, done, failed
from app.services.window_management_service import WindowManagementService

logger = logging.getLogger(__name__)


class WindowEmptyParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WindowIdentifierParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(
        min_length=1,
        max_length=512,
        description="Target window title, process/app name, or numeric window handle ID.",
    )


def register_window_actions(
    registry: ActionRegistry,
    window_service: WindowManagementService,
) -> None:
    """Register desktop window management actions with the action registry."""

    def handle_list(_params: WindowEmptyParameters) -> ActionOutcomeResponse:
        try:
            windows = window_service.list_windows()
            return done(
                action="window.list",
                message=f"Found {len(windows)} visible desktop windows.",
                data={"windows": windows, "count": len(windows)},
            )
        except Exception as exc:
            logger.exception("window.list action failed")
            return failed(
                action="window.list",
                error=str(exc),
                message=f"Failed to list desktop windows: {exc}",
            )

    def handle_active(_params: WindowEmptyParameters) -> ActionOutcomeResponse:
        try:
            active = window_service.get_active_window()
            if active is None:
                return done(
                    action="window.active",
                    message="No active foreground window found.",
                    data={"active": None},
                )
            app_name = active.get("application", "unknown")
            return done(
                action="window.active",
                message=f"Active window: {active.get('title', 'unknown')} (app: {app_name}).",
                data={"active": active},
            )
        except Exception as exc:
            logger.exception("window.active action failed")
            return failed(
                action="window.active",
                error=str(exc),
                message=f"Failed to inspect active window: {exc}",
            )

    def handle_focus(params: WindowIdentifierParameters) -> ActionOutcomeResponse:
        try:
            result = window_service.focus_window(params.identifier)
            win = result.get("window", {})
            return done(
                action="window.focus",
                message=f"Focused window: {win.get('title', params.identifier)}.",
                data=result,
            )
        except Exception as exc:
            logger.exception("window.focus action failed")
            return failed(
                action="window.focus",
                error=str(exc),
                message=f"Could not focus window '{params.identifier}': {exc}",
            )

    def handle_close(params: WindowIdentifierParameters) -> ActionOutcomeResponse:
        try:
            result = window_service.close_window(params.identifier)
            win = result.get("window", {})
            return done(
                action="window.close",
                message=f"Sent polite close request to '{win.get('title', params.identifier)}'.",
                data=result,
            )
        except Exception as exc:
            logger.exception("window.close action failed")
            return failed(
                action="window.close",
                error=str(exc),
                message=f"Could not close window '{params.identifier}': {exc}",
            )

    registry.register(ActionDefinition(
        action_id="window.list",
        name="List desktop windows",
        description="Enumerate all visible top-level application windows on the desktop.",
        category="system",
        parameters=WindowEmptyParameters,
        handler=handle_list,
        timeout_seconds=5,
    ))
    registry.register(ActionDefinition(
        action_id="window.active",
        name="Get active window",
        description="Retrieve information about the currently active foreground desktop window.",
        category="system",
        parameters=WindowEmptyParameters,
        handler=handle_active,
        timeout_seconds=5,
    ))
    registry.register(ActionDefinition(
        action_id="window.focus",
        name="Focus desktop window",
        description="Bring a target desktop application window to the foreground by title or ID.",
        category="system",
        parameters=WindowIdentifierParameters,
        handler=handle_focus,
        timeout_seconds=5,
    ))
    registry.register(ActionDefinition(
        action_id="window.close",
        name="Close desktop window",
        description="Politely request a desktop window or application to close via standard OS close signals.",
        category="system",
        parameters=WindowIdentifierParameters,
        handler=handle_close,
        timeout_seconds=5,
    ))
