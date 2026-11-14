from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkModality(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class JobSource(str, Enum):
    LINKEDIN_ALERT = "linkedin_alert"
    LINKEDIN_URL = "linkedin_url"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    PUBLIC_API = "public_api"
    WEB_SEARCH = "web_search"
    DIRECT_URL = "direct_url"
    COMPANY_CAREERS = "company_careers"
    MANUAL = "manual"
    INDEED = "indeed"
    NAUKRI = "naukri"
    FOUNDIT = "foundit"
    GLASSDOOR = "glassdoor"
    WELLFOUND = "wellfound"
    INSTAHYRE = "instahyre"


class ApplicationStatus(str, Enum):
    DISCOVERED = "discovered"
    SAVED = "saved"
    INTERESTED = "interested"
    ANALYZED = "analyzed"
    BOOKMARKED = "bookmarked"
    TAILORED = "tailored"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    APPLIED = "applied"
    ASSESSMENT = "assessment"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    OFFER_RECEIVED = "offer_received"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ARCHIVED = "archived"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalChannel(str, Enum):
    UI = "ui"
    VOICE = "voice"
    API = "api"


# ---------------------------------------------------------------------------
# Candidate Profile Schemas
# ---------------------------------------------------------------------------

class EducationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    institution: str
    degree: str
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    location: Optional[str] = None


class CertificationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    issuing_organization: Optional[str] = None
    issue_year: Optional[int] = None
    credential_url: Optional[str] = None


class ProjectItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    description: str
    tech_stack: List[str] = Field(default_factory=list)
    project_url: Optional[str] = None


class CareerRecommendations(BaseModel):
    model_config = ConfigDict(extra="ignore")

    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    skills_to_improve: List[str] = Field(default_factory=list)
    recommended_certifications: List[str] = Field(default_factory=list)
    suggested_job_titles: List[str] = Field(default_factory=list)
    recommended_career_paths: List[str] = Field(default_factory=list)


class CandidatePreferences(BaseModel):
    model_config = ConfigDict(extra="ignore")

    target_roles: List[str] = Field(
        default_factory=lambda: [
            "Software Developer",
            "Full Stack Developer",
            "Frontend Developer",
            "React Developer",
            "Next.js Developer",
            "Node.js Developer",
        ]
    )
    min_years_experience: int = Field(default=2, ge=0)
    max_years_experience: int = Field(default=5, ge=0)
    modalities: List[WorkModality] = Field(
        default_factory=lambda: [WorkModality.REMOTE, WorkModality.HYBRID, WorkModality.ONSITE]
    )
    target_locations: List[str] = Field(default_factory=lambda: ["Worldwide", "Remote"])
    preferred_currency: str = Field(default="USD")
    min_base_salary: Optional[float] = None
    keywords: List[str] = Field(
        default_factory=lambda: [
            "React",
            "Next.js",
            "Node.js",
            "TypeScript",
            "FastAPI",
            "Full Stack",
            "JavaScript",
        ]
    )
    excluded_keywords: List[str] = Field(default_factory=list)
    auto_discovery_enabled: bool = True
    discovery_interval_hours: int = Field(default=12, ge=1)
    factor_weights: Optional[Dict[str, float]] = None


class WorkExperienceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    company_name: str
    role_title: str
    location: Optional[str] = None
    is_remote: bool = False
    start_date: str  # YYYY-MM
    end_date: Optional[str] = None  # None if current
    is_current: bool = False
    highlights: List[str] = Field(default_factory=list)
    tech_stack: List[str] = Field(default_factory=list)


class SkillItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    category: str = "General"  # Frontend, Backend, Database, Cloud, etc.
    proficiency: str = "Proficient"  # Expert, Proficient, Familiar
    years_experience: float = 2.0


class CandidateProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = "default_candidate"
    full_name: str = "Candidate"
    email: str = ""
    phone: Optional[str] = None
    location: str = "Worldwide / Remote"
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    headline: str = "Full Stack Developer (React / Next.js / Node.js)"
    summary: str = "Experienced Software Developer with 2-5 years building modern web applications."
    total_years_experience: float = 3.0
    seniority_level: str = "Mid-Level"  # Junior, Mid-Level, Senior, Lead
    programming_languages: List[str] = Field(default_factory=lambda: ["TypeScript", "JavaScript", "Python"])
    frameworks: List[str] = Field(default_factory=lambda: ["React", "Next.js", "Node.js", "FastAPI"])
    databases: List[str] = Field(default_factory=lambda: ["PostgreSQL", "SQLite", "Redis"])
    skills: List[SkillItem] = Field(default_factory=list)
    work_history: List[WorkExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    tools_and_platforms: List[str] = Field(default_factory=list)
    non_technical_skills: List[str] = Field(default_factory=list)
    industry_experience: List[str] = Field(default_factory=list)
    management_experience: Optional[str] = None
    expected_salary: Optional[str] = None
    notice_period: Optional[str] = None
    current_location: Optional[str] = None
    preferred_locations: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    career_recommendations: Optional[CareerRecommendations] = None
    preferences: CandidatePreferences = Field(default_factory=CandidatePreferences)
    master_resume_path: Optional[str] = None
    raw_resume_text: Optional[str] = None
    is_verified: bool = False
    verified_at: Optional[str] = None
    verification_notes: Optional[str] = None
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Job Listing Schemas
# ---------------------------------------------------------------------------

class JobListing(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    source: JobSource
    external_id: Optional[str] = None
    source_url: str
    company_name: str
    company_website: Optional[str] = None
    title: str
    location: str
    modality: WorkModality = WorkModality.REMOTE
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    workplace_type: str = "remote"  # remote, hybrid, onsite
    employment_type: str = "Full-time"  # Full-time, Part-time, Contract, Internship
    logo_url: Optional[str] = None
    application_deadline: Optional[str] = None
    recruiter_info: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "USD"
    experience_required_min: int = 2
    experience_required_max: int = 5
    raw_description: str
    cleaned_description: str = ""
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    posted_at: Optional[str] = None
    discovered_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    is_expired: bool = False
    expiry_checked_at: Optional[str] = None
    content_hash: str


class JobListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total: int
    jobs: List[JobListing]


# ---------------------------------------------------------------------------
# Matching & Compatibility Schemas
# ---------------------------------------------------------------------------

class CompatibilityScore(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    job_id: str
    candidate_id: str

    # Overall match (0-100)
    match_percentage: int = Field(default=0, ge=0, le=100)
    overall_score: int = Field(default=0, ge=0, le=100)
    match_tier: str = "good"  # excellent (85-100), good (70-84), potential (50-69), low (<50)

    # 6-Factor Multi-Dimensional Scoring Breakdown
    technical_skills_score: int = Field(default=0, ge=0, le=100)      # Weight: 30%
    work_experience_score: int = Field(default=0, ge=0, le=100)       # Weight: 25%
    experience_score: int = Field(default=0, ge=0, le=100)            # Compatibility alias for work_experience_score
    responsibilities_score: int = Field(default=0, ge=0, le=100)      # Weight: 15%
    education_score: int = Field(default=0, ge=0, le=100)             # Weight: 10%
    industry_score: int = Field(default=0, ge=0, le=100)              # Weight: 10%
    location_score: int = Field(default=0, ge=0, le=100)              # Weight: 10%
    seniority_score: int = Field(default=0, ge=0, le=100)             # Legacy
    tech_stack_score: int = Field(default=0, ge=0, le=100)            # Legacy

    # Factor weights used for this calculation
    factor_weights: Dict[str, float] = Field(default_factory=dict)

    # Legacy/compatibility aliases
    skills_score: int = Field(default=0, ge=0, le=100)
    location_modality_score: int = Field(default=0, ge=0, le=100)

    # Detailed Comparative Analysis
    skills_matched: List[str] = Field(default_factory=list)
    skills_missing: List[str] = Field(default_factory=list)
    matching_skills: List[str] = Field(default_factory=list)          # Alias to skills_matched
    missing_skills: List[str] = Field(default_factory=list)           # Alias to skills_missing
    mandatory_requirements_not_met: List[str] = Field(default_factory=list)
    experience_gaps: List[str] = Field(default_factory=list)
    experience_gap_analysis: str = ""
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    why_matched: str = ""
    why_not_matched: str = ""

    # Recommendation
    ai_recommendation: str = "CONSIDER_TAILORING"
    recommended_action: str = "CONSIDER_TAILORING"
    match_summary: str = ""
    calculated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Job Comparison Schemas
# ---------------------------------------------------------------------------

class JobComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_ids: List[str]


class JobComparisonItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: str
    title: str
    company_name: str
    location: str
    modality: str
    salary: str
    responsibilities: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    experience_required: str = ""
    match_percentage: int = 0
    match_tier: str = "good"
    company_info: str = ""
    growth_potential: str = ""


class JobComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    compared_jobs: List[JobComparisonItem]
    best_fit_job_id: str
    best_fit_job_title: str
    best_fit_company: str
    ai_recommendation_reason: str
    comparison_summary: str


# ---------------------------------------------------------------------------
# Resume Tailoring & Cover Letter Schemas
# ---------------------------------------------------------------------------

class TailoredDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    job_id: str
    candidate_id: str
    version_number: int = 1
    resume_markdown: str
    cover_letter_markdown: str
    ats_keywords_included: List[str] = Field(default_factory=list)
    customizations_summary: List[str] = Field(default_factory=list)
    relevant_experience_identified: List[str] = Field(default_factory=list)
    relevant_skills_identified: List[str] = Field(default_factory=list)
    docx_resume_path: Optional[str] = None
    pdf_resume_path: Optional[str] = None
    docx_cover_letter_path: Optional[str] = None
    pdf_cover_letter_path: Optional[str] = None
    original_resume_preserved: bool = True
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = None


class UpdateTailoredDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resume_markdown: Optional[str] = None
    cover_letter_markdown: Optional[str] = None
    create_new_version: bool = False


class TailoredDocumentListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str
    total_versions: int
    documents: List[TailoredDocument]


# ---------------------------------------------------------------------------
# Application & Approval Schemas
# ---------------------------------------------------------------------------

class ApplicationApproval(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    application_id: str
    requested_action: str  # e.g. "SUBMIT_APPLICATION", "SEND_EMAIL_OUTREACH"
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approval_channel: ApprovalChannel = ApprovalChannel.UI
    user_confirmation_text: Optional[str] = None
    decided_at: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    application_id: str
    event_type: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class InterviewRound(BaseModel):
    model_config = ConfigDict(extra="ignore")
    round_name: str
    scheduled_at: str
    interviewer: Optional[str] = None
    feedback: Optional[str] = None
    passed: Optional[bool] = None


class JobApplication(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    job_id: str
    candidate_id: str
    tailored_document_id: Optional[str] = None
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    applied_at: Optional[str] = None
    submission_method: Optional[str] = None
    notes: Optional[str] = None
    interview_rounds: List[InterviewRound] = Field(default_factory=list)
    compensation_offered: Optional[float] = None
    latest_approval: Optional[ApplicationApproval] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Ingestion & Request DTOs
# ---------------------------------------------------------------------------

class IngestLinkedInAlertRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    alert_text: str = Field(..., min_length=5, description="Raw text or email body of LinkedIn job alert")
    default_modality: WorkModality = WorkModality.REMOTE


class IngestLinkedInUrlRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str = Field(..., min_length=10, description="User-supplied LinkedIn job URL")
    optional_title: Optional[str] = None
    optional_company: Optional[str] = None
    optional_snippet: Optional[str] = None
    modality: WorkModality = WorkModality.REMOTE


class IngestDirectUrlRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str = Field(..., min_length=5)
    title: Optional[str] = None
    company: Optional[str] = None
    raw_text: Optional[str] = None
    modality: WorkModality = WorkModality.REMOTE


class DiscoverJobsRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query: Optional[str] = None
    location: Optional[str] = None
    modalities: Optional[List[WorkModality]] = None
    max_results: int = Field(default=10, ge=1, le=50)


class ExtractJobDescriptionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    raw_text: str = Field(..., min_length=20)
    source_url: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    approved: bool
    channel: ApprovalChannel = ApprovalChannel.UI
    confirmation_text: Optional[str] = None


class ApplicationStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: ApplicationStatus
    notes: Optional[str] = None


class AdapterStatusReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    adapter_name: str
    available: bool
    description: str
    reason: Optional[str] = None


class ResumeUploadRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    file_path: Optional[str] = None
    file_name: Optional[str] = "master_resume.txt"
    raw_text: Optional[str] = None
    content_base64: Optional[str] = None


class DiscoveryRunRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    source: str = "all"
    query: str
    started_at: str
    finished_at: Optional[str] = None
    status: str = "completed"  # completed, partial, failed
    jobs_found: int = 0
    new_jobs_stored: int = 0
    errors: List[str] = Field(default_factory=list)


class DiscoveryRunListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total: int
    runs: List[DiscoveryRunRecord]


class ScheduleDiscoveryConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    interval_hours: int = Field(default=12, ge=1, le=168)
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None


class IngestGreenhouseRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    board_token: str = Field(..., description="Greenhouse company board token (e.g., 'gitlab', 'stripe')")
    filter_role: Optional[str] = None


class IngestLeverRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company_id: str = Field(..., description="Lever company identifier (e.g., 'netflix', 'spotify')")
    filter_role: Optional[str] = None


class CheckExpiryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str
    source_url: str
    is_expired: bool
    status_code: Optional[int] = None
    checked_at: str
    reason: Optional[str] = None


class BulkExpiryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_checked: int
    expired_count: int
    results: List[CheckExpiryResponse]
