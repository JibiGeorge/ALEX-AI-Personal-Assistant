"""
FastAPI Routes for ALEX Job Hunting Module.
All endpoints mounted under /api/job-hunting/.
Secured by existing ApiTokenMiddleware.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, Response, UploadFile, status

from app.schemas.job_hunting import (
    AdapterStatusReport,
    ApplicationApproval,
    ApplicationStatus,
    ApplicationStatusUpdateRequest,
    ApprovalChannel,
    ApprovalDecisionRequest,
    BulkExpiryResponse,
    CandidatePreferences,
    CandidateProfile,
    CareerRecommendations,
    CheckExpiryResponse,
    CompatibilityScore,
    DiscoverJobsRequest,
    DiscoveryRunListResponse,
    DiscoveryRunRecord,
    ExtractJobDescriptionRequest,
    IngestDirectUrlRequest,
    IngestGreenhouseRequest,
    IngestLeverRequest,
    IngestLinkedInAlertRequest,
    IngestLinkedInUrlRequest,
    JobApplication,
    JobComparisonRequest,
    JobComparisonResponse,
    JobListResponse,
    JobListing,
    JobSource,
    ResumeUploadRequest,
    ScheduleDiscoveryConfig,
    TailoredDocument,
    TailoredDocumentListResponse,
    TimelineEvent,
    UpdateTailoredDocumentRequest,
    WorkModality,
)
from app.services.job_hunting.approval_service import ApprovalRequiredError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/job-hunting", tags=["job-hunting"])


def get_job_hunting_service(request: Request):
    service = getattr(request.app.state, "job_hunting_service", None)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job Hunting service is not initialized on the application state.",
        )
    return service


# ---------------------------------------------------------------------------
# Candidate Profile Endpoints
# ---------------------------------------------------------------------------

@router.get("/profile", response_model=CandidateProfile)
def get_candidate_profile(request: Request):
    service = get_job_hunting_service(request)
    return service.get_profile()


@router.put("/profile", response_model=CandidateProfile)
def update_candidate_profile(profile: CandidateProfile, request: Request):
    service = get_job_hunting_service(request)
    return service.update_profile(profile)


@router.put("/preferences", response_model=CandidateProfile)
def update_candidate_preferences(preferences: CandidatePreferences, request: Request):
    service = get_job_hunting_service(request)
    return service.update_preferences(preferences)


@router.post("/profile/upload-resume", response_model=CandidateProfile)
async def upload_master_resume(
    request: Request,
):
    service = get_job_hunting_service(request)
    uploads_dir = getattr(request.app.state, "uploads_dir", Path("/tmp"))
    uploads_dir.mkdir(parents=True, exist_ok=True)

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body_dict = await request.json()
        req = ResumeUploadRequest.model_validate(body_dict)
        if req.file_path and Path(req.file_path).exists():
            return service.ingest_resume_file(Path(req.file_path))
        elif req.raw_text:
            dest_path = uploads_dir / (req.file_name or "master_resume.txt")
            dest_path.write_text(req.raw_text, encoding="utf-8")
            return service.ingest_resume_file(dest_path)
        elif req.content_base64:
            import base64
            dest_path = uploads_dir / (req.file_name or "master_resume.pdf")
            dest_path.write_bytes(base64.b64decode(req.content_base64))
            return service.ingest_resume_file(dest_path)

    # Fallback: raw body bytes
    content = await request.body()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload body")

    filename = request.headers.get("x-filename") or "master_resume.txt"
    dest_path = uploads_dir / filename
    dest_path.write_bytes(content)
    return service.ingest_resume_file(dest_path)


@router.post("/profile/linkedin", response_model=CandidateProfile)
async def ingest_linkedin_profile(request: Request):
    service = get_job_hunting_service(request)
    body = await request.json()
    url = body.get("url", "")
    if not url:
        raise HTTPException(status_code=400, detail="LinkedIn profile URL is required.")
    return service.ingest_linkedin_profile(url)


@router.get("/career-recommendations", response_model=CareerRecommendations)
def get_career_recommendations(request: Request):
    service = get_job_hunting_service(request)
    return service.get_career_recommendations()


@router.post("/compare", response_model=JobComparisonResponse)
def compare_jobs(payload: JobComparisonRequest, request: Request):
    service = get_job_hunting_service(request)
    if not payload.job_ids:
        raise HTTPException(status_code=400, detail="At least 1 job ID must be provided for comparison.")
    try:
        return service.compare_jobs(payload.job_ids)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Discovery & External Source Ingestion Endpoints
# ---------------------------------------------------------------------------

@router.get("/adapters", response_model=List[AdapterStatusReport])
def list_adapters(request: Request):
    service = get_job_hunting_service(request)
    return service.list_adapters()


@router.post("/discover", response_model=List[JobListing])
async def discover_jobs(payload: DiscoverJobsRequest, request: Request):
    service = get_job_hunting_service(request)
    return await service.discover_jobs(
        query=payload.query,
        location=payload.location,
        modalities=payload.modalities,
        max_results=payload.max_results,
    )


@router.post("/ingest/linkedin-alert", response_model=List[JobListing])
async def ingest_linkedin_alert(payload: IngestLinkedInAlertRequest, request: Request):
    service = get_job_hunting_service(request)
    return await service.ingest_linkedin_alert(
        alert_text=payload.alert_text,
        default_modality=payload.default_modality,
    )


@router.post("/ingest/linkedin-url", response_model=JobListing)
async def ingest_linkedin_url(payload: IngestLinkedInUrlRequest, request: Request):
    service = get_job_hunting_service(request)
    return await service.ingest_linkedin_url(
        url=payload.url,
        optional_title=payload.optional_title,
        optional_company=payload.optional_company,
        optional_snippet=payload.optional_snippet,
        modality=payload.modality,
    )


@router.post("/ingest/url", response_model=JobListing)
async def ingest_direct_url(payload: IngestDirectUrlRequest, request: Request):
    service = get_job_hunting_service(request)
    return await service.ingest_direct_url(
        url=payload.url,
        title=payload.title,
        company=payload.company,
        raw_text=payload.raw_text,
        modality=payload.modality,
    )


@router.post("/ingest/greenhouse", response_model=List[JobListing])
async def ingest_greenhouse(payload: IngestGreenhouseRequest, request: Request):
    service = get_job_hunting_service(request)
    try:
        return await service.ingest_greenhouse(
            board_token=payload.board_token,
            filter_role=payload.filter_role,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/ingest/lever", response_model=List[JobListing])
async def ingest_lever(payload: IngestLeverRequest, request: Request):
    service = get_job_hunting_service(request)
    try:
        return await service.ingest_lever(
            company_id=payload.company_id,
            filter_role=payload.filter_role,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/ingest/company-careers", response_model=JobListing)
async def ingest_company_careers(payload: IngestDirectUrlRequest, request: Request):
    service = get_job_hunting_service(request)
    return await service.ingest_company_careers(
        url=payload.url,
        title=payload.title,
        company=payload.company,
        raw_text=payload.raw_text,
        modality=payload.modality,
    )


@router.get("/discovery/history", response_model=DiscoveryRunListResponse)
def list_discovery_runs(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
):
    service = get_job_hunting_service(request)
    runs = service.list_discovery_runs(limit=limit)
    return DiscoveryRunListResponse(total=len(runs), runs=runs)


@router.get("/discovery/schedule", response_model=ScheduleDiscoveryConfig)
def get_discovery_schedule(request: Request):
    service = get_job_hunting_service(request)
    return service.get_schedule_config()


@router.put("/discovery/schedule", response_model=ScheduleDiscoveryConfig)
def update_discovery_schedule(payload: ScheduleDiscoveryConfig, request: Request):
    service = get_job_hunting_service(request)
    return service.update_schedule_config(
        enabled=payload.enabled,
        interval_hours=payload.interval_hours,
    )


@router.post("/extract", response_model=JobListing)
async def extract_job_details(payload: ExtractJobDescriptionRequest, request: Request):
    service = get_job_hunting_service(request)
    return await service.extract_job_details(
        raw_text=payload.raw_text,
        source_url=payload.source_url or "",
    )


# ---------------------------------------------------------------------------
# Job Listings & Matching Endpoints
# ---------------------------------------------------------------------------

@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    request: Request,
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status"),
    modality: Optional[WorkModality] = None,
    source: Optional[JobSource] = None,
    min_salary: Optional[float] = None,
    experience_min: Optional[int] = None,
    experience_max: Optional[int] = None,
    is_expired: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    service = get_job_hunting_service(request)
    jobs = service.list_jobs(
        status=status_filter,
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
    return JobListResponse(total=len(jobs), jobs=jobs)


@router.post("/jobs/{job_id}/check-expiry", response_model=CheckExpiryResponse)
async def check_job_expiry(job_id: str, request: Request):
    service = get_job_hunting_service(request)
    try:
        return await service.check_job_expiry(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/jobs/check-expiry", response_model=BulkExpiryResponse)
async def bulk_check_expiry(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
):
    service = get_job_hunting_service(request)
    return await service.bulk_check_expiry(limit=limit)


@router.get("/jobs/{job_id}", response_model=JobListing)
def get_job(job_id: str, request: Request):
    service = get_job_hunting_service(request)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    return job


@router.post("/jobs/{job_id}/match", response_model=CompatibilityScore)
async def calculate_job_match(job_id: str, request: Request):
    service = get_job_hunting_service(request)
    try:
        return await service.calculate_match_async(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs/{job_id}/score", response_model=Optional[CompatibilityScore])
def get_job_score(job_id: str, request: Request):
    service = get_job_hunting_service(request)
    score = service.get_score_for_job(job_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score not yet calculated for this job.")
    return score


# ---------------------------------------------------------------------------
# ALEX Resume Studio Endpoints (Customization, Preview, Editing & Downloads)
# ---------------------------------------------------------------------------

@router.post("/jobs/{job_id}/tailor-resume", response_model=TailoredDocument)
async def tailor_resume_package(
    job_id: str,
    request: Request,
    instructions: Optional[str] = Query(None, description="Optional custom tailoring instructions"),
):
    service = get_job_hunting_service(request)
    try:
        return await service.tailor_resume_package(job_id=job_id, custom_instructions=instructions)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs/{job_id}/tailored-documents", response_model=TailoredDocumentListResponse)
def list_tailored_documents_for_job(job_id: str, request: Request):
    service = get_job_hunting_service(request)
    docs = service.list_tailored_documents_for_job(job_id)
    return TailoredDocumentListResponse(
        job_id=job_id,
        total_versions=len(docs),
        documents=docs,
    )


@router.get("/jobs/{job_id}/tailored-document", response_model=TailoredDocument)
def get_tailored_document(job_id: str, request: Request):
    service = get_job_hunting_service(request)
    doc = service.get_tailored_document(job_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Tailored document not found for this job.")
    return doc


@router.get("/tailored-documents/{document_id}", response_model=TailoredDocument)
def get_tailored_document_by_id(document_id: str, request: Request):
    service = get_job_hunting_service(request)
    doc = service.get_tailored_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")
    return doc


@router.put("/tailored-documents/{document_id}", response_model=TailoredDocument)
def update_tailored_document(
    document_id: str,
    payload: UpdateTailoredDocumentRequest,
    request: Request,
):
    service = get_job_hunting_service(request)
    try:
        return service.update_tailored_document(
            doc_id=document_id,
            resume_markdown=payload.resume_markdown,
            cover_letter_markdown=payload.cover_letter_markdown,
            create_new_version=payload.create_new_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/tailored-documents/{document_id}/download")
def download_tailored_document(
    document_id: str,
    request: Request,
    format: str = Query("pdf", pattern="^(pdf|docx|markdown|md)$"),
    doc_type: str = Query("resume", pattern="^(resume|cover_letter)$"),
):
    service = get_job_hunting_service(request)
    try:
        file_bytes, media_type, filename = service.get_document_download(
            doc_id=document_id,
            doc_type=doc_type,
            format_type=format,
        )
        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Application Management & Explicit Approval Endpoints
# ---------------------------------------------------------------------------

@router.get("/applications", response_model=List[JobApplication])
def list_applications(
    request: Request,
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status"),
):
    service = get_job_hunting_service(request)
    return service.list_applications(status=status_filter)


@router.get("/applications/{application_id}", response_model=JobApplication)
def get_application(application_id: str, request: Request):
    service = get_job_hunting_service(request)
    app = service.get_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    return app


@router.patch("/applications/{application_id}/status", response_model=JobApplication)
def update_application_status(
    application_id: str,
    payload: ApplicationStatusUpdateRequest,
    request: Request,
):
    service = get_job_hunting_service(request)
    try:
        return service.update_application_status(
            application_id=application_id,
            status=payload.status,
            notes=payload.notes,
        )
    except ApprovalRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Approval Required: {exc}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/applications/{application_id}/approval", response_model=ApplicationApproval)
def decide_application_approval(
    application_id: str,
    payload: ApprovalDecisionRequest,
    request: Request,
):
    service = get_job_hunting_service(request)
    return service.decide_approval(
        application_id=application_id,
        approved=payload.approved,
        channel=payload.channel,
        confirmation_text=payload.confirmation_text,
    )


@router.get("/approvals/pending", response_model=List[ApplicationApproval])
def list_pending_approvals(request: Request):
    service = get_job_hunting_service(request)
    return service.list_pending_approvals()


@router.post("/approvals/{approval_id}/decision", response_model=ApplicationApproval)
def decide_approval_by_id(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    request: Request,
):
    service = get_job_hunting_service(request)
    try:
        return service.decide_approval_by_id(
            approval_id=approval_id,
            approved=payload.approved,
            channel=payload.channel,
            confirmation_text=payload.confirmation_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/applications/{application_id}/timeline", response_model=List[TimelineEvent])
def get_application_timeline(application_id: str, request: Request):
    service = get_job_hunting_service(request)
    return service.get_application_timeline(application_id)
