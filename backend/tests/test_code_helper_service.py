"""
Unit tests for CodeHelperService and code.helper action (TASK-GAP-04 / GAP-04).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.code_helper import register_code_helper_actions
from app.schemas.code_helper import CodeHelperParameters
from app.services.code_helper_service import (
    CodeHelperService,
    resolve_save_path,
    strip_fences,
)


def test_resolve_save_path(tmp_path):
    p1 = resolve_save_path(None, "python")
    assert p1.name == "jarvis_code.py"

    p2 = resolve_save_path(None, "javascript")
    assert p2.name == "jarvis_code.js"

    custom = str(tmp_path / "custom.py")
    p3 = resolve_save_path(custom, "python")
    assert p3 == Path(custom)


def test_code_helper_write(tmp_path):
    mock_settings = MagicMock()
    mock_settings.get_api_key_for_service.return_value = "fake_key_123"

    service = CodeHelperService(mock_settings)
    target_file = tmp_path / "fib.py"

    with patch.object(service, "_call_llm", return_value="def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)"):
        params = CodeHelperParameters(
            action="write",
            description="Write a recursive Fibonacci function",
            language="python",
            output_path=str(target_file),
        )
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert target_file.exists()
        assert "def fib" in target_file.read_text()


def test_code_helper_edit(tmp_path):
    mock_settings = MagicMock()
    mock_settings.get_api_key_for_service.return_value = "fake_key_123"

    service = CodeHelperService(mock_settings)
    target_file = tmp_path / "script.py"
    target_file.write_text("def greet(): print('hi')", encoding="utf-8")

    with patch.object(service, "_call_llm", return_value="def greet(name='world'): print(f'hi {name}')"):
        params = CodeHelperParameters(
            action="edit",
            file_path=str(target_file),
            description="Add a default name parameter",
        )
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert "name='world'" in target_file.read_text()


def test_code_helper_edit_missing_file():
    mock_settings = MagicMock()
    service = CodeHelperService(mock_settings)
    params = CodeHelperParameters(action="edit", file_path="/non/existent/file.py", description="Fix bug")
    res = service.execute(params)

    assert res.status == ToolOutcome.FAILED
    assert "does not exist" in res.message


def test_code_helper_explain():
    mock_settings = MagicMock()
    service = CodeHelperService(mock_settings)

    with patch.object(service, "_call_llm", return_value="This function computes sum of elements."):
        params = CodeHelperParameters(
            action="explain",
            code="def sum_all(arr): return sum(arr)",
        )
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert "sum of elements" in res.data["explanation"]


@patch("subprocess.run")
def test_code_helper_run_success(mock_sub, tmp_path):
    mock_settings = MagicMock()
    service = CodeHelperService(mock_settings)

    target_file = tmp_path / "run_test.py"
    target_file.write_text("print('All tests passed')", encoding="utf-8")

    mock_sub.return_value = MagicMock(returncode=0, stdout="All tests passed\n", stderr="")

    params = CodeHelperParameters(action="run", file_path=str(target_file))
    res = service.execute(params)

    assert res.status == ToolOutcome.DONE
    assert "executed successfully" in res.message


@patch("subprocess.run")
def test_code_helper_run_failure(mock_sub, tmp_path):
    mock_settings = MagicMock()
    service = CodeHelperService(mock_settings)

    target_file = tmp_path / "failing.py"
    target_file.write_text("1 / 0", encoding="utf-8")

    mock_sub.return_value = MagicMock(returncode=1, stdout="", stderr="ZeroDivisionError: division by zero")

    params = CodeHelperParameters(action="run", file_path=str(target_file))
    res = service.execute(params)

    assert res.status == ToolOutcome.FAILED
    assert "failed with code 1" in res.message


def test_code_helper_action_registry_integration():
    mock_settings = MagicMock()
    service = CodeHelperService(mock_settings)
    registry = ActionRegistry()
    register_code_helper_actions(registry, service)

    defn = registry.get("code.helper")
    assert defn is not None
    assert defn.category == "automation"
    assert defn.requires_confirmation is True

    view = defn.public_view()
    assert view["action_id"] == "code.helper"
    assert view["requires_confirmation"] is True

