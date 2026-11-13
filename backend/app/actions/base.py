"""
Standardized Five-Word Outcome Contract (TASK-P3-08).

Defines the ToolOutcome enum and ActionOutcomeResponse schema enforcing the
Mark-LVI five-word outcome contract across all Alex AI action handlers:
- DONE: verified to have completed successfully
- UNVERIFIED: initiated, but state could not be verified
- FAILED: could not be completed
- ASK: requires user clarification or confirmation
- STARTED: asynchronous process initiated cleanly and still running
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ToolOutcome(str, Enum):
    """The canonical five outcome states for action execution."""
    DONE = "done"             # Action verified to have completed successfully
    UNVERIFIED = "unverified" # Request initiated, but state could not be verified
    FAILED = "failed"         # Action could not be completed
    ASK = "ask"               # Requires user clarification or approval
    STARTED = "started"       # Asynchronous process initiated cleanly; still running


class ActionOutcomeResponse(BaseModel):
    """Standardized action response contract implementing the five-word outcome protocol."""
    model_config = ConfigDict(extra="allow")

    status: ToolOutcome
    action: str
    message: str
    data: Any = Field(default_factory=dict)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Backward-compatibility property: True ONLY when operation has completed successfully.
        NEVER returns True for STARTED, UNVERIFIED, FAILED, or ASK.
        """
        return self.status == ToolOutcome.DONE

    @property
    def is_done(self) -> bool:
        """True only when the operation has reached verified completion."""
        return self.status == ToolOutcome.DONE

    @property
    def is_started(self) -> bool:
        """True when operation was initiated asynchronously and is still running."""
        return self.status == ToolOutcome.STARTED

    @property
    def is_pending(self) -> bool:
        """True when operation is non-terminal (either still running or unverified)."""
        return self.status in (ToolOutcome.STARTED, ToolOutcome.UNVERIFIED)

    @property
    def requires_clarification(self) -> bool:
        """True when user confirmation or input is required."""
        return self.status == ToolOutcome.ASK

    @property
    def is_failed(self) -> bool:
        """True when operation encountered an execution failure."""
        return self.status == ToolOutcome.FAILED

    def __getitem__(self, item: Any) -> Any:
        if isinstance(self.data, (dict, list)):
            return self.data[item]
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        if isinstance(self.data, dict):
            return self.data.get(item, default)
        return getattr(self, item, default)

    def __contains__(self, item: Any) -> bool:
        if isinstance(self.data, (dict, list)):
            return item in self.data
        return hasattr(self, item)


def done(
    action: str,
    message: str = "Operation completed successfully.",
    data: Any = None,
    **kwargs: Any,
) -> ActionOutcomeResponse:
    """Create a verified successful action outcome (DONE)."""
    if isinstance(data, dict):
        merged_data = dict(data)
        merged_data.update(kwargs)
    elif data is None and kwargs:
        merged_data = kwargs
    else:
        merged_data = data if data is not None else {}
    return ActionOutcomeResponse(
        status=ToolOutcome.DONE,
        action=action,
        message=message,
        data=merged_data,
    )


def unverified(
    action: str,
    message: str = "Operation initiated but state could not be verified.",
    data: Any = None,
    **kwargs: Any,
) -> ActionOutcomeResponse:
    """Create an unverified action outcome (UNVERIFIED). Never to be spoken as success."""
    if isinstance(data, dict):
        merged_data = dict(data)
        merged_data.update(kwargs)
    elif data is None and kwargs:
        merged_data = kwargs
    else:
        merged_data = data if data is not None else {}
    return ActionOutcomeResponse(
        status=ToolOutcome.UNVERIFIED,
        action=action,
        message=message,
        data=merged_data,
    )


def failed(
    action: str,
    error: str,
    message: str = "Operation failed.",
    data: Any = None,
    **kwargs: Any,
) -> ActionOutcomeResponse:
    """Create a failed action outcome (FAILED) with diagnostic error reason."""
    if isinstance(data, dict):
        merged_data = dict(data)
        merged_data.update(kwargs)
    elif data is None and kwargs:
        merged_data = kwargs
    else:
        merged_data = data if data is not None else {}
    return ActionOutcomeResponse(
        status=ToolOutcome.FAILED,
        action=action,
        message=message,
        error=error,
        data=merged_data,
    )


def ask(
    action: str,
    question: str,
    message: str = "User confirmation or input required.",
    data: Any = None,
    **kwargs: Any,
) -> ActionOutcomeResponse:
    """Create an outcome indicating user input or confirmation is required (ASK)."""
    if isinstance(data, dict):
        merged_data = dict(data)
        merged_data.update(kwargs)
    elif data is None and kwargs:
        merged_data = kwargs
    else:
        merged_data = data if data is not None else {}
    return ActionOutcomeResponse(
        status=ToolOutcome.ASK,
        action=action,
        message=message,
        error=question,
        data=merged_data,
    )


def started(
    action: str,
    message: str = "Process initiated in background.",
    data: Any = None,
    **kwargs: Any,
) -> ActionOutcomeResponse:
    """Create an asynchronous in-progress outcome (STARTED)."""
    if isinstance(data, dict):
        merged_data = dict(data)
        merged_data.update(kwargs)
    elif data is None and kwargs:
        merged_data = kwargs
    else:
        merged_data = data if data is not None else {}
    return ActionOutcomeResponse(
        status=ToolOutcome.STARTED,
        action=action,
        message=message,
        data=merged_data,
    )
