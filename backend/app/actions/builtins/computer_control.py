from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.services.computer_control_service import (
    ComputerControlService,
    ControlParameters,
    PermissionParameters,
    StopParameters,
)


class RequestIdParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID


def register_computer_control_actions(
    registry: ActionRegistry,
    service: ComputerControlService,
) -> None:
    registry.register(ActionDefinition(
        action_id="computer.status",
        name="Get desktop-control status",
        description="Check whether desktop control is available, permitted, or currently running.",
        category="computer",
        parameters=StopParameters,
        handler=lambda _: service.status(),
        timeout_seconds=5,
    ))
    registry.register(ActionDefinition(
        action_id="computer.request",
        name="Request a desktop-control operation",
        description=(
            "Propose one bounded mouse, keyboard, clipboard, window, or screen operation "
            "for the user to review. "
            "This never controls the computer until the user approves it in Alex."
        ),
        category="computer",
        parameters=ControlParameters,
        handler=lambda params: service.request_control(params),
        timeout_seconds=5,
    ))
    registry.register(ActionDefinition(
        action_id="computer.pending",
        name="List pending desktop-control requests",
        description="List desktop operations awaiting the user's approval.",
        category="computer",
        parameters=StopParameters,
        handler=lambda _: service.pending_requests(),
        timeout_seconds=5,
    ))
    registry.register(ActionDefinition(
        action_id="computer.approve",
        name="Approve a desktop-control request",
        description="Execute a desktop-control request after explicit user approval.",
        category="computer",
        parameters=RequestIdParameters,
        handler=lambda params: service.approve_request(str(params.request_id)),
        timeout_seconds=15,
        requires_confirmation=True,
    ))
    registry.register(ActionDefinition(
        action_id="computer.dismiss",
        name="Dismiss a desktop-control request",
        description="Dismiss a pending desktop-control request.",
        category="computer",
        parameters=RequestIdParameters,
        handler=lambda params: service.dismiss_request(str(params.request_id)),
        timeout_seconds=5,
        requires_confirmation=True,
    ))
    registry.register(ActionDefinition(
        action_id="computer.permission",
        name="Grant or revoke desktop-control permission",
        description="Grant desktop-control permission for this Alex session, or revoke it.",
        category="computer",
        parameters=PermissionParameters,
        handler=lambda params: service.set_permission(params.enabled),
        timeout_seconds=5,
        requires_confirmation=True,
    ))
    registry.register(ActionDefinition(
        action_id="computer.control",
        name="Execute an approved desktop operation",
        description=(
            "Execute one bounded mouse, keyboard, clipboard, window, screenshot, or visual-search operation. "
            "Requires session permission and per-operation user confirmation."
        ),
        category="computer",
        parameters=ControlParameters,
        handler=lambda params: service.execute(params),
        timeout_seconds=15,
        requires_confirmation=True,
    ))
    registry.register(ActionDefinition(
        action_id="computer.stop",
        name="Emergency stop desktop control",
        description="Stop the current desktop-control operation and release the mouse button.",
        category="computer",
        parameters=StopParameters,
        handler=lambda _: service.stop(),
        timeout_seconds=5,
    ))
