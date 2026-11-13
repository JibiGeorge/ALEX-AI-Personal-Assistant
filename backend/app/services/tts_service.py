"""
Text-to-Speech (TTS) Service (TASK-P4-02 / CAT-09).

Unified neural and system speech synthesis engine:
- Neural Synthesis: Piper TTS (local, 50+ languages, 15x real-time on CPU)
- Native System Fallback: Windows SAPI5, macOS `say`, Linux `espeak-ng`
- Automatic Language Following: Tracks preceding speech turn language
- Punctuation Chunking: Sentence-by-sentence streaming for low-latency playback
- Sample Rate Standardization: Converts all outputs to 24 kHz mono 16-bit PCM
"""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
import logging
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from app.services.adapters.system_tts_adapter import (
    SystemTTSAdapter,
    list_system_voices,
    split_sentences,
)
from app.services.speech_service import SPEAKER_RATE, resample

logger = logging.getLogger(__name__)

DEFAULT_PIPER_VOICE = "en_US-lessac-medium"


def _default_voice_dir() -> Path:
    """Determine writable directory for Piper neural voice models."""
    try:
        custom = os.environ.get("PIPER_VOICE_DIR", "").strip()
        if custom:
            p = Path(custom).expanduser().resolve()
            p.mkdir(parents=True, exist_ok=True)
            return p

        app_data = os.environ.get("ALEX_DATA_DIR", "").strip()
        if app_data:
            base = Path(app_data).expanduser().resolve()
        else:
            base = Path.home() / ".alex"

        target = base / "piper-voices"
        target.mkdir(parents=True, exist_ok=True)
        return target
    except (PermissionError, OSError, Exception):
        fallback = Path(tempfile.gettempdir()) / "alex_piper_voices"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


class VoiceDescriptor(BaseModel):
    """Metadata describing a downloadable or available speech synthesis voice."""
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    language: str
    engine: str  # "piper" | "system"
    sample_rate: int = 24000
    is_installed: bool = False


class TTSService:
    """Unified Text-to-Speech service with Piper neural synthesis and system fallback."""

    def __init__(
        self,
        engine: str = "piper",
        default_voice: str = DEFAULT_PIPER_VOICE,
        voice_dir: Optional[Union[str, Path]] = None,
        speed: float = 1.0,
        follow_language: bool = True,
    ) -> None:
        self.engine = engine.strip().lower() or "piper"
        self.default_voice = default_voice.strip() or DEFAULT_PIPER_VOICE
        self.voice_dir = Path(voice_dir).expanduser().resolve() if voice_dir else _default_voice_dir()
        self.speed = max(0.5, min(2.0, float(speed)))
        self.follow_language = follow_language

        self._piper_models: Dict[str, Any] = {}
        self._piper_lock = threading.Lock()
        self._system_adapter = SystemTTSAdapter()
        self._is_warmed_up: bool = False
        self.last_voice_used: str = ""

    def installed_piper_voices(self) -> List[str]:
        """List voice names with corresponding .onnx models on disk."""
        try:
            return sorted(p.stem for p in self.voice_dir.glob("*.onnx"))
        except Exception:
            return []

    def language_of(self, voice_name: str) -> str:
        """Extract language code from voice name (e.g. 'en_US-lessac-medium' -> 'en')."""
        if not voice_name:
            return "en"
        parts = voice_name.split("_")
        return parts[0].lower() if parts else "en"

    def pick_voice(self, requested_voice: str = "", language: str = "") -> Tuple[str, str]:
        """Select appropriate voice and engine for current turn.

        Returns: (voice_id, engine_name)
        """
        # If system engine forced:
        if self.engine == "system":
            return requested_voice or self.default_voice, "system"

        installed = self.installed_piper_voices()

        # Specific requested voice
        if requested_voice and requested_voice in installed:
            return requested_voice, "piper"

        # Language following
        if self.follow_language and language:
            clean_lang = language.split("-")[0].split("_")[0].lower()
            for v in installed:
                if self.language_of(v) == clean_lang:
                    return v, "piper"

        # Default configured voice
        if self.default_voice in installed:
            return self.default_voice, "piper"

        # Any installed Piper voice
        if installed:
            return installed[0], "piper"

        # Fallback to system voice if no Piper model installed
        return requested_voice or "", "system"

    def _load_piper_model(self, voice_name: str) -> Optional[Any]:
        """Load PiperVoice model from disk into cache."""
        with self._piper_lock:
            if voice_name in self._piper_models:
                return self._piper_models[voice_name]

        if find_spec("piper") is None:
            return None

        model_path = self.voice_dir / f"{voice_name}.onnx"
        if not model_path.exists():
            return None

        try:
            from piper import PiperVoice
            loaded = PiperVoice.load(model_path)
            with self._piper_lock:
                self._piper_models[voice_name] = loaded
            return loaded
        except Exception as exc:
            logger.warning("Failed loading Piper model %s: %s", voice_name, exc)
            return None

    def _synth_piper_sentence(self, model: Any, sentence: str) -> bytes:
        """Synthesize a single sentence chunk via Piper into 24 kHz PCM."""
        if not sentence.strip():
            return b""
        try:
            from piper import SynthesisConfig
            cfg = None
            if abs(self.speed - 1.0) > 0.02:
                # Piper length_scale is inverse of speed
                cfg = SynthesisConfig(length_scale=1.0 / self.speed)

            chunks = []
            for chunk in (model.synthesize(sentence, cfg) if cfg else model.synthesize(sentence)):
                chunks.append(chunk.audio_int16_bytes)

            raw_pcm = b"".join(chunks)
            model_rate = int(getattr(model.config, "sample_rate", 22050))
            return resample(raw_pcm, model_rate, SPEAKER_RATE)
        except Exception as exc:
            logger.warning("Piper sentence synthesis failed: %s", exc)
            return b""

    async def synthesize(
        self,
        text: str,
        voice: str = "",
        language: str = "",
    ) -> bytes:
        """Synthesize text into full 24 kHz mono 16-bit PCM bytes."""
        text = text.strip()
        if not text:
            return b""

        chosen_voice, chosen_engine = self.pick_voice(voice, language)
        self.last_voice_used = chosen_voice or "default"

        if chosen_engine == "piper":
            model = await asyncio.to_thread(self._load_piper_model, chosen_voice)
            if model is not None:
                sentences = split_sentences(text)
                pcm_parts: List[bytes] = []
                for s in sentences:
                    part = await asyncio.to_thread(self._synth_piper_sentence, model, s)
                    if part:
                        pcm_parts.append(part)
                return b"".join(pcm_parts)

        # Fallback to system TTS adapter
        return await self._system_adapter.speak(text, voice=chosen_voice)

    async def stream_synthesize(
        self,
        text: str,
        voice: str = "",
        language: str = "",
    ) -> AsyncIterator[bytes]:
        """Stream synthesized 24 kHz mono PCM chunks sentence by sentence."""
        text = text.strip()
        if not text:
            return

        chosen_voice, chosen_engine = self.pick_voice(voice, language)
        self.last_voice_used = chosen_voice or "default"

        if chosen_engine == "piper":
            model = await asyncio.to_thread(self._load_piper_model, chosen_voice)
            if model is not None:
                for sentence in split_sentences(text):
                    part = await asyncio.to_thread(self._synth_piper_sentence, model, sentence)
                    if part:
                        yield part
                return

        # Fallback to streaming system TTS
        async for chunk in self._system_adapter.stream_speak(text, voice=chosen_voice):
            yield chunk

    def list_voices(self) -> List[VoiceDescriptor]:
        """List all available Piper voices and installed OS system voices."""
        descriptors: List[VoiceDescriptor] = []

        # Installed Piper voices
        for name in self.installed_piper_voices():
            descriptors.append(
                VoiceDescriptor(
                    id=name,
                    name=f"Piper: {name}",
                    language=self.language_of(name),
                    engine="piper",
                    sample_rate=22050,
                    is_installed=True,
                )
            )

        # System voices
        for sys_v in list_system_voices():
            descriptors.append(
                VoiceDescriptor(
                    id=sys_v,
                    name=f"System: {sys_v}",
                    language="system",
                    engine="system",
                    sample_rate=24000,
                    is_installed=True,
                )
            )
        return descriptors

    async def warmup(self, voice: str = "") -> None:
        """Pre-warm TTS engine to eliminate first-sentence synthesis latency."""
        if self._is_warmed_up:
            return

        chosen_voice, chosen_engine = self.pick_voice(voice)
        t0 = time.monotonic()
        if chosen_engine == "piper":
            model = await asyncio.to_thread(self._load_piper_model, chosen_voice)
            if model is not None:
                await asyncio.to_thread(self._synth_piper_sentence, model, "ok")
                self._is_warmed_up = True
                logger.info("Piper TTS warmed up with %s in %.2fs", chosen_voice, time.monotonic() - t0)
                return

        # Fallback warmup on system adapter
        await asyncio.to_thread(self._system_adapter.synth_sentence_blocking, "ok")
        self._is_warmed_up = True
        logger.info("System TTS warmed up in %.2fs", time.monotonic() - t0)

    def probe(self) -> Tuple[bool, str]:
        """Probe overall TTS health and available voices."""
        installed = self.installed_piper_voices()
        sys_ok, sys_msg = self._system_adapter.probe()

        if installed:
            return True, f"Piper neural TTS ready ({len(installed)} models on disk, system fallback active)"
        if sys_ok:
            return True, f"System TTS ready (Piper has 0 models on disk; {sys_msg})"
        return False, "No speech synthesis engine available"
