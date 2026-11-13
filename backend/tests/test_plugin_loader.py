from __future__ import annotations

import asyncio
from pathlib import Path
import pytest

from app.actions.action_executor import ActionExecutor
from app.actions.action_registry import ActionRegistry
from app.services.plugin_loader_service import PluginLoaderService


def test_plugin_loader_discovers_and_registers_plugins(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir(parents=True)

    # 1. Plugin with TOOL_DECLARATION and run()
    plugin_py = """
TOOL_DECLARATION = {
    "name": "sample_weather",
    "description": "Get weather for a city",
    "requires_confirmation": False,
}

def run(params):
    return {"forecast": "Sunny", "temp_c": 21}
"""
    (plugins_dir / "weather_plugin.py").write_text(plugin_py, encoding="utf-8")

    registry = ActionRegistry()
    loader = PluginLoaderService(plugins_dir=plugins_dir)
    loaded = loader.discover_and_register(registry)

    assert "plugin.sample_weather" in loaded
    assert registry.get("plugin.sample_weather") is not None

    # Test executing the dynamic plugin action
    executor = ActionExecutor(registry)

    async def _test():
        res = await executor.execute("plugin.sample_weather", {})
        assert res.status == "success"
        assert res.data["outcome_status"] == "done"
        assert res.data["forecast"] == "Sunny"

    asyncio.run(_test())


def test_plugin_loader_handles_broken_plugin_gracefully(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir(parents=True)

    # Broken syntax plugin
    (plugins_dir / "broken.py").write_text("def broken_syntax( {", encoding="utf-8")

    registry = ActionRegistry()
    loader = PluginLoaderService(plugins_dir=plugins_dir)
    loaded = loader.discover_and_register(registry)

    # Does not crash, ignores broken plugin
    assert "plugin.broken" not in loaded
