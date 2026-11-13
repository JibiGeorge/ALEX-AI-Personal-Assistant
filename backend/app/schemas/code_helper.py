"""
Schemas for Single-File Interactive Code Helper (TASK-GAP-04 / GAP-04).
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CodeHelperParameters(BaseModel):
    """Parameters for the single-file interactive code helper."""
    model_config = ConfigDict(extra="ignore")

    action: str = Field(
        default="auto",
        description="Operation to perform: auto | write | edit | explain | run | build | screen_debug | optimize",
    )
    description: Optional[str] = Field(
        default="",
        description="Goal, instruction, prompt, or explanation request for the code.",
    )
    language: str = Field(
        default="python",
        description="Target programming language (e.g. python, javascript, typescript, bash, html).",
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Custom file path or filename to save generated/modified code.",
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Path to an existing code file on disk for edit, explain, run, build, or optimize.",
    )
    code: Optional[str] = Field(
        default=None,
        description="Inline code string for explain or optimize without saving to disk.",
    )
    args: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional command-line arguments to pass when executing the script with run or build.",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Maximum execution timeout in seconds when running code.",
    )

