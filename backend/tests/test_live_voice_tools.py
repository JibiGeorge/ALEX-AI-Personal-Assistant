import asyncio

from google.genai import types
from pydantic import BaseModel, ConfigDict

from app.actions.action_executor import ActionExecutor
from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.services.live_voice_service import LiveVoiceService


class NoParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FakeSession:
    def __init__(self):
        self.responses = []

    async def send_tool_response(self, *, function_responses):
        self.responses.extend(function_responses)


def create_service():
    registry = ActionRegistry()
    registry.register(ActionDefinition(
        action_id="system.get_metrics",
        name="Get metrics",
        description="Read system metrics.",
        category="system",
        parameters=NoParameters,
        handler=lambda _: {"cpu_percent": 12},
    ))
    return LiveVoiceService(
        settings=None,
        memory=None,
        action_registry=registry,
        action_executor=ActionExecutor(registry),
    )


def test_live_tool_calls_execute_registered_action_and_return_result():
    service = create_service()
    session = FakeSession()
    function_call = type(
        "FunctionCall",
        (),
        {"id": "call-1", "name": "system.get_metrics", "args": {}},
    )()

    executed = asyncio.run(service._handle_tool_calls(session, [function_call], 0))

    assert executed == 1
    assert session.responses[0].id == "call-1"
    assert session.responses[0].response == {
        "output": {"cpu_percent": 12},
        "status": "success",
    }


def test_live_config_accepts_registry_generated_tool_declarations():
    service = create_service()
    assert service._action_registry is not None

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        tools=[
            types.Tool(
                function_declarations=service._action_registry.model_declarations(),
            )
        ],
    )

    assert config.tools[0].function_declarations[0].name == "system.get_metrics"


def test_live_tool_calls_enforce_per_turn_limit():
    service = create_service()
    session = FakeSession()
    function_call = type(
        "FunctionCall",
        (),
        {"id": "call-2", "name": "system.get_metrics", "args": {}},
    )()

    executed = asyncio.run(service._handle_tool_calls(session, [function_call], 4))

    assert executed == 1
    assert session.responses[0].response == {
        "error": "The action limit for this conversation turn was reached.",
    }
    assert asyncio.run(service._action_executor.history()) == []
