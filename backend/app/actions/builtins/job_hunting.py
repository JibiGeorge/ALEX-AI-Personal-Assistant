"""
Action Registry integration for ALEX Job Hunting Module.
Exposes voice, chat, and agent-callable actions with strict human approval gates.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import done, failed
from app.schemas.job_hunting import ApplicationStatus, WorkModality
from app.services.job_hunting.job_hunting_service import JobHuntingService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Action Parameter Schemas
# ---------------------------------------------------------------------------


class JobSearchParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: Optional[str] = Field(None, description="Job title, keywords, or role (e.g. 'full-stack developer', 'React developer')")
    location: Optional[str] = Field(None, description="Preferred location, 'Worldwide', or 'Remote'")
    modalities: Optional[List[str]] = Field(None, description="Work modalities: 'remote', 'hybrid', 'onsite'")
    max_results: int = Field(5, description="Maximum number of listings to return (1-25)")


class JobAnalyseParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: Optional[str] = Field(None, description="URL of the job posting (LinkedIn, Greenhouse, Lever, etc.)")
    text: Optional[str] = Field(None, description="Raw job description or alert text to extract")
    title: Optional[str] = Field(None, description="Optional job title if known")
    company: Optional[str] = Field(None, description="Optional company name if known")
    modality: Optional[str] = Field("remote", description="Work modality: 'remote', 'hybrid', 'onsite'")


class JobMatchResumeParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: Optional[str] = Field(None, description="ID of the job to match against verified resume. If omitted, uses the most recent job.")


class JobPrepareApplicationParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: Optional[str] = Field(None, description="ID of the target job listing. If omitted, uses the most recent job.")
    instructions: Optional[str] = Field(None, description="Custom focus or notes for the resume and cover letter")


class JobListApprovalsParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    limit: int = Field(10, description="Max number of pending approvals to list")


class JobTrackApplicationParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: Optional[str] = Field(None, description="Filter by status: 'discovered', 'analyzed', 'tailored', 'ready_to_apply', 'applied', 'interviewing', 'offered'")
    application_id: Optional[str] = Field(None, description="Specific application ID to inspect")


class JobListInterviewsParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    application_id: Optional[str] = Field(None, description="Filter interviews by application ID")


class SubmitApplicationActionParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    application_id: str = Field(..., description="Unique ID of the job application to submit")
    confirm: bool = Field(True, description="Explicit confirmation to submit the application")


# ---------------------------------------------------------------------------
# Registration Function
# ---------------------------------------------------------------------------


def register_job_hunting_actions(
    registry: ActionRegistry,
    job_service: JobHuntingService,
) -> None:
    """Registers voice/chat/agent accessible actions for job hunting."""

    # 1. job_search
    async def handle_job_search(params: JobSearchParams):
        try:
            mods = None
            if params.modalities:
                mods = [WorkModality(m.lower()) for m in params.modalities if m.lower() in ("remote", "hybrid", "onsite")]

            results = await job_service.discover_jobs(
                query=params.query,
                location=params.location,
                modalities=mods,
                max_results=params.max_results,
            )

            job_summaries = [
                {
                    "id": j.id,
                    "title": j.title,
                    "company": j.company_name,
                    "location": j.location,
                    "modality": j.modality.value if hasattr(j.modality, "value") else str(j.modality),
                    "source": j.source.value if hasattr(j.source, "value") else str(j.source),
                    "source_url": j.source_url,
                    "experience": f"{j.experience_required_min}-{j.experience_required_max} yrs",
                    "skills": j.required_skills[:6],
                }
                for j in results[:5]
            ]

            summary_text = (
                f"Discovered {len(results)} jobs matching '{params.query or 'developer roles'}'."
            )
            if results:
                summary_text += f" Top opening: {results[0].title} at {results[0].company_name} ({results[0].location or 'Remote'})."

            return done(
                "job_search",
                summary_text,
                data={"count": len(results), "jobs": job_summaries},
            )
        except Exception as exc:
            logger.error("job_search action failed: %s", exc)
            return failed("job_search", str(exc))

    # 2. job_analyse
    async def handle_job_analyse(params: JobAnalyseParams):
        try:
            target_job = None
            modality_enum = WorkModality(params.modality.lower()) if params.modality and params.modality.lower() in ("remote", "hybrid", "onsite") else WorkModality.REMOTE

            if params.url:
                if "linkedin.com/jobs" in params.url:
                    target_job = await job_service.ingest_linkedin_url(
                        url=params.url,
                        optional_title=params.title,
                        optional_company=params.company,
                        modality=modality_enum,
                    )
                else:
                    target_job = await job_service.ingest_direct_url(
                        url=params.url,
                        title=params.title,
                        company=params.company,
                        raw_text=params.text,
                        modality=modality_enum,
                    )
            elif params.text:
                if "linkedin" in params.text.lower() and "job" in params.text.lower():
                    alert_jobs = await job_service.ingest_linkedin_alert(params.text, default_modality=modality_enum)
                    if alert_jobs:
                        target_job = alert_jobs[0]
                if not target_job:
                    target_job = await job_service.extract_job_details(params.text, source_url="")
            else:
                # Use most recent job if none specified
                recent = job_service.list_jobs(limit=1)
                if recent:
                    target_job = recent[0]

            if not target_job:
                return failed("job_analyse", "Please provide a job posting URL or job description text to analyse.")

            return done(
                "job_analyse",
                f"Analysed {target_job.title} at {target_job.company_name}. Extracted {len(target_job.required_skills)} required skills.",
                data={
                    "id": target_job.id,
                    "title": target_job.title,
                    "company": target_job.company_name,
                    "modality": target_job.modality.value if hasattr(target_job.modality, "value") else str(target_job.modality),
                    "required_skills": target_job.required_skills,
                    "preferred_skills": target_job.preferred_skills,
                    "experience_required": f"{target_job.experience_required_min}-{target_job.experience_required_max} yrs",
                },
            )
        except Exception as exc:
            logger.error("job_analyse action failed: %s", exc)
            return failed("job_analyse", str(exc))

    # 3. job_match_resume
    def handle_job_match_resume(params: JobMatchResumeParams):
        try:
            job_id = params.job_id
            if not job_id:
                recent = job_service.list_jobs(limit=1)
                if not recent:
                    return failed("job_match_resume", "No job listings found. Discover jobs first with job_search.")
                job_id = recent[0].id

            target_job = job_service.get_job(job_id)
            if not target_job:
                return failed("job_match_resume", f"Job {job_id} not found.")

            score = job_service.calculate_match(job_id)
            return done(
                "job_match_resume",
                f"Calculated {score.match_percentage}% compatibility for {target_job.title} at {target_job.company_name}. Recommendation: {score.ai_recommendation}",
                data=score.model_dump(),
            )
        except Exception as exc:
            logger.error("job_match_resume action failed: %s", exc)
            return failed("job_match_resume", str(exc))

    # 4. job_prepare_application
    async def handle_job_prepare_application(params: JobPrepareApplicationParams):
        try:
            job_id = params.job_id
            if not job_id:
                recent = job_service.list_jobs(limit=1)
                if not recent:
                    return failed("job_prepare_application", "No job listings found. Discover jobs first with job_search.")
                job_id = recent[0].id

            target_job = job_service.get_job(job_id)
            if not target_job:
                return failed("job_prepare_application", f"Job {job_id} not found.")

            # Generate tailored resume & cover letter (never fabricates experience)
            doc = await job_service.tailor_resume_package(job_id, custom_instructions=params.instructions)

            return done(
                "job_prepare_application",
                f"Application package prepared for {target_job.title} at {target_job.company_name} (Resume & Letter v{doc.version_number}). Action is queued for your explicit confirmation before submission.",
                data={
                    "job_id": job_id,
                    "document_id": doc.id,
                    "version": doc.version_number,
                    "requires_user_approval": True,
                    "approval_status": "pending",
                    "ats_keywords": doc.ats_keywords_included,
                    "notice": "Never auto-submits. Requires user approval in the Approvals queue.",
                },
            )
        except Exception as exc:
            logger.error("job_prepare_application action failed: %s", exc)
            return failed("job_prepare_application", str(exc))

    # 5. job_list_approvals
    def handle_job_list_approvals(params: JobListApprovalsParams):
        try:
            approvals = job_service.list_pending_approvals(limit=params.limit)
            return done(
                "job_list_approvals",
                f"Found {len(approvals)} application action(s) awaiting your explicit confirmation.",
                data={
                    "count": len(approvals),
                    "approvals": [
                        {
                            "id": a.id,
                            "application_id": a.application_id,
                            "requested_action": a.requested_action,
                            "approval_status": a.approval_status.value if hasattr(a.approval_status, "value") else str(a.approval_status),
                            "created_at": a.created_at,
                        }
                        for a in approvals
                    ],
                },
            )
        except Exception as exc:
            logger.error("job_list_approvals action failed: %s", exc)
            return failed("job_list_approvals", str(exc))

    # 6. job_track_application
    def handle_job_track_application(params: JobTrackApplicationParams):
        try:
            if params.application_id:
                app = job_service.get_application(params.application_id)
                if not app:
                    return failed("job_track_application", f"Application {params.application_id} not found.")
                return done(
                    "job_track_application",
                    f"Application {app.id} is currently '{app.status.value}'.",
                    data=app.model_dump(),
                )

            status_enum = None
            if params.status:
                try:
                    status_enum = ApplicationStatus(params.status.lower())
                except ValueError:
                    pass

            apps = job_service.list_applications(status=status_enum)
            return done(
                "job_track_application",
                f"Tracking {len(apps)} applications in your pipeline.",
                data={
                    "count": len(apps),
                    "applications": [
                        {
                            "id": a.id,
                            "job_id": a.job_id,
                            "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                            "applied_at": a.applied_at,
                            "notes": a.notes,
                            "interview_rounds_count": len(a.interview_rounds or []),
                        }
                        for a in apps
                    ],
                },
            )
        except Exception as exc:
            logger.error("job_track_application action failed: %s", exc)
            return failed("job_track_application", str(exc))

    # 7. job_list_interviews
    def handle_job_list_interviews(params: JobListInterviewsParams):
        try:
            apps = job_service.list_applications()
            rounds = []
            for app in apps:
                if params.application_id and app.id != params.application_id:
                    continue
                job = job_service.get_job(app.job_id)
                for r in (app.interview_rounds or []):
                    rounds.append({
                        "application_id": app.id,
                        "company": job.company_name if job else "Unknown",
                        "role": job.title if job else "Unknown",
                        "round_name": r.round_name,
                        "scheduled_at": r.scheduled_at,
                        "interviewer": r.interviewer,
                        "feedback": r.feedback,
                        "passed": r.passed,
                    })

            rounds.sort(key=lambda x: x.get("scheduled_at", ""), reverse=True)
            return done(
                "job_list_interviews",
                f"You have {len(rounds)} interview round(s) logged.",
                data={"count": len(rounds), "interviews": rounds},
            )
        except Exception as exc:
            logger.error("job_list_interviews action failed: %s", exc)
            return failed("job_list_interviews", str(exc))

    # 8. Submit Application - Strictly gated by human approval
    def handle_submit(params: SubmitApplicationActionParams):
        try:
            # Human-in-the-loop verification
            job_service.application_service.approval_service.verify_approval(params.application_id)
            app = job_service.update_application_status(
                application_id=params.application_id,
                status=ApplicationStatus.APPLIED,
                notes="Submitted via verified human approval.",
            )
            return done(
                "job_hunting.submit_application",
                f"Application {params.application_id} successfully submitted with verified user approval.",
                data={"application_id": app.id, "status": app.status.value},
            )
        except Exception as exc:
            logger.warning("Attempted submission blocked by approval check: %s", exc)
            return failed("job_hunting.submit_application", f"Submission Blocked: {exc}")

    # -----------------------------------------------------------------------
    # Register Core Requested Actions
    # -----------------------------------------------------------------------

    registry.register(
        ActionDefinition(
            action_id="job_search",
            name="Search and Discover Job Listings",
            description="Search for developer jobs matching user preferences (roles, tech stack, location, remote/hybrid). Supports natural language queries like 'Alex, find full-stack developer jobs' or 'Find remote React jobs worldwide'.",
            category="job_hunting",
            parameters=JobSearchParams,
            handler=handle_job_search,
            timeout_seconds=30,
            requires_confirmation=False,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="job_analyse",
            name="Analyse Job Posting",
            description="Extract and analyse requirements, technical skills, and seniority from a LinkedIn, Greenhouse, Lever URL or job description text. e.g., 'Analyse this LinkedIn job'.",
            category="job_hunting",
            parameters=JobAnalyseParams,
            handler=handle_job_analyse,
            timeout_seconds=30,
            requires_confirmation=False,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="job_match_resume",
            name="Compare Job With Resume",
            description="Evaluates 10-factor weighted compatibility between candidate's verified master resume and a target job. e.g., 'Compare this job with my resume'.",
            category="job_hunting",
            parameters=JobMatchResumeParams,
            handler=handle_job_match_resume,
            timeout_seconds=20,
            requires_confirmation=False,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="job_prepare_application",
            name="Prepare Tailored Application Package",
            description="Synthesizes ATS-optimized tailored resume and personalized cover letter. Queues application for explicit human approval before submission. e.g., 'Prepare my application'.",
            category="job_hunting",
            parameters=JobPrepareApplicationParams,
            handler=handle_job_prepare_application,
            timeout_seconds=35,
            requires_confirmation=False,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="job_list_approvals",
            name="List Pending Application Approvals",
            description="Lists all job application actions awaiting explicit user confirmation. e.g., 'Show my pending approvals'.",
            category="job_hunting",
            parameters=JobListApprovalsParams,
            handler=handle_job_list_approvals,
            timeout_seconds=15,
            requires_confirmation=False,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="job_track_application",
            name="Track Job Applications",
            description="View application pipeline statuses, notes, and milestones. e.g., 'Show my pending applications' or 'Track my applications'.",
            category="job_hunting",
            parameters=JobTrackApplicationParams,
            handler=handle_job_track_application,
            timeout_seconds=15,
            requires_confirmation=False,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="job_list_interviews",
            name="List Scheduled Interviews",
            description="List scheduled technical interviews, screens, and debrief notes. e.g., 'Show my interviews'.",
            category="job_hunting",
            parameters=JobListInterviewsParams,
            handler=handle_job_list_interviews,
            timeout_seconds=15,
            requires_confirmation=False,
        )
    )

    # -----------------------------------------------------------------------
    # Register Legacy Aliases & Submission Gate
    # -----------------------------------------------------------------------

    registry.register(
        ActionDefinition(
            action_id="job_hunting.discover",
            name="Discover Job Opportunities",
            description="Legacy alias for job_search.",
            category="job_hunting",
            parameters=JobSearchParams,
            handler=handle_job_search,
            timeout_seconds=30,
            requires_confirmation=False,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="job_hunting.match",
            name="Calculate Job Match Score",
            description="Legacy alias for job_match_resume.",
            category="job_hunting",
            parameters=JobMatchResumeParams,
            handler=handle_job_match_resume,
            timeout_seconds=20,
            requires_confirmation=False,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="job_hunting.tailor_resume",
            name="Tailor Resume and Cover Letter",
            description="Legacy alias for job_prepare_application.",
            category="job_hunting",
            parameters=JobPrepareApplicationParams,
            handler=handle_job_prepare_application,
            timeout_seconds=35,
            requires_confirmation=False,
        )
    )

    registry.register(
        ActionDefinition(
            action_id="job_hunting.submit_application",
            name="Submit Job Application",
            description="Submits a prepared job application. REQUIRES EXPLICIT USER APPROVAL. AI cannot bypass approval.",
            category="job_hunting",
            parameters=SubmitApplicationActionParams,
            handler=handle_submit,
            timeout_seconds=20,
            requires_confirmation=True,
        )
    )
