import asyncio

import pytest
from pydantic import BaseModel

from app.actions.action_executor import (
    ActionExecutionResult,
    ActionExecutor,
    model_function_response,
)
from app.actions.action_registry import ActionDefinition, ActionRegistry


class Parameters(BaseModel):
    value: int


def test_registry_rejects_duplicate_ids_and_invalid_timeout():
    registry = ActionRegistry()
    action = ActionDefinition(
        action_id="test.echo",
        name="Echo",
        description="Return a value.",
        category="test",
        parameters=Parameters,
        handler=lambda params: params.value,
    )
    registry.register(action)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(action)
    with pytest.raises(ValueError, match="timeout"):
        registry.register(ActionDefinition(
            action_id="test.long",
            name="Long",
            description="Too long.",
            category="test",
            parameters=Parameters,
            handler=lambda _: None,
            timeout_seconds=121,
        ))


def test_model_declarations_exclude_confirmation_gated_actions():
    registry = ActionRegistry()
    registry.register(ActionDefinition(
        action_id="test.safe",
        name="Safe read",
        description="Read available data.",
        category="test",
        parameters=Parameters,
        handler=lambda _: None,
    ))
    registry.register(ActionDefinition(
        action_id="test.confirmed",
        name="Confirmed action",
        description="Requires user consent.",
        category="test",
        parameters=Parameters,
        handler=lambda _: None,
        requires_confirmation=True,
    ))

    declarations = registry.model_declarations()

    assert [declaration.name for declaration in declarations] == ["test.safe"]
    assert declarations[0].parameters_json_schema["properties"]["value"]["type"] == "integer"
    registry.set_enabled("test.safe", False)
    assert registry.model_declarations() == []


def test_model_function_response_does_not_expose_handler_exception_details():
    response = model_function_response(ActionExecutionResult(
        action_id="test.echo",
        status="failed",
        message="Action execution failed.",
        error="RuntimeError: private-path-or-token",
        execution_time=0.1,
    ))

    assert response == {"error": "Action failed.", "status": "failed"}


def test_executor_validates_runs_and_records_errors():
    registry = ActionRegistry()
    registry.register(ActionDefinition(
        action_id="test.echo",
        name="Echo",
        description="Return a value.",
        category="test",
        parameters=Parameters,
        handler=lambda params: {"value": params.value},
    ))
    executor = ActionExecutor(registry)

    async def execute():
        success = await executor.execute("test.echo", {"value": 7})
        invalid = await executor.execute("test.echo", {"value": "wrong"})
        unknown = await executor.execute("test.missing", {})
        return success, invalid, unknown, await executor.history()

    success, invalid, unknown, history = asyncio.run(execute())
    assert success.status == "success"
    assert success.data == {"value": 7}
    assert invalid.status == "rejected"
    assert unknown.status == "rejected"
    assert [item.action_id for item in history] == [
        "test.missing",
        "test.echo",
        "test.echo",
    ]
