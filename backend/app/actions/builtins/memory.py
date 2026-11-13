from pydantic import BaseModel, ConfigDict, Field

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, done
from app.services.memory_service import MemoryService


class RecallParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(default="", max_length=200)


def register_memory_actions(registry: ActionRegistry, memory: MemoryService) -> None:
    def recall(parameters: RecallParameters) -> ActionOutcomeResponse:
        query = parameters.query.strip().casefold()
        entries = memory.list_entries()
        if query:
            entries = [
                entry
                for entry in entries
                if query in entry.key.casefold()
                or query in entry.value.casefold()
                or query in entry.category.casefold()
            ]
        serialized = [entry.model_dump(mode="json") for entry in entries[:40]]
        return done(
            "memory.recall",
            "Memory recall completed.",
            data=serialized,
        )

    registry.register(ActionDefinition(
        action_id="memory.recall",
        name="Recall saved memory",
        description=(
            "Find user-saved facts by matching a query against their category, name, or value."
        ),
        category="memory",
        parameters=RecallParameters,
        handler=recall,
        timeout_seconds=5,
    ))
