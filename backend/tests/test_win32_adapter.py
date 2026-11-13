from __future__ import annotations

import sys
from unittest.mock import MagicMock, call
import pytest

from app.services.adapters.win32_window_adapter import (
    SW_RESTORE,
    WM_CLOSE,
    Win32WindowAdapter,
)
from app.services.window_management_service import WindowManagementService


class MockWintypes:
    BOOL = int
    HWND = int
    LPARAM = int

    class DWORD:
        def __init__(self, value: int = 1234) -> None:
            self.value = value


class MockCtypes:
    wintypes = MockWintypes

    @staticmethod
    def WINFUNCTYPE(restype, *argtypes):
        def decorator(fn):
            return fn
        return decorator

    @staticmethod
    def create_unicode_buffer(size: int):
        class Buf:
            def __init__(self):
                self.value = ""
        return Buf()

    @staticmethod
    def byref(obj):
        return obj


def create_mock_user32(windows_data: list[dict]):
    """Create a mock user32 library configured with sample windows."""
    user32 = MagicMock()

    def mock_enum_windows(callback, lparam):
        for win in windows_data:
            hwnd = win["hwnd"]
            callback(hwnd, lparam)
        return True

    def mock_is_window_visible(hwnd):
        for win in windows_data:
            if win["hwnd"] == hwnd:
                return win.get("visible", True)
        return False

    def mock_get_window_text_length(hwnd):
        for win in windows_data:
            if win["hwnd"] == hwnd:
                return len(win.get("title", ""))
        return 0

    def mock_get_window_text(hwnd, buf, size):
        for win in windows_data:
            if win["hwnd"] == hwnd:
                buf.value = win.get("title", "")
                return len(buf.value)
        return 0

    def mock_get_window_thread_process_id(hwnd, pid_ref):
        for win in windows_data:
            if win["hwnd"] == hwnd:
                if hasattr(pid_ref, "value"):
                    pid_ref.value = win.get("pid", 1000)
                return win.get("thread_id", 10)
        return 0

    user32.EnumWindows = MagicMock(side_effect=mock_enum_windows)
    user32.IsWindowVisible = MagicMock(side_effect=mock_is_window_visible)
    user32.GetWindowTextLengthW = MagicMock(side_effect=mock_get_window_text_length)
    user32.GetWindowTextW = MagicMock(side_effect=mock_get_window_text)
    user32.GetWindowThreadProcessId = MagicMock(side_effect=mock_get_window_thread_process_id)
    user32.GetForegroundWindow = MagicMock(return_value=101)
    user32.IsIconic = MagicMock(return_value=False)
    user32.ShowWindow = MagicMock(return_value=True)
    user32.SetForegroundWindow = MagicMock(return_value=True)
    user32.AttachThreadInput = MagicMock(return_value=True)
    user32.BringWindowToTop = MagicMock(return_value=True)
    user32.PostMessageW = MagicMock(return_value=True)

    return user32


def test_win32_adapter_availability():
    # When user32 is supplied, adapter is always available
    adapter = Win32WindowAdapter(user32=MagicMock(), kernel32=MagicMock(), ctypes_module=MockCtypes)
    assert adapter.is_available is True

    # Without user32, available depends on sys.platform
    adapter_default = Win32WindowAdapter()
    assert adapter_default.is_available == (sys.platform == "win32")


def test_win32_adapter_non_windows_raises(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    adapter = Win32WindowAdapter()
    with pytest.raises(NotImplementedError, match="supported natively on Windows"):
        adapter._get_libraries()


def test_win32_adapter_list_windows():
    windows_data = [
        {"hwnd": 101, "title": "Notepad - notes.txt", "pid": 2040, "visible": True},
        {"hwnd": 102, "title": "Google Chrome", "pid": 3050, "visible": True},
        {"hwnd": 103, "title": "Hidden Helper", "pid": 4060, "visible": False},
        {"hwnd": 104, "title": "", "pid": 5070, "visible": True},  # empty title
    ]
    user32 = create_mock_user32(windows_data)
    kernel32 = MagicMock()

    process_resolver = lambda pid: "notepad.exe" if pid == 2040 else "chrome.exe"
    adapter = Win32WindowAdapter(
        user32=user32,
        kernel32=kernel32,
        process_name_resolver=process_resolver,
        ctypes_module=MockCtypes,
    )

    windows = adapter.list_windows()
    assert len(windows) == 2
    assert windows[0] == {
        "window_id": "101",
        "title": "Notepad - notes.txt",
        "process_id": 2040,
        "application": "notepad.exe",
    }
    assert windows[1] == {
        "window_id": "102",
        "title": "Google Chrome",
        "process_id": 3050,
        "application": "chrome.exe",
    }


def test_win32_adapter_get_active_window():
    windows_data = [
        {"hwnd": 101, "title": "Notepad - notes.txt", "pid": 2040, "visible": True},
        {"hwnd": 102, "title": "Google Chrome", "pid": 3050, "visible": True},
    ]
    user32 = create_mock_user32(windows_data)
    user32.GetForegroundWindow.return_value = 102
    kernel32 = MagicMock()

    adapter = Win32WindowAdapter(user32=user32, kernel32=kernel32, ctypes_module=MockCtypes)
    active = adapter.get_active_window()
    assert active is not None
    assert active["window_id"] == "102"
    assert active["title"] == "Google Chrome"


def test_win32_adapter_focus_window_direct():
    windows_data = [
        {"hwnd": 101, "title": "Notepad - Document 1", "pid": 2040, "visible": True},
    ]
    user32 = create_mock_user32(windows_data)
    user32.IsIconic.return_value = False
    user32.SetForegroundWindow.return_value = True
    kernel32 = MagicMock()

    adapter = Win32WindowAdapter(user32=user32, kernel32=kernel32, ctypes_module=MockCtypes)
    res = adapter.focus_window("Notepad")

    assert res["operation"] == "focus_window"
    assert res["focused"] is True
    assert res["window"]["window_id"] == "101"
    user32.SetForegroundWindow.assert_called_with(101)


def test_win32_adapter_focus_window_restores_minimized():
    windows_data = [
        {"hwnd": 101, "title": "Notepad - Document 1", "pid": 2040, "visible": True},
    ]
    user32 = create_mock_user32(windows_data)
    user32.IsIconic.return_value = True
    user32.ShowWindow.return_value = True
    user32.SetForegroundWindow.return_value = True
    kernel32 = MagicMock()

    adapter = Win32WindowAdapter(user32=user32, kernel32=kernel32, ctypes_module=MockCtypes)
    adapter.focus_window("101")

    user32.IsIconic.assert_called_with(101)
    user32.ShowWindow.assert_called_with(101, SW_RESTORE)
    user32.SetForegroundWindow.assert_called_with(101)


def test_win32_adapter_focus_window_attach_thread_input_fallback():
    windows_data = [
        {"hwnd": 101, "title": "Notepad", "pid": 2040, "visible": True, "thread_id": 55},
        {"hwnd": 999, "title": "Foreground App", "pid": 9999, "visible": True, "thread_id": 99},
    ]
    user32 = create_mock_user32(windows_data)
    # Direct SetForegroundWindow fails first, then succeeds after attach
    user32.SetForegroundWindow.side_effect = [False, True]
    user32.GetForegroundWindow.return_value = 999
    user32.GetWindowThreadProcessId.return_value = 99  # foreground thread

    kernel32 = MagicMock()
    kernel32.GetCurrentThreadId.return_value = 11  # our thread

    adapter = Win32WindowAdapter(user32=user32, kernel32=kernel32, ctypes_module=MockCtypes)
    res = adapter.focus_window("Notepad")

    assert res["focused"] is True
    # Verify AttachThreadInput flow: attach True, bring to top, SetForegroundWindow, attach False
    user32.AttachThreadInput.assert_has_calls([
        call(11, 99, True),
        call(11, 99, False),
    ])
    user32.BringWindowToTop.assert_called_with(101)


def test_win32_adapter_focus_window_ambiguous_and_missing():
    windows_data = [
        {"hwnd": 101, "title": "Project - Editor 1", "pid": 2040, "visible": True},
        {"hwnd": 102, "title": "Project - Editor 2", "pid": 3050, "visible": True},
    ]
    user32 = create_mock_user32(windows_data)
    kernel32 = MagicMock()

    adapter = Win32WindowAdapter(user32=user32, kernel32=kernel32, ctypes_module=MockCtypes)

    with pytest.raises(ValueError, match="More than one window matches"):
        adapter.focus_window("Project")

    with pytest.raises(ValueError, match="No visible window matches"):
        adapter.focus_window("Nonexistent App")


def test_win32_adapter_close_window():
    windows_data = [
        {"hwnd": 101, "title": "Notepad - Unsaved Notes", "pid": 2040, "visible": True},
    ]
    user32 = create_mock_user32(windows_data)
    user32.PostMessageW.return_value = True
    kernel32 = MagicMock()

    adapter = Win32WindowAdapter(user32=user32, kernel32=kernel32, ctypes_module=MockCtypes)
    res = adapter.close_window("Notepad")

    assert res["operation"] == "close_window"
    assert res["closed"] is True
    assert res["method"] == "WM_CLOSE"
    user32.PostMessageW.assert_called_with(101, WM_CLOSE, 0, 0)


def test_window_management_service_delegation():
    mock_adapter = MagicMock()
    mock_adapter.is_available = True
    mock_adapter.list_windows.return_value = [{"window_id": "1", "title": "App"}]
    mock_adapter.get_active_window.return_value = {"window_id": "1", "title": "App"}
    mock_adapter.focus_window.return_value = {"operation": "focus_window", "focused": True}
    mock_adapter.close_window.return_value = {"operation": "close_window", "closed": True}

    service = WindowManagementService(adapter=mock_adapter)
    assert service.is_available is True
    assert service.list_windows() == [{"window_id": "1", "title": "App"}]
    assert service.get_active_window() == {"window_id": "1", "title": "App"}
    assert service.focus_window("App")["focused"] is True
    assert service.close_window("App")["closed"] is True


def test_window_management_service_unavailable(monkeypatch):
    monkeypatch.setattr(sys, "platform", "freebsd")
    service = WindowManagementService(adapter=None)
    status = service.get_platform_status()
    assert "platform" in status
    assert status["adapter"] is None

    if not service.is_available:
        with pytest.raises(NotImplementedError, match="not currently available"):
            service.list_windows()


def test_window_actions_registration():
    from app.actions.action_registry import ActionRegistry
    from app.actions.builtins.window import register_window_actions, WindowIdentifierParameters, WindowEmptyParameters

    registry = ActionRegistry()
    mock_service = MagicMock()
    mock_service.list_windows.return_value = [{"window_id": "101", "title": "Notepad", "application": "notepad.exe"}]
    mock_service.get_active_window.return_value = {"window_id": "101", "title": "Notepad", "application": "notepad.exe"}
    mock_service.focus_window.return_value = {"operation": "focus_window", "window": {"title": "Notepad"}}
    mock_service.close_window.return_value = {"operation": "close_window", "window": {"title": "Notepad"}}

    register_window_actions(registry, mock_service)

    actions = {a.action_id: a for a in registry.list()}
    assert "window.list" in actions
    assert "window.active" in actions
    assert "window.focus" in actions
    assert "window.close" in actions

    # Execute window.list
    res_list = actions["window.list"].handler(WindowEmptyParameters())
    assert res_list.status == "done"
    assert res_list.data["count"] == 1

    # Execute window.active
    res_active = actions["window.active"].handler(WindowEmptyParameters())
    assert res_active.status == "done"
    assert res_active.data["active"]["window_id"] == "101"

    # Execute window.focus
    res_focus = actions["window.focus"].handler(WindowIdentifierParameters(identifier="Notepad"))
    assert res_focus.status == "done"
    assert "Notepad" in res_focus.message

    # Execute window.close
    res_close = actions["window.close"].handler(WindowIdentifierParameters(identifier="Notepad"))
    assert res_close.status == "done"
    assert "Notepad" in res_close.message


def test_window_api_endpoints(tmp_path, monkeypatch):
    import keyring
    from fastapi.testclient import TestClient
    from app.main import create_app

    monkeypatch.setattr(keyring, "get_password", lambda *_: None)
    monkeypatch.setattr(keyring, "set_password", lambda *_: None)

    app = create_app(data_dir=tmp_path, api_token="test-token")
    mock_window_service = MagicMock()
    mock_window_service.get_platform_status.return_value = {
        "platform": "windows",
        "available": True,
        "adapter": "Win32WindowAdapter",
    }
    mock_window_service.list_windows.return_value = [
        {"window_id": "101", "title": "Notepad", "process_id": 2040, "application": "notepad.exe"}
    ]
    mock_window_service.get_active_window.return_value = {
        "window_id": "101", "title": "Notepad", "process_id": 2040, "application": "notepad.exe"
    }
    mock_window_service.focus_window.return_value = {
        "operation": "focus_window",
        "window": {"window_id": "101", "title": "Notepad"},
        "focused": True,
    }
    mock_window_service.close_window.return_value = {
        "operation": "close_window",
        "window": {"window_id": "101", "title": "Notepad"},
        "closed": True,
        "method": "WM_CLOSE",
    }
    app.state.window_management_service = mock_window_service

    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    # 1. GET /window/status
    res = client.get("/api/v1/window/status", headers=headers)
    assert res.status_code == 200
    assert res.json()["platform"] == "windows"

    # 2. GET /window/list
    res = client.get("/api/v1/window/list", headers=headers)
    assert res.status_code == 200
    assert res.json()["count"] == 1

    # 3. GET /window/active
    res = client.get("/api/v1/window/active", headers=headers)
    assert res.status_code == 200
    assert res.json()["active"]["title"] == "Notepad"

    # 4. POST /window/focus
    res = client.post("/api/v1/window/focus", json={"identifier": "Notepad"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["focused"] is True

    # 5. POST /window/close
    res = client.post("/api/v1/window/close", json={"identifier": "Notepad"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["closed"] is True
    assert res.json()["method"] == "WM_CLOSE"


def test_win32_adapter_focus_by_window_id():
    """Verify focus_window resolves window by exact numeric window_id string."""
    windows_data = [
        {"hwnd": 1001, "title": "Notepad - Untitled", "pid": 2040, "visible": True},
        {"hwnd": 1002, "title": "Calculator", "pid": 3050, "visible": True},
    ]
    user32 = create_mock_user32(windows_data)
    kernel32 = MagicMock()
    adapter = Win32WindowAdapter(user32=user32, kernel32=kernel32, ctypes_module=MockCtypes)

    res = adapter.focus_window("1001")
    assert res["focused"] is True
    assert res["window"]["window_id"] == "1001"
    assert res["window"]["title"] == "Notepad - Untitled"


def test_win32_adapter_custom_process_resolver():
    """Verify custom process name resolver hook."""
    windows_data = [
        {"hwnd": 1001, "title": "Notepad - Untitled", "pid": 2040, "visible": True},
    ]
    user32 = create_mock_user32(windows_data)
    kernel32 = MagicMock()
    adapter = Win32WindowAdapter(
        user32=user32,
        kernel32=kernel32,
        ctypes_module=MockCtypes,
        process_name_resolver=lambda pid: f"custom_app_{pid}.exe",
    )

    windows = adapter.list_windows()
    assert len(windows) == 1
    assert windows[0]["application"] == "custom_app_2040.exe"

