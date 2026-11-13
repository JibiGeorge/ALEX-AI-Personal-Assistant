"""
Automated unit tests for Dynamic Tool Budgeting Engine (TASK-P3-07).

Verifies:
- Restricting tool count for 8B models (clamping to max 12 tools).
- Restricting tool count for 3B models (clamping to max 8 tools).
- Prioritizing frequently used tools via usage statistics.
- Enforcing character payload limits (<9,000 chars for 8B models).
- Query keyword relevance ranking and promotion.
- Unconstrained pass-through for flagship cloud models (Gemini / GPT-4o).
- Preservation of safety-critical confirmation gates for high-risk actions.
- Integration with ActionRegistry.get_budgeted_declarations and get_budgeted_tools.
"""

from __future__ import annotations

import asyncio
import json
import pytest
from pydantic import BaseModel, Field

from app.actions.action_executor import ActionExecutor
from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.providers.schema_budget import (
    BUDGET_PROFILES,
    CORE_TOOLS_PRIORITY,
    ToolBudgetConfig,
    budget_tools,
    extract_tool_parts,
    payload_size,
)


def _generate_dummy_tools(count: int, param_size: int = 100) -> list[dict]:
    """Generate arbitrary tool schemas with configurable parameter payload sizes."""
    tools = []
    for i in range(count):
        props = {
            f"field_{j}": {"type": "string", "description": f"Field description {j} " + ("x" * param_size)}
            for j in range(3)
        }
        tools.append({
            "name": f"tool_action_{i:02d}",
            "description": f"Generic automated action handler number {i:02d}",
            "parameters": {
                "type": "object",
                "properties": props,
                "required": ["field_0"],
            },
        })
    return tools


# ==============================================================================
# Tool Budget Limits Tests
# ==============================================================================

def test_tool_budget_restricts_tool_count_for_8b_models():
    """Verify tool budgeting restricts 25 tools to max 12 for 8B models."""
    tools = _generate_dummy_tools(25, param_size=20)
    assert len(tools) == 25

    budgeted = budget_tools(tools, capacity_or_config="8b")
    assert len(budgeted) == 12
    assert len(budgeted) <= BUDGET_PROFILES["8b"]["max_tools"]


def test_tool_budget_restricts_tool_count_for_3b_models():
    """Verify tool budgeting restricts 25 tools to max 8 for 3B models."""
    tools = _generate_dummy_tools(25, param_size=20)
    budgeted = budget_tools(tools, capacity_or_config="3b")
    assert len(budgeted) == 8
    assert len(budgeted) <= BUDGET_PROFILES["3b"]["max_tools"]


def test_tool_budget_full_capacity_for_cloud_models():
    """Verify flagship cloud models receive all tool declarations without pruning."""
    tools = _generate_dummy_tools(25, param_size=50)

    budgeted_full = budget_tools(tools, capacity_or_config="full")
    assert len(budgeted_full) == 25
    assert budgeted_full == tools

    budgeted_gemini = budget_tools(tools, capacity_or_config="gemini")
    assert len(budgeted_gemini) == 25

    budgeted_gpt = budget_tools(tools, capacity_or_config="gpt-4o")
    assert len(budgeted_gpt) == 25


def test_tool_budget_enforces_character_limit():
    """Verify total JSON schema payload size is clamped under 9,000 characters for 8B models."""
    # Create 15 tools with large parameter schemas (~1,500 chars each = >22,000 chars total)
    large_tools = _generate_dummy_tools(15, param_size=400)
    initial_size = payload_size(large_tools)
    assert initial_size > 15000

    budgeted = budget_tools(large_tools, capacity_or_config="8b")
    final_size = payload_size(budgeted)

    assert final_size <= 9000
    assert len(budgeted) <= 12
    # Verify non-empty and fits comfortably
    assert len(budgeted) > 0


# ==============================================================================
# Tool Ranking & Prioritization Tests
# ==============================================================================

def test_tool_budget_prioritizes_frequently_used_tools():
    """Verify tools with high runtime usage frequency are prioritized over unused tools."""
    tools = [
        {"name": "tool_unused_alpha", "description": "Rarely used alpha action", "parameters": {}},
        {"name": "tool_unused_beta", "description": "Rarely used beta action", "parameters": {}},
        {"name": "tool_unused_gamma", "description": "Rarely used gamma action", "parameters": {}},
        {"name": "tool_frequent_hero", "description": "Special non-core action with high usage", "parameters": {}},
    ]

    # Constrain to 2 tools
    config = ToolBudgetConfig(max_tools=2, max_chars=5000)
    usage_stats = {"tool_frequent_hero": 150, "tool_unused_alpha": 1}

    budgeted = budget_tools(tools, capacity_or_config=config, usage_stats=usage_stats)
    budgeted_names = [t["name"] for t in budgeted]

    assert len(budgeted) == 2
    assert "tool_frequent_hero" in budgeted_names


def test_tool_budget_query_relevance_promotion():
    """Verify tool relevant to the user query is prioritized into a restricted budget."""
    tools = [
        {"name": "read_notes", "description": "Read personal notes", "parameters": {}},
        {"name": "weather_lookup", "description": "Check current weather forecast", "parameters": {}},
        {"name": "document_converter", "description": "Convert markdown document to PDF format", "parameters": {}},
        {"name": "volume_adjuster", "description": "Change speaker volume", "parameters": {}},
    ]

    # Restrict to only 1 tool
    config = ToolBudgetConfig(max_tools=1, max_chars=5000)
    user_query = "Can you convert this document to PDF?"

    budgeted = budget_tools(tools, capacity_or_config=config, user_query=user_query)
    assert len(budgeted) == 1
    assert budgeted[0]["name"] == "document_converter"


def test_tool_budget_core_tools_priority():
    """Verify built-in core tools take precedence over generic extra tools in tight budget."""
    tools = [
        {"name": "arbitrary_custom_plugin", "description": "Third party plugin", "parameters": {}},
        {"name": "web_search", "description": "Search the live internet for information", "parameters": {}},
        {"name": "another_extra_tool", "description": "Extra helper", "parameters": {}},
    ]

    config = ToolBudgetConfig(max_tools=1, max_chars=5000)
    budgeted = budget_tools(tools, capacity_or_config=config)
    assert len(budgeted) == 1
    assert budgeted[0]["name"] == "web_search"


# ==============================================================================
# Security Confirmation Gate Preservation Tests
# ==============================================================================

def test_high_risk_actions_preserve_confirmation_gates():
    """Verify that high-risk actions requiring confirmation preserve confirmation gates."""
    async def _test():
        registry = ActionRegistry()

        class ControlParams(BaseModel):
            target: str

        def fake_handler(params: ControlParams):
            return {"status": "executed", "target": params.target}

        dangerous_action = ActionDefinition(
            action_id="computer_control",
            name="Computer Control",
            description="Direct OS peripheral control",
            category="system",
            parameters=ControlParams,
            handler=fake_handler,
            requires_confirmation=True,
        )
        safe_action = ActionDefinition(
            action_id="web_search",
            name="Web Search",
            description="Search public internet",
            category="network",
            parameters=ControlParams,
            handler=fake_handler,
            requires_confirmation=False,
        )

        registry.register(dangerous_action)
        registry.register(safe_action)

        executor = ActionExecutor(registry)

        # Attempt execution without confirmation -> Must be rejected
        rejected_result = await executor.execute("computer_control", {"target": "click"}, confirmed=False)
        assert rejected_result.status == "rejected"
        assert "confirmation" in rejected_result.message.lower()

        # Attempt execution with confirmation -> Succeeds
        confirmed_result = await executor.execute("computer_control", {"target": "click"}, confirmed=True)
        assert confirmed_result.status == "success"

        # Verify model_declarations excludes dangerous unconfirmed actions
        decls = registry.model_declarations()
        decl_names = [d.name for d in decls]
        assert "computer_control" not in decl_names
        assert "web_search" in decl_names

    asyncio.run(_test())


# ==============================================================================
# ActionRegistry Budgeting Integration Tests
# ==============================================================================

def test_action_registry_get_budgeted_declarations_and_tools():
    """Verify ActionRegistry.get_budgeted_declarations and get_budgeted_tools."""
    registry = ActionRegistry()

    class SimpleParams(BaseModel):
        query: str

    for i in range(16):
        registry.register(
            ActionDefinition(
                action_id=f"action_{i:02d}",
                name=f"Action {i}",
                description=f"Automated action {i}",
                category="test",
                parameters=SimpleParams,
                handler=lambda p: None,
            )
        )

    # Full capacity
    full_decls = registry.get_budgeted_declarations(model_capacity="full")
    assert len(full_decls) == 16

    # 8B model capacity -> Clamped to 12
    decls_8b = registry.get_budgeted_declarations(model_capacity="8b")
    assert len(decls_8b) == 12

    # 3B model capacity -> Clamped to 8
    tools_3b = registry.get_budgeted_tools(model_capacity="3b")
    assert len(tools_3b) == 8
    assert all("name" in t for t in tools_3b)
