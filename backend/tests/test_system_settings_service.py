"""
Unit tests for SystemSettingsService and system.setting action (TASK-GAP-02 / GAP-02).
"""

from unittest.mock import MagicMock, patch
import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.system_settings import register_system_settings_actions
from app.schemas.system_settings import SystemSettingParameters
from app.services.system_settings_service import SystemSettingsService


@patch("subprocess.run")
@patch("app.services.system_settings_service.SystemSettingsService._get_darwin_volume", return_value=75)
def test_system_settings_volume_up_darwin(mock_vol, mock_sub):
    service = SystemSettingsService()
    with patch("app.services.system_settings_service._OS", "Darwin"):
        params = SystemSettingParameters(setting_action="volume_up")
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert "75%" in res.message
        assert res.data.get("volume") == 75


@patch("subprocess.run")
@patch("app.services.system_settings_service.SystemSettingsService._get_darwin_volume", return_value=40)
def test_system_settings_volume_down_darwin(mock_vol, mock_sub):
    service = SystemSettingsService()
    with patch("app.services.system_settings_service._OS", "Darwin"):
        params = SystemSettingParameters(setting_action="volume_down")
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert "40%" in res.message
        assert res.data.get("volume") == 40


@patch("subprocess.run")
@patch("app.services.system_settings_service.SystemSettingsService._get_darwin_muted", return_value=True)
def test_system_settings_volume_mute_darwin(mock_muted, mock_sub):
    service = SystemSettingsService()
    with patch("app.services.system_settings_service._OS", "Darwin"):
        params = SystemSettingParameters(setting_action="volume_mute")
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert "muted" in res.message
        assert res.data.get("muted") is True


@patch("subprocess.run")
def test_system_settings_volume_set(mock_sub):
    service = SystemSettingsService()
    with patch("app.services.system_settings_service._OS", "Darwin"):
        params = SystemSettingParameters(setting_action="volume_set", value=60)
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert res.data.get("volume") == 60


def test_system_settings_volume_set_missing_value():
    service = SystemSettingsService()
    params = SystemSettingParameters(setting_action="volume_set", value=None)
    res = service.execute(params)

    assert res.status == ToolOutcome.FAILED
    assert "must be specified" in res.message


def test_system_settings_brightness_cycle():
    service = SystemSettingsService()
    # Test set brightness
    res_set = service.brightness_set(80)
    assert res_set.status == ToolOutcome.DONE
    assert res_set.data.get("brightness") == 80

    # Test get brightness
    res_get = service.brightness_get()
    assert res_get.status == ToolOutcome.DONE
    assert res_get.data.get("brightness") == 80

    # Test brightness up
    res_up = service.brightness_up(10)
    assert res_up.status == ToolOutcome.DONE
    assert res_up.data.get("brightness") == 90

    # Test brightness down
    res_down = service.brightness_down(20)
    assert res_down.status == ToolOutcome.DONE
    assert res_down.data.get("brightness") == 70


@patch("subprocess.check_output", return_value="AirPort power is On\n")
@patch("subprocess.run")
def test_system_settings_toggle_wifi_darwin(mock_run, mock_chk):
    service = SystemSettingsService()
    with patch("app.services.system_settings_service._OS", "Darwin"):
        params = SystemSettingParameters(setting_action="toggle_wifi")
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert "off" in res.message


@patch("subprocess.Popen")
def test_system_settings_lock_screen(mock_popen):
    service = SystemSettingsService()
    with patch("app.services.system_settings_service._OS", "Darwin"):
        params = SystemSettingParameters(setting_action="lock_screen")
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert "locked" in res.message.lower()


@patch("subprocess.Popen")
def test_system_settings_sleep_display(mock_popen):
    service = SystemSettingsService()
    with patch("app.services.system_settings_service._OS", "Darwin"):
        params = SystemSettingParameters(setting_action="sleep_display")
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert "sleep" in res.message.lower()


@patch("subprocess.Popen")
def test_system_settings_open_utilities(mock_popen):
    service = SystemSettingsService()
    with patch("app.services.system_settings_service._OS", "Darwin"):
        res1 = service.execute(SystemSettingParameters(setting_action="open_system_settings"))
        assert res1.status == ToolOutcome.DONE

        res2 = service.execute(SystemSettingParameters(setting_action="open_task_manager"))
        assert res2.status == ToolOutcome.DONE

        res3 = service.execute(SystemSettingParameters(setting_action="open_file_explorer"))
        assert res3.status == ToolOutcome.DONE


def test_system_settings_unsupported_action():
    service = SystemSettingsService()
    params = SystemSettingParameters(setting_action="unknown_action_abc")
    res = service.execute(params)

    assert res.status == ToolOutcome.FAILED
    assert "Unsupported" in res.message


def test_system_settings_action_registry_integration():
    registry = ActionRegistry()
    service = SystemSettingsService()
    register_system_settings_actions(registry, service)

    defn = registry.get("system.setting")
    assert defn is not None
    assert defn.category == "system"

    view = defn.public_view()
    assert view["action_id"] == "system.setting"
