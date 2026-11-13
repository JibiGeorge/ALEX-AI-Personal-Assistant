import platform
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OperatingSystem = Literal["Windows", "macOS", "Linux"]
AssistantVoice = Literal["Charon", "Puck", "Kore", "Fenrir", "Aoede"]
HudStyle = Literal[
    "face",
    "core",
    "robot",
    "realistic_humanoid",
    "existing_face",
    "reactor_core",
]


def _detected_operating_system() -> OperatingSystem:
    system = platform.system()
    if system == "Darwin":
        return "macOS"
    if system in ("Windows", "Linux"):
        return system
    return "Linux"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppSettings(StrictModel):
    assistant_name: str = Field(default="ALEX", min_length=1, max_length=50)
    user_name: str = Field(default="", max_length=80)
    accent_color: str = Field(default="#00d4ff", pattern=r"^#[0-9a-fA-F]{6}$")
    operating_system: OperatingSystem = Field(default_factory=_detected_operating_system)
    voice_name: AssistantVoice = "Charon"
    hud_style: HudStyle = "face"
    audio_input_device_id: str = Field(default="", max_length=512)
    audio_output_device_id: str = Field(default="", max_length=512)
    push_to_talk_enabled: bool = Field(default=False, strict=True)


class SettingsUpdate(StrictModel):
    assistant_name: str | None = Field(default=None, min_length=1, max_length=50)
    user_name: str | None = Field(default=None, max_length=80)
    accent_color: str | None = Field(
        default=None,
        pattern=r"^#[0-9a-fA-F]{6}$",
    )
    operating_system: OperatingSystem | None = None
    voice_name: AssistantVoice | None = None
    hud_style: HudStyle | None = None
    audio_input_device_id: str | None = Field(default=None, max_length=512)
    audio_output_device_id: str | None = Field(default=None, max_length=512)
    push_to_talk_enabled: bool | None = Field(default=None, strict=True)


class SettingsResponse(StrictModel):
    settings: AppSettings
    api_key_configured: bool


class ApiKeyInput(StrictModel):
    api_key: str = Field(min_length=16, max_length=512)


class ApiKeyResponse(StrictModel):
    configured: bool
