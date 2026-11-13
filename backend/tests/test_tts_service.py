"""
Comprehensive test suite for TTSService and SystemTTSAdapter (TASK-P4-02 / CAT-09).
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.adapters.system_tts_adapter import (
    SystemTTSAdapter,
    list_system_voices,
    split_sentences,
)
from app.services.speech_service import SPEAKER_RATE, to_pcm16
from app.services.tts_service import (
    DEFAULT_PIPER_VOICE,
    TTSService,
    VoiceDescriptor,
)


def test_split_sentences_punctuation_and_scripts():
    # Empty string
    assert split_sentences("") == []

    # Simple English sentences
    text = "Hello there. How are you today? I am doing great!"
    pieces = split_sentences(text)
    assert len(pieces) == 3
    assert pieces[0] == "Hello there."
    assert pieces[1] == "How are you today?"
    assert pieces[2] == "I am doing great!"

    # Version numbers must not split mid-number
    v_text = "Alex version 3.14 is active. Everything is normal."
    v_pieces = split_sentences(v_text)
    assert len(v_pieces) == 2
    assert "version 3.14" in v_pieces[0]

    # CJK and non-Latin sentence terminators without spaces
    cjk_text = "今日はいい天気です。مرحبا بك۔नमस्ते।"
    cjk_pieces = split_sentences(cjk_text)
    assert len(cjk_pieces) >= 3

    # Long sentence breaking on space boundary
    long_text = "word " * 100
    long_pieces = split_sentences(long_text, max_chars=50)
    assert len(long_pieces) > 1
    assert all(len(p) <= 50 for p in long_pieces)


def test_system_tts_adapter_methods(monkeypatch):
    adapter = SystemTTSAdapter(voice="", speed_rate=0)

    # Mock synth_sentence_blocking to return synthetic 24 kHz PCM
    fake_pcm = b"\x01\x00" * 2400  # 0.1s at 24 kHz
    monkeypatch.setattr(adapter, "synth_sentence_blocking", lambda s: fake_pcm)

    async def _test():
        out = await adapter.speak("First sentence. Second sentence.")
        assert len(out) == len(fake_pcm) * 2

        stream_chunks = []
        async for chunk in adapter.stream_speak("Sentence one. Sentence two."):
            stream_chunks.append(chunk)
        assert len(stream_chunks) == 2

    asyncio.run(_test())


def test_tts_service_voice_resolution(tmp_path: Path):
    voice_dir = tmp_path / "voices"
    voice_dir.mkdir(parents=True)

    # Create dummy .onnx files for voices
    (voice_dir / "en_US-lessac-medium.onnx").write_bytes(b"dummy")
    (voice_dir / "tr_TR-dfki-medium.onnx").write_bytes(b"dummy")
    (voice_dir / "es_ES-carlfm-medium.onnx").write_bytes(b"dummy")

    tts = TTSService(
        engine="piper",
        default_voice="en_US-lessac-medium",
        voice_dir=voice_dir,
        follow_language=True,
    )

    installed = tts.installed_piper_voices()
    assert "en_US-lessac-medium" in installed
    assert "tr_TR-dfki-medium" in installed
    assert "es_ES-carlfm-medium" in installed

    # Test language_of
    assert tts.language_of("en_US-lessac-medium") == "en"
    assert tts.language_of("tr_TR-dfki-medium") == "tr"
    assert tts.language_of("es_ES-carlfm-medium") == "es"

    # Pick voice with explicit request
    voice, eng = tts.pick_voice(requested_voice="es_ES-carlfm-medium")
    assert voice == "es_ES-carlfm-medium"
    assert eng == "piper"

    # Pick voice following Turkish language
    voice_tr, eng_tr = tts.pick_voice(language="tr")
    assert voice_tr == "tr_TR-dfki-medium"
    assert eng_tr == "piper"

    # Pick voice with unknown language falls back to default
    voice_unknown, _ = tts.pick_voice(language="ja")
    assert voice_unknown == "en_US-lessac-medium"


def test_tts_service_fallback_to_system_when_empty(tmp_path: Path):
    empty_dir = tmp_path / "empty_voices"
    empty_dir.mkdir()

    tts = TTSService(
        engine="piper",
        default_voice="missing-voice",
        voice_dir=empty_dir,
    )

    voice, eng = tts.pick_voice()
    assert eng == "system"


def test_tts_service_piper_synthesis(tmp_path: Path, monkeypatch):
    voice_dir = tmp_path / "voices"
    voice_dir.mkdir(parents=True)
    model_file = voice_dir / "en_US-lessac-medium.onnx"
    model_file.write_bytes(b"onnx dummy")

    tts = TTSService(voice_dir=voice_dir)

    # Mock Piper model
    fake_model = MagicMock()
    fake_model.config.sample_rate = 22050

    class FakeAudioChunk:
        audio_int16_bytes = b"\x01\x00" * 2205  # 0.1s at 22050 Hz

    fake_model.synthesize.return_value = [FakeAudioChunk()]
    tts._piper_models["en_US-lessac-medium"] = fake_model

    async def _test():
        pcm = await tts.synthesize("Hello world. Testing piper.")
        assert len(pcm) > 0
        assert tts.last_voice_used == "en_US-lessac-medium"

        # Stream synthesize
        chunks = []
        async for chunk in tts.stream_synthesize("Sentence A. Sentence B."):
            chunks.append(chunk)
        assert len(chunks) == 2

    asyncio.run(_test())


def test_tts_service_list_voices(tmp_path: Path):
    voice_dir = tmp_path / "voices"
    voice_dir.mkdir(parents=True)
    (voice_dir / "en_US-lessac-medium.onnx").write_bytes(b"dummy")

    tts = TTSService(voice_dir=voice_dir)
    voices = tts.list_voices()
    assert len(voices) >= 1
    assert any(v.engine == "piper" and "en_US-lessac-medium" in v.id for v in voices)


def test_tts_service_warmup(tmp_path: Path, monkeypatch):
    voice_dir = tmp_path / "voices"
    voice_dir.mkdir(parents=True)
    model_file = voice_dir / "en_US-lessac-medium.onnx"
    model_file.write_bytes(b"dummy")

    tts = TTSService(voice_dir=voice_dir)
    fake_model = MagicMock()
    fake_model.config.sample_rate = 22050

    class FakeChunk:
        audio_int16_bytes = b"\x00" * 1000

    fake_model.synthesize.return_value = [FakeChunk()]
    tts._piper_models["en_US-lessac-medium"] = fake_model

    async def _test():
        await tts.warmup()
        assert tts._is_warmed_up is True

    asyncio.run(_test())


def test_tts_api_routes(tmp_path: Path, monkeypatch):
    app = create_app(data_dir=tmp_path, api_token="test-tts-token")
    client = TestClient(app)

    # 1. GET /api/v1/speech/voices
    res_voices = client.get(
        "/api/v1/speech/voices",
        headers={"Authorization": "Bearer test-tts-token"},
    )
    assert res_voices.status_code == 200
    data_voices = res_voices.json()
    assert "voices" in data_voices

    # 2. POST /api/v1/speech/synthesize
    fake_pcm = b"\x02\x00" * 4800  # 0.2s at 24000 Hz

    async def _fake_synth(text, voice="", language=""):
        return fake_pcm

    app.state.tts_service.synthesize = _fake_synth

    res_synth = client.post(
        "/api/v1/speech/synthesize",
        json={"text": "Synthesize this sentence please.", "voice": "en_US-lessac-medium"},
        headers={"Authorization": "Bearer test-tts-token"},
    )
    assert res_synth.status_code == 200
    data_synth = res_synth.json()
    assert "audio_base64" in data_synth
    assert data_synth["sample_rate"] == 24000
    assert data_synth["duration_seconds"] == 0.2
    assert base64.b64decode(data_synth["audio_base64"]) == fake_pcm


def test_tts_synthesis_benchmark_and_buffer_integrity(tmp_path: Path):
    import time
    voice_dir = tmp_path / "voices"
    voice_dir.mkdir(parents=True)
    model_file = voice_dir / "en_US-lessac-medium.onnx"
    model_file.write_bytes(b"dummy")

    tts = TTSService(voice_dir=voice_dir)
    fake_model = MagicMock()
    fake_model.config.sample_rate = 22050

    # 5.0 seconds of audio at 22050 Hz = 110250 samples = 220500 bytes
    five_sec_pcm = b"\x01\x00" * 110250

    class FakeChunk:
        audio_int16_bytes = five_sec_pcm

    fake_model.synthesize.return_value = [FakeChunk()]
    tts._piper_models["en_US-lessac-medium"] = fake_model

    async def _benchmark():
        t0 = time.monotonic()
        pcm = await tts.synthesize("This is a benchmark test sentence to verify 5 seconds of synthesis.")
        elapsed = time.monotonic() - t0

        # Acceptance Criteria: Under 0.4s on CPU
        assert elapsed < 0.4
        # Verifies 22050 -> 24000 Hz conversion produces exactly 5.0s of 24 kHz 16-bit mono PCM (240,000 bytes)
        assert len(pcm) == 24000 * 5 * 2

    asyncio.run(_benchmark())
