from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class PairingInitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pairing_code: str = Field(description="8-character unambiguous human-readable pairing code")
    qr_data_uri: str = Field(description="Base64 data URI of QR code image for instant mobile pairing")
    pairing_url: str = Field(description="Direct alex:// or https:// pairing deep link URL")
    lan_host: str = Field(description="Local network IP address of the Alex host")
    port: int = Field(default=8766, description="LAN Gateway port")
    expires_in_seconds: int = Field(default=300, description="Time until pairing code expires")


class PairingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pairing_code: str = Field(min_length=6, max_length=16, description="The pairing code displayed on desktop")
    device_name: Optional[str] = Field(default="Mobile Client", max_length=128)
    device_platform: Optional[str] = Field(default="iOS", max_length=64)


class PairingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    session_token: str
    salt: str
    iterations: int = 200000
    message: str = "Pairing successful"


class EncryptedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iv: str = Field(description="Base64 encoded 12-byte IV for AES-GCM")
    ciphertext: str = Field(description="Base64 encoded ciphertext + 16-byte authentication tag")


class DecryptedPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = Field(description="Message type, e.g. ping, turn, action_approval, audio_frame")
    payload: Any = None


class MobileGatewayStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool
    lan_ip: str
    port: int
    paired_devices: int
    pending_approvals: int


class MobileTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, description="User spoken or typed text prompt")
    conversation_id: Optional[str] = Field(default=None, description="Optional conversation UUID")
    synthesize_voice: bool = Field(default=True, description="Whether to generate TTS audio response")
    voice: str = Field(default="", description="Optional custom voice name")
    language: str = Field(default="", description="Spoken language code")


class MobileTurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str
    audio_base64: Optional[str] = None
    sample_rate: int = 24000
    voice_used: str = ""


class MobileMemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    key: str
    value: str
    updated: Optional[str] = None


class MobileMemoriesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memories: list[MobileMemoryItem]


class ActionApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    signature: Optional[str] = Field(default=None, description="Optional cryptographic signature of approval decision")


class PendingApprovalItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    action_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    created_at: float
    timeout: float


class PendingApprovalsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approvals: list[PendingApprovalItem]


class MobileUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    filename: str = Field(description="Sanitized unique filename")
    saved_path: str = Field(description="Full path on host where file was saved")
    size: int = Field(description="Uploaded file size in bytes")
    content_type: Optional[str] = Field(default=None, description="MIME content type")


class MobileUploadedFileInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    size: int
    modified_at: float
    download_url: str


class MobileUploadsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uploads: list[MobileUploadedFileInfo]
    total: int




