"""
Unit tests for ElevenLabsService and elevenlabs.synthesize action (TASK-GAP-08 / GAP-08).
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.elevenlabs import register_elevenlabs_actions
from app.schemas.elevenlabs import ElevenLabsSynthesizeParameters
from app.services.elevenlabs_service import (
    ElevenLabsService,
    PCM_FORMAT,
    MP3_FORMAT,
    parse_elevenlabs_error,
)


def test_parse_elevenlabs_error():
    err_json = json.dumps({"detail": {"message": "Invalid API key provided.", "status": "invalid_api_key"}})
    assert parse_elevenlabs_error(err_json) == "Invalid API key provided."

    fallback = parse_elevenlabs_error("Plain text internal server error")
    assert "Plain text" in fallback


def test_elevenlabs_get_api_key_resolution():
    # Explicit key
    service1 = ElevenLabsService(api_key="key_explicit_123")
    assert service1.get_api_key() == "key_explicit_123"

    # Environment variable
    with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "key_env_456"}):
        service2 = ElevenLabsService()
        assert service2.get_api_key() == "key_env_456"

    # Settings service fallback
    mock_settings = MagicMock()
    mock_settings.get_api_key_for_service.return_value = "xi-key-from-settings-32charslong"
    with patch.dict("os.environ", {}, clear=True):
        service3 = ElevenLabsService(settings_service=mock_settings)
        assert service3.get_api_key() == "xi-key-from-settings-32charslong"


def test_elevenlabs_missing_key_fails():
    with patch.dict("os.environ", {}, clear=True):
        service = ElevenLabsService(api_key=None)
        params = ElevenLabsSynthesizeParameters(text="Hello from Alex")
        res = service.execute(params)

        assert res.status == ToolOutcome.FAILED
        assert "api key" in res.message.lower()


@pytest.mark.anyio
async def test_elevenlabs_stream_synthesize_pcm():
    service = ElevenLabsService(api_key="fake_key_789")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    async def mock_aiter():
        yield b"pcm_chunk_1"
        yield b"pcm_chunk_2"

    mock_resp.aiter_bytes = mock_aiter

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream.return_value = mock_stream_ctx

    mock_client_ctx = MagicMock()
    mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_ctx):
        chunks = []
        async for chunk in service.stream_synthesize("Good morning"):
            chunks.append(chunk)

        assert b"".join(chunks) == b"pcm_chunk_1pcm_chunk_2"


def test_elevenlabs_execute_save_to_disk(tmp_path):
    service = ElevenLabsService(api_key="fake_key_789")
    target_path = tmp_path / "voice_output.pcm"

    with patch.object(service, "synthesize", AsyncMock(return_value=b"raw_audio_pcm_stream")):
        params = ElevenLabsSynthesizeParameters(
            text="Testing speech save",
            save_to_disk=True,
            output_path=str(target_path),
        )
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert target_path.exists()
        assert target_path.read_bytes() == b"raw_audio_pcm_stream"
        assert res.data["size_bytes"] == len(b"raw_audio_pcm_stream")


def test_elevenlabs_list_voices_and_probe():
    service = ElevenLabsService(api_key="fake_key_789")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "voices": [
            {"voice_id": "v1", "name": "Rachel"},
            {"voice_id": "v2", "name": "George"},
        ]
    }

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__.return_value = mock_client
    mock_client_ctx.__exit__.return_value = None

    with patch("httpx.Client", return_value=mock_client_ctx):
        voices = service.list_voices()
        assert len(voices) == 2
        assert voices[0]["name"] == "Rachel"

        ok, msg = service.probe()
        assert ok is True
        assert "Rachel" in msg


def test_elevenlabs_action_registry_integration():
    service = ElevenLabsService(api_key="fake_key_789")
    registry = ActionRegistry()
    register_elevenlabs_actions(registry, service)

    defn = registry.get("elevenlabs.synthesize")
    assert defn is not None
    assert defn.category == "speech"
    assert defn.requires_confirmation is False

    view = defn.public_view()
    assert view["action_id"] == "elevenlabs.synthesize"
    assert view["requires_confirmation"] is False
