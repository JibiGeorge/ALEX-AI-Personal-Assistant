"""
Schemas for Vision and Webcam Video Frame Capture (TASK-GAP-07 / GAP-07).
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class VisionCaptureParameters(BaseModel):
    """Parameters for capturing visual frames from webcam or desktop screen."""
    model_config = ConfigDict(extra="ignore")

    source: str = Field(
        default="camera",
        description="Capture source: camera | screen | probe_cameras",
    )
    camera_index: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Optional camera index (0-10) to capture from. Auto-detected if omitted.",
    )
    save_to_disk: bool = Field(
        default=True,
        description="Whether to save the captured frame as a JPEG image on disk.",
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Custom file path or filename to save the captured frame.",
    )
    include_base64: bool = Field(
        default=False,
        description="Whether to include the base64-encoded image data in the response.",
    )

