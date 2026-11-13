"""
ElevenLabs Multilingual Streaming TTS Service (TASK-GAP-08 / GAP-08).

Cloud-based neural speech synthesis with automatic language following:
- Ultra-low latency multilingual synthesis (eleven_flash_v2_5, eleven_turbo_v2_5)
- Automated format negotiation (direct pcm_24000 with mp3_44100_128 fallback)
- Real-time sentence chunk streaming via async iterators
- Dynamic voice catalogue query and account probing
- Full Five-Word Outcome Contract adherence (done, failed, unverified)
"""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
import json
import logging
import os
from pathlib import Path
import tempfile
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union

import httpx

from app.actions.base import ActionOutcomeResponse, done, failed, unverified
from app.schemas.elevenlabs import ElevenLabsSynthesizeParameters
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

API_BASE = "https://api.elevenlabs.io/v1"

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
DEFAULT_MODEL = "eleven_flash_v2_5"
MODELS = (
    "eleven_flash_v2_5",       # Fastest, low latency multilingual
    "eleven_turbo_v2_5",       # Richer, quick
    "eleven_multilingual_v2",  # Highest quality
)

PCM_FORMAT = "pcm_24000"
MP3_FORMAT = "mp3_44100_128"


def parse_elevenlabs_error(body: str) -> str:
    """Extract human-readable error reason from ElevenLabs error JSON."""
    try:
        obj = json.loads(body)
        detail = obj.get("detail", obj)
        if isinstance(detail, dict):
            return str(detail.get("message", detail))
        return str(detail)
    except Exception:
        return body[:300]


class ElevenLabsService:
    """Service providing streaming and batch neural speech synthesis via ElevenLabs API."""

    def __init__(
        self,
        settings_service: Optional[SettingsService] = None,
        api_key: Optional[str] = None,
        default_voice_id: str = DEFAULT_VOICE_ID,
        default_model: str = DEFAULT_MODEL,
    ) -> None:
        self._settings = settings_service
        self._explicit_key = api_key
        self.default_voice_id = default_voice_id or DEFAULT_VOICE_ID
        self.default_model = default_model or DEFAULT_MODEL
        self._negotiated_format: Optional[str] = None

    def get_api_key(self) -> Optional[str]:
        """Resolve ElevenLabs API key from explicit config, environment, or settings."""
        if self._explicit_key:
            return self._explicit_key.strip()
        env_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
        if env_key:
            return env_key
        if self._settings:
            # Check if stored in settings
            key = self._settings.get_api_key_for_service()
            if key and key.startswith("xi-") or len(key or "") == 32:
                return key
        return None

    def _headers(self, key: str) -> Dict[str, str]:
        return {
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

    def _payload(
        self,
        text: str,
        model_id: str,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> Dict[str, Any]:
        return {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": max(0.0, min(1.0, float(stability))),
                "similarity_boost": max(0.0, min(1.0, float(similarity_boost))),
            },
        }

    async def stream_synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        output_format: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """Stream synthesized audio chunks asynchronously."""
        key = self.get_api_key()
        if not key:
            raise RuntimeError("ElevenLabs API key is not configured.")

        text = text.strip()
        if not text:
            return

        voice = voice_id or self.default_voice_id
        model = model_id or self.default_model
        requested_format = output_format or self._negotiated_format or PCM_FORMAT

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                async for chunk in self._stream_request(client, key, text, voice, model, stability, similarity_boost, requested_format):
                    yield chunk
                self._negotiated_format = requested_format
                return
            except httpx.HTTPStatusError as exc:
                # If tier restricts PCM (400/401/422), fallback to MP3
                if requested_format == PCM_FORMAT and exc.response.status_code in (400, 401, 422):
                    logger.info("ElevenLabs PCM format not permitted for current tier; falling back to MP3.")
                    self._negotiated_format = MP3_FORMAT
                else:
                    err_msg = parse_elevenlabs_error(exc.response.text)
                    raise RuntimeError(f"ElevenLabs error ({exc.response.status_code}): {err_msg}") from exc

            # Retry with MP3 fallback
            async for chunk in self._stream_request(client, key, text, voice, model, stability, similarity_boost, MP3_FORMAT):
                yield chunk

    async def _stream_request(
        self,
        client: httpx.AsyncClient,
        key: str,
        text: str,
        voice_id: str,
        model_id: str,
        stability: float,
        similarity_boost: float,
        fmt: str,
    ) -> AsyncIterator[bytes]:
        url = f"{API_BASE}/text-to-speech/{voice_id}/stream"
        payload = self._payload(text, model_id, stability, similarity_boost)
        headers = self._headers(key)
        params = {"output_format": fmt}

        async with client.stream("POST", url, headers=headers, params=params, json=payload) as resp:
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", "replace")
                raise httpx.HTTPStatusError(
                    message=f"HTTP {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            async for piece in resp.aiter_bytes():
                if piece:
                    yield piece

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        output_format: Optional[str] = None,
    ) -> bytes:
        """Batch synthesize text and return complete audio bytes."""
        chunks: List[bytes] = []
        async for piece in self.stream_synthesize(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            stability=stability,
            similarity_boost=similarity_boost,
            output_format=output_format,
        ):
            chunks.append(piece)
        return b"".join(chunks)

    def list_voices(self) -> List[Dict[str, Any]]:
        """Fetch available voice catalogue from the user's ElevenLabs account."""
        key = self.get_api_key()
        if not key:
            raise RuntimeError("ElevenLabs API key is not configured.")

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{API_BASE}/voices", headers={"xi-api-key": key})
            if resp.status_code >= 400:
                err_msg = parse_elevenlabs_error(resp.text)
                raise RuntimeError(f"Failed fetching ElevenLabs voices ({resp.status_code}): {err_msg}")
            return resp.json().get("voices", [])

    def probe(self) -> Tuple[bool, str]:
        """Test API connectivity and key validity."""
        key = self.get_api_key()
        if not key:
            return False, "No ElevenLabs API key is configured."
        try:
            voices = self.list_voices()
            names = ", ".join(v.get("name", "") for v in voices[:4])
            return True, f"ElevenLabs connected. {len(voices)} voices available: {names}..."
        except Exception as exc:
            return False, str(exc)

    def execute(self, params: ElevenLabsSynthesizeParameters) -> ActionOutcomeResponse:
        """Execute a speech synthesis request adhering to the Five-Word Outcome Contract."""
        text = params.text.strip()
        if not text:
            return failed("elevenlabs.synthesize", error="Empty text", message="Text to synthesize cannot be empty.")

        key = self.get_api_key()
        if not key:
            return failed(
                "elevenlabs.synthesize",
                error="Missing API key",
                message="ElevenLabs API key is not configured. Set ELEVENLABS_API_KEY or configure in Settings.",
            )

        try:
            audio_bytes = asyncio.run(
                self.synthesize(
                    text=text,
                    voice_id=params.voice_id,
                    model_id=params.model_id,
                    stability=params.stability,
                    similarity_boost=params.similarity_boost,
                    output_format=params.output_format,
                )
            )

            if not audio_bytes:
                return failed("elevenlabs.synthesize", error="Empty audio output", message="Synthesis returned no audio bytes.")

            saved_path: Optional[str] = None
            if params.save_to_disk or params.output_path:
                ext = ".mp3" if self._negotiated_format == MP3_FORMAT else ".pcm"
                path = Path(params.output_path).expanduser().resolve() if params.output_path else Path(tempfile.gettempdir()) / f"elevenlabs_{int(time.time())}{ext}"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(audio_bytes)
                saved_path = str(path)

            dest_info = f" saved to {saved_path}" if saved_path else ""
            return done(
                "elevenlabs.synthesize",
                f"Synthesized {len(text)} characters of speech with ElevenLabs ({self._negotiated_format or PCM_FORMAT}){dest_info}.",
                data={
                    "voice_id": params.voice_id or self.default_voice_id,
                    "model_id": params.model_id or self.default_model,
                    "format": self._negotiated_format or PCM_FORMAT,
                    "size_bytes": len(audio_bytes),
                    "saved_to": saved_path,
                },
            )
        except Exception as exc:
            logger.exception("ElevenLabs synthesis error")
            return failed("elevenlabs.synthesize", error=str(exc), message=f"ElevenLabs synthesis failed: {exc}")

