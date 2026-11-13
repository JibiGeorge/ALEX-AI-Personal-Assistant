from __future__ import annotations

import base64
import json
import time
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.memory import MemoryWrite
from app.services.speech_service import SpeechRecognitionResult
from app.services.dashboard_service import DashboardService


@pytest.fixture
def test_setup(tmp_path, monkeypatch):
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda *_: None)
    monkeypatch.setattr(keyring, "set_password", lambda *_: None)

    app = create_app(data_dir=tmp_path, api_token="test-secret-token")
    dashboard = DashboardService(iterations=1000)
    app.state.dashboard_service = dashboard

    # Pair a test device
    info = dashboard.generate_pairing_info()
    pair_res = dashboard.verify_and_pair(
        client_ip="127.0.0.1",
        code=info.pairing_code,
        device_name="Test iPhone",
        device_platform="iOS",
    )
    token = pair_res.session_token

    client = TestClient(app)
    return {
        "app": app,
        "client": client,
        "dashboard": dashboard,
        "token": token,
        "desktop_headers": {"Authorization": "Bearer test-secret-token"},
        "mobile_headers": {"X-Mobile-Session": token},
    }


def test_mobile_turn_endpoint_success(test_setup):
    client = test_setup["client"]
    mobile_headers = test_setup["mobile_headers"]
    app = test_setup["app"]

    # Mock TTS service synthesis
    mock_tts = MagicMock()
    mock_tts.synthesize = AsyncMock(return_value=b"\x00\x01\x00\x02" * 100)
    mock_tts.last_voice_used = "en_US-lessac-medium"
    app.state.tts_service = mock_tts

    # Mock Conversation service reply
    mock_conv = MagicMock()
    mock_turn_res = MagicMock()
    mock_turn_res.reply = "Hello! I am Alex running on desktop."
    mock_conv.reply.return_value = mock_turn_res
    app.state.conversation_service = mock_conv

    res = client.post(
        "/api/v1/mobile/turn",
        json={"text": "Hello Alex!", "synthesize_voice": True},
        headers=mobile_headers,
    )

    assert res.status_code == 200
    data = res.json()
    assert data["reply"] == "Hello! I am Alex running on desktop."
    assert data["audio_base64"] is not None
    assert data["sample_rate"] == 24000
    assert data["voice_used"] == "en_US-lessac-medium"


def test_mobile_turn_unauthorized(test_setup):
    client = test_setup["client"]
    res = client.post(
        "/api/v1/mobile/turn",
        json={"text": "Hello without token"},
        headers={"X-Mobile-Session": "invalid-token"},
    )
    assert res.status_code == 401


def test_mobile_memories_endpoint(test_setup):
    client = test_setup["client"]
    mobile_headers = test_setup["mobile_headers"]
    app = test_setup["app"]

    # Write a test memory
    app.state.memory_service.upsert(
        category="identity",
        key="favorite_color",
        item=MemoryWrite(value="blue"),
    )

    res = client.get("/api/v1/mobile/memories", headers=mobile_headers)
    assert res.status_code == 200
    data = res.json()
    assert "memories" in data
    assert any(m["key"] == "favorite_color" and m["value"] == "blue" for m in data["memories"])


def test_mobile_web_asset_serving(test_setup):
    client = test_setup["client"]

    # Request mobile web index.html
    res = client.get("/api/v1/mobile/web/index.html")
    assert res.status_code == 200
    assert "ALEX COMPANION" in res.text

    # Request companion.js
    res_js = client.get("/api/v1/mobile/web/companion.js")
    assert res_js.status_code == 200
    assert "Alex Mobile Companion" in res_js.text

    # Missing file inside web companion returns 404
    res_missing = client.get("/api/v1/mobile/web/does_not_exist.html")
    assert res_missing.status_code == 404

    # Directory traversal prevention
    res_bad = client.get("/api/v1/mobile/web/../../../../etc/passwd")
    assert res_bad.status_code in (401, 404)


def test_mobile_encrypted_ws_turn(test_setup):
    client = test_setup["client"]
    dashboard = test_setup["dashboard"]
    token = test_setup["token"]
    app = test_setup["app"]

    # Mock Conversation service reply
    mock_conv = MagicMock()
    mock_turn_res = MagicMock()
    mock_turn_res.reply = "Quantum computing uses qubits."
    mock_conv.reply.return_value = mock_turn_res
    app.state.conversation_service = mock_conv

    with client.websocket_connect(f"/api/v1/mobile/ws?token={token}") as ws:
        # Initial welcome message
        welcome_raw = ws.receive_text()
        welcome_frame = json.loads(welcome_raw)
        welcome_bytes = dashboard.decrypt(token, welcome_frame["iv"], welcome_frame["ciphertext"])
        welcome_obj = json.loads(welcome_bytes.decode("utf-8"))
        assert welcome_obj["type"] == "connected"

        # Send encrypted turn message
        turn_payload = json.dumps({"type": "turn", "content": "What is quantum computing?"})
        enc_turn = dashboard.encrypt(token, turn_payload)
        ws.send_text(json.dumps(enc_turn))

        # Receive encrypted response
        reply_raw = ws.receive_text()
        reply_frame = json.loads(reply_raw)
        reply_bytes = dashboard.decrypt(token, reply_frame["iv"], reply_frame["ciphertext"])
        reply_obj = json.loads(reply_bytes.decode("utf-8"))
        assert reply_obj["type"] == "response"
        assert reply_obj["text"] == "Quantum computing uses qubits."


def test_mobile_audio_websocket_streaming(test_setup):
    client = test_setup["client"]
    token = test_setup["token"]
    app = test_setup["app"]

    # 1. Reject unauthorized connection
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/mobile/ws/audio?token=invalid_token") as ws:
            pass

    # 2. Mock SpeechService STT
    mock_speech = MagicMock()
    mock_speech.transcribe = AsyncMock(return_value=SpeechRecognitionResult(
        text="Turn on desk lights",
        language="en",
        language_probability=0.99,
        duration_seconds=1.5,
    ))
    app.state.speech_service = mock_speech

    # Mock ConversationService
    mock_conv = MagicMock()
    mock_turn_res = MagicMock()
    mock_turn_res.reply = "Desk lights have been switched on."
    mock_conv.reply.return_value = mock_turn_res
    app.state.conversation_service = mock_conv

    # Mock TTSService
    mock_tts = MagicMock()
    mock_tts.synthesize = AsyncMock(return_value=b"\x00\x02" * 500)
    app.state.tts_service = mock_tts

    # 3. Connect to audio WebSocket
    with client.websocket_connect(f"/api/v1/mobile/ws/audio?token={token}") as ws:
        # Start audio stream
        ws.send_text(json.dumps({"type": "audio_start"}))

        # Stream 16kHz PCM audio bytes
        dummy_pcm = b"\x00\x05\x00\x03" * 400
        ws.send_bytes(dummy_pcm)

        # Signal end of speech
        ws.send_text(json.dumps({"type": "audio_end"}))

        # Expect transcript event
        transcript_msg = json.loads(ws.receive_text())
        assert transcript_msg["type"] == "transcript"
        assert transcript_msg["text"] == "Turn on desk lights"

        # Expect response event
        response_msg = json.loads(ws.receive_text())
        assert response_msg["type"] == "response"
        assert response_msg["text"] == "Desk lights have been switched on."

        # Expect synthesized audio binary response
        audio_bytes = ws.receive_bytes()
        assert len(audio_bytes) == 1000
