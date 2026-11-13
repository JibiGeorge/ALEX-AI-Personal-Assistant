import base64
import binascii
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileAttachment(StrictModel):
    name: str = Field(min_length=1, max_length=255)
    mime_type: Literal[
        "application/json",
        "application/pdf",
        "application/xml",
        "audio/aac",
        "audio/flac",
        "audio/mp4",
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
        "text/csv",
        "text/markdown",
        "text/plain",
        "video/mp4",
        "video/quicktime",
        "video/webm",
    ]
    data_base64: str = Field(min_length=4, max_length=11_184_812)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if "/" in value or "\\" in value or value in (".", ".."):
            raise ValueError("Attachment name must be a file name, not a path")
        return value

    @field_validator("data_base64")
    @classmethod
    def validate_data(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Attachment data must be valid base64") from exc
        if not decoded or len(decoded) > 8 * 1024 * 1024:
            raise ValueError("Attachment must be between 1 byte and 8 MiB")
        return value


class ConversationTurnRequest(StrictModel):
    conversation_id: UUID | None = None
    text: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
    ]
    attachment: FileAttachment | None = None


class ConversationTurnResponse(StrictModel):
    conversation_id: UUID
    text: str = Field(min_length=1, max_length=20000)
