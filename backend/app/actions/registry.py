"""
Compatibility re-export for ActionRegistry and ActionDefinition.
"""

from app.actions.action_registry import (
    ActionDefinition,
    ActionHandler,
    ActionRegistry,
)

__all__ = ["ActionDefinition", "ActionHandler", "ActionRegistry"]

