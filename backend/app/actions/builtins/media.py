"""
Media playback built-in action handlers (TASK-P4-06 / CAT-24).

Exposes 'media.play', 'media.stop', 'media.pause', 'media.resume', 'media.set_muted',
and 'media.status' actions for embedded HUD video playback.
"""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, done, failed
from app.services.media_service import MediaService

logger = logging.getLogger(__name__)


class MediaPlayParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(
        min_length=1,
        max_length=2048,
        description="Local file path, media URL, or YouTube video/search query.",
    )
    title: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Optional display title for the video.",
    )
    muted: bool = Field(
        default=True,
        description="Whether to start media playback muted (default True to avoid audio overlap).",
    )


class MediaEmptyParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MediaMuteParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    muted: bool = Field(
        description="True to mute video audio, False to unmute.",
    )


class MediaTranscriptParameters(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url_or_id: str = Field(
        min_length=1,
        max_length=2048,
        description="YouTube video URL or 11-character video ID to extract transcript from without playback.",
    )
    language: Optional[str] = Field(
        default="en",
        description="Preferred language code (e.g. 'en', 'es', 'fr', 'de').",
    )


class MediaSummarizeParameters(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url_or_id: str = Field(
        min_length=1,
        max_length=2048,
        description="YouTube video URL or 11-character video ID to summarize without playback.",
    )
    language: Optional[str] = Field(
        default="en",
        description="Preferred language code for the transcript.",
    )
    save_to_disk: bool = Field(
        default=False,
        description="Whether to save the summary to a text file on the Desktop.",
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Optional custom destination path for saving the summary.",
    )


def register_media_actions(
    registry: ActionRegistry,
    media_service: MediaService,
) -> None:
    """Register media playback actions with the action registry."""

    def handle_play(params: MediaPlayParameters) -> ActionOutcomeResponse:
        try:
            state = media_service.play(params.source, title=params.title, muted=params.muted)
            if state.error:
                return failed("media.play", state.error, message=f"Could not play media: {state.error}")
            return done(
                "media.play",
                f"Playing '{state.title or params.source}' on display.",
                data=state.model_dump(mode="json"),
            )
        except Exception as exc:
            logger.exception("Error executing media.play: %s", exc)
            return failed("media.play", str(exc), message="Failed to initiate media playback.")

    def handle_stop(_: MediaEmptyParameters) -> ActionOutcomeResponse:
        state = media_service.stop()
        return done("media.stop", "Closed media playback.", data=state.model_dump(mode="json"))

    def handle_pause(_: MediaEmptyParameters) -> ActionOutcomeResponse:
        state = media_service.pause()
        return done("media.pause", "Paused media playback.", data=state.model_dump(mode="json"))

    def handle_resume(_: MediaEmptyParameters) -> ActionOutcomeResponse:
        state = media_service.resume()
        return done("media.resume", "Resumed media playback.", data=state.model_dump(mode="json"))

    def handle_set_muted(params: MediaMuteParameters) -> ActionOutcomeResponse:
        state = media_service.set_muted(params.muted)
        verdict = "Muted media audio." if params.muted else "Unmuted media audio."
        return done("media.set_muted", verdict, data=state.model_dump(mode="json"))

    def handle_status(_: MediaEmptyParameters) -> ActionOutcomeResponse:
        state = media_service.get_status()
        verdict = f"Media {'playing' if state.is_playing else 'paused' if state.active else 'inactive'}."
        return done("media.status", verdict, data=state.model_dump(mode="json"))

    def handle_transcript(params: MediaTranscriptParameters) -> ActionOutcomeResponse:
        return media_service.get_transcript(params.url_or_id, language=params.language or "en")

    def handle_summarize(params: MediaSummarizeParameters) -> ActionOutcomeResponse:
        return media_service.summarize_video(
            params.url_or_id,
            language=params.language or "en",
            save_to_disk=params.save_to_disk,
            output_path=params.output_path,
        )

    registry.register(
        ActionDefinition(
            action_id="media.play",
            name="Play media",
            description="Play a local video, direct media URL, or YouTube video in the HUD player stage. Use whenever the user asks to play a video or open/watch YouTube on the HUD.",
            category="media",
            parameters=MediaPlayParameters,
            handler=handle_play,
            timeout_seconds=30,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="media.stop",
            name="Stop media",
            description="Stop HUD video playback and return to avatar view.",
            category="media",
            parameters=MediaEmptyParameters,
            handler=handle_stop,
            timeout_seconds=5,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="media.pause",
            name="Pause media",
            description="Pause active HUD video playback.",
            category="media",
            parameters=MediaEmptyParameters,
            handler=handle_pause,
            timeout_seconds=5,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="media.resume",
            name="Resume media",
            description="Resume paused HUD video playback.",
            category="media",
            parameters=MediaEmptyParameters,
            handler=handle_resume,
            timeout_seconds=5,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="media.set_muted",
            name="Set media muted",
            description="Mute or unmute the HUD video player.",
            category="media",
            parameters=MediaMuteParameters,
            handler=handle_set_muted,
            timeout_seconds=5,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="media.status",
            name="Media status",
            description="Get current status of HUD video player.",
            category="media",
            parameters=MediaEmptyParameters,
            handler=handle_status,
            timeout_seconds=5,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="media.transcript",
            name="Get YouTube video transcript",
            description="Extract transcript text from a YouTube video without starting playback.",
            category="media",
            parameters=MediaTranscriptParameters,
            handler=handle_transcript,
            timeout_seconds=60,
            requires_confirmation=False,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="media.summarize_video",
            name="Summarize YouTube video",
            description="Extract transcript and summarize a YouTube video with Gemini AI without playing the video.",
            category="media",
            parameters=MediaSummarizeParameters,
            handler=handle_summarize,
            timeout_seconds=60,
            requires_confirmation=False,
        )
    )

