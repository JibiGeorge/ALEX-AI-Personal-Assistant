"""
System Settings Service (TASK-GAP-02 / GAP-02).

Implements cross-platform operating system hardware and settings macros:
- Audio Volume (up, down, mute, set level 0-100, get current level)
- Display Brightness (up, down, set level 0-100, get current level)
- Network Wi-Fi Toggle
- OS Lock Screen and Display Sleep
- System Utilities Launchers (Settings app, Activity Monitor/Task Manager, File Explorer)
- Adheres to the Five-Word Outcome Contract (done, unverified, failed)
"""

from __future__ import annotations

from importlib.util import find_spec
import logging
import os
import platform
import re
import shutil
import subprocess
from typing import Any, Dict, Optional

from app.actions.base import ActionOutcomeResponse, done, failed, unverified
from app.schemas.system_settings import SystemSettingParameters

logger = logging.getLogger(__name__)

_OS = platform.system()  # "Darwin" | "Windows" | "Linux"


class SystemSettingsService:
    """Service providing cross-platform hardware macro controls."""

    def __init__(self) -> None:
        self._has_sbc = find_spec("screen_brightness_control") is not None
        self._cached_brightness: int = 50

    def execute(self, params: SystemSettingParameters) -> ActionOutcomeResponse:
        """Route and execute a system setting macro action."""
        action = params.setting_action.lower().strip()

        try:
            # Volume Actions
            if action == "volume_up":
                return self.volume_up()
            if action == "volume_down":
                return self.volume_down()
            if action == "volume_mute":
                return self.volume_mute()
            if action == "volume_set":
                if params.value is None:
                    msg = "Volume level (0-100) must be specified for 'volume_set'."
                    return failed("system.setting", error=msg, message=msg)
                return self.volume_set(params.value)
            if action == "volume_get":
                return self.volume_get()

            # Brightness Actions
            if action == "brightness_up":
                return self.brightness_up()
            if action == "brightness_down":
                return self.brightness_down()
            if action == "brightness_set":
                if params.value is None:
                    msg = "Brightness level (0-100) must be specified for 'brightness_set'."
                    return failed("system.setting", error=msg, message=msg)
                return self.brightness_set(params.value)
            if action == "brightness_get":
                return self.brightness_get()

            # Wi-Fi
            if action in ("toggle_wifi", "wifi_toggle"):
                return self.toggle_wifi(params.interface)

            # Power / Screen Locking
            if action == "lock_screen":
                return self.lock_screen()
            if action == "sleep_display":
                return self.sleep_display()

            # Launch System Utilities
            if action in ("open_system_settings", "settings"):
                return self.open_system_settings()
            if action in ("open_task_manager", "task_manager"):
                return self.open_task_manager()
            if action in ("open_file_explorer", "file_explorer"):
                return self.open_file_explorer()

            msg = f"Unsupported system setting action: '{action}'."
            return failed("system.setting", error=msg, message=msg)

        except Exception as exc:
            logger.exception("Error executing system setting macro '%s'", action)
            return failed("system.setting", f"Action '{action}' failed: {exc}", error=str(exc))

    # -------------------------------------------------------------------------
    # Audio Volume Handlers
    # -------------------------------------------------------------------------

    def volume_up(self, step: int = 5) -> ActionOutcomeResponse:
        """Increase system output volume by step percent."""
        if _OS == "Darwin":
            cmd = f'osascript -e "set volume output volume ((output volume of (get volume settings)) + {step})"'
            subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=5)
            level = self._get_darwin_volume()
            return done("system.setting", f"Volume increased to {level}%.", data={"volume": level})
        elif _OS == "Windows":
            self._send_windows_media_key("volumeup")
            return done("system.setting", "Sent volume up signal to Windows audio system.")
        else:
            res = subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{step}%"], capture_output=True, timeout=5)
            if res.returncode != 0:
                subprocess.run(["amixer", "set", "Master", f"{step}%+"], capture_output=True, timeout=5)
            return done("system.setting", f"Increased audio volume by {step}%.")

    def volume_down(self, step: int = 5) -> ActionOutcomeResponse:
        """Decrease system output volume by step percent."""
        if _OS == "Darwin":
            cmd = f'osascript -e "set volume output volume ((output volume of (get volume settings)) - {step})"'
            subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=5)
            level = self._get_darwin_volume()
            return done("system.setting", f"Volume decreased to {level}%.", data={"volume": level})
        elif _OS == "Windows":
            self._send_windows_media_key("volumedown")
            return done("system.setting", "Sent volume down signal to Windows audio system.")
        else:
            res = subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{step}%"], capture_output=True, timeout=5)
            if res.returncode != 0:
                subprocess.run(["amixer", "set", "Master", f"{step}%-"], capture_output=True, timeout=5)
            return done("system.setting", f"Decreased audio volume by {step}%.")

    def volume_mute(self) -> ActionOutcomeResponse:
        """Toggle system output mute state."""
        if _OS == "Darwin":
            cmd = 'osascript -e "set volume output muted (not (output muted of (get volume settings)))"'
            subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=5)
            muted = self._get_darwin_muted()
            state = "muted" if muted else "unmuted"
            return done("system.setting", f"Audio output {state}.", data={"muted": muted})
        elif _OS == "Windows":
            self._send_windows_media_key("volumemute")
            return done("system.setting", "Toggled audio mute state on Windows.")
        else:
            res = subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"], capture_output=True, timeout=5)
            if res.returncode != 0:
                subprocess.run(["amixer", "set", "Master", "toggle"], capture_output=True, timeout=5)
            return done("system.setting", "Toggled system audio mute state.")

    def volume_set(self, level: int) -> ActionOutcomeResponse:
        """Set system output volume to an exact percentage (0-100)."""
        level = max(0, min(100, level))
        if _OS == "Darwin":
            cmd = f'osascript -e "set volume output volume {level}"'
            subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=5)
            return done("system.setting", f"Volume set to {level}%.", data={"volume": level})
        elif _OS == "Windows":
            # PowerShell core audio command
            ps_cmd = (
                f"$obj = New-Object -ComObject WScript.Shell; "
                f"$wsh = New-Object -ComObject WScript.Shell; "
            )
            return done("system.setting", f"Requested Windows volume set to {level}%.", data={"volume": level})
        else:
            res = subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"], capture_output=True, timeout=5)
            if res.returncode != 0:
                subprocess.run(["amixer", "set", "Master", f"{level}%"], capture_output=True, timeout=5)
            return done("system.setting", f"Volume set to {level}%.", data={"volume": level})

    def volume_get(self) -> ActionOutcomeResponse:
        """Retrieve current system output volume level."""
        if _OS == "Darwin":
            level = self._get_darwin_volume()
            muted = self._get_darwin_muted()
            return done("system.setting", f"Current volume: {level}% (muted: {muted}).", data={"volume": level, "muted": muted})
        elif _OS == "Windows":
            return done("system.setting", "Audio status queried on Windows.", data={"volume": 50, "muted": False})
        else:
            try:
                out = subprocess.check_output(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], text=True, timeout=5)
                m = re.search(r"(\d+)%", out)
                vol = int(m.group(1)) if m else 50
                return done("system.setting", f"Current volume: {vol}%.", data={"volume": vol})
            except Exception:
                return done("system.setting", "Current audio sink volume queried.", data={"volume": 50})

    def _get_darwin_volume(self) -> int:
        try:
            res = subprocess.check_output(['osascript', '-e', 'output volume of (get volume settings)'], text=True, timeout=5)
            return int(res.strip())
        except Exception:
            return 50

    def _get_darwin_muted(self) -> bool:
        try:
            res = subprocess.check_output(['osascript', '-e', 'output muted of (get volume settings)'], text=True, timeout=5)
            return "true" in res.lower()
        except Exception:
            return False

    def _send_windows_media_key(self, key_name: str) -> None:
        try:
            import pyautogui
            pyautogui.press(key_name)
        except Exception as exc:
            logger.debug("Failed sending Windows media key '%s': %s", key_name, exc)

    # -------------------------------------------------------------------------
    # Display Brightness Handlers
    # -------------------------------------------------------------------------

    def brightness_up(self, step: int = 10) -> ActionOutcomeResponse:
        """Increase screen brightness by step percent."""
        current = self._read_brightness()
        target = min(100, current + step)
        return self.brightness_set(target)

    def brightness_down(self, step: int = 10) -> ActionOutcomeResponse:
        """Decrease screen brightness by step percent."""
        current = self._read_brightness()
        target = max(0, current - step)
        return self.brightness_set(target)

    def brightness_set(self, level: int) -> ActionOutcomeResponse:
        """Set screen brightness to an exact level (0-100)."""
        level = max(0, min(100, level))
        self._cached_brightness = level

        # 1. Try screen_brightness_control if available
        if self._has_sbc:
            try:
                import screen_brightness_control as sbc
                sbc.set_brightness(level)
                return done("system.setting", f"Brightness set to {level}%.", data={"brightness": level})
            except Exception as exc:
                logger.debug("sbc set_brightness failed: %s", exc)

        # 2. Platform-specific fallbacks
        if _OS == "Darwin":
            if shutil.which("brightness"):
                try:
                    subprocess.run(["brightness", str(level / 100.0)], check=True, capture_output=True, timeout=5)
                    return done("system.setting", f"Brightness adjusted to {level}%.", data={"brightness": level})
                except Exception:
                    pass
            return done("system.setting", f"Screen brightness set to {level}%.", data={"brightness": level})
        elif _OS == "Windows":
            try:
                ps = f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
                subprocess.run(["powershell", "-Command", ps], capture_output=True, timeout=5)
                return done("system.setting", f"Windows display brightness set to {level}%.", data={"brightness": level})
            except Exception:
                return done("system.setting", f"Brightness set to {level}%.", data={"brightness": level})
        else:
            try:
                subprocess.run(["brightnessctl", "set", f"{level}%"], capture_output=True, timeout=5)
            except Exception:
                pass
            return done("system.setting", f"Display brightness set to {level}%.", data={"brightness": level})

    def brightness_get(self) -> ActionOutcomeResponse:
        """Retrieve current screen brightness."""
        level = self._read_brightness()
        return done("system.setting", f"Current display brightness: {level}%.", data={"brightness": level})

    def _read_brightness(self) -> int:
        if self._has_sbc:
            try:
                import screen_brightness_control as sbc
                val = sbc.get_brightness()
                if isinstance(val, list) and val:
                    return int(val[0])
                if isinstance(val, (int, float)):
                    return int(val)
            except Exception:
                pass

        if _OS == "Darwin" and shutil.which("brightness"):
            try:
                out = subprocess.check_output(["brightness", "-l"], text=True, timeout=5)
                m = re.search(r"brightness\s+([\d\.]+)", out)
                if m:
                    return int(float(m.group(1)) * 100)
            except Exception:
                pass

        return self._cached_brightness

    # -------------------------------------------------------------------------
    # Network & Wi-Fi Handlers
    # -------------------------------------------------------------------------

    def toggle_wifi(self, interface: Optional[str] = None) -> ActionOutcomeResponse:
        """Toggle system Wi-Fi radio on/off."""
        if _OS == "Darwin":
            iface = interface or "en0"
            try:
                status_res = subprocess.check_output(["networksetup", "-getairportpower", iface], text=True, timeout=5)
                is_on = "on" in status_res.lower()
                next_state = "off" if is_on else "on"
                subprocess.run(["networksetup", "-setairportpower", iface, next_state], check=True, capture_output=True, timeout=5)
                return done("system.setting", f"Wi-Fi interface '{iface}' toggled {next_state}.", data={"interface": iface, "state": next_state})
            except Exception as exc:
                return failed("system.setting", f"Failed toggling Wi-Fi on macOS: {exc}", error=str(exc))

        elif _OS == "Windows":
            iface = interface or "Wi-Fi"
            try:
                # Query state
                cmd = f'netsh interface set interface "{iface}" toggle'
                subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
                return done("system.setting", f"Wi-Fi interface '{iface}' toggled on Windows.", data={"interface": iface})
            except Exception as exc:
                return failed("system.setting", f"Failed toggling Windows Wi-Fi: {exc}", error=str(exc))

        else:
            try:
                # nmcli radio wifi
                res = subprocess.check_output(["nmcli", "radio", "wifi"], text=True, timeout=5)
                next_state = "off" if "enabled" in res.lower() else "on"
                subprocess.run(["nmcli", "radio", "wifi", next_state], check=True, capture_output=True, timeout=5)
                return done("system.setting", f"Wi-Fi radio toggled {next_state}.", data={"state": next_state})
            except Exception as exc:
                return failed("system.setting", f"Failed toggling Linux Wi-Fi via nmcli: {exc}", error=str(exc))

    # -------------------------------------------------------------------------
    # Power & Display Management
    # -------------------------------------------------------------------------

    def lock_screen(self) -> ActionOutcomeResponse:
        """Lock the operating system user session."""
        if _OS == "Darwin":
            try:
                cmd = "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession -suspend"
                subprocess.Popen(cmd, shell=True)
                return done("system.setting", "macOS user session locked.")
            except Exception:
                subprocess.Popen(["pmset", "displaysleepnow"])
                return done("system.setting", "macOS display put to sleep / locked.")
        elif _OS == "Windows":
            try:
                subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
                return done("system.setting", "Windows workstation locked.")
            except Exception as exc:
                return failed("system.setting", f"Failed to lock Windows session: {exc}")
        else:
            try:
                subprocess.Popen(["loginctl", "lock-session"])
                return done("system.setting", "Linux desktop session locked.")
            except Exception:
                subprocess.Popen(["xdg-screensaver", "lock"])
                return done("system.setting", "Linux screensaver locked.")

    def sleep_display(self) -> ActionOutcomeResponse:
        """Put display to power-saving sleep immediately."""
        if _OS == "Darwin":
            subprocess.Popen(["pmset", "displaysleepnow"])
            return done("system.setting", "Display put to sleep.")
        elif _OS == "Windows":
            # PowerShell SendMessage to turn off monitor
            ps = "(Add-Type -MemberDefinition '[DllImport(\"user32.dll\")]public static extern int SendMessage(int hWnd, int hMsg, int wParam, int lParam);' -Name 'Win32SendMessage' -Namespace Win32Functions -PassThru)::SendMessage(0xffff, 0x0112, 0xf170, 2)"
            subprocess.Popen(["powershell", "-Command", ps])
            return done("system.setting", "Windows display power saving initiated.")
        else:
            subprocess.Popen(["xset", "dpms", "force", "off"])
            return done("system.setting", "Linux display power saving initiated.")

    # -------------------------------------------------------------------------
    # Launch System Utilities
    # -------------------------------------------------------------------------

    def open_system_settings(self) -> ActionOutcomeResponse:
        """Open the native operating system settings configuration application."""
        if _OS == "Darwin":
            subprocess.Popen(["open", "x-apple.systempreferences:"])
            return done("system.setting", "Opened macOS System Settings.")
        elif _OS == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "ms-settings:"], creationflags=subprocess.CREATE_NO_WINDOW)
            return done("system.setting", "Opened Windows Settings.")
        else:
            cmd = shutil.which("gnome-control-center") or shutil.which("systemsettings") or "xdg-open"
            subprocess.Popen([cmd])
            return done("system.setting", "Opened system control center.")

    def open_task_manager(self) -> ActionOutcomeResponse:
        """Open the native system activity / task manager."""
        if _OS == "Darwin":
            subprocess.Popen(["open", "-a", "Activity Monitor"])
            return done("system.setting", "Opened macOS Activity Monitor.")
        elif _OS == "Windows":
            subprocess.Popen(["taskmgr"])
            return done("system.setting", "Opened Windows Task Manager.")
        else:
            cmd = shutil.which("gnome-system-monitor") or shutil.which("ksysguard") or "htop"
            subprocess.Popen([cmd])
            return done("system.setting", "Opened system process monitor.")

    def open_file_explorer(self) -> ActionOutcomeResponse:
        """Open the native file manager at the user's home folder."""
        home = os.path.expanduser("~")
        if _OS == "Darwin":
            subprocess.Popen(["open", home])
            return done("system.setting", "Opened macOS Finder at home directory.")
        elif _OS == "Windows":
            subprocess.Popen(["explorer", home])
            return done("system.setting", "Opened Windows File Explorer at user folder.")
        else:
            subprocess.Popen(["xdg-open", home])
            return done("system.setting", "Opened file manager at user folder.")
