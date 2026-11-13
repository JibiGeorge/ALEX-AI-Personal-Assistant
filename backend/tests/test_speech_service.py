"""
Comprehensive test suite for SpeechService (TASK-P4-01 / CAT-08).
"""

from __future__ import annotations

import asyncio
import io
import wave
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.speech_service import (
    DEFAULT_WHISPER_MODEL,
    MIC_RATE,
    SPEAKER_RATE,
    SpeechRecognitionResult,
    SpeechService,
    _threads,
    duration_s,
    resample,
    to_float32,
    to_pcm16,
    to_wav,
)


def test_audio_utilities_to_float32_and_pcm16():
    # 0 amplitude
    zero_pcm = b"\x00\x00"
    f32 = to_float32(zero_pcm)
    assert len(f32) == 1
    assert f32[0] == 0.0

    # Max positive (32767)
    max_pcm = (32767).to_bytes(2, byteorder="little", signed=True)
    f32_max = to_float32(max_pcm)
    assert np.isclose(f32_max[0], 32767.0 / 32768.0, atol=1e-4)

    # Conversion back to PCM for 1.0 peak
    pcm_one = to_pcm16(np.array([1.0], dtype=np.float32))
    assert pcm_one == max_pcm

    # Roundtrip accuracy for arbitrary samples
    back_pcm = to_pcm16(f32_max)
    back_f32 = to_float32(back_pcm)
    assert np.isclose(back_f32[0], f32_max[0], atol=1e-4)

    # Clipping without wrap-around
    overflow = np.array([2.5, -3.0], dtype=np.float32)
    clipped_pcm = to_pcm16(overflow)
    val1 = int.from_bytes(clipped_pcm[:2], byteorder="little", signed=True)
    val2 = int.from_bytes(clipped_pcm[2:], byteorder="little", signed=True)
    assert val1 == 32767
    assert val2 == -32767

    # Odd byte count drops trailing byte safely
    odd_pcm = b"\x00\x00\x01"
    f32_odd = to_float32(odd_pcm)
    assert len(f32_odd) == 1


def test_audio_resampling():
    # 1 second of 16kHz audio = 16000 samples = 32000 bytes
    samples_16k = np.sin(np.linspace(0, 2 * np.pi * 440, 16000)).astype(np.float32)
    pcm_16k = to_pcm16(samples_16k)

    # Resample 16k -> 24k
    pcm_24k = resample(pcm_16k, src_rate=16_000, dst_rate=24_000)
    samples_24k = to_float32(pcm_24k)
    assert len(samples_24k) == 24000

    # Resample identical rate is zero-op
    assert resample(pcm_16k, 16_000, 16_000) == pcm_16k


def test_to_wav_and_duration():
    # 0.5s at 16kHz = 8000 samples = 16000 bytes
    pcm = b"\x00" * 16000
    assert duration_s(pcm, rate=16_000) == 0.5

    wav_bytes = to_wav(pcm, rate=16_000, channels=1)
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 8000


def test_threads_budgeting():
    threads = _threads()
    assert 1 <= threads <= 8


def test_transcribe_drops_audio_under_quarter_second():
    svc = SpeechService(backend="local")
    short_pcm = b"\x00" * 3200  # 0.1s at 16kHz
    assert duration_s(short_pcm, 16_000) < 0.25

    async def _test():
        res = await svc.transcribe(short_pcm, sample_rate=16_000)
        assert isinstance(res, SpeechRecognitionResult)
        assert res.text == ""
        assert res.duration_seconds == 0.1

    asyncio.run(_test())


def test_language_acceptance_rules():
    svc = SpeechService()
    assert svc.detected_language == ""

    # Rule 1: First detection is accepted regardless of confidence/length
    svc._accept_language("en", confidence=0.4, text="hi")
    assert svc.detected_language == "en"

    # Rule 2: Low confidence candidate is ignored
    svc._accept_language("tr", confidence=0.5, text="burada uzun bir cumle var")
    assert svc.detected_language == "en"

    # Rule 3: Short candidate is ignored even if confident
    svc._accept_language("tr", confidence=0.95, text="tamam")  # len 5 < 12
    assert svc.detected_language == "en"

    # Rule 4: Confident and sufficiently long candidate switches language
    svc._accept_language("tr", confidence=0.88, text="merhaba dunya nasilsiniz bugun")
    assert svc.detected_language == "tr"


def test_speech_service_api_fallback(monkeypatch):
    svc = SpeechService(backend="api", base_url="https://api.openai.com/v1", api_key="sk-test")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"text": "Hello world from cloud API", "language": "en"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers=None, data=None, files=None):
            assert "/audio/transcriptions" in url
            assert headers["Authorization"] == "Bearer sk-test"
            assert data["model"] == DEFAULT_WHISPER_MODEL
            return FakeResponse()

    import httpx
    monkeypatch.setattr(httpx, "Client", FakeClient)

    pcm = b"\x00" * 32000  # 1.0 second of audio
    async def _test():
        res = await svc.transcribe(pcm, sample_rate=16_000)
        assert res.text == "Hello world from cloud API"
        assert res.language == "en"
        assert res.duration_seconds == 1.0

    asyncio.run(_test())


def test_speech_service_probe():
    # Local probe
    local_svc = SpeechService(backend="local", model="base")
    ok, msg = local_svc.probe()
    assert "faster-whisper" in msg or "not installed" in msg

    # API probe without base_url
    api_svc_empty = SpeechService(backend="api", base_url="")
    ok, msg = api_svc_empty.probe()
    assert ok is False
    assert "No transcription API base_url" in msg

    # API probe with base_url
    api_svc = SpeechService(backend="api", base_url="http://localhost:8000/v1")
    ok, msg = api_svc.probe()
    assert ok is True
    assert "localhost:8000" in msg


def test_speech_service_warmup(monkeypatch):
    svc = SpeechService(backend="local", model="tiny")
    fake_model = MagicMock()

    class FakeSegment:
        text = ""

    class FakeInfo:
        language = "en"
        language_probability = 1.0

    fake_model.transcribe.return_value = ([FakeSegment()], FakeInfo())
    svc._model = fake_model

    async def _test():
        await svc.warmup()
        assert svc._is_warmed_up is True
        assert fake_model.transcribe.called

    asyncio.run(_test())


def test_transcribe_audio_fixture_english():
    svc = SpeechService(backend="local")
    fake_model = MagicMock()

    class FakeSegment:
        start = 0.0
        end = 1.0
        text = "Hello Alex what is the weather today"

    class FakeInfo:
        language = "en"
        language_probability = 0.98

    fake_model.transcribe.return_value = ([FakeSegment()], FakeInfo())
    svc._model = fake_model

    pcm = b"\x01\x00" * 16000  # 1.0 second of audio
    async def _test():
        res = await svc.transcribe(pcm, sample_rate=16_000)
        assert res.text == "Hello Alex what is the weather today"
        assert res.language == "en"
        assert res.language_probability == 0.98
        assert res.duration_seconds == 1.0
        assert len(res.segments) == 1
        assert res.segments[0]["text"] == "Hello Alex what is the weather today"
        assert svc.detected_language == "en"

    asyncio.run(_test())


def test_transcribe_audio_fixture_turkish():
    svc = SpeechService(backend="local")
    fake_model = MagicMock()

    class FakeSegment:
        start = 0.0
        end = 1.2
        text = "Bugün hava durumu nasıl olacak acaba"

    class FakeInfo:
        language = "tr"
        language_probability = 0.94

    fake_model.transcribe.return_value = ([FakeSegment()], FakeInfo())
    svc._model = fake_model

    pcm = b"\x02\x00" * 19200  # 1.2 seconds of audio
    async def _test():
        res = await svc.transcribe(pcm, sample_rate=16_000)
        assert res.text == "Bugün hava durumu nasıl olacak acaba"
        assert res.language == "tr"
        assert res.language_probability == 0.94
        assert np.isclose(res.duration_seconds, 1.2, atol=1e-2)
        assert svc.detected_language == "tr"

    asyncio.run(_test())


def test_speech_transcribe_api_route(tmp_path):
    import base64
    from fastapi.testclient import TestClient
    from app.main import create_app

    app = create_app(data_dir=tmp_path, api_token="test-speech-token")
    client = TestClient(app)

    # Mock transcribe on app.state.speech_service
    fake_res = SpeechRecognitionResult(
        text="Open the browser and search for news",
        language="en",
        language_probability=0.99,
        duration_seconds=1.5,
        segments=[{"start": 0.0, "end": 1.5, "text": "Open the browser and search for news"}],
    )

    async def _fake_transcribe(pcm, sample_rate=16000, language=""):
        return fake_res

    app.state.speech_service.transcribe = _fake_transcribe

    pcm = b"\x01\x00" * 24000  # 1.5s
    b64_audio = base64.b64encode(pcm).decode("ascii")

    response = client.post(
        "/api/v1/speech/transcribe",
        json={"audio_base64": b64_audio, "sample_rate": 16000},
        headers={"Authorization": "Bearer test-speech-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Open the browser and search for news"
    assert data["language"] == "en"
    assert data["language_probability"] == 0.99
    assert data["duration_seconds"] == 1.5

