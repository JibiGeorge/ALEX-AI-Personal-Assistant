"""
Unit tests for BrowserControlService and browser.control action (TASK-GAP-01 / GAP-01).
"""

from unittest.mock import MagicMock, patch
import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.browser import register_browser_actions
from app.schemas.browser_control import BrowserControlParameters
from app.services.browser_control_service import BrowserControlService, normalize_url


def test_normalize_url():
    assert normalize_url("github.com") == "https://github.com"
    assert normalize_url("https://example.org/path") == "https://example.org/path"
    assert normalize_url("http://localhost:8080") == "http://localhost:8080"
    assert normalize_url("   ") == "about:blank"
    assert normalize_url("wikipedia") == "https://wikipedia.com"


def test_browser_control_list_browsers():
    service = BrowserControlService()
    params = BrowserControlParameters(action="list_browsers")
    res = service.execute(params)

    assert res.status == ToolOutcome.DONE
    assert "browsers" in res.data
    assert "chrome" in res.data["browsers"]


@patch("subprocess.run")
@patch("webbrowser.open", return_value=True)
def test_browser_control_navigate_native(mock_wb, mock_sub):
    service = BrowserControlService()
    params = BrowserControlParameters(action="go_to", url="https://example.com")
    res = service.execute(params)

    assert res.status == ToolOutcome.UNVERIFIED
    assert "https://example.com" in res.data.get("url", "")


@patch("subprocess.run")
def test_browser_control_search(mock_sub):
    service = BrowserControlService()
    params = BrowserControlParameters(action="search", query="fastapi tutorial", engine="google")
    res = service.execute(params)

    assert res.status == ToolOutcome.UNVERIFIED
    assert "google.com/search?q=fastapi+tutorial" in res.data.get("url", "")


def test_browser_control_search_empty():
    service = BrowserControlService()
    params = BrowserControlParameters(action="search", query="")
    res = service.execute(params)

    assert res.status == ToolOutcome.FAILED
    assert "empty" in res.message.lower()


def test_browser_control_playwright_missing():
    service = BrowserControlService()
    with patch("app.services.browser_control_service.find_spec", return_value=None):
        params = BrowserControlParameters(action="click", selector="#submit-btn")
        res = service.execute(params)

        assert res.status == ToolOutcome.UNVERIFIED
        assert res.data.get("playwright_required") is True
        assert "pip install playwright" in res.message


def test_browser_control_playwright_mock_click():
    service = BrowserControlService()
    with patch("app.services.browser_control_service.find_spec", return_value=MagicMock()):
        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_pw_inst = MagicMock()
        mock_pw_inst.chromium.launch.return_value = mock_browser

        mock_sync_pw = MagicMock()
        mock_sync_pw.return_value.__enter__.return_value = mock_pw_inst

        mock_sync_api = MagicMock(sync_playwright=mock_sync_pw)

        with patch.dict("sys.modules", {"playwright": MagicMock(), "playwright.sync_api": mock_sync_api}):
            params = BrowserControlParameters(action="click", selector="button#login", url="https://app.test")
            res = service.execute(params)

            assert res.status == ToolOutcome.DONE
            mock_page.goto.assert_called_with("https://app.test", timeout=30000)
            mock_page.click.assert_called_with("button#login", timeout=10000)


def test_browser_control_unsupported_action():
    service = BrowserControlService()
    params = BrowserControlParameters(action="non_existent_action_xyz")
    res = service.execute(params)

    assert res.status == ToolOutcome.FAILED
    assert "Unsupported" in res.message


def test_browser_action_registry_integration():
    registry = ActionRegistry()
    service = BrowserControlService()
    register_browser_actions(registry, service)

    defn = registry.get("browser.control")
    assert defn is not None
    assert defn.category == "automation"
    assert defn.requires_confirmation is True

    view = defn.public_view()
    assert view["action_id"] == "browser.control"
    assert view["requires_confirmation"] is True
