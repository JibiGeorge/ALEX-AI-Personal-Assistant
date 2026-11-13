from pydantic import BaseModel, ConfigDict, Field


class SystemMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    network_mb_per_sec: float | None = Field(default=None, ge=0)
    operating_system: str
    uptime_seconds: int = Field(ge=0)
    process_count: int = Field(ge=0)
    gpu_percent: float | None = Field(default=None, ge=0, le=100)
    temperature_c: float | None = Field(default=None, ge=0)
