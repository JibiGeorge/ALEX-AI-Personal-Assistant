"""
Schemas for Background Topic News Monitor (GAP-11).
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TopicMonitorParameters(BaseModel):
    """Parameters for user-configured background topic news monitoring."""
    model_config = ConfigDict(extra="ignore")

    action: str = Field(
        default="list",
        description="Action to execute: 'add' | 'remove' | 'list' | 'check'.",
    )
    topic: Optional[str] = Field(
        default=None,
        description="Topic, company, or subject name to monitor (e.g. 'SpaceX', 'DeepMind', 'Quantum Computing').",
    )
    force: bool = Field(
        default=False,
        description="Whether to force check today even if already checked.",
    )

