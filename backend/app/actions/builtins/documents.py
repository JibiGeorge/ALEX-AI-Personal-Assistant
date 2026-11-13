"""
Document parsing built-in action handler (TASK-P3-09).

Exposes the 'documents.parse' action for structured text, metadata,
and tabular data extraction from PDF, DOCX, XLSX, and PPTX documents.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, done, failed
from app.services.document_parser_service import (
    DocumentParserService,
    DocumentParsingError,
    FileSizeLimitExceededError,
    PageCountLimitExceededError,
    UnsupportedDocumentFormatError,
)
from app.services.file_workspace_service import FileWorkspaceService, WorkspacePathError

logger = logging.getLogger(__name__)


class ParseDocumentParameters(BaseModel):
    """Parameters for the documents.parse action."""
    model_config = ConfigDict(extra="forbid")

    path: str = Field(
        min_length=1,
        max_length=1024,
        description="Path to the document file (relative to workspace or system file path).",
    )
    max_chars: int = Field(
        default=50000,
        ge=100,
        le=500000,
        description="Maximum characters of text to extract from the document.",
    )


def register_document_actions(
    registry: ActionRegistry,
    parser: DocumentParserService,
    workspace: Optional[FileWorkspaceService] = None,
) -> None:
    """Register document extraction and parsing actions with the action registry."""

    def handle_parse(params: ParseDocumentParameters) -> ActionOutcomeResponse:
        try:
            if workspace is not None:
                # Confined within workspace sandbox
                resolved_target = workspace._resolve(params.path, allow_root=False)
            else:
                resolved_target = Path(params.path).resolve()

            parsed = parser.parse(resolved_target, max_chars=params.max_chars)
            from app.core.sanitizer import wrap_untrusted_data
            data = parsed.model_dump(mode="json")
            data["text"] = wrap_untrusted_data(parsed.text, source=f"file:{resolved_target.name}")
            return done(
                "documents.parse",
                f"Document '{resolved_target.name}' parsed successfully.",
                data=data,
            )
        except (WorkspacePathError, PermissionError) as exc:
            return failed("documents.parse", str(exc), message="Workspace boundary violation or permission denied.")
        except FileNotFoundError as exc:
            return failed("documents.parse", str(exc), message=f"Document file not found: {params.path}")
        except FileSizeLimitExceededError as exc:
            return failed("documents.parse", str(exc), message="Document exceeds 25 MB size limit.")
        except PageCountLimitExceededError as exc:
            return failed("documents.parse", str(exc), message="Document exceeds maximum page/slide count limit.")
        except UnsupportedDocumentFormatError as exc:
            return failed("documents.parse", str(exc), message="Unsupported document file format.")
        except (DocumentParsingError, ValueError) as exc:
            return failed("documents.parse", str(exc), message="Document parsing failed.")
        except Exception as exc:
            logger.exception("Unexpected error parsing document %s: %s", params.path, exc)
            return failed("documents.parse", str(exc), message="Unexpected document parsing error.")

    registry.register(
        ActionDefinition(
            action_id="documents.parse",
            name="Parse document",
            description="Deeply parse and extract text, metadata, and tables from PDF, DOCX, XLSX, and PPTX documents.",
            category="documents",
            parameters=ParseDocumentParameters,
            handler=handle_parse,
            timeout_seconds=30,
        )
    )

