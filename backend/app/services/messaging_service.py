"""
Messaging Service (TASK-GAP-05 / GAP-05).

Automates message dispatch across desktop messaging clients:
- WhatsApp Desktop and WhatsApp Web
- Telegram Desktop
- Signal, Discord, Instagram
- Safe clipboard-based text insertion
- Five-Word Outcome Contract adherence (unverified for blind typing, done for verified drivers, failed for launch errors)
"""

from __future__ import annotations

from importlib.util import find_spec
import logging
import platform
import subprocess
import time
from typing import Any, Dict, Optional
import webbrowser

from app.actions.base import ActionOutcomeResponse, done, failed, unverified
from app.schemas.messaging import SendMessageParameters

logger = logging.getLogger(__name__)

_OS = platform.system()  # "Darwin" | "Windows" | "Linux"


class MessagingService:
    """Service orchestrating message dispatch to desktop and web messaging platforms."""

    def __init__(self) -> None:
        pass

    @property
    def has_automation_deps(self) -> bool:
        """Check whether pyautogui and pyperclip are importable."""
        return find_spec("pyautogui") is not None and find_spec("pyperclip") is not None

    def execute(self, params: SendMessageParameters) -> ActionOutcomeResponse:
        """Route and execute a message dispatch request."""
        receiver = params.receiver.strip()
        message_text = params.message_text.strip()
        target_platform = (params.platform or "WhatsApp").strip()

        if not receiver:
            return failed("message.send", error="Missing receiver", message="Recipient contact name must be specified.")
        if not message_text:
            return failed("message.send", error="Missing message text", message="Message text cannot be empty.")

        platform_clean = target_platform.lower()
        if "whatsapp" in platform_clean:
            return self._send_whatsapp(receiver, message_text)
        elif "telegram" in platform_clean:
            return self._send_desktop_app("Telegram", receiver, message_text)
        elif "signal" in platform_clean:
            return self._send_desktop_app("Signal", receiver, message_text)
        elif "discord" in platform_clean:
            return self._send_desktop_app("Discord", receiver, message_text)
        elif "instagram" in platform_clean:
            return self._send_instagram(receiver, message_text)
        else:
            return self._send_desktop_app(target_platform, receiver, message_text)

    def _send_whatsapp(self, receiver: str, message: str) -> ActionOutcomeResponse:
        """Send message via WhatsApp (desktop client or web fallback)."""
        # Try launching native app first
        launched = self._open_app("WhatsApp")
        if not launched:
            # Fall back to opening WhatsApp Web chat link
            web_url = f"https://web.whatsapp.com/"
            webbrowser.open(web_url)
            return unverified(
                "message.send",
                f"WhatsApp Web opened for contact '{receiver}'. Awaiting manual or visual confirmation.",
                data={"platform": "WhatsApp Web", "receiver": receiver},
            )

        return self._type_into_app("WhatsApp", receiver, message)

    def _send_desktop_app(self, app_name: str, receiver: str, message: str) -> ActionOutcomeResponse:
        """Generic desktop messaging app dispatch."""
        launched = self._open_app(app_name)
        if not launched:
            return failed(
                "message.send",
                error=f"Could not open {app_name}",
                message=f"{app_name} could not be launched on this system. Please ensure the app is installed.",
                data={"platform": app_name, "receiver": receiver},
            )

        return self._type_into_app(app_name, receiver, message)

    def _send_instagram(self, receiver: str, message: str) -> ActionOutcomeResponse:
        """Instagram direct messaging via browser."""
        try:
            webbrowser.open("https://www.instagram.com/direct/new/")
            time.sleep(2.0)
            return unverified(
                "message.send",
                f"Instagram Direct opened in browser for '{receiver}'.",
                data={"platform": "Instagram", "receiver": receiver},
            )
        except Exception as exc:
            return failed("message.send", error=str(exc), message=f"Failed opening Instagram: {exc}")

    def _open_app(self, app_name: str) -> bool:
        """Launch desktop application by name."""
        try:
            if _OS == "Darwin":
                res = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=10)
                if res.returncode != 0:
                    res = subprocess.run(["open", "-a", f"{app_name}.app"], capture_output=True, timeout=10)
                return res.returncode == 0
            elif _OS == "Windows":
                # Start via cmd /c start
                subprocess.Popen(["cmd", "/c", "start", app_name], shell=True)
                return True
            else:
                for launcher in [["gtk-launch", app_name.lower()], [app_name.lower()]]:
                    try:
                        subprocess.Popen(launcher, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return True
                    except FileNotFoundError:
                        continue
                return False
        except Exception as exc:
            logger.debug("Failed opening '%s': %s", app_name, exc)
            return False

    def _type_into_app(self, app_name: str, receiver: str, message: str) -> ActionOutcomeResponse:
        """Simulate keyboard navigation, contact search, and message pasting."""
        if not self.has_automation_deps:
            return unverified(
                "message.send",
                f"{app_name} was opened, but PyAutoGUI/pyperclip are missing for automated keystrokes.",
                data={"platform": app_name, "receiver": receiver},
            )

        try:
            import pyautogui
            import pyperclip

            time.sleep(1.0)
            # Focus search bar (Cmd+F / Ctrl+F)
            search_key = ("command", "f") if _OS == "Darwin" else ("ctrl", "f")
            pyautogui.hotkey(*search_key)
            time.sleep(0.3)

            # Paste receiver contact name
            pyperclip.copy(receiver)
            paste_key = ("command", "v") if _OS == "Darwin" else ("ctrl", "v")
            pyautogui.hotkey(*paste_key)
            time.sleep(0.8)
            pyautogui.press("enter")
            time.sleep(0.8)

            # Paste message body
            pyperclip.copy(message)
            pyautogui.hotkey(*paste_key)
            time.sleep(0.3)
            pyautogui.press("enter")

            # Honest Five-Word Outcome: blind keystroke dispatches cannot verify delivery
            return unverified(
                "message.send",
                f"Message was dispatched to {app_name} for '{receiver}'. Awaiting recipient confirmation.",
                data={"platform": app_name, "receiver": receiver, "message_preview": message[:80]},
            )
        except Exception as exc:
            logger.error("Keystroke simulation error into '%s': %s", app_name, exc)
            return failed(
                "message.send",
                error=str(exc),
                message=f"Failed to complete typing into {app_name}: {exc}",
                data={"platform": app_name, "receiver": receiver},
            )

