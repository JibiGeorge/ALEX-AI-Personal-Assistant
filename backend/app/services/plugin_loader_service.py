from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any, Callable, Optional
from pydantic import BaseModel, create_model

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, done, failed

logger = logging.getLogger(__name__)


class PluginLoaderService:
    def __init__(self, plugins_dir: Optional[Path] = None) -> None:
        self.plugins_dir = plugins_dir or (Path.home() / ".alex" / "plugins")
        try:
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self._loaded_plugins: list[str] = []

    @property
    def loaded_plugins(self) -> list[str]:
        return list(self._loaded_plugins)

    def discover_and_register(self, registry: ActionRegistry) -> list[str]:
        if not self.plugins_dir.exists():
            return []

        registered: list[str] = []
        for file_path in sorted(self.plugins_dir.glob("*.py")):
            if file_path.name.startswith(("_", ".")):
                continue

            plugin_name = file_path.stem
            try:
                spec = importlib.util.spec_from_file_location(
                    f"alex_plugin_{plugin_name}", file_path
                )
                if not spec or not spec.loader:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Pattern 1: Module defines register_actions(registry)
                if hasattr(module, "register_actions") and callable(module.register_actions):
                    module.register_actions(registry)
                    registered.append(f"custom.{plugin_name}")
                    continue

                # Pattern 2: Module defines ACTION_DEFINITION
                action_def = getattr(module, "ACTION_DEFINITION", None)
                if isinstance(action_def, ActionDefinition):
                    registry.register(action_def)
                    registered.append(action_def.action_id)
                    continue

                # Pattern 3: Mark-LVI style TOOL_DECLARATION / TOOL_SPEC + run()
                tool_decl = getattr(module, "TOOL_DECLARATION", None) or getattr(module, "TOOL_SPEC", None)
                run_fn = getattr(module, "run", None)
                if isinstance(tool_decl, dict) and callable(run_fn):
                    t_name = str(tool_decl.get("name") or plugin_name).lower()
                    t_desc = str(tool_decl.get("description") or f"Custom plugin {plugin_name}")
                    action_id = f"plugin.{t_name}"

                    class DynamicPluginParams(BaseModel):
                        pass

                    def make_handler(fn: Callable) -> Callable:
                        def _handler(params: BaseModel) -> ActionOutcomeResponse:
                            try:
                                res = fn(params.model_dump())
                                return done(
                                    action=action_id,
                                    data={"result": res} if not isinstance(res, dict) else res,
                                    message=f"Plugin {plugin_name} executed successfully",
                                )
                            except Exception as ex:
                                return failed(
                                    action=action_id,
                                    error=f"Plugin {plugin_name} error: {ex}",
                                )
                        return _handler

                    def_obj = ActionDefinition(
                        action_id=action_id,
                        name=f"Plugin: {plugin_name}",
                        description=t_desc,
                        category="plugin",
                        parameters=DynamicPluginParams,
                        handler=make_handler(run_fn),
                        requires_confirmation=bool(tool_decl.get("requires_confirmation", False)),
                    )
                    registry.register(def_obj)
                    registered.append(action_id)

            except Exception as exc:
                logger.warning("Failed to load user plugin %s: %s", file_path.name, exc)

        self._loaded_plugins = registered
        return registered

