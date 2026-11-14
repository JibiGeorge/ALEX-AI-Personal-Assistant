"""
Job Application Lifecycle Management Service.
Manages application state machine transitions, notes, interview tracking, and timeline logs.
Enforces the mandatory approval gate before marking an application as applied.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.schemas.job_hunting import (
    ApplicationStatus,
    InterviewRound,
    JobApplication,
    TimelineEvent,
)
from app.services.job_hunting.approval_service import (
    ApprovalManagementService,
    ApprovalRequiredError,
)
from app.services.job_hunting.storage import JobHuntingStorage

logger = logging.getLogger(__name__)


class ApplicationManagementService:
    """Coordinates application pipeline state, tracking, and approval checks."""

    def __init__(
        self,
        storage: JobHuntingStorage,
        approval_service: ApprovalManagementService,
    ) -> None:
        self.storage = storage
        self.approval_service = approval_service

    def get_or_create_application(
        self,
        job_id: str,
        candidate_id: str = "default_candidate",
    ) -> JobApplication:
        """Retrieves existing application for a job, or creates a draft."""
        existing = self.storage.get_application_by_job(job_id)
        if existing:
            return existing

        now_iso = datetime.now(timezone.utc).isoformat()
        app = JobApplication(
            id=str(uuid4()),
            job_id=job_id,
            candidate_id=candidate_id,
            status=ApplicationStatus.DISCOVERED,
            created_at=now_iso,
            updated_at=now_iso,
        )
        saved = self.storage.save_application(app)

        self.storage.add_timeline_event(
            TimelineEvent(
                id=str(uuid4()),
                application_id=saved.id,
                event_type="APPLICATION_CREATED",
                description=f"Application record initialized for job {job_id}.",
            )
        )
        return saved

    def update_status(
        self,
        application_id: str,
        new_status: ApplicationStatus,
        notes: Optional[str] = None,
    ) -> JobApplication:
        """Transitions application status with validation and timeline logging."""
        app = self.storage.get_application(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found.")

        # Guard: Transition to APPLIED requires explicit user approval
        if new_status == ApplicationStatus.APPLIED:
            self.approval_service.verify_approval(application_id)
            if not app.applied_at:
                app.applied_at = datetime.now(timezone.utc).isoformat()

        old_status = app.status
        app.status = new_status
        if notes:
            app.notes = f"{app.notes}\n{notes}".strip() if app.notes else notes
        app.updated_at = datetime.now(timezone.utc).isoformat()

        saved = self.storage.save_application(app)

        self.storage.add_timeline_event(
            TimelineEvent(
                id=str(uuid4()),
                application_id=application_id,
                event_type="STATUS_CHANGED",
                description=f"Status transitioned from {old_status.value} to {new_status.value}.",
                metadata={"notes": notes} if notes else {},
            )
        )
        return saved

    def link_tailored_document(
        self,
        application_id: str,
        document_id: str,
    ) -> JobApplication:
        """Associates a tailored resume/cover letter with the application."""
        app = self.storage.get_application(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found.")

        app.tailored_document_id = document_id
        app.status = ApplicationStatus.TAILORED
        app.updated_at = datetime.now(timezone.utc).isoformat()
        saved = self.storage.save_application(app)

        self.storage.add_timeline_event(
            TimelineEvent(
                id=str(uuid4()),
                application_id=application_id,
                event_type="DOCUMENT_LINKED",
                description=f"Tailored resume and cover letter (ID: {document_id}) linked to application.",
            )
        )
        return saved

    def list_applications(
        self,
        status: Optional[ApplicationStatus] = None,
    ) -> List[JobApplication]:
        """Lists applications, optionally filtered by lifecycle status."""
        return self.storage.list_applications(status=status)

    def record_interview(
        self,
        application_id: str,
        round_name: str,
        scheduled_at: str,
        interviewer: Optional[str] = None,
        feedback: Optional[str] = None,
        passed: Optional[bool] = None,
    ) -> JobApplication:
        """Records an interview round on the application and logs to timeline."""
        app = self.storage.get_application(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found.")

        round_item = InterviewRound(
            round_name=round_name,
            scheduled_at=scheduled_at,
            interviewer=interviewer,
            feedback=feedback,
            passed=passed,
        )
        app.interview_rounds.append(round_item)
        if app.status in (ApplicationStatus.APPLIED, ApplicationStatus.TAILORED, ApplicationStatus.DISCOVERED):
            app.status = ApplicationStatus.INTERVIEWING
        app.updated_at = datetime.now(timezone.utc).isoformat()
        saved = self.storage.save_application(app)

        self.storage.add_timeline_event(
            TimelineEvent(
                id=str(uuid4()),
                application_id=application_id,
                event_type="INTERVIEW_SCHEDULED",
                description=f"Interview round '{round_name}' scheduled for {scheduled_at}.",
                metadata={"interviewer": interviewer, "round_name": round_name},
            )
        )
        return saved

    def get_timeline(self, application_id: str) -> List[TimelineEvent]:
        """Returns the chronological audit timeline for an application."""
        return self.storage.list_timeline_events(application_id)
