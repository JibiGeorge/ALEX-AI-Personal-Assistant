import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.services.speech_service import SpeechRecognitionResult, SpeechService
from app.services.voice_lifecycle_manager import VoiceLifecycleManager, VoiceState


@pytest.fixture
def mock_speech_service():
    service = MagicMock(spec=SpeechService)
    service.transcribe = AsyncMock(
        return_value=SpeechRecognitionResult(
            text="what time is it",
            language="en",
            language_probability=0.99,
            duration_seconds=1.5,
        )
    )
    return service


@pytest.fixture
def mock_tts_service():
    service = MagicMock()
    service.synthesize = AsyncMock(return_value=b"\x00\x00" * 100)
    return service


@pytest.fixture
def mock_wake_service():
    service = MagicMock()
    service.predict = MagicMock(return_value=0.1)
    service.start = MagicMock()
    service.stop = MagicMock()
    return service


@pytest.fixture
def mock_conv_service():
    service = MagicMock()
    reply_obj = MagicMock()
    reply_obj.text = "It is 3:30 PM, Commander."
    service.reply = MagicMock(return_value=reply_obj)
    return service


def test_voice_lifecycle_initial_state(mock_wake_service, mock_speech_service, mock_tts_service, mock_conv_service):
    manager = VoiceLifecycleManager(
        wake_word_service=mock_wake_service,
        speech_service=mock_speech_service,
        tts_service=mock_tts_service,
        conversation_service=mock_conv_service,
    )
    assert manager.state == VoiceState.SLEEPING
    assert manager.wake_word_enabled is True
    assert manager.mic_enabled is True


def test_voice_lifecycle_wake_and_sleep(mock_wake_service, mock_speech_service, mock_tts_service, mock_conv_service):
    async def _run():
        manager = VoiceLifecycleManager(
            wake_word_service=mock_wake_service,
            speech_service=mock_speech_service,
            tts_service=mock_tts_service,
            conversation_service=mock_conv_service,
        )
        events = []
        manager.subscribe(lambda e: events.append(e))

        await manager.wake(reason="manual_button")
        assert manager.state == VoiceState.LISTENING
        assert any(e.get("type") == "state_changed" and e.get("new_state") == "LISTENING" for e in events)

        await manager.sleep(reason="user_request")
        assert manager.state == VoiceState.SLEEPING
        assert any(e.get("type") == "state_changed" and e.get("new_state") == "SLEEPING" for e in events)

    asyncio.run(_run())


def test_voice_lifecycle_interruption(mock_wake_service, mock_speech_service, mock_tts_service, mock_conv_service):
    async def _run():
        manager = VoiceLifecycleManager(
            wake_word_service=mock_wake_service,
            speech_service=mock_speech_service,
            tts_service=mock_tts_service,
            conversation_service=mock_conv_service,
        )
        await manager.wake()
        manager._transition_to(VoiceState.SPEAKING)
        assert manager.state == VoiceState.SPEAKING

        await manager.interrupt(reason="user_voice")
        assert manager.state == VoiceState.LISTENING

    asyncio.run(_run())


def test_voice_lifecycle_process_turn(mock_wake_service, mock_speech_service, mock_tts_service, mock_conv_service):
    async def _run():
        manager = VoiceLifecycleManager(
            wake_word_service=mock_wake_service,
            speech_service=mock_speech_service,
            tts_service=mock_tts_service,
            conversation_service=mock_conv_service,
        )
        events = []
        manager.subscribe(lambda e: events.append(e))

        await manager.process_turn("hello alex")
        assert any(e.get("type") == "response" for e in events)
        assert manager.state == VoiceState.WAITING_FOR_FOLLOWUP

    asyncio.run(_run())


def test_voice_lifecycle_inactivity_timeout(mock_wake_service, mock_speech_service, mock_tts_service, mock_conv_service):
    async def _run():
        manager = VoiceLifecycleManager(
            wake_word_service=mock_wake_service,
            speech_service=mock_speech_service,
            tts_service=mock_tts_service,
            conversation_service=mock_conv_service,
            inactivity_timeout=0.1,
        )
        await manager.wake()
        assert manager.state == VoiceState.LISTENING
        manager._last_interaction_time = 0.0  # simulate elapsed timeout
        await manager.check_inactivity()
        assert manager.state == VoiceState.SLEEPING

    asyncio.run(_run())

