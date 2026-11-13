"""
Schemas for ElevenLabs Multilingual Streaming TTS (TASK-GAP-08 / GAP-08).
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ElevenLabsSynthesizeParameters(BaseModel):
    """Parameters for synthesizing speech with ElevenLabs."""
    model_config = ConfigDict(extra="ignore")

    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text to synthesize into speech.",
    )
    voice_id: Optional[str] = Field(
        default=None,
        description="Optional ElevenLabs voice ID (e.g. '21m00Tcm4TlvDq8ikWAM' for Rachel).",
    )
    model_id: Optional[str] = Field(
        default="eleven_flash_v2_5",
        description="ElevenLabs model: eleven_flash_v2_5 | eleven_turbo_v2_5 | eleven_multilingual_v2",
    )
    stability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Voice stability setting between 0.0 and 1.0.",
    )
    similarity_boost: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Voice similarity boost setting between 0.0 and 1.0.",
    )
    output_format: Optional[str] = Field(
        default=None,
        description="Output audio format: pcm_24000 | mp3_44100_128 (auto-negotiated if omitted).",
    )
    save_to_disk: bool = Field(
        default=False,
        description="Whether to save the synthesized audio file to disk.",
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Custom file destination path for the generated audio file.",
    )

