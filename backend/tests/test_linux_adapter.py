from __future__ import annotations

import sys
from unittest.mock import MagicMock
import pytest

from app.services.adapters.linux_window_adapter import LinuxWindowAdapter
from app.services.window_management_service import WindowManagementService


def test_linux_adapter_availability():
    mock_runner = MagicMock(return_value=(0, "", ""))
    adapter = LinuxWindowAdapter(runner=mock_runner)
    assert adapter.is_available is True

    # Without mock runner on non-linux, should be False
    adapter_default = LinuxWindowAdapter(which_resolver=lambda _: None, session_detector=lambda: "headless")
    if not sys.platform.startswith("linux"):
        assert adapter_default.is_available is False


def test_linux_adapter_session_detection():
    adapter_x11 = LinuxWindowAdapter(session_detector=lambda: "x11")
    assert adapter_x11.session_type == "x11"

    adapter_wayland = LinuxWindowAdapter(session_detector=lambda: "wayland")
    assert adapter_wayland.session_type == "wayland"

    adapter_headless = LinuxWindowAdapter(session_detector=lambda: "headless")
    assert adapter_headless.session_type == "headless"


def test_linux_adapter_list_windows_wmctrl():
    sample_wmctrl_output = (
        "0x0280000a  0 14854 user-pc Terminal\n"
        "0x03a00002  0 16200 user-pc Google Chrome - GitHub\n"
        "0x01000001 -1 99999 user-pc Desktop\n"  # Desktop background layer to filter out
    )

    def mock_runner(cmd):
        if cmd == ["wmctrl", "-l", "-p"]:
            return (0, sample_wmctrl_output, "")
        return (1, "", "")

    process_resolver = lambda pid: "gnome-terminal" if pid == 14854 else "chrome"
    adapter = LinuxWindowAdapter(
        runner=mock_runner,
        which_resolver=lambda tool: f"/usr/bin/{tool}",
        process_name_resolver=process_resolver,
    )

    windows = adapter.list_windows()
    assert len(windows) == 2
    assert windows[0] == {
        "window_id": "0x0280000a",
        "title": "Terminal",
        "process_id": 14854,
        "application": "gnome-terminal",
    }
    assert windows[1] == {
        "window_id": "0x03a00002",
        "title": "Google Chrome - GitHub",
        "process_id": 16200,
        "application": "chrome",
    }


def test_linux_adapter_list_windows_xdotool_fallback():
    def mock_runner(cmd):
        if cmd == ["wmctrl", "-l", "-p"]:
            return (127, "", "wmctrl not found")
        if cmd == ["xdotool", "search", "--onlyvisible", "--name", ".*"]:
            return (0, "41943050\n52428802\n", "")
        if cmd == ["xdotool", "getwindowname", "41943050"]:
            return (0, "Gedit - Untitled Document", "")
        if cmd == ["xdotool", "getwindowpid", "41943050"]:
            return (0, "22334", "")
        if cmd == ["xdotool", "getwindowname", "52428802"]:
            return (0, "VLC media player", "")
        if cmd == ["xdotool", "getwindowpid", "52428802"]:
            return (0, "22335", "")
        return (1, "", "")

    def mock_which(tool):
        return None if tool == "wmctrl" else f"/usr/bin/{tool}"

    adapter = LinuxWindowAdapter(
        runner=mock_runner,
        which_resolver=mock_which,
        process_name_resolver=lambda pid: "gedit" if pid == 22334 else "vlc",
    )

    windows = adapter.list_windows()
    assert len(windows) == 2
    assert windows[0]["title"] == "Gedit - Untitled Document"
    assert windows[0]["application"] == "gedit"
    assert windows[1]["title"] == "VLC media player"
    assert windows[1]["application"] == "vlc"


def test_linux_adapter_get_active_window():
    def mock_runner(cmd):
        if cmd == ["xdotool", "getactivewindow"]:
            return (0, "41943050", "")
        if cmd == ["xdotool", "getwindowname", "41943050"]:
            return (0, "Active Terminal", "")
        if cmd == ["xdotool", "getwindowpid", "41943050"]:
            return (0, "1234", "")
        return (1, "", "")

    adapter = LinuxWindowAdapter(
        runner=mock_runner,
        which_resolver=lambda tool: f"/usr/bin/{tool}",
        process_name_resolver=lambda _: "bash",
    )
    # Mock list_windows returning the window
    adapter.list_windows = lambda: [{
        "window_id": "41943050",
        "title": "Active Terminal",
        "process_id": 1234,
        "application": "bash",
    }]

    active = adapter.get_active_window()
    assert active is not None
    assert active["window_id"] == "41943050"
    assert active["title"] == "Active Terminal"


def test_linux_adapter_focus_window_wmctrl():
    executed_commands = []
    def mock_runner(cmd):
        executed_commands.append(cmd)
        return (0, "", "")

    adapter = LinuxWindowAdapter(
        runner=mock_runner,
        which_resolver=lambda tool: f"/usr/bin/{tool}",
    )
    adapter.list_windows = lambda: [{
        "window_id": "0x0280000a",
        "title": "Terminal",
        "process_id": 14854,
        "application": "gnome-terminal",
    }]

    res = adapter.focus_window("Terminal")
    assert res["operation"] == "focus_window"
    assert res["focused"] is True
    assert ["wmctrl", "-ia", "0x0280000a"] in executed_commands


def test_linux_adapter_focus_window_xdotool_fallback():
    executed_commands = []
    def mock_runner(cmd):
        executed_commands.append(cmd)
        if cmd[0] == "wmctrl":
            return (1, "", "wmctrl failed")
        if cmd[0] == "xdotool":
            return (0, "", "")
        return (1, "", "")

    adapter = LinuxWindowAdapter(
        runner=mock_runner,
        which_resolver=lambda tool: f"/usr/bin/{tool}",
    )
    adapter.list_windows = lambda: [{
        "window_id": "41943050",
        "title": "Text Editor",
        "process_id": 22334,
        "application": "gedit",
    }]

    res = adapter.focus_window("Text Editor")
    assert res["focused"] is True
    assert ["xdotool", "windowactivate", "41943050"] in executed_commands


def test_linux_adapter_focus_window_ambiguous_and_missing():
    adapter = LinuxWindowAdapter(
        runner=lambda _: (0, "", ""),
        which_resolver=lambda tool: f"/usr/bin/{tool}",
    )
    adapter.list_windows = lambda: [
        {"window_id": "1", "title": "Editor Window 1", "process_id": 100, "application": "code"},
        {"window_id": "2", "title": "Editor Window 2", "process_id": 100, "application": "code"},
    ]

    with pytest.raises(ValueError, match="More than one window matches"):
        adapter.focus_window("Editor Window")

    with pytest.raises(ValueError, match="No visible window matches"):
        adapter.focus_window("NonexistentApp")


def test_linux_adapter_close_window_wmctrl():
    executed_commands = []
    def mock_runner(cmd):
        executed_commands.append(cmd)
        return (0, "", "")

    adapter = LinuxWindowAdapter(
        runner=mock_runner,
        which_resolver=lambda tool: f"/usr/bin/{tool}",
    )
    adapter.list_windows = lambda: [{
        "window_id": "0x0280000a",
        "title": "Terminal",
        "process_id": 14854,
        "application": "gnome-terminal",
    }]

    res = adapter.close_window("Terminal")
    assert res["operation"] == "close_window"
    assert res["closed"] is True
    assert res["method"] == "wmctrl -ic (_NET_CLOSE_WINDOW)"
    assert ["wmctrl", "-ic", "0x0280000a"] in executed_commands


def test_linux_adapter_close_window_xdotool_fallback():
    executed_commands = []
    def mock_runner(cmd):
        executed_commands.append(cmd)
        if cmd[0] == "wmctrl":
            return (1, "", "wmctrl failed")
        if cmd[0] == "xdotool":
            return (0, "", "")
        return (1, "", "")

    adapter = LinuxWindowAdapter(
        runner=mock_runner,
        which_resolver=lambda tool: f"/usr/bin/{tool}",
    )
    adapter.list_windows = lambda: [{
        "window_id": "41943050",
        "title": "Gedit",
        "process_id": 22334,
        "application": "gedit",
    }]

    res = adapter.close_window("Gedit")
    assert res["closed"] is True
    assert res["method"] == "xdotool windowclose"
    assert ["xdotool", "windowclose", "41943050"] in executed_commands


def test_window_management_service_linux_integration():
    mock_adapter = MagicMock()
    mock_adapter.is_available = True
    mock_adapter.list_windows.return_value = [{"window_id": "1", "title": "Gedit", "application": "gedit"}]

    service = WindowManagementService(adapter=mock_adapter)
    windows = service.list_windows()
    assert len(windows) == 1
    assert windows[0]["application"] == "gedit"


def test_linux_adapter_focus_by_hex_window_id():
    """Verify focus_window resolves window by exact hex window_id string."""
    executed_commands = []
    def mock_runner(cmd):
        executed_commands.append(cmd)
        return (0, "", "")

    adapter = LinuxWindowAdapter(
        runner=mock_runner,
        which_resolver=lambda tool: f"/usr/bin/{tool}",
    )
    adapter.list_windows = lambda: [
        {"window_id": "0x01a00003", "title": "Firefox", "process_id": 9999, "application": "firefox"},
        {"window_id": "0x0280000a", "title": "Terminal", "process_id": 14854, "application": "gnome-terminal"},
    ]

    res = adapter.focus_window("0x0280000a")
    assert res["focused"] is True
    assert res["window"]["window_id"] == "0x0280000a"
    assert res["window"]["title"] == "Terminal"
    assert ["wmctrl", "-ia", "0x0280000a"] in executed_commands


def test_linux_adapter_session_detection_matrix(monkeypatch):
    """Verify session_type accurately detects x11, wayland, and headless from env."""
    adapter = LinuxWindowAdapter()

    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert adapter.session_type == "wayland"

    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert adapter.session_type == "x11"

    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    assert adapter.session_type == "wayland"

    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")
    assert adapter.session_type == "x11"

    monkeypatch.delenv("DISPLAY", raising=False)
    assert adapter.session_type == "headless"


