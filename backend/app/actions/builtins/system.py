from pydantic import BaseModel, ConfigDict

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import done
from app.services.system_metrics_service import SystemMetricsService


class NoParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")


def register_system_actions(
    registry: ActionRegistry,
    metrics: SystemMetricsService,
) -> None:
    registry.register(ActionDefinition(
        action_id="system.get_metrics",
        name="Get system metrics",
        description="Read current CPU, memory, network, OS, uptime and available sensors.",
        category="system",
        parameters=NoParameters,
        handler=lambda _: done("system.get_metrics", "System metrics snapshot captured.", data=metrics.snapshot().model_dump(mode="json")),
        timeout_seconds=5,
    ))
