"""
Unit tests for DevAgentService and dev.agent action (TASK-GAP-03 / GAP-03).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.dev_agent import register_dev_agent_actions
from app.schemas.dev_agent import DevAgentParameters
from app.services.dev_agent_service import (
    DevAgentService,
    classify_error,
    parse_traceback,
    strip_fences,
)


def test_strip_fences():
    code = "```python\nprint('hello')\n```"
    assert strip_fences(code) == "print('hello')"

    raw = "def add(a, b):\n    return a + b"
    assert strip_fences(raw) == raw


def test_classify_error():
    assert classify_error("ModuleNotFoundError: No module named 'requests'") == "dependency_error"
    assert classify_error("SyntaxError: invalid syntax") == "syntax_error"
    assert classify_error("ImportError: cannot import name 'foo'") == "import_error"
    assert classify_error("ZeroDivisionError: division by zero") == "runtime_error"
    assert classify_error("Process completed successfully") == "none"


def test_parse_traceback():
    tb = """Traceback (most recent call last):
  File "main.py", line 14, in <module>
    run_app()
  File "utils/helpers.py", line 42, in run_app
    1 / 0
ZeroDivisionError: division by zero"""

    file_name, line = parse_traceback(tb, ["main.py", "utils/helpers.py"])
    assert file_name == "utils/helpers.py"
    assert line == 42


def test_dev_agent_missing_api_key(tmp_path):
    mock_settings = MagicMock()
    mock_settings.get_api_key_for_service.return_value = None

    service = DevAgentService(mock_settings, projects_dir=tmp_path)
    res = service.execute(DevAgentParameters(description="Build a CLI tool"))

    assert res.status == ToolOutcome.FAILED
    assert "API key" in res.message


@patch("subprocess.run")
def test_dev_agent_build_success(mock_sub, tmp_path):
    mock_settings = MagicMock()
    mock_settings.get_api_key_for_service.return_value = "fake_key_123"

    mock_client = MagicMock()
    plan_json = json.dumps({
        "project_name": "calc_app",
        "entry_point": "main.py",
        "files": [
            {"path": "helpers.py", "description": "Add function", "imports": []},
            {"path": "main.py", "description": "Entry point", "imports": ["helpers"]},
        ],
        "run_command": "python main.py",
        "dependencies": [],
    })

    res_plan = MagicMock(text=plan_json)
    res_helper = MagicMock(text="def add(a, b): return a + b")
    res_main = MagicMock(text="import helpers\nprint(helpers.add(2, 3))")

    mock_client.models.generate_content.side_effect = [res_plan, res_helper, res_main]

    # Mock subprocess run to simulate successful execution
    mock_sub.return_value = MagicMock(returncode=0, stdout="5\n", stderr="")

    service = DevAgentService(mock_settings, projects_dir=tmp_path)
    with patch("google.genai.Client", return_value=mock_client), \
         patch.object(service, "_open_editor"):
        params = DevAgentParameters(
            description="Build a calculator application",
            project_name="calc_app",
            auto_fix=False,
        )
        outcome = service.execute(params)

        assert outcome.status == ToolOutcome.DONE
        assert "built and verified" in outcome.message
        assert (tmp_path / "calc_app" / "main.py").exists()
        assert (tmp_path / "calc_app" / "helpers.py").exists()


@patch("subprocess.run")
def test_dev_agent_timeout_returns_unverified(mock_sub, tmp_path):
    import subprocess
    mock_settings = MagicMock()
    mock_settings.get_api_key_for_service.return_value = "fake_key_123"

    mock_client = MagicMock()
    plan_json = json.dumps({
        "project_name": "server_app",
        "entry_point": "server.py",
        "files": [{"path": "server.py", "description": "HTTP server", "imports": []}],
        "run_command": "python server.py",
        "dependencies": [],
    })

    mock_client.models.generate_content.side_effect = [
        MagicMock(text=plan_json),
        MagicMock(text="import time\ntime.sleep(100)"),
    ]

    mock_sub.side_effect = subprocess.TimeoutExpired(cmd="python server.py", timeout=10)

    service = DevAgentService(mock_settings, projects_dir=tmp_path)
    with patch("google.genai.Client", return_value=mock_client), \
         patch.object(service, "_open_editor"):
        params = DevAgentParameters(
            description="Run a simple background server",
            project_name="server_app",
            timeout=10,
        )
        outcome = service.execute(params)

        assert outcome.status == ToolOutcome.UNVERIFIED
        assert "timed out" in outcome.message.lower()


def test_dev_agent_action_registry_integration():
    mock_settings = MagicMock()
    service = DevAgentService(mock_settings)
    registry = ActionRegistry()
    register_dev_agent_actions(registry, service)

    defn = registry.get("dev.agent")
    assert defn is not None
    assert defn.category == "automation"
    assert defn.requires_confirmation is True

    view = defn.public_view()
    assert view["action_id"] == "dev.agent"
    assert view["requires_confirmation"] is True

