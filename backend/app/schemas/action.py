from pydantic import BaseModel, ConfigDict, Field

class ActionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actions: list[dict[str, object]]


class ActionExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameters: dict[str, object] = Field(default_factory=dict)
    confirmed: bool = False


class ActionEnableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
