from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints
from typing_extensions import Annotated


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReminderCreate(StrictModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    due_at: AwareDatetime


class Reminder(StrictModel):
    id: UUID
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    due_at: AwareDatetime
    status: Literal["pending", "delivered"]


class ReminderList(StrictModel):
    reminders: list[Reminder]


class DueReminderList(StrictModel):
    reminders: list[Reminder]
