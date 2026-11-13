"""
YouTube built-in action handlers (TASK-GAP-09 / GAP-09).

Exposes 'youtube.transcript' for transcript extraction, video summarization, metadata scraping,
and trending video feeds.
"""

from __future__ import annotations

import logging

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse
from app.schemas.youtube_transcript import YouTubeTranscriptParameters
from app.services.youtube_transcript_service import YouTubeTranscriptService

logger = logging.getLogger(__name__)


def register_youtube_actions(
    registry: ActionRegistry,
    youtube_service: YouTubeTranscriptService,
) -> None:
    """Register YouTube transcript & summarization actions with the ActionRegistry."""

    def handle_youtube(params: YouTubeTranscriptParameters) -> ActionOutcomeResponse:
        return youtube_service.execute(params)

    registry.register(
        ActionDefinition(
            action_id="youtube.transcript",
            name="YouTube transcript extractor and video summarizer",
            description="Extracts transcripts from YouTube videos, generates AI summaries, fetches video metadata and trending lists.",
            category="search",
            parameters=YouTubeTranscriptParameters,
            handler=handle_youtube,
            timeout_seconds=60.0,
            requires_confirmation=False,
        )
    )

