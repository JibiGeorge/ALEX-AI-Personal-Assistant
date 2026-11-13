import importlib.util
from dataclasses import dataclass
from typing import Any, Callable

from google.genai import types
from pydantic import BaseModel

ActionHandler = Callable[[BaseModel], Any]


@dataclass(frozen=True)
class ActionDefinition:
    action_id: str
    name: str
    description: str
    category: str
    parameters: type[BaseModel]
    handler: ActionHandler
    enabled: bool = True
    dependencies: tuple[str, ...] = ()
    timeout_seconds: float = 15.0
    requires_confirmation: bool = False

    def public_view(self) -> dict[str, object]:
        missing = tuple(
            dependency
            for dependency in self.dependencies
            if importlib.util.find_spec(dependency) is None
        )
        return {
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": self.parameters.model_json_schema(),
            "enabled": self.enabled and not missing,
            "missing_dependencies": list(missing),
            "timeout_seconds": self.timeout_seconds,
            "requires_confirmation": self.requires_confirmation,
        }


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, ActionDefinition] = {}

    def register(self, action: ActionDefinition) -> None:
        if not action.action_id or len(action.action_id) > 100:
            raise ValueError("Action ID must contain 1 to 100 characters")
        if action.action_id in self._actions:
            raise ValueError(f"Action is already registered: {action.action_id}")
        if action.timeout_seconds <= 0 or action.timeout_seconds > 120:
            raise ValueError("Action timeout must be greater than 0 and at most 120 seconds")
        self._actions[action.action_id] = action

    def get(self, action_id: str) -> ActionDefinition | None:
        return self._actions.get(action_id)

    def list(self) -> list[ActionDefinition]:
        return sorted(self._actions.values(), key=lambda action: (action.category, action.name))

    def model_declarations(self) -> list[types.FunctionDeclaration]:
        return [
            types.FunctionDeclaration(
                name=action.action_id,
                description=action.description,
                parameters_json_schema=action.parameters.model_json_schema(),
            )
            for action in self.list()
            if action.enabled
            and not action.requires_confirmation
            and action.public_view()["enabled"]
        ]

    def get_budgeted_declarations(
        self,
        model_capacity: str = "full",
        user_query: str | None = None,
        usage_stats: dict[str, int] | None = None,
    ) -> list[types.FunctionDeclaration]:
        """Return Gemini function declarations budgeted and ranked for model capacity."""
        from app.providers.schema_budget import budget_tools
        full_declarations = self.model_declarations()
        return budget_tools(
            full_declarations,
            capacity_or_config=model_capacity,
            user_query=user_query,
            usage_stats=usage_stats,
        )

    def get_budgeted_tools(
        self,
        model_capacity: str = "full",
        user_query: str | None = None,
        usage_stats: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        """Return raw tool schemas budgeted and ranked for model capacity."""
        from app.providers.schema_budget import budget_tools
        raw_tools = [
            {
                "name": action.action_id,
                "description": action.description,
                "parameters": action.parameters.model_json_schema(),
                "requires_confirmation": action.requires_confirmation,
            }
            for action in self.list()
            if action.enabled
            and not action.requires_confirmation
            and action.public_view()["enabled"]
        ]
        return budget_tools(
            raw_tools,
            capacity_or_config=model_capacity,
            user_query=user_query,
            usage_stats=usage_stats,
        )

    def set_enabled(self, action_id: str, enabled: bool) -> ActionDefinition:
        action = self._actions.get(action_id)
        if action is None:
            raise KeyError(action_id)
        updated = ActionDefinition(
            action_id=action.action_id,
            name=action.name,
            description=action.description,
            category=action.category,
            parameters=action.parameters,
            handler=action.handler,
            enabled=enabled,
            dependencies=action.dependencies,
            timeout_seconds=action.timeout_seconds,
            requires_confirmation=action.requires_confirmation,
        )
        self._actions[action_id] = updated
        return updated
