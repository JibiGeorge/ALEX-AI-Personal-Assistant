from __future__ import annotations

import sys
from unittest.mock import MagicMock
import pytest

from app.services.adapters.macos_window_adapter import MacOSWindowAdapter
from app.services.window_management_service import WindowManagementService


def create_mock_quartz(windows_data: list[dict]):
    """Create a mock Quartz module with sample CGWindowListCopyWindowInfo output."""
    quartz = MagicMock()
    quartz.kCGWindowListOptionOnScreenOnly = 1
    quartz.kCGWindowListExcludeDesktopElements = 16
    quartz.kCGNullWindowID = 0

    raw_windows = []
    for win in windows_data:
        raw_windows.append({
            "kCGWindowNumber": win.get("id", 100),
            "kCGWindowLayer": win.get("layer", 0),
            "kCGWindowOwnerPID": win.get("pid", 1000),
            "kCGWindowOwnerName": win.get("app", "Finder"),
            "kCGWindowName": win.get("title", ""),
            "kCGWindowBounds": {
                "Width": win.get("width", 800),
                "Height": win.get("height", 600),
                "X": 0,
                "Y": 0,
            },
        })

    quartz.CGWindowListCopyWindowInfo = MagicMock(return_value=raw_windows)
    return quartz


def create_mock_appkit():
    """Create a mock AppKit module with NSRunningApplication and NSWorkspace."""
    appkit = MagicMock()
    appkit.NSApplicationActivateIgnoringOtherApps = 2

    mock_app = MagicMock()
    mock_app.processIdentifier.return_value = 1001
    mock_app.localizedName.return_value = "Spotify"
    mock_app.activateWithOptions_.return_value = True
    mock_app.terminate.return_value = True

    mock_workspace = MagicMock()
    mock_workspace.frontmostApplication.return_value = mock_app
    appkit.NSWorkspace.sharedWorkspace.return_value = mock_workspace

    appkit.NSRunningApplication.runningApplicationWithProcessIdentifier_.return_value = mock_app
    return appkit, mock_app


def test_macos_adapter_availability():
    adapter_with_mock = MacOSWindowAdapter(quartz_module=MagicMock())
    assert adapter_with_mock.is_available is True

    adapter_default = MacOSWindowAdapter()
    assert adapter_default.is_available == (sys.platform == "darwin")


def test_macos_adapter_list_windows_quartz():
    windows_data = [
        {"id": 101, "title": "Spotify Free", "app": "Spotify", "pid": 2040, "layer": 0, "width": 1000, "height": 700},
        {"id": 102, "title": "ALEX-AI - Visual Studio Code", "app": "Code", "pid": 3050, "layer": 0, "width": 1200, "height": 900},
        {"id": 103, "title": "Menubar Helper", "app": "System", "pid": 100, "layer": 25, "width": 50, "height": 25}, # non-zero layer
        {"id": 104, "title": "Invisible Tooltip", "app": "Finder", "pid": 500, "layer": 0, "width": 5, "height": 5}, # tiny size
    ]
    quartz = create_mock_quartz(windows_data)
    adapter = MacOSWindowAdapter(quartz_module=quartz)

    windows = adapter.list_windows()
    assert len(windows) == 2
    assert windows[0] == {
        "window_id": "101",
        "title": "Spotify Free",
        "process_id": 2040,
        "application": "Spotify",
    }
    assert windows[1] == {
        "window_id": "102",
        "title": "ALEX-AI - Visual Studio Code",
        "process_id": 3050,
        "application": "Code",
    }


def test_macos_adapter_list_windows_osascript_fallback():
    # When Quartz is None, fall back to osascript runner
    def mock_runner(cmd):
        script = cmd[2]
        if "appList" in script:
            return (0, "Safari::4010, Spotify::4020", "")
        return (0, "", "")

    adapter = MacOSWindowAdapter(quartz_module=None, osascript_runner=mock_runner)
    adapter._get_quartz = lambda: None  # force fallback

    windows = adapter.list_windows()
    assert len(windows) == 2
    assert windows[0] == {
        "window_id": "4010",
        "title": "Safari",
        "process_id": 4010,
        "application": "Safari",
    }
    assert windows[1] == {
        "window_id": "4020",
        "title": "Spotify",
        "process_id": 4020,
        "application": "Spotify",
    }


def test_macos_adapter_get_active_window():
    windows_data = [
        {"id": 101, "title": "Spotify", "app": "Spotify", "pid": 1001, "layer": 0, "width": 1000, "height": 700},
    ]
    quartz = create_mock_quartz(windows_data)
    appkit, _ = create_mock_appkit()

    adapter = MacOSWindowAdapter(quartz_module=quartz, appkit_module=appkit)
    active = adapter.get_active_window()

    assert active is not None
    assert active["window_id"] == "101"
    assert active["application"] == "Spotify"


def test_macos_adapter_focus_window_appkit():
    windows_data = [
        {"id": 101, "title": "Spotify - Today's Top Hits", "app": "Spotify", "pid": 1001, "layer": 0},
    ]
    quartz = create_mock_quartz(windows_data)
    appkit, mock_app = create_mock_appkit()

    adapter = MacOSWindowAdapter(quartz_module=quartz, appkit_module=appkit)
    res = adapter.focus_window("Spotify")

    assert res["operation"] == "focus_window"
    assert res["focused"] is True
    assert res["window"]["application"] == "Spotify"
    mock_app.activateWithOptions_.assert_called_once()


def test_macos_adapter_focus_window_osascript_fallback():
    windows_data = [
        {"id": 101, "title": "Terminal", "app": "Terminal", "pid": 5050, "layer": 0},
    ]
    quartz = create_mock_quartz(windows_data)

    executed_scripts = []
    def mock_runner(cmd):
        executed_scripts.append(cmd[2])
        return (0, "", "")

    adapter = MacOSWindowAdapter(quartz_module=quartz, appkit_module=None, osascript_runner=mock_runner)
    adapter._get_appkit = lambda: None  # force osascript path

    res = adapter.focus_window("Terminal")
    assert res["focused"] is True
    assert any('tell application "Terminal" to activate' in s for s in executed_scripts)


def test_macos_adapter_focus_window_ambiguous_and_missing():
    windows_data = [
        {"id": 101, "title": "Chrome - Window 1", "app": "Google Chrome", "pid": 2001, "layer": 0},
        {"id": 102, "title": "Chrome - Window 2", "app": "Google Chrome", "pid": 2001, "layer": 0},
    ]
    quartz = create_mock_quartz(windows_data)
    adapter = MacOSWindowAdapter(quartz_module=quartz)

    with pytest.raises(ValueError, match="More than one window matches"):
        adapter.focus_window("Chrome - Window")

    with pytest.raises(ValueError, match="No visible window matches"):
        adapter.focus_window("NonexistentApp")


def test_macos_adapter_close_window_appkit():
    windows_data = [
        {"id": 101, "title": "Spotify", "app": "Spotify", "pid": 1001, "layer": 0},
    ]
    quartz = create_mock_quartz(windows_data)
    appkit, mock_app = create_mock_appkit()

    adapter = MacOSWindowAdapter(quartz_module=quartz, appkit_module=appkit)
    res = adapter.close_window("Spotify")

    assert res["operation"] == "close_window"
    assert res["closed"] is True
    assert res["method"] == "AppKit.terminate"
    mock_app.terminate.assert_called_once()


def test_macos_adapter_close_window_osascript_fallback():
    windows_data = [
        {"id": 101, "title": "TextEdit", "app": "TextEdit", "pid": 8080, "layer": 0},
    ]
    quartz = create_mock_quartz(windows_data)

    executed_scripts = []
    def mock_runner(cmd):
        executed_scripts.append(cmd[2])
        return (0, "", "")

    adapter = MacOSWindowAdapter(quartz_module=quartz, appkit_module=None, osascript_runner=mock_runner)
    adapter._get_appkit = lambda: None

    res = adapter.close_window("TextEdit")
    assert res["closed"] is True
    assert res["method"] == "osascript.quit"
    assert any('tell application "TextEdit" to quit' in s for s in executed_scripts)


def test_window_management_service_macos_integration():
    mock_adapter = MagicMock()
    mock_adapter.is_available = True
    mock_adapter.list_windows.return_value = [{"window_id": "1", "title": "Finder", "application": "Finder"}]

    service = WindowManagementService(adapter=mock_adapter)
    windows = service.list_windows()
    assert len(windows) == 1
    assert windows[0]["application"] == "Finder"


def test_macos_adapter_focus_by_window_id():
    """Verify focus_window resolves window by exact numeric window_id string."""
    windows_data = [
        {"id": 501, "title": "Document 1", "app": "Pages", "pid": 1111, "layer": 0},
        {"id": 502, "title": "Spreadsheet", "app": "Numbers", "pid": 2222, "layer": 0},
    ]
    quartz = create_mock_quartz(windows_data)
    appkit, mock_app = create_mock_appkit()

    adapter = MacOSWindowAdapter(quartz_module=quartz, appkit_module=appkit)
    res = adapter.focus_window("501")
    assert res["focused"] is True
    assert res["window"]["window_id"] == "501"
    assert res["window"]["application"] == "Pages"


def test_macos_adapter_focus_by_application_name():
    """Verify focus_window matches by application name substring."""
    windows_data = [
        {"id": 501, "title": "Untitled Document", "app": "TextEdit", "pid": 1234, "layer": 0},
    ]
    quartz = create_mock_quartz(windows_data)
    appkit, mock_app = create_mock_appkit()

    adapter = MacOSWindowAdapter(quartz_module=quartz, appkit_module=appkit)
    res = adapter.focus_window("TextEdit")
    assert res["focused"] is True
    assert res["window"]["application"] == "TextEdit"


def test_macos_adapter_window_filtering_microscopic():
    """Verify microscopic or layer!=0 windows are filtered out."""
    windows_data = [
        {"id": 101, "title": "Normal Window", "app": "Notes", "pid": 1000, "layer": 0, "width": 800, "height": 600},
        {"id": 102, "title": "Dock / Status Item", "app": "Dock", "pid": 200, "layer": 25, "width": 800, "height": 40},
        {"id": 103, "title": "Tiny Icon", "app": "Helper", "pid": 300, "layer": 0, "width": 5, "height": 5},
    ]
    quartz = create_mock_quartz(windows_data)
    adapter = MacOSWindowAdapter(quartz_module=quartz, appkit_module=None)

    windows = adapter.list_windows()
    assert len(windows) == 1
    assert windows[0]["window_id"] == "101"
    assert windows[0]["title"] == "Normal Window"


