from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SystemAlert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: Literal["cpu", "memory", "gpu", "temperature"]
    value: float = Field(ge=0)
    message: str = Field(min_length=1, max_length=300)


class SystemAlertList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alerts: list[SystemAlert] = Field(max_length=4)
