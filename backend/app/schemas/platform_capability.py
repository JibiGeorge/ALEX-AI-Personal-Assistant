from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CapabilityStatus(StrictModel):
    available: bool = Field(description="Whether this capability is functional in the current environment")
    status_detail: str = Field(default="", description="Human-readable status or reason if unavailable")
    platform_restricted: bool = Field(
        default=False,
        description="True if this capability is intentionally limited to specific operating systems",
    )


class PlatformCapabilityReport(StrictModel):
    operating_system: str = Field(description="Operating system identifier (Windows, macOS, Linux)")
    os_release: str = Field(description="OS release or kernel version string")
    architecture: str = Field(description="CPU architecture string")
    desktop_notifications: CapabilityStatus
    screen_capture: CapabilityStatus
    window_management: CapabilityStatus
    computer_control: CapabilityStatus
    gemini_live_voice: CapabilityStatus
    gemini_grounded_search: CapabilityStatus
    memory_persistence: CapabilityStatus
    audio_input_devices: CapabilityStatus

