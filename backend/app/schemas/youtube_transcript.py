"""
Schemas for YouTube Transcript Extractor and Video Summarizer (TASK-GAP-09 / GAP-09).
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class YouTubeTranscriptParameters(BaseModel):
    """Parameters for extracting transcripts, summarizing videos, or fetching info from YouTube."""
    model_config = ConfigDict(extra="ignore")

    url_or_id: Optional[str] = Field(
        default=None,
        description="YouTube video URL or 11-character video ID (e.g. 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' or 'dQw4w9WgXcQ').",
    )
    query: Optional[str] = Field(
        default=None,
        description="Search query to locate a video if URL or ID is not provided.",
    )
    action: str = Field(
        default="summarize",
        description="Action to execute: 'summarize' | 'transcript' | 'info' | 'trending' | 'play'.",
    )
    language: Optional[str] = Field(
        default="en",
        description="Preferred transcript language code (e.g. 'en', 'es', 'fr', 'de', 'tr').",
    )
    save_to_disk: bool = Field(
        default=False,
        description="Whether to save the generated summary to a text file on the Desktop.",
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Optional custom file destination path for saving the summary.",
    )
    region: str = Field(
        default="US",
        description="Two-letter ISO country code for trending video queries (e.g. 'US', 'GB', 'TR').",
    )
    max_results: int = Field(
        default=8,
        ge=1,
        le=25,
        description="Maximum number of trending videos to retrieve.",
    )

