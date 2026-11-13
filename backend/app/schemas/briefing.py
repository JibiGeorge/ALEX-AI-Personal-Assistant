from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BriefingReminderSummary(StrictModel):
    total_pending: int = Field(default=0, ge=0)
    due_now: int = Field(default=0, ge=0)
    upcoming_messages: list[str] = Field(default_factory=list)


class BriefingSystemSummary(StrictModel):
    cpu_percent: float = Field(default=0.0, ge=0.0)
    ram_percent: float = Field(default=0.0, ge=0.0)
    active_alerts_count: int = Field(default=0, ge=0)
    system_status: str = Field(default="Normal")


class BriefingResponse(StrictModel):
    greeting: str
    assistant_name: str
    user_name: str
    timestamp_iso: str
    system: BriefingSystemSummary
    reminders: BriefingReminderSummary
    known_identity_facts: list[str] = Field(default_factory=list)

