"""
Code helper built-in action handlers (TASK-GAP-04 / GAP-04).

Exposes 'code.helper' action for single-file script generation, modification,
semantic explanation, test execution, iterative build-fix, and optimization.
"""

from __future__ import annotations

import logging

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse
from app.schemas.code_helper import CodeHelperParameters
from app.services.code_helper_service import CodeHelperService

logger = logging.getLogger(__name__)


def register_code_helper_actions(
    registry: ActionRegistry,
    code_service: CodeHelperService,
) -> None:
    """Register single-file interactive code helper actions with the ActionRegistry."""

    def handle_code_helper(params: CodeHelperParameters) -> ActionOutcomeResponse:
        return code_service.execute(params)

    registry.register(
        ActionDefinition(
            action_id="code.helper",
            name="Single-file interactive code assistant",
            description=(
                "Write, edit, explain, run, iteratively build and fix, or optimize single-file scripts."
            ),
            category="automation",
            parameters=CodeHelperParameters,
            handler=handle_code_helper,
            timeout_seconds=60.0,
            requires_confirmation=True,
        )
    )

