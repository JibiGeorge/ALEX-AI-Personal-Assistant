from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class GameItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    app_id: Optional[str] = None
    platform: str
    install_dir: Optional[str] = None
    status: str = "installed"


class GameUpdaterParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["list", "update", "launch", "schedule", "cancel_schedule", "status"] = Field(
        default="list",
        description="Action to perform: list installed games, update games, launch a game, or manage schedule",
    )
    platform: Literal["steam", "epic", "both"] = Field(default="both", description="Game platform")
    game_name: Optional[str] = Field(default=None, description="Game title to match for update/launch")
    app_id: Optional[str] = Field(default=None, description="Platform App ID for targeted launch/update")
    hour: int = Field(default=3, ge=0, le=23, description="Hour for scheduled daily updates (0-23)")
    minute: int = Field(default=0, ge=0, le=59, description="Minute for scheduled daily updates (0-59)")


class GameUpdaterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    platform: str
    games: list[GameItem]
    message: str
    scheduled_time: Optional[str] = None

