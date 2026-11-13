"""
Dev Agent built-in action handlers (TASK-GAP-03 / GAP-03).

Exposes 'dev.agent' action for autonomous multi-file project scaffolding,
dependency installation, execution, and self-correcting error fixing.
"""

from __future__ import annotations

import logging

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse
from app.schemas.dev_agent import DevAgentParameters
from app.services.dev_agent_service import DevAgentService

logger = logging.getLogger(__name__)


def register_dev_agent_actions(
    registry: ActionRegistry,
    dev_service: DevAgentService,
) -> None:
    """Register autonomous dev agent actions with the ActionRegistry."""

    def handle_dev_agent(params: DevAgentParameters) -> ActionOutcomeResponse:
        return dev_service.execute(params)

    registry.register(
        ActionDefinition(
            action_id="dev.agent",
            name="Autonomous multi-file software engineering agent",
            description=(
                "Architects and builds complete multi-file projects: plans file dependencies, "
                "writes source files, installs pip packages, executes tests, and autonomously fixes errors."
            ),
            category="automation",
            parameters=DevAgentParameters,
            handler=handle_dev_agent,
            timeout_seconds=120.0,
            requires_confirmation=True,
        )
    )

