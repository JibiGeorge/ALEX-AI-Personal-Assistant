"""
Unit tests for MessagingService and message.send action (TASK-GAP-05 / GAP-05).
"""

from unittest.mock import MagicMock, patch
import pydantic
import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.messaging import register_messaging_actions
from app.schemas.messaging import SendMessageParameters
from app.services.messaging_service import MessagingService


def test_messaging_empty_receiver_validation():
    with pytest.raises(pydantic.ValidationError):
        SendMessageParameters(receiver="", message_text="Hello world")

    # Whitespace receiver stripped inside service
    service = MessagingService()
    res = service.execute(SendMessageParameters(receiver="   ", message_text="Hello"))
    assert res.status == ToolOutcome.FAILED
    assert "recipient" in res.message.lower()


def test_messaging_empty_message_validation():
    with pytest.raises(pydantic.ValidationError):
        SendMessageParameters(receiver="Alice", message_text="")

    # Whitespace message stripped inside service
    service = MessagingService()
    res = service.execute(SendMessageParameters(receiver="Alice", message_text="   "))
    assert res.status == ToolOutcome.FAILED
    assert "empty" in res.message.lower()


@patch("webbrowser.open")
def test_messaging_whatsapp_web_fallback(mock_wb):
    service = MessagingService()
    with patch.object(service, "_open_app", return_value=False):
        params = SendMessageParameters(receiver="Bob", message_text="Meeting at 3pm", platform="WhatsApp")
        res = service.execute(params)

        assert res.status == ToolOutcome.UNVERIFIED
        mock_wb.assert_called_once()
        assert "WhatsApp Web" in res.message


@patch("webbrowser.open")
def test_messaging_instagram(mock_wb):
    service = MessagingService()
    params = SendMessageParameters(receiver="charlie", message_text="Check this out", platform="Instagram")
    res = service.execute(params)

    assert res.status == ToolOutcome.UNVERIFIED
    mock_wb.assert_called_once()
    assert "Instagram Direct" in res.message


def test_messaging_desktop_app_typing():
    service = MessagingService()
    with patch.object(service, "_open_app", return_value=True), \
         patch("app.services.messaging_service.find_spec", return_value=MagicMock()), \
         patch("time.sleep"), \
         patch("pyautogui.hotkey"), \
         patch("pyautogui.press"), \
         patch("pyperclip.copy"):

        params = SendMessageParameters(receiver="David", message_text="System update ready", platform="Telegram")
        res = service.execute(params)

        assert res.status == ToolOutcome.UNVERIFIED
        assert "Telegram" in res.message
        assert res.data["receiver"] == "David"


def test_messaging_action_registry_integration():
    service = MessagingService()
    registry = ActionRegistry()
    register_messaging_actions(registry, service)

    defn = registry.get("message.send")
    assert defn is not None
    assert defn.category == "communication"
    assert defn.requires_confirmation is True

    view = defn.public_view()
    assert view["action_id"] == "message.send"
    assert view["requires_confirmation"] is True
