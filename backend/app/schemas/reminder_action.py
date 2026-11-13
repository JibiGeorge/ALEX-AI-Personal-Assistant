"""
Schemas for Reminder Action (GAP-10).
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ReminderActionParameters(BaseModel):
    """Parameters for scheduling, listing, and canceling persistent OS reminders."""
    model_config = ConfigDict(extra="ignore")

    action: str = Field(
        default="create",
        description="Action to perform: 'create' | 'list' | 'cancel'.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Reminder message text to alert the user.",
    )
    due_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp with timezone when the reminder should fire (e.g. '2026-11-05T15:30:00Z').",
    )
    date: Optional[str] = Field(
        default=None,
        description="Date in YYYY-MM-DD format (used with time parameter).",
    )
    time: Optional[str] = Field(
        default=None,
        description="Time in HH:MM format (24-hour, used with date parameter).",
    )
    reminder_id: Optional[str] = Field(
        default=None,
        description="Unique reminder ID to cancel.",
    )

