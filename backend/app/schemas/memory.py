from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryCategory = Literal[
    "identity",
    "preferences",
    "projects",
    "relationships",
    "wishes",
    "notes",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MemoryWrite(StrictModel):
    value: str = Field(min_length=1, max_length=4000)


class MemoryEntry(StrictModel):
    category: MemoryCategory
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=4000)
    updated: date


class MemoryListResponse(StrictModel):
    entries: list[MemoryEntry]
