"""
Schemas for System Settings & Hardware Macros (TASK-GAP-02 / GAP-02).

Supports volume, brightness, Wi-Fi, lock screen, and system settings dialogs.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SystemSettingParameters(BaseModel):
    """Parameters for system settings actions."""
    model_config = ConfigDict(extra="ignore")

    setting_action: str = Field(
        ...,
        description="The system setting action to execute: volume_up | volume_down | volume_mute | volume_set | volume_get | brightness_up | brightness_down | brightness_set | brightness_get | toggle_wifi | lock_screen | sleep_display | open_system_settings | open_task_manager | open_file_explorer",
    )
    value: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Target numeric value between 0 and 100 for volume_set or brightness_set.",
    )
    interface: Optional[str] = Field(
        default=None,
        description="Optional network interface identifier for Wi-Fi toggle.",
    )

