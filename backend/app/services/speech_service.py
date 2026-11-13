"""
Speech Recognition Service (TASK-P4-01 / CAT-08).

High-performance, CPU-based local speech recognition using faster-whisper (CTranslate2)
with automatic per-turn language detection, kernel pre-warming, and hosted transcription API fallback.
"""

from __future__ import annotations

import asyncio
import io
from importlib.util import find_spec
import logging
import os
import time
import wave
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

MIC_RATE = 16_000
SPEAKER_RATE = 24_000
SAMPLE_WIDTH = 2  # 16-bit signed little-endian
CHANNELS = 1

SUPPORTED_WHISPER_MODELS = (
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
    "large-v3-turbo",
)
DEFAULT_WHISPER_MODEL = "base"


def _threads() -> int:
    """Calculate CPU thread allocation to prevent audio and UI thread starvation."""
    try:
        n = os.cpu_count() or 4
    except Exception:
        n = 4
    return max(1, min(8, n // 2))


def to_float32(pcm: bytes) -> np.ndarray:
    """Convert 16-bit PCM bytes to normalized float32 array in [-1.0, 1.0]."""
    if not pcm:
        return np.zeros(0, dtype=np.float32)
    if len(pcm) % 2:
        pcm = pcm[:-1]
    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0


def to_pcm16(samples: Union[np.ndarray, List[float]]) -> bytes:
    """Convert float32 samples to 16-bit PCM, clipped to avoid wrap-around distortion."""
    arr = np.asarray(samples, dtype=np.float32)
    return (np.clip(arr, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


def resample(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    """Resample 16-bit PCM from src_rate to dst_rate using linear interpolation."""
    if src_rate == dst_rate or not pcm:
        return pcm
    src = to_float32(pcm)
    if src.size == 0:
        return b""
    n_out = int(round(src.size * (dst_rate / float(src_rate))))
    if n_out <= 0:
        return b""
    idx = np.linspace(0, src.size, num=n_out, endpoint=False)
    return to_pcm16(np.interp(idx, np.arange(src.size), src))


def to_wav(pcm: bytes, rate: int = MIC_RATE, channels: int = CHANNELS) -> bytes:
    """Package raw 16-bit PCM into a standard in-memory WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def to_mono(pcm: bytes, channels: int) -> bytes:
    """Average interleaved multi-channel PCM down to mono."""
    if channels <= 1 or not pcm:
        return pcm
    arr = to_float32(pcm)
    usable = (arr.size // channels) * channels
    return to_pcm16(arr[:usable].reshape(-1, channels).mean(axis=1))


def wav_to_pcm(data: bytes, want_rate: int = SPEAKER_RATE) -> bytes:
    """Convert arbitrary WAV bytes to mono 16-bit PCM at want_rate."""
    if not data:
        return b""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            channels = w.getnchannels()
            width = w.getsampwidth()
            rate = w.getframerate()
            frames = w.readframes(w.getnframes())
    except Exception:
        # Fallback salvage if WAV header is non-standard
        return b""

    if width == 1:
        arr = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        frames = to_pcm16(arr)
    elif width == 4:
        arr = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
        frames = to_pcm16(arr)

    if channels > 1:
        frames = to_mono(frames, channels)
    return resample(frames, rate, want_rate)


def duration_s(pcm: bytes, rate: int = MIC_RATE, channels: int = CHANNELS) -> float:
    """Calculate duration of 16-bit PCM in seconds."""
    bytes_per_sec = rate * channels * SAMPLE_WIDTH
    return len(pcm) / bytes_per_sec if bytes_per_sec > 0 else 0.0


class SpeechRecognitionResult(BaseModel):
    """Structured transcription output with per-turn language identification."""
    model_config = ConfigDict(extra="forbid")

    text: str
    language: str
    language_probability: float
    duration_seconds: float
    segments: List[Dict[str, Any]] = Field(default_factory=list)


class SpeechService:
    """Speech recognition service managing local faster-whisper and cloud API fallback."""

    # Language hysteresis thresholds
    _LANG_MIN_CONFIDENCE = 0.65
    _LANG_MIN_CHARS = 12

    def __init__(
        self,
        backend: str = "local",
        model: str = DEFAULT_WHISPER_MODEL,
        device: str = "cpu",
        language: str = "",
        base_url: str = "",
        api_key: str = "",
        download_root: Optional[str] = None,
    ) -> None:
        self.backend = backend.strip().lower()
        self.model_name = model.strip() or DEFAULT_WHISPER_MODEL
        self.device = device.strip().lower() or "cpu"
        self.language = language.strip()
        self.base_url = base_url.strip()
        self.api_key = api_key.strip()
        self.download_root = download_root.strip() if download_root else None

        self._model = None
        self._load_lock = asyncio.Lock()
        self.detected_language: str = ""
        self._is_warmed_up: bool = False

    def _compute_type(self) -> str:
        """Select optimal computation precision: int8 for CPU, float16 for CUDA."""
        return "float16" if self.device.startswith("cuda") else "int8"

    def _load_blocking(self) -> Any:
        from faster_whisper import WhisperModel
        logger.info(
            "Loading Whisper model '%s' (device: %s, compute: %s, threads: %d)",
            self.model_name,
            self.device,
            self._compute_type(),
            _threads(),
        )
        return WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self._compute_type(),
            cpu_threads=_threads(),
            download_root=self.download_root,
        )

    async def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        async with self._load_lock:
            if self._model is not None:
                return self._model
            if find_spec("faster_whisper") is None:
                raise RuntimeError(
                    "faster-whisper is not installed. Install with: pip install faster-whisper"
                )
            self._model = await asyncio.to_thread(self._load_blocking)
            return self._model

    def _accept_language(self, code: str, confidence: float, text: str) -> None:
        """Update language following confident evidence, resisting noise jitter."""
        code = code.strip().lower()
        if not code:
            return
        if not self.detected_language:
            self.detected_language = code
            return
        if code == self.detected_language:
            return
        if confidence >= self._LANG_MIN_CONFIDENCE and len(text) >= self._LANG_MIN_CHARS:
            logger.info(
                "STT language switched: %s -> %s (conf: %.1f%%, chars: %d)",
                self.detected_language,
                code,
                confidence * 100,
                len(text),
            )
            self.detected_language = code
        else:
            logger.debug(
                "STT keeping language '%s'; ignoring candidate '%s' (conf: %.1f%%, chars: %d)",
                self.detected_language,
                code,
                confidence * 100,
                len(text),
            )

    def _transcribe_blocking(
        self, samples: np.ndarray
    ) -> Tuple[str, str, float, List[Dict[str, Any]]]:
        """Execute blocking Whisper transcription on worker thread."""
        segments_gen, info = self._model.transcribe(
            samples,
            language=self.language or None,
            beam_size=1,                         # Fast greedy decoding for voice commands
            vad_filter=True,                     # Drop silence at boundaries
            condition_on_previous_text=False,    # Avoid error chaining
        )

        segment_records: List[Dict[str, Any]] = []
        text_parts: List[str] = []
        for s in segments_gen:
            clean = s.text.strip()
            if clean:
                text_parts.append(clean)
                segment_records.append(
                    {
                        "start": getattr(s, "start", 0.0),
                        "end": getattr(s, "end", 0.0),
                        "text": clean,
                    }
                )

        full_text = " ".join(text_parts).strip()
        lang = str(getattr(info, "language", "") or "")
        prob = float(getattr(info, "language_probability", 0.0) or 0.0)
        self._accept_language(lang, prob, full_text)
        return full_text, lang, prob, segment_records

    def _api_blocking(
        self, pcm: bytes, sample_rate: int
    ) -> Tuple[str, str, float, List[Dict[str, Any]]]:
        """Execute remote /v1/audio/transcriptions HTTP request."""
        import httpx

        base = self.base_url.rstrip("/")
        wav = to_wav(pcm, rate=sample_rate)
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        data = {"model": self.model_name, "response_format": "json"}
        if self.language:
            data["language"] = self.language

        with httpx.Client(timeout=60.0) as client:
            res = client.post(
                f"{base}/audio/transcriptions",
                headers=headers,
                data=data,
                files={"file": ("speech.wav", wav, "audio/wav")},
            )
            if res.status_code >= 400:
                raise RuntimeError(f"Transcription API failed ({res.status_code}): {res.text[:200]}")
            payload = res.json()

        text = (payload.get("text") or "").strip()
        lang = str(payload.get("language") or self.language or "en")
        self._accept_language(lang, 1.0, text)
        return text, lang, 1.0, [{"start": 0.0, "end": duration_s(pcm, sample_rate), "text": text}]

    async def transcribe(
        self,
        pcm: bytes,
        sample_rate: int = MIC_RATE,
        language: str = "",
    ) -> SpeechRecognitionResult:
        """Transcribe 16-bit PCM audio to text with language detection."""
        dur = duration_s(pcm, sample_rate)
        if not pcm or dur < 0.25:
            # Drop audio shorter than 0.25s to prevent Whisper silence hallucination
            return SpeechRecognitionResult(
                text="",
                language=self.detected_language or "en",
                language_probability=0.0,
                duration_seconds=dur,
                segments=[],
            )

        if language:
            self.language = language

        if self.backend == "api":
            text, lang, prob, segs = await asyncio.to_thread(self._api_blocking, pcm, sample_rate)
            return SpeechRecognitionResult(
                text=text,
                language=lang,
                language_probability=prob,
                duration_seconds=dur,
                segments=segs,
            )

        await self._ensure_model()
        # Whisper requires 16 kHz mono float32
        resampled_pcm = resample(pcm, sample_rate, 16_000)
        samples = to_float32(resampled_pcm)

        text, lang, prob, segs = await asyncio.to_thread(self._transcribe_blocking, samples)
        return SpeechRecognitionResult(
            text=text,
            language=lang,
            language_probability=prob,
            duration_seconds=dur,
            segments=segs,
        )

    async def warmup(self) -> None:
        """Pre-warm CTranslate2 Whisper kernels with 100ms silent audio."""
        if self.backend != "local" or self._is_warmed_up:
            return
        try:
            await self._ensure_model()
            t0 = time.monotonic()
            silence_pcm = b"\x00" * 3200  # 0.1s at 16 kHz (16-bit mono = 3200 bytes)
            silence_samples = to_float32(silence_pcm)
            await asyncio.to_thread(self._transcribe_blocking, silence_samples)
            self._is_warmed_up = True
            logger.info("Speech recognition pre-warmed in %.2fs", time.monotonic() - t0)
        except Exception as exc:
            logger.warning("Speech recognition warmup failed: %s", exc)

    def probe(self) -> Tuple[bool, str]:
        """Probe provider availability."""
        if self.backend == "api":
            if not self.base_url:
                return False, "No transcription API base_url configured."
            return True, f"API transcription ready ({self.base_url})"

        if find_spec("faster_whisper") is None:
            return False, "faster-whisper is not installed."
        return (
            True,
            f"faster-whisper {self.model_name} on {self.device} ({self._compute_type()}, {_threads()} threads)",
        )

