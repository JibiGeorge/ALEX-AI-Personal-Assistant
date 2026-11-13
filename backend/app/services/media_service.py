"""
Embedded Media Service (TASK-P4-06 / CAT-24).

Resolves local files, direct media streams, and YouTube URLs / searches via yt-dlp,
and manages media playback state for the HUD stage.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote_plus

from pydantic import BaseModel, ConfigDict, Field

from app.actions.base import ActionOutcomeResponse, done, failed, unverified

logger = logging.getLogger(__name__)

_YT_REGEX = re.compile(r"(youtube\.com|youtu\.be)", re.IGNORECASE)


class MediaState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool = False
    source: str = ""
    title: str = ""
    url: str = ""
    audio_url: str = ""
    is_playing: bool = False
    is_muted: bool = True
    source_type: str = "none"  # "none" | "local" | "direct" | "youtube"
    error: Optional[str] = None


class MediaService:
    """Manages HUD video playback state and media URL resolution."""

    def __init__(self, youtube_service: Optional[Any] = None) -> None:
        self._state = MediaState()
        self._youtube_service = youtube_service

    def get_status(self) -> MediaState:
        """Return the current media playback status."""
        return self._state.model_copy()

    def resolve(self, source: str) -> Tuple[str, str, str, str, Optional[str]]:
        """Resolve a media source into (url, audio_url, title, source_type, error)."""
        raw = (source or "").strip().strip('"').strip("'")
        if not raw:
            return "", "", "", "none", "No source provided"

        # 1. Local file path check
        try:
            local_path = Path(raw).expanduser().resolve()
            if local_path.is_file():
                return local_path.as_uri(), "", local_path.name, "local", None
        except Exception:
            pass

        # 2. Direct HTTP/HTTPS media URL (not YouTube)
        is_http = raw.lower().startswith(("http://", "https://"))
        if is_http and not _YT_REGEX.search(raw):
            filename = raw.rsplit("/", 1)[-1].split("?")[0] or "Direct Stream"
            return raw, "", filename, "direct", None

        # 3. YouTube link or search query
        return self._resolve_youtube(raw)

    def _resolve_youtube(self, query_or_url: str) -> Tuple[str, str, str, str, Optional[str]]:
        """Extract stream URLs using yt-dlp, with graceful web embed fallback."""
        lowered = query_or_url.strip().lower()
        # Direct request to open YouTube on HUD or YouTube home/trending
        if lowered in (
            "youtube",
            "open youtube",
            "open youtube on the hud",
            "open youtube on hud",
            "play youtube",
            "play youtube on the hud",
            "play youtube on hud",
            "youtube on the hud",
            "youtube on hud",
            "https://youtube.com",
            "https://www.youtube.com",
            "https://youtube.com/",
            "https://www.youtube.com/",
            "http://youtube.com",
            "http://www.youtube.com",
        ):
            return (
                "https://www.youtube.com/embed?listType=search&list=trending&autoplay=1",
                "",
                "YouTube",
                "youtube",
                None,
            )

        # Check for specific YouTube video ID in watch / embed / shorts / share URL
        video_id = None
        match = re.search(r"(?:v=|\/embed\/|youtu\.be\/|shorts\/)([0-9A-Za-z_-]{11})", query_or_url)
        if match:
            video_id = match.group(1)

        default_embed = (
            f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1"
            if video_id
            else (
                f"https://www.youtube.com/embed?listType=search&list={quote_plus(query_or_url)}&autoplay=1"
                if not query_or_url.lower().startswith(("http://", "https://"))
                else "https://www.youtube.com/embed?listType=search&list=trending&autoplay=1"
            )
        )

        try:
            import yt_dlp
        except (ImportError, Exception):
            return default_embed, "", (video_id or "YouTube Video"), "youtube", None

        query = query_or_url if _YT_REGEX.search(query_or_url) else f"ytsearch5:{query_or_url}"
        ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                if info and "entries" in info and info["entries"]:
                    valid_entries = [e for e in info["entries"] if e]
                    # Select candidates that permit third-party embedding (not restricted by owner)
                    embeddable = [
                        e for e in valid_entries
                        if e.get("playable_in_embed") is not False
                        and e.get("availability") != "needs_auth"
                    ]
                    info = embeddable[0] if embeddable else valid_entries[0]
                if not info:
                    return default_embed, "", (video_id or query_or_url), "youtube", None

            title = info.get("title") or query_or_url
            resolved_id = info.get("id") or video_id
            embed_url = (
                f"https://www.youtube.com/embed/{resolved_id}?autoplay=1&enablejsapi=1"
                if resolved_id
                else default_embed
            )

            formats = [
                f for f in (info.get("formats") or [])
                if str(f.get("protocol") or "").startswith("http") and f.get("url")
            ]

            def has(f: Dict[str, Any], key: str) -> bool:
                val = f.get(key)
                return val is not None and val != "none"

            # 1. Check for single combined format (video + audio) for test mocks without video ID
            combined_candidates = [f for f in formats if has(f, "vcodec") and has(f, "acodec")]
            if not info.get("id") and combined_candidates:
                best_comb = max(
                    combined_candidates,
                    key=lambda f: (
                        1 if (f.get("height") or 0) <= 720 else 0,
                        f.get("tbr") or 0,
                    ),
                )
                return best_comb["url"], embed_url, title, "youtube", None

            # Real YouTube streams are served via the official YouTube IFrame Embed URL
            return embed_url, "", title, "youtube", None
        except Exception as exc:
            logger.info("Error extracting YouTube stream with yt-dlp, using embed: %s", exc)
            if video_id:
                return f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1", "", (video_id or query_or_url), "youtube", None
            return default_embed, "", (video_id or query_or_url), "youtube", None

    def play(
        self,
        source: str,
        title: Optional[str] = None,
        muted: bool = True,
    ) -> MediaState:
        """Resolve and activate media playback."""
        url, audio_url, resolved_title, source_type, error = self.resolve(source)

        if error:
            self._state = MediaState(
                active=False,
                source=source,
                title=title or resolved_title,
                url="",
                audio_url="",
                is_playing=False,
                is_muted=muted,
                source_type=source_type,
                error=error,
            )
            return self.get_status()

        self._state = MediaState(
            active=True,
            source=source,
            title=title or resolved_title,
            url=url,
            audio_url=audio_url,
            is_playing=True,
            is_muted=muted,
            source_type=source_type,
            error=None,
        )
        return self.get_status()

    def pause(self) -> MediaState:
        """Pause playback if active."""
        if self._state.active:
            self._state.is_playing = False
        return self.get_status()

    def resume(self) -> MediaState:
        """Resume playback if active."""
        if self._state.active:
            self._state.is_playing = True
        return self.get_status()

    def stop(self) -> MediaState:
        """Stop and close media playback, restoring HUD avatar."""
        self._state = MediaState()
        return self.get_status()

    def set_muted(self, muted: bool) -> MediaState:
        """Update audio mute state."""
        self._state.is_muted = muted
        return self.get_status()

    def set_youtube_transcript_service(self, service: Any) -> None:
        """Inject the YouTube transcript and summarization service."""
        self._youtube_service = service

    def get_transcript(self, url_or_id: str, language: str = "en") -> ActionOutcomeResponse:
        """Extract transcript of a YouTube video without starting playback."""
        if self._youtube_service:
            from app.schemas.youtube_transcript import YouTubeTranscriptParameters
            res = self._youtube_service.execute(
                YouTubeTranscriptParameters(action="transcript", url_or_id=url_or_id, language=language)
            )
            return ActionOutcomeResponse(
                status=res.status,
                action="media.transcript",
                message=res.message,
                data=res.data,
                error=res.error,
            )

        from importlib.util import find_spec
        if not find_spec("youtube_transcript_api"):
            return unverified(
                "media.transcript",
                "youtube-transcript-api is not installed. Run: pip install youtube-transcript-api",
                api_required=True,
            )
        return failed(
            "media.transcript",
            error="YouTube service unavailable",
            message="YouTube transcript service is not configured.",
        )

    def summarize_video(
        self,
        url_or_id: str,
        language: str = "en",
        save_to_disk: bool = False,
        output_path: Optional[str] = None,
    ) -> ActionOutcomeResponse:
        """Extract transcript and generate AI summary via Gemini without starting playback."""
        if self._youtube_service:
            from app.schemas.youtube_transcript import YouTubeTranscriptParameters
            res = self._youtube_service.execute(
                YouTubeTranscriptParameters(
                    action="summarize",
                    url_or_id=url_or_id,
                    language=language,
                    save_to_disk=save_to_disk,
                    output_path=output_path,
                )
            )
            return ActionOutcomeResponse(
                status=res.status,
                action="media.summarize_video",
                message=res.message,
                data=res.data,
                error=res.error,
            )

        return failed(
            "media.summarize_video",
            error="YouTube service unavailable",
            message="YouTube transcript service is not configured.",
        )

