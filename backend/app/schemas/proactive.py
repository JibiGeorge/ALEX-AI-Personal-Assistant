from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProactiveCheckParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = Field(default=False, description="Bypass the silence gate and cooldown for manual invocation")
    last_user_speech_seconds_ago: Optional[float] = Field(
        default=None,
        description="Override how many seconds ago user last spoke; defaults to internal tracker",
    )


class ProactiveCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    triggered: bool
    reason: str
    prompt: Optional[str] = None
    period: Optional[str] = None
    focus_index: Optional[int] = None

