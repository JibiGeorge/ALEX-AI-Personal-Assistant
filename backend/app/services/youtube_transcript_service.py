"""
YouTube Transcript Extractor & Video Summarizer Service (TASK-GAP-09 / GAP-09).

Provides YouTube transcript fetching, AI summarization via Gemini, video metadata scraping,
trending feeds, and video playback control.
Adheres strictly to the Five-Word Outcome Contract (done, unverified, failed).
"""

from __future__ import annotations

from datetime import datetime
from importlib.util import find_spec
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
import webbrowser

import httpx
from google import genai
from google.genai import types

from app.actions.base import ActionOutcomeResponse, done, failed, unverified
from app.schemas.youtube_transcript import YouTubeTranscriptParameters
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_YT_VIDEO_FILTER = "EgIQAQ%3D%3D"
_SUMMARY_MODELS = (
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
)


class YouTubeTranscriptService:
    """Service for YouTube transcripts, Gemini summarization, and video metadata."""

    def __init__(self, settings: SettingsService) -> None:
        self._settings = settings

    @property
    def is_transcript_api_installed(self) -> bool:
        """Check if youtube_transcript_api is installed."""
        return find_spec("youtube_transcript_api") is not None

    def extract_video_id(self, url_or_id: Optional[str]) -> Optional[str]:
        """Extract an 11-character YouTube video ID from a URL or raw ID string."""
        if not url_or_id:
            return None
        clean = url_or_id.strip()
        if re.match(r"^[A-Za-z0-9_-]{11}$", clean):
            return clean
        match = re.search(
            r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})", clean
        )
        return match.group(1) if match else None

    def scrape_first_video_url(self, query: str) -> Optional[str]:
        """Scrape YouTube search results for the first non-Shorts video matching the query."""
        if not query or not query.strip():
            return None
        search_url = (
            f"https://www.youtube.com/results"
            f"?search_query={quote_plus(query.strip())}"
            f"&sp={_YT_VIDEO_FILTER}"
        )
        try:
            with httpx.Client(headers=HEADERS, timeout=12.0, follow_redirects=True) as client:
                resp = client.get(search_url)
                html = resp.text

            video_ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
            seen = set()
            for vid in video_ids:
                if vid in seen:
                    continue
                seen.add(vid)
                if f"/shorts/{vid}" in html:
                    continue
                return f"https://www.youtube.com/watch?v={vid}"
        except Exception as exc:
            logger.warning("Scrape first video URL failed for '%s': %s", query, exc)
        return None

    def get_transcript(self, video_id: str, lang: str = "en") -> Optional[str]:
        """Retrieve the transcript of a video using youtube_transcript_api with language fallback."""
        if not self.is_transcript_api_installed:
            return None
        try:
            from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore

            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            priority = [lang] + [
                code for code in ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "ar", "zh", "tr"]
                if code != lang
            ]

            transcript = None
            try:
                transcript = transcript_list.find_manually_created_transcript(priority)
            except Exception:
                pass

            if transcript is None:
                try:
                    transcript = transcript_list.find_generated_transcript(priority)
                except Exception:
                    for t in transcript_list:
                        transcript = t
                        break

            if transcript is None:
                return None

            fetched = transcript.fetch()
            entries = []
            for entry in fetched:
                if isinstance(entry, dict):
                    entries.append(entry.get("text", ""))
                else:
                    text_attr = getattr(entry, "text", str(entry))
                    entries.append(str(text_attr))
            return " ".join(entries).strip()
        except Exception as exc:
            logger.warning("YouTube transcript fetch failed for %s: %s", video_id, exc)
            return None

    def scrape_video_info(self, video_id: str) -> Dict[str, Any]:
        """Scrape video metadata (title, channel, views, duration, likes)."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            with httpx.Client(headers=HEADERS, timeout=12.0, follow_redirects=True) as client:
                resp = client.get(url)
                html = resp.text

            info: Dict[str, Any] = {"video_id": video_id, "url": url}
            patterns = [
                ("title", r'"title":\{"runs":\[\{"text":"([^"]+)"'),
                ("channel", r'"ownerChannelName":"([^"]+)"'),
                ("views", r'"viewCount":"(\d+)"'),
                ("duration", r'"lengthSeconds":"(\d+)"'),
                ("likes", r'"label":"([0-9,]+ likes)"'),
            ]
            for key, pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    val = match.group(1)
                    if key == "views":
                        info[key] = f"{int(val):,}"
                    elif key == "duration":
                        secs = int(val)
                        info[key] = f"{secs // 60}:{secs % 60:02d}"
                    else:
                        info[key] = val

            return info
        except Exception as exc:
            logger.warning("YouTube info scrape failed for %s: %s", video_id, exc)
            return {"video_id": video_id, "url": url}

    def scrape_trending(self, region: str = "US", max_results: int = 8) -> List[Dict[str, Any]]:
        """Scrape trending videos for a given ISO country code."""
        url = f"https://www.youtube.com/feed/trending?gl={region.upper()}"
        try:
            with httpx.Client(headers=HEADERS, timeout=12.0, follow_redirects=True) as client:
                resp = client.get(url)
                html = resp.text

            titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}\]', html)
            channels = re.findall(r'"ownerText":\{"runs":\[\{"text":"([^"]+)"', html)

            results: List[Dict[str, Any]] = []
            seen = set()
            for i, title in enumerate(titles):
                if title in seen or len(title) < 5:
                    continue
                seen.add(title)
                channel = channels[i] if i < len(channels) else "Unknown"
                results.append({"rank": len(results) + 1, "title": title, "channel": channel})
                if len(results) >= max_results:
                    break

            return results
        except Exception as exc:
            logger.warning("Trending scrape failed for %s: %s", region, exc)
            return []

    def summarize(self, transcript: str, video_url: str) -> str:
        """Summarize transcript using Gemini."""
        max_chars = 80000
        truncated = transcript[:max_chars] + ("..." if len(transcript) > max_chars else "")

        api_key = self._settings.get_api_key_for_service()
        if not api_key:
            return f"Gemini API key is not configured in Settings. Transcript excerpt:\n{truncated[:500]}..."

        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))
        prompt = f"Please summarize this YouTube video transcript:\n\n{truncated}"
        system_instruction = (
            "You are Alex, an AI desktop assistant. "
            "Summarize YouTube video transcripts clearly and concisely. "
            "Structure: 1-sentence overview, then 3-5 bullet points of key takeaways. "
            "Be direct and actionable."
        )

        for model in _SUMMARY_MODELS:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                        max_output_tokens=2048,
                    ),
                )
                txt = (response.text or "").strip()
                if txt:
                    return txt
            except Exception as exc:
                logger.debug("Summarization model '%s' failed: %s", model, exc)

        return "Could not generate summary using Gemini models."

    def save_summary(self, summary: str, video_url: str, output_path: Optional[str] = None) -> str:
        """Save formatted summary to a file on the Desktop or custom path."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_path:
            filepath = Path(output_path).expanduser().resolve()
        else:
            desktop = Path.home() / "Desktop"
            desktop.mkdir(parents=True, exist_ok=True)
            filepath = desktop / f"youtube_summary_{ts}.txt"

        filepath.parent.mkdir(parents=True, exist_ok=True)
        header = (
            f"Alex — YouTube Summary\n"
            f"{'─' * 50}\n"
            f"URL    : {video_url}\n"
            f"Date   : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"{'─' * 50}\n\n"
        )
        filepath.write_text(header + summary, encoding="utf-8")
        return str(filepath)

    def play_video(self, url: str) -> None:
        """Open a YouTube video URL in the default web browser."""
        webbrowser.open(url)

    def execute(self, params: YouTubeTranscriptParameters) -> ActionOutcomeResponse:
        """Execute a YouTube action adhering to the Five-Word Outcome Contract."""
        action = (params.action or "summarize").lower().strip()

        valid_actions = {"summarize", "transcript", "info", "get_info", "trending", "play"}
        if action not in valid_actions:
            return failed(
                "youtube.transcript",
                error="Unknown action",
                message=f"Unknown YouTube action: '{action}'. Available actions: summarize, transcript, info, trending, play.",
            )

        # Action: trending
        if action == "trending":
            region = (params.region or "US").upper()
            trending = self.scrape_trending(region=region, max_results=params.max_results)
            if not trending:
                return failed(
                    "youtube.transcript",
                    error="Scrape trending failed",
                    message=f"Could not fetch trending videos for region {region}.",
                )
            lines = [f"Top trending videos in {region}:"]
            lines += [f"{v['rank']}. {v['title']} — {v['channel']}" for v in trending]
            return done(
                "youtube.transcript",
                "\n".join(lines),
                data={"region": region, "trending": trending},
            )

        # Resolve video ID and URL
        video_id = self.extract_video_id(params.url_or_id)
        video_url: Optional[str] = None
        if video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
        elif params.query:
            video_url = self.scrape_first_video_url(params.query)
            if video_url:
                video_id = self.extract_video_id(video_url)

        # Action: play
        if action == "play":
            if not video_url:
                if params.query:
                    # Fallback to search results page
                    fallback_url = (
                        f"https://www.youtube.com/results"
                        f"?search_query={quote_plus(params.query.strip())}"
                        f"&sp={_YT_VIDEO_FILTER}"
                    )
                    self.play_video(fallback_url)
                    return done(
                        "youtube.transcript",
                        f"Opened YouTube search for: {params.query}",
                        data={"url": fallback_url},
                    )
                return failed(
                    "youtube.transcript",
                    error="Missing video URL or query",
                    message="Please provide a video URL or search query to play.",
                )
            self.play_video(video_url)
            return done(
                "youtube.transcript",
                f"Playing: {video_url}",
                data={"url": video_url, "video_id": video_id},
            )

        # Actions requiring video ID: info, transcript, summarize
        if not video_id:
            return failed(
                "youtube.transcript",
                error="Invalid YouTube video URL or ID",
                message="Please provide a valid YouTube video URL or 11-character video ID.",
            )

        if not video_url:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Action: info
        if action in ("info", "get_info"):
            info = self.scrape_video_info(video_id)
            lines = [f"YouTube Video Info ({video_id}):"]
            for key in ("title", "channel", "views", "duration", "likes"):
                if key in info:
                    lines.append(f"{key.capitalize()}: {info[key]}")
            return done(
                "youtube.transcript",
                "\n".join(lines),
                data=info,
            )

        # Actions requiring transcript: transcript, summarize
        if not self.is_transcript_api_installed:
            return unverified(
                "youtube.transcript",
                "youtube-transcript-api is not installed. Run: pip install youtube-transcript-api",
                api_required=True,
            )

        transcript = self.get_transcript(video_id, lang=params.language or "en")
        if not transcript:
            return failed(
                "youtube.transcript",
                error="Transcript not available",
                message=f"Could not retrieve transcript for video {video_id}.",
            )

        # Action: transcript
        if action == "transcript":
            return done(
                "youtube.transcript",
                transcript,
                data={
                    "video_id": video_id,
                    "url": video_url,
                    "characters": len(transcript),
                },
            )

        # Action: summarize
        if action == "summarize":
            summary = self.summarize(transcript, video_url)
            saved_to: Optional[str] = None
            if params.save_to_disk or params.output_path:
                saved_to = self.save_summary(summary, video_url, output_path=params.output_path)

            dest_info = f" (Saved to: {saved_to})" if saved_to else ""
            return done(
                "youtube.transcript",
                f"{summary}{dest_info}",
                data={
                    "video_id": video_id,
                    "url": video_url,
                    "summary": summary,
                    "saved_to": saved_to,
                },
            )

        return failed(
            "youtube.transcript",
            error="Unknown action",
            message=f"Unknown YouTube action: '{action}'. Available actions: summarize, transcript, info, trending, play.",
        )
