"""
Unified Job Hunting Coordinator Service for ALEX AI Desktop Assistant.
Orchestrates discovery, extraction, profile, matching, tailoring, applications, and approvals.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, List, Optional

from app.schemas.job_hunting import (
    AdapterStatusReport,
    ApplicationApproval,
    ApplicationStatus,
    ApprovalChannel,
    BulkExpiryResponse,
    CandidatePreferences,
    CandidateProfile,
    CareerRecommendations,
    CheckExpiryResponse,
    CompatibilityScore,
    DiscoveryRunRecord,
    JobApplication,
    JobComparisonItem,
    JobComparisonResponse,
    JobListing,
    JobSource,
    ScheduleDiscoveryConfig,
    TailoredDocument,
    TimelineEvent,
    WorkModality,
)
from app.services.job_hunting.adapters import (
    CompanyCareersJobAdapter,
    DirectUrlJobAdapter,
    GreenhouseJobAdapter,
    LeverJobAdapter,
    LinkedInAlertJobAdapter,
    LinkedInUrlJobAdapter,
    RemoteOKJobAdapter,
    WebSearchJobAdapter,
)
from app.services.job_hunting.application_service import ApplicationManagementService
from app.services.job_hunting.approval_service import ApprovalManagementService
from app.services.job_hunting.discovery_service import JobDiscoveryService
from app.services.job_hunting.extraction import JobExtractionService
from app.services.job_hunting.matching_service import JobMatchingService
from app.services.job_hunting.profile_service import CandidateProfileService
from app.services.job_hunting.scheduler import JobDiscoveryScheduler
from app.services.job_hunting.storage import JobHuntingStorage
from app.services.job_hunting.tailoring_service import ResumeTailoringService

logger = logging.getLogger(__name__)


class JobHuntingService:
    """Unified service interface for the ALEX Job Hunting module."""

    def __init__(
        self,
        data_dir: Path,
        settings_service: Any = None,
        document_parser_service: Any = None,
        web_search_service: Any = None,
        model_ladder_service: Any = None,
    ) -> None:
        self.data_dir = data_dir
        self.db_path = data_dir / "job_hunting.db"
        self.storage = JobHuntingStorage(self.db_path)

        self.profile_service = CandidateProfileService(
            storage=self.storage,
            document_parser_service=document_parser_service,
        )
        self.extraction_service = JobExtractionService(
            settings_service=settings_service,
        )
        self.matching_service = JobMatchingService(
            storage=self.storage,
            settings_service=settings_service,
            model_ladder_service=model_ladder_service,
        )
        self.tailoring_service = ResumeTailoringService(
            storage=self.storage,
            settings_service=settings_service,
            workspace_root=self.data_dir / "workspace",
            model_ladder_service=model_ladder_service,
        )
        self.approval_service = ApprovalManagementService(
            storage=self.storage,
        )
        self.application_service = ApplicationManagementService(
            storage=self.storage,
            approval_service=self.approval_service,
        )
        self.discovery_service = JobDiscoveryService(
            storage=self.storage,
            web_search_service=web_search_service,
        )
        self.scheduler = JobDiscoveryScheduler(
            discovery_service=self.discovery_service,
            profile_service=self.profile_service,
        )

    # -----------------------------------------------------------------------
    # Candidate Profile Operations
    # -----------------------------------------------------------------------

    def get_profile(self) -> CandidateProfile:
        return self.profile_service.get_profile()

    def update_profile(self, profile: CandidateProfile) -> CandidateProfile:
        return self.profile_service.update_profile(profile)

    def update_preferences(self, preferences: CandidatePreferences) -> CandidateProfile:
        return self.profile_service.update_preferences(preferences)

    def ingest_resume_file(self, file_path: Path) -> CandidateProfile:
        return self.profile_service.ingest_resume_file(file_path)

    # -----------------------------------------------------------------------
    # Job Discovery & Ingestion Operations
    # -----------------------------------------------------------------------

    def list_adapters(self) -> List[AdapterStatusReport]:
        return self.discovery_service.list_adapters()

    async def discover_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        modalities: Optional[List[WorkModality]] = None,
        max_results: int = 10,
    ) -> List[JobListing]:
        profile = self.get_profile()
        return await self.discovery_service.discover_jobs(
            query=query,
            location=location,
            modalities=modalities,
            max_results=max_results,
            profile=profile,
        )

    async def ingest_linkedin_alert(
        self,
        alert_text: str,
        default_modality: WorkModality = WorkModality.REMOTE,
    ) -> List[JobListing]:
        return await self.discovery_service.ingest_linkedin_alert(
            alert_text=alert_text,
            default_modality=default_modality,
        )

    async def ingest_linkedin_url(
        self,
        url: str,
        optional_title: Optional[str] = None,
        optional_company: Optional[str] = None,
        optional_snippet: Optional[str] = None,
        modality: WorkModality = WorkModality.REMOTE,
    ) -> JobListing:
        return await self.discovery_service.ingest_linkedin_url(
            url=url,
            optional_title=optional_title,
            optional_company=optional_company,
            optional_snippet=optional_snippet,
            modality=modality,
        )

    async def ingest_linkedin_data_export(
        self,
        file_bytes: Optional[bytes] = None,
        file_text: Optional[str] = None,
        filename: str = "export.csv",
        default_modality: WorkModality = WorkModality.REMOTE,
    ) -> List[JobListing]:
        return await self.discovery_service.ingest_linkedin_data_export(
            file_bytes=file_bytes,
            file_text=file_text,
            filename=filename,
            default_modality=default_modality,
        )

    async def ingest_direct_url(
        self,
        url: str,
        title: Optional[str] = None,
        company: Optional[str] = None,
        raw_text: Optional[str] = None,
        modality: WorkModality = WorkModality.REMOTE,
    ) -> JobListing:
        return await self.discovery_service.ingest_direct_url(
            url=url,
            title=title,
            company=company,
            raw_text=raw_text,
            modality=modality,
        )

    async def ingest_greenhouse(
        self,
        board_token: str,
        filter_role: Optional[str] = None,
        max_results: int = 15,
    ) -> List[JobListing]:
        return await self.discovery_service.ingest_greenhouse(
            board_token=board_token,
            filter_role=filter_role,
            max_results=max_results,
        )

    async def ingest_lever(
        self,
        company_id: str,
        filter_role: Optional[str] = None,
        max_results: int = 15,
    ) -> List[JobListing]:
        return await self.discovery_service.ingest_lever(
            company_id=company_id,
            filter_role=filter_role,
            max_results=max_results,
        )

    async def ingest_company_careers(
        self,
        url: str,
        title: Optional[str] = None,
        company: Optional[str] = None,
        raw_text: Optional[str] = None,
        modality: WorkModality = WorkModality.REMOTE,
    ) -> JobListing:
        return await self.discovery_service.ingest_company_careers(
            url=url,
            title=title,
            company=company,
            raw_text=raw_text,
            modality=modality,
        )

    async def check_job_expiry(self, job_id: str) -> CheckExpiryResponse:
        return await self.discovery_service.check_job_expiry(job_id)

    async def bulk_check_expiry(self, limit: int = 20) -> BulkExpiryResponse:
        return await self.discovery_service.bulk_check_expiry(limit=limit)

    def list_discovery_runs(self, limit: int = 50) -> List[DiscoveryRunRecord]:
        return self.discovery_service.list_discovery_runs(limit=limit)

    def get_schedule_config(self) -> ScheduleDiscoveryConfig:
        return self.scheduler.get_config()

    def update_schedule_config(self, enabled: bool, interval_hours: int) -> ScheduleDiscoveryConfig:
        return self.scheduler.update_config(enabled=enabled, interval_hours=interval_hours)

    async def extract_job_details(
        self,
        raw_text: str,
        source_url: str = "",
    ) -> JobListing:
        job = await self.extraction_service.extract_job_details(
            raw_text=raw_text,
            source_url=source_url,
        )
        return self.storage.save_job(job)

    # -----------------------------------------------------------------------
    # Job Listings & Matching Operations
    # -----------------------------------------------------------------------

    def list_jobs(
        self,
        status: Optional[ApplicationStatus] = None,
        modality: Optional[WorkModality] = None,
        source: Optional[JobSource] = None,
        min_salary: Optional[float] = None,
        experience_min: Optional[int] = None,
        experience_max: Optional[int] = None,
        is_expired: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[JobListing]:
        return self.storage.list_jobs(
            status=status,
            modality=modality,
            source=source,
            min_salary=min_salary,
            experience_min=experience_min,
            experience_max=experience_max,
            is_expired=is_expired,
            search=search,
            limit=limit,
            offset=offset,
        )

    def get_job(self, job_id: str) -> Optional[JobListing]:
        return self.storage.get_job(job_id)

    def calculate_match(self, job_id: str) -> CompatibilityScore:
        job = self.storage.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found.")
        profile = self.get_profile()
        score = self.matching_service.calculate_match(job=job, profile=profile)

        # Update job status to analyzed
        job.status = ApplicationStatus.ANALYZED
        self.storage.save_job(job)

        # Ensure application tracking initialized
        app = self.application_service.get_or_create_application(job_id=job.id, candidate_id=profile.id)
        if app.status == ApplicationStatus.DISCOVERED:
            self.application_service.update_status(app.id, ApplicationStatus.ANALYZED)

        return score

    async def calculate_match_async(self, job_id: str) -> CompatibilityScore:
        job = self.storage.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found.")
        profile = self.get_profile()
        score = await self.matching_service.calculate_match_async(job=job, profile=profile)

        # Update job status to analyzed
        job.status = ApplicationStatus.ANALYZED
        self.storage.save_job(job)

        # Ensure application tracking initialized
        app = self.application_service.get_or_create_application(job_id=job.id, candidate_id=profile.id)
        if app.status == ApplicationStatus.DISCOVERED:
            self.application_service.update_status(app.id, ApplicationStatus.ANALYZED)

        return score

    def get_score_for_job(self, job_id: str) -> Optional[CompatibilityScore]:
        return self.storage.get_score_for_job(job_id)

    # -----------------------------------------------------------------------
    # Resume Tailoring, Cover Letters & Resume Studio Operations
    # -----------------------------------------------------------------------

    async def tailor_resume_package(
        self,
        job_id: str,
        custom_instructions: Optional[str] = None,
    ) -> TailoredDocument:
        job = self.storage.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found.")
        profile = self.get_profile()
        doc = await self.tailoring_service.generate_tailored_package(
            job=job,
            profile=profile,
            custom_instructions=custom_instructions,
        )

        # Link document to application
        app = self.application_service.get_or_create_application(job_id=job.id, candidate_id=profile.id)
        self.application_service.link_tailored_document(app.id, doc.id)

        # Request user approval to prepare for review
        self.approval_service.request_approval(app.id, action="SUBMIT_APPLICATION", channel=ApprovalChannel.UI)

        return doc

    def get_tailored_document(self, job_id: str) -> Optional[TailoredDocument]:
        return self.storage.get_tailored_document_for_job(job_id)

    def get_tailored_document_by_id(self, doc_id: str) -> Optional[TailoredDocument]:
        return self.storage.get_tailored_document(doc_id)

    def list_tailored_documents_for_job(self, job_id: str) -> List[TailoredDocument]:
        return self.tailoring_service.list_versions_for_job(job_id)

    def update_tailored_document(
        self,
        doc_id: str,
        resume_markdown: Optional[str] = None,
        cover_letter_markdown: Optional[str] = None,
        create_new_version: bool = False,
    ) -> TailoredDocument:
        return self.tailoring_service.update_tailored_document(
            doc_id=doc_id,
            resume_markdown=resume_markdown,
            cover_letter_markdown=cover_letter_markdown,
            create_new_version=create_new_version,
        )

    def get_document_download(
        self,
        doc_id: str,
        doc_type: str = "resume",
        format_type: str = "pdf",
    ) -> Tuple[bytes, str, str]:
        return self.tailoring_service.get_document_bytes(
            doc_id=doc_id,
            doc_type=doc_type,
            format_type=format_type,
        )

    # -----------------------------------------------------------------------
    # Application & Approval Management
    # -----------------------------------------------------------------------

    def list_applications(self, status: Optional[ApplicationStatus] = None) -> List[JobApplication]:
        return self.application_service.list_applications(status=status)

    def get_application(self, application_id: str) -> Optional[JobApplication]:
        return self.storage.get_application(application_id)

    def update_application_status(
        self,
        application_id: str,
        status: ApplicationStatus,
        notes: Optional[str] = None,
    ) -> JobApplication:
        return self.application_service.update_status(application_id, status, notes=notes)

    def decide_approval(
        self,
        application_id: str,
        approved: bool,
        channel: ApprovalChannel = ApprovalChannel.UI,
        confirmation_text: Optional[str] = None,
    ) -> ApplicationApproval:
        approval = self.approval_service.record_decision(
            application_id=application_id,
            approved=approved,
            channel=channel,
            confirmation_text=confirmation_text,
        )
        # If approved, transition application to APPROVED
        if approved:
            self.application_service.update_status(application_id, ApplicationStatus.APPROVED)
        else:
            self.application_service.update_status(application_id, ApplicationStatus.READY_FOR_REVIEW)
        return approval

    def list_pending_approvals(self, limit: int = 50) -> List[ApplicationApproval]:
        return self.storage.list_pending_approvals(limit=limit)

    def decide_approval_by_id(
        self,
        approval_id: str,
        approved: bool,
        channel: ApprovalChannel = ApprovalChannel.UI,
        confirmation_text: Optional[str] = None,
    ) -> ApplicationApproval:
        approval = self.storage.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval request {approval_id} not found.")
        return self.decide_approval(
            application_id=approval.application_id,
            approved=approved,
            channel=channel,
            confirmation_text=confirmation_text,
        )

    def get_application_timeline(self, application_id: str) -> List[TimelineEvent]:
        return self.application_service.get_timeline(application_id)

    def record_interview(
        self,
        application_id: str,
        round_name: str,
        scheduled_at: str,
        interviewer: Optional[str] = None,
        feedback: Optional[str] = None,
        passed: Optional[bool] = None,
    ) -> JobApplication:
        return self.application_service.record_interview(
            application_id=application_id,
            round_name=round_name,
            scheduled_at=scheduled_at,
            interviewer=interviewer,
            feedback=feedback,
            passed=passed,
        )

    # -----------------------------------------------------------------------
    # Job Comparison & Career Recommendations
    # -----------------------------------------------------------------------

    def compare_jobs(self, job_ids: List[str]) -> JobComparisonResponse:
        """Compares multiple job opportunities side-by-side with AI recommendation."""
        profile = self.get_profile()
        compared_items: List[JobComparisonItem] = []
        best_fit_id = ""
        highest_score = -1

        for j_id in job_ids:
            job = self.get_job(j_id)
            if not job:
                continue
            score = self.storage.get_score_for_job(j_id)
            if not score:
                score = self.matching_service.calculate_match(job, profile)

            sal_str = (
                f"${int(job.salary_min):,} - ${int(job.salary_max):,} {job.salary_currency}"
                if job.salary_min and job.salary_max
                else (f"${int(job.salary_min):,} {job.salary_currency}" if job.salary_min else "Competitive / Market")
            )

            responsibilities = [
                r.strip() for r in (job.cleaned_description or job.raw_description).split("\n")
                if len(r.strip()) > 20 and any(r.strip().lower().startswith(w) for w in ("develop", "build", "design", "manage", "collaborate", "lead", "maintain", "architect", "deliver", "create", "write", "ensure", "optimize"))
            ][:5]
            if not responsibilities:
                responsibilities = [
                    f"Core engineering and delivery for {job.title}",
                    f"Cross-functional collaboration with product and design at {job.company_name}",
                    f"Production maintenance and code quality adhering to best practices",
                ]

            company_info = f"{job.company_name} — hiring for {job.title} ({job.location}, {job.modality.value.capitalize()})."
            growth_potential = (
                "High growth potential in modern engineering ecosystem with accelerated responsibility tracks."
                if score.match_percentage >= 70
                else "Lateral transition with opportunity to expand into adjacent technology domains."
            )

            item = JobComparisonItem(
                job_id=job.id,
                title=job.title,
                company_name=job.company_name,
                location=job.location,
                modality=job.modality.value,
                salary=sal_str,
                responsibilities=responsibilities,
                required_skills=job.required_skills or ["Full Stack", "JavaScript", "React"],
                matching_skills=score.matching_skills,
                missing_skills=score.missing_skills,
                experience_required=f"{job.experience_required_min}-{job.experience_required_max} years",
                match_percentage=score.match_percentage,
                match_tier=score.match_tier,
                company_info=company_info,
                growth_potential=growth_potential,
            )
            compared_items.append(item)

            if score.match_percentage > highest_score:
                highest_score = score.match_percentage
                best_fit_id = job.id

        if not compared_items:
            raise ValueError("No valid jobs found for comparison.")

        best_job = next((j for j in compared_items if j.job_id == best_fit_id), compared_items[0])
        ai_recommendation = (
            f"Based on your verified skills ({', '.join(best_job.matching_skills[:3]) or 'core competencies'}) "
            f"and {profile.total_years_experience} years professional background, "
            f"'{best_job.title}' at {best_job.company_name} presents the highest overall compatibility ({best_job.match_percentage}%) "
            f"with the lowest technical barrier and optimal work arrangement ({best_job.modality.capitalize()})."
        )
        summary = f"Evaluated {len(compared_items)} opportunities. Leading fit: {best_job.title} @ {best_job.company_name} ({best_job.match_percentage}% match)."

        return JobComparisonResponse(
            compared_jobs=compared_items,
            best_fit_job_id=best_job.job_id,
            best_fit_job_title=best_job.title,
            best_fit_company=best_job.company_name,
            ai_recommendation_reason=ai_recommendation,
            comparison_summary=summary,
        )

    def get_career_recommendations(self) -> CareerRecommendations:
        """Returns candidate career strengths, weaknesses, and improvement paths."""
        profile = self.get_profile()
        if profile.career_recommendations:
            return profile.career_recommendations
        return CareerRecommendations(
            strengths=[
                f"Core competency in {', '.join(profile.frameworks[:2]) or 'modern web development'}",
                f"{profile.total_years_experience} years verified engineering experience ({profile.seniority_level})",
            ],
            weaknesses=["Cloud infrastructure and automated distributed systems certifications"],
            missing_keywords=["Kubernetes", "GraphQL", "Distributed Architecture"],
            skills_to_improve=["Cloud Native Orchestration", "System Design at scale"],
            recommended_certifications=["AWS Certified Solutions Architect", "CKAD"],
            suggested_job_titles=[f"Senior {profile.headline.split('(')[0].strip() or 'Software Engineer'}", "Tech Lead"],
            recommended_career_paths=["Senior Engineer -> Staff Architect", "Individual Contributor -> Tech Lead"],
        )

    def ingest_linkedin_profile(self, linkedin_url: str) -> CandidateProfile:
        """Ingests LinkedIn profile URL and links candidate identity."""
        profile = self.get_profile()
        profile.linkedin_url = linkedin_url.strip()
        match = re.search(r"linkedin\.com/in/([a-zA-Z0-9_-]+)", linkedin_url)
        if match:
            slug = match.group(1).replace("-", " ").title()
            if not profile.full_name or profile.full_name == "Candidate":
                profile.full_name = slug
        return self.update_profile(profile)

    def export_all_data(self) -> dict[str, Any]:
        """Exports all career radar data from storage."""
        return self.storage.export_all_data()

    def purge_all_data(self) -> dict[str, int]:
        """Purges all user career records from local SQLite."""
        return self.storage.purge_all_data()

