"""
Schemas for Autonomous Multi-File Dev Agent (TASK-GAP-03 / GAP-03).
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DevAgentParameters(BaseModel):
    """Parameters for the autonomous multi-file dev agent."""
    model_config = ConfigDict(extra="ignore")

    description: str = Field(
        ...,
        min_length=3,
        description="Detailed description of the application or system to build.",
    )
    language: str = Field(
        default="python",
        description="Target programming language (e.g. python, javascript, typescript, html).",
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Optional directory / folder name for the project.",
    )
    timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Execution timeout in seconds for verifying and running the project.",
    )
    open_editor: bool = Field(
        default=True,
        description="Whether to attempt opening the project directory in VS Code or system file explorer.",
    )
    auto_fix: bool = Field(
        default=True,
        description="Whether to autonomously parse tracebacks and fix syntax/import/runtime errors.",
    )

