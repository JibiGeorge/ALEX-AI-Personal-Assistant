"""
Unified Gemini Model Gateway & Dynamic Fallback Ladder.

Adapted from MARK-LVI architecture to provide a single, hardened entrypoint
for all Gemini REST and Live one-shot generations across ALEX-AI.

Key capabilities ported from MARK-LVI:
1. Unified Ladder: FAST, SMART, SEARCH, LIVE ladders with tested model order.
2. Quota Isolation: Uses throwaway Live WebSocket turns first to preserve free-tier
   REST text quotas, falling back to REST models seamlessly.
3. Bounded Concurrency: Limits one-shot Live sessions to 3 concurrent slots to protect
   the primary user voice conversation.
4. Enforced Timeouts: Guaranteed >= 10,000ms timeout boundary required by the Google GenAI SDK.
5. Error Classification & Cooldown:
   - 429 / RESOURCE_EXHAUSTED -> 300s cooldown
   - 404 / GONE / NOT FOUND -> 6h quarantine
   - 503 / 504 / UNAVAILABLE / TIMEOUT -> 30m cooldown
6. Safe Parsers: text() with defaults and as_json() tolerating markdown code fences.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Ladders, tried left to right
FAST = "fast"      # short classification, extraction, one-line decisions
SMART = "smart"    # reasoning, generation, long documents, images
SEARCH = "search"  # grounded search — REST only
LIVE = "live"

# Model hierarchies measured and verified
_LADDERS: dict[str, tuple[str, ...]] = {
    FAST: (
        LIVE,
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-2.5-flash",
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "gemini-3-flash-preview",
    ),
    SMART: (
        LIVE,
        "gemini-2.5-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
        "gemini-3-flash-preview",
        "gemini-flash-latest",
    ),
    # Grounded search needs response.candidates[...].grounding_metadata, which a
    # Live turn does not produce. REST only.
    SEARCH: (
        "gemini-2.5-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-flash-latest",
    ),
}

LIVE_MODELS: tuple[str, ...] = (
    "models/gemini-3.1-flash-live-preview",
    "models/gemini-2.5-flash-native-audio-preview-12-2025",
)

_LIVE_FALLBACK = "models/gemini-3.1-flash-live-preview"

# Concurrency semaphore for throwaway Live sessions (preserves slots for user conversation)
_LIVE_SLOTS = threading.BoundedSemaphore(3)
_LIVE_SLOT_WAIT = 3.0

_ONE_SHOT_SYSTEM = (
    "You are a data-processing function, not an assistant and not in a "
    "conversation. There is no person listening to you. Produce exactly the "
    "output the request asks for and nothing else: no greeting, no "
    "acknowledgement, no 'Understood', no explanation, no closing remark, no "
    "restating of the question. If the request asks for JSON, emit only the "
    "JSON. If it asks for code, emit only the code. If it asks for one word, "
    "emit that one word. Preserve the exact spelling, punctuation, capitals "
    "and whitespace of anything you are asked to copy or return."
)

DEFAULT_TIMEOUT_MS = 10_000
MIN_TIMEOUT_MS = 10_000

_key_lock = threading.Lock()
_cached_key: str | None = None

_COOLDOWN_SECONDS = 300          # 5 minutes for quota (429)
_GONE_SECONDS = 6 * 60 * 60      # 6 hours for missing / permission (404/403)
_UNAVAILABLE_SECONDS = 30 * 60   # 30 minutes for server error / timeout (503/504)

_cooldown: dict[str, float] = {}
_cool_lock = threading.Lock()


def _cool(model: str, seconds: float = _COOLDOWN_SECONDS) -> None:
    with _cool_lock:
        _cooldown[model] = time.monotonic() + seconds


def is_quota_error(err: str) -> bool:
    return "429" in err or "RESOURCE_EXHAUSTED" in err


def is_unavailable_error(err: str) -> bool:
    low = err.lower()
    return (
        "503" in err
        or "504" in err
        or "unavailable" in low
        or "deadline_exceeded" in low
    )


def is_gone_error(err: str) -> bool:
    low = err.lower()
    return (
        "404" in err
        or "not found" in low
        or "is not supported" in low
        or "permission" in low
        or "403" in err
    )


def _cooling(model: str) -> bool:
    with _cool_lock:
        until = _cooldown.get(model, 0.0)
        if until and time.monotonic() < until:
            return True
        _cooldown.pop(model, None)
        return False


def live_model() -> str:
    """The Live model to open conversations with: the first rung that is not resting."""
    for m in LIVE_MODELS:
        if not _cooling(m):
            return m
    return LIVE_MODELS[0]


def note_live_failure(model: str, err: str) -> bool:
    """Record why a Live model failed. Returns True when worth trying the next."""
    if is_quota_error(err):
        _cool(model, _COOLDOWN_SECONDS)
        logger.warning(
            "[Gemini] Live model %s out of quota; cooling for %d minutes",
            model,
            _COOLDOWN_SECONDS // 60,
        )
        return True
    if is_gone_error(err):
        _cool(model, _GONE_SECONDS)
        logger.warning(
            "[Gemini] Live model %s unavailable/unsupported; setting aside for 6h",
            model,
        )
        return True
    return False


def api_key(refresh: bool = False) -> str:
    """The Gemini API key from environment, keyring, config/api_keys.json, or settings storage."""
    global _cached_key
    with _key_lock:
        if _cached_key is not None and not refresh:
            return _cached_key

        try:
            from app.core.api_key_store import resolve_gemini_key
            resolved = resolve_gemini_key()
            if resolved:
                _cached_key = resolved.strip()
                return _cached_key
        except Exception as exc:
            logger.debug("api_key_store resolution failed: %s", exc)

        # Direct fallback for tests or independent imports
        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key and env_key.strip():
            _cached_key = env_key.strip()
            return _cached_key

        _cached_key = ""
        return _cached_key


def client(timeout_ms: int = DEFAULT_TIMEOUT_MS, key: str = ""):
    """Configured genai.Client enforcing the minimum 10,000ms deadline and v1alpha options."""
    from google import genai
    from google.genai import types as gtypes

    resolved_key = key or api_key()
    if not resolved_key:
        raise RuntimeError("No Gemini API key is configured")

    effective_timeout = max(MIN_TIMEOUT_MS, int(timeout_ms))
    return genai.Client(
        api_key=resolved_key,
        http_options=gtypes.HttpOptions(
            api_version="v1alpha",
            timeout=effective_timeout,
        ),
    )


class _Reply:
    """Wraps text output to present a .text attribute matching REST responses."""

    __slots__ = ("text",)

    def __init__(self, text: str):
        self.text = text


def _to_live_parts(contents: Any) -> list[dict[str, Any]]:
    """Convert REST contents into Live WebSocket parts."""
    import base64

    items = contents if isinstance(contents, (list, tuple)) else [contents]
    parts: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, str):
            parts.append({"text": item})
            continue
        blob = getattr(item, "inline_data", None)
        if blob is not None:
            data = getattr(blob, "data", None)
            mime = getattr(blob, "mime_type", None) or "application/octet-stream"
            if isinstance(data, bytes):
                data = base64.b64encode(data).decode("ascii")
            parts.append({"inline_data": {"mime_type": mime, "data": data}})
            continue
        txt = getattr(item, "text", None)
        if txt:
            parts.append({"text": txt})
            continue
        if isinstance(item, dict):
            parts.append(item)
    return parts


def _carries_recording(contents: Any) -> bool:
    """Check if contents hold pre-recorded audio or video (Live only accepts realtime stream)."""
    if isinstance(contents, str):
        return False
    items = contents if isinstance(contents, (list, tuple)) else [contents]
    for item in items:
        if isinstance(item, str):
            continue
        mime = None
        blob = getattr(item, "inline_data", None)
        if blob is not None:
            mime = getattr(blob, "mime_type", None)
        elif isinstance(item, dict):
            inline = item.get("inline_data") or item.get("inlineData")
            if isinstance(inline, dict):
                mime = inline.get("mime_type") or inline.get("mimeType")
        if isinstance(mime, str) and mime.startswith(("audio/", "video/")):
            return True
    return False


async def _live_turn(parts: list[dict[str, Any]], system: str, key: str, timeout_s: float) -> str:
    """Run a single throwaway Live WebSocket turn."""
    from google import genai
    from google.genai import types as gtypes

    cl = genai.Client(api_key=key, http_options={"api_version": "v1beta"})
    kwargs = {
        "response_modalities": ["AUDIO"],
        "output_audio_transcription": {},
        "system_instruction": _ONE_SHOT_SYSTEM + (f"\n\n{system}" if system else ""),
    }

    cm = cl.aio.live.connect(
        model=_LIVE_FALLBACK,
        config=gtypes.LiveConnectConfig(**kwargs),
    )
    session = await asyncio.wait_for(cm.__aenter__(), 30.0)
    try:
        await session.send_client_content(
            turns={"role": "user", "parts": parts}, turn_complete=True
        )
        chunks: list[str] = []

        async def drain():
            async for resp in session.receive():
                sc = getattr(resp, "server_content", None)
                if sc and sc.output_transcription and sc.output_transcription.text:
                    chunks.append(sc.output_transcription.text)

        await asyncio.wait_for(drain(), timeout=timeout_s)
        try:
            await asyncio.wait_for(drain(), timeout=1.5)
        except asyncio.TimeoutError:
            pass
        return "".join(chunks).strip()
    finally:
        try:
            await cm.__aexit__(None, None, None)
        except Exception:
            pass


def _live_call(contents: Any, config: Any, timeout_ms: int, key: str) -> Optional[_Reply]:
    """Execute a throwaway Live session in a dedicated thread to preserve text quota."""
    system = ""
    if config is not None:
        system = getattr(config, "system_instruction", None) or (
            config.get("system_instruction") if isinstance(config, dict) else ""
        ) or ""

    parts = _to_live_parts(contents)
    if not parts:
        return None

    if not _LIVE_SLOTS.acquire(timeout=_LIVE_SLOT_WAIT):
        raise RuntimeError("No free Live slot — leaving slots for primary voice conversation")

    box: dict[str, Any] = {}

    def runner():
        try:
            box["text"] = asyncio.run(
                _live_turn(parts, str(system), key, max(10.0, timeout_ms / 1000.0))
            )
        except BaseException as e:
            box["error"] = e

    try:
        th = threading.Thread(target=runner, daemon=True, name="alex-gemini-live-oneshot")
        th.start()
        th.join(timeout=max(15.0, timeout_ms / 1000.0 + 20.0))
    finally:
        _LIVE_SLOTS.release()

    if "error" in box:
        raise box["error"]

    text_res = box.get("text")
    return _Reply(text_res) if text_res else None


def call(
    contents: Any,
    tier: str = FAST,
    config: Any = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    key: str = "",
) -> Any:
    """Run one generation walking the fallback ladder until a candidate succeeds.

    Returns the response object (with .text, grounding_metadata, etc.).
    """
    ladder = _LADDERS.get(tier)
    if ladder is None:
        ladder = (tier,) + tuple(m for m in _LADDERS[SMART] if m != tier)

    resolved_key = key or api_key()
    if not resolved_key:
        logger.warning("[Gemini] No Gemini API key configured")
        return None

    if _carries_recording(contents):
        ladder = tuple(m for m in ladder if m != LIVE)
        if not ladder:
            logger.warning("[Gemini] Nothing on ladder can process pre-recorded media")
            return None

    cl = None
    tried = [m for m in ladder if not _cooling(m)] or list(ladder)

    for model in tried:
        try:
            if model == LIVE:
                reply = _live_call(contents, config, timeout_ms, resolved_key)
                if reply is not None:
                    return reply
                raise RuntimeError("Live turn returned empty response")

            if cl is None:
                cl = client(timeout_ms=timeout_ms, key=resolved_key)

            kwargs: dict[str, Any] = {"model": model, "contents": contents}
            if config is not None:
                kwargs["config"] = config

            return cl.models.generate_content(**kwargs)
        except Exception as e:
            msg = str(e)
            if is_quota_error(msg):
                _cool(model)
                logger.warning(
                    "[Gemini] %s out of quota; skipping for %d min",
                    model,
                    _COOLDOWN_SECONDS // 60,
                )
            elif is_gone_error(msg):
                _cool(model, _GONE_SECONDS)
                logger.warning(
                    "[Gemini] %s unavailable to key; setting aside for 6h",
                    model,
                )
            elif is_unavailable_error(msg):
                _cool(model, _UNAVAILABLE_SECONDS)
                logger.warning(
                    "[Gemini] %s not answering; resting for %d min",
                    model,
                    _UNAVAILABLE_SECONDS // 60,
                )
            else:
                logger.warning("[Gemini] %s error: %s: %s", model, type(e).__name__, msg[:140])

    return None


def text(
    contents: Any,
    tier: str = FAST,
    config: Any = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    key: str = "",
    default: str = "",
) -> str:
    """Generate content and return the reply string stripped, or `default` on failure."""
    resp = call(contents, tier=tier, config=config, timeout_ms=timeout_ms, key=key)
    if resp is None:
        return default
    return (getattr(resp, "text", None) or "").strip() or default


def parse_json(raw: str, default: Any = None) -> Any:
    """Extract and parse JSON cleanly from raw text, tolerating markdown fences and prose."""
    if not raw:
        return default
    cleaned = raw.strip()
    if "{" in cleaned and "}" in cleaned:
        cleaned = cleaned[cleaned.find("{"): cleaned.rfind("}") + 1]
    elif "[" in cleaned and "]" in cleaned:
        cleaned = cleaned[cleaned.find("["): cleaned.rfind("]") + 1]
    try:
        return json.loads(cleaned)
    except Exception as exc:
        logger.warning("[Gemini] Response was not valid JSON: %s", exc)
        return default


def as_json(
    contents: Any,
    tier: str = FAST,
    config: Any = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    key: str = "",
    default: Any = None,
) -> Any:
    """Generate content, extract JSON cleanly (stripping fences/prose), or return `default`."""
    raw = text(contents, tier=tier, config=config, timeout_ms=timeout_ms, key=key)
    return parse_json(raw, default=default)
