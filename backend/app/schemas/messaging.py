"""
Schemas for Messaging Automation (TASK-GAP-05 / GAP-05).
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SendMessageParameters(BaseModel):
    """Parameters for sending messages across WhatsApp, Telegram, and other messaging platforms."""
    model_config = ConfigDict(extra="ignore")

    receiver: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Recipient contact name, handle, or phone number.",
    )
    message_text: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="The content of the message to send.",
    )
    platform: str = Field(
        default="WhatsApp",
        description="Target platform: WhatsApp | Telegram | Signal | Discord | Instagram",
    )

