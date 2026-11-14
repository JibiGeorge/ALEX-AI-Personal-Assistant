"""
Approval Management Service for ALEX Job Hunting Module.
Enforces the mandatory human-in-the-loop gate before any external application action.
No job application or outreach may be submitted without explicit, recorded user consent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.schemas.job_hunting import (
    ApplicationApproval,
    ApprovalChannel,
    ApprovalStatus,
    TimelineEvent,
)
from app.services.job_hunting.storage import JobHuntingStorage

logger = logging.getLogger(__name__)


class ApprovalRequiredError(RuntimeError):
    """Raised when an application action is attempted without prior user approval."""


class ApprovalManagementService:
    """Manages application approval requests and audits."""

    def __init__(self, storage: JobHuntingStorage) -> None:
        self.storage = storage

    def request_approval(
        self,
        application_id: str,
        action: str = "SUBMIT_APPLICATION",
        channel: ApprovalChannel = ApprovalChannel.UI,
    ) -> ApplicationApproval:
        """Creates a pending approval request for a job application."""
        approval = ApplicationApproval(
            id=str(uuid4()),
            application_id=application_id,
            requested_action=action,
            approval_status=ApprovalStatus.PENDING,
            approval_channel=channel,
        )
        saved = self.storage.save_approval(approval)

        self.storage.add_timeline_event(
            TimelineEvent(
                id=str(uuid4()),
                application_id=application_id,
                event_type="APPROVAL_REQUESTED",
                description=f"Approval requested for action '{action}' via {channel.value}.",
            )
        )
        return saved

    def record_decision(
        self,
        application_id: str,
        approved: bool,
        channel: ApprovalChannel = ApprovalChannel.UI,
        confirmation_text: Optional[str] = None,
    ) -> ApplicationApproval:
        """Records explicit user approval or rejection."""
        existing = self.storage.get_latest_approval(application_id)
        approval_id = existing.id if existing else str(uuid4())
        action = existing.requested_action if existing else "SUBMIT_APPLICATION"

        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        now_iso = datetime.now(timezone.utc).isoformat()

        approval = ApplicationApproval(
            id=approval_id,
            application_id=application_id,
            requested_action=action,
            approval_status=status,
            approval_channel=channel,
            user_confirmation_text=confirmation_text,
            decided_at=now_iso,
        )
        saved = self.storage.save_approval(approval)

        self.storage.add_timeline_event(
            TimelineEvent(
                id=str(uuid4()),
                application_id=application_id,
                event_type="APPROVAL_DECIDED",
                description=f"User {status.value} action '{action}' via {channel.value} (Confirmation: '{confirmation_text or 'explicit click'}').",
            )
        )
        return saved

    def verify_approval(self, application_id: str) -> bool:
        """Verifies if the application has an approved record."""
        latest = self.storage.get_latest_approval(application_id)
        if not latest or latest.approval_status != ApprovalStatus.APPROVED:
            raise ApprovalRequiredError(
                f"Application {application_id} has not received explicit user approval."
            )
        return True
