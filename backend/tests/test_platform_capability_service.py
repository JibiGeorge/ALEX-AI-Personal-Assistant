import pytest
from app.core.storage import JsonDocumentStore
from app.services.platform_capability_service import PlatformCapabilityService
from app.services.settings_service import SettingsService


def test_platform_capability_snapshot_structure(tmp_path):
    store = JsonDocumentStore(tmp_path)
    settings_service = SettingsService(store)
    service = PlatformCapabilityService(settings_service)

    report = service.snapshot()

    assert report.operating_system in ("Windows", "macOS", "Linux")
    assert report.os_release != ""
    assert report.architecture != ""

    assert isinstance(report.desktop_notifications.available, bool)
    assert isinstance(report.screen_capture.available, bool)
    assert isinstance(report.window_management.available, bool)
    assert isinstance(report.computer_control.available, bool)
    assert isinstance(report.gemini_live_voice.available, bool)
    assert isinstance(report.gemini_grounded_search.available, bool)
    assert isinstance(report.memory_persistence.available, bool)
    assert isinstance(report.audio_input_devices.available, bool)

    # When API key is not configured, Gemini services must report unavailable with descriptive reason
    assert not report.gemini_live_voice.available
    assert "API key" in report.gemini_live_voice.status_detail or "google.genai" in report.gemini_live_voice.status_detail
    assert not report.gemini_grounded_search.available
    assert "API key" in report.gemini_grounded_search.status_detail


def test_platform_capability_with_mocked_key(tmp_path, monkeypatch):
    import keyring
    saved = {}
    monkeypatch.setattr(keyring, "set_password", lambda _, name, val: saved.update({name: val}))
    monkeypatch.setattr(keyring, "get_password", lambda _, name: saved.get(name))

    store = JsonDocumentStore(tmp_path)
    settings_service = SettingsService(store)
    settings_service.save_api_key("fake-gemini-api-key-1234567890")

    service = PlatformCapabilityService(settings_service)
    report = service.snapshot()

    # Search should now be available
    assert report.gemini_grounded_search.available is True
    assert "Grounded web search enabled" in report.gemini_grounded_search.status_detail


def test_platform_capability_across_os_matrix(tmp_path, monkeypatch):
    """Verify platform capability reports for Windows, macOS, Linux, and unsupported platforms."""
    import sys
    store = JsonDocumentStore(tmp_path)
    settings_service = SettingsService(store)
    service = PlatformCapabilityService(settings_service)

    # Windows
    monkeypatch.setattr(sys, "platform", "win32")
    win_report = service.snapshot()
    assert win_report.operating_system == "Windows"
    assert win_report.window_management.available is True
    assert "Win32" in win_report.window_management.status_detail

    # macOS
    monkeypatch.setattr(sys, "platform", "darwin")
    mac_report = service.snapshot()
    assert mac_report.operating_system == "macOS"
    assert mac_report.window_management.available is True
    assert "macOS" in mac_report.window_management.status_detail

    # Linux
    monkeypatch.setattr(sys, "platform", "linux")
    linux_report = service.snapshot()
    assert linux_report.operating_system == "Linux"
    assert linux_report.window_management.available is True
    assert "Linux" in linux_report.window_management.status_detail

    # Unsupported OS
    monkeypatch.setattr(sys, "platform", "freebsd13")
    other_report = service.snapshot()
    assert other_report.window_management.available is False
    assert "unsupported" in other_report.window_management.status_detail.lower()


def test_platform_capability_missing_dependencies(tmp_path, monkeypatch):
    """Verify degraded capability report when dependencies (google.genai, pyperclip) are absent."""
    import importlib.util

    orig_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str):
        if name in ("google.genai", "pyperclip"):
            return None
        return orig_find_spec(name)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    store = JsonDocumentStore(tmp_path)
    settings_service = SettingsService(store)
    service = PlatformCapabilityService(settings_service)

    report = service.snapshot()
    assert report.gemini_live_voice.available is False
    assert "not installed" in report.gemini_live_voice.status_detail
    assert report.computer_control.available is False


