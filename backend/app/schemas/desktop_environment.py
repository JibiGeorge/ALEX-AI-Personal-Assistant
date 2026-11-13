"""
Schemas for Desktop Hygiene & Wallpaper Manager (TASK-GAP-06 / GAP-06).
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DesktopActionParameters(BaseModel):
    """Parameters for desktop environment and hygiene management."""
    model_config = ConfigDict(extra="ignore")

    action: str = Field(
        ...,
        description="The desktop action: wallpaper | wallpaper_url | current_wallpaper | organize | clean | list | stats",
    )
    image_path: Optional[str] = Field(
        default=None,
        description="Local image path for setting wallpaper (png, jpg, jpeg, bmp, webp).",
    )
    url: Optional[str] = Field(
        default=None,
        description="Public image URL for wallpaper_url.",
    )
    organize_mode: Optional[str] = Field(
        default="by_type",
        description="Desktop file organization mode: by_type | by_date",
    )

