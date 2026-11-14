"""
Comprehensive Unit and Integration Tests for ALEX Job Hunting Module.
Tests storage, deduplication, adapters, extraction, matching, tailoring,
approval management, application lifecycle, and all REST endpoints.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.job_hunting import (
    ApplicationStatus,
    ApprovalChannel,
    ApprovalStatus,
    CandidatePreferences,
    CandidateProfile,
    JobListing,
    JobSource,
    WorkModality,
)
from app.services.job_hunting.adapters import (
    DirectUrlJobAdapter,
    LinkedInAlertJobAdapter,
    LinkedInUrlJobAdapter,
    RemoteOKJobAdapter,
    WebSearchJobAdapter,
)
from app.services.job_hunting.approval_service import (
    ApprovalManagementService,
    ApprovalRequiredError,
)
from app.services.job_hunting.deduplication import compute_job_content_hash, normalize_text
from app.services.job_hunting.extraction import JobExtractionService
from app.services.job_hunting.job_hunting_service import JobHuntingService
from app.services.job_hunting.matching_service import JobMatchingService
from app.services.job_hunting.profile_service import CandidateProfileService
from app.services.job_hunting.storage import JobHuntingStorage
from app.services.job_hunting.tailoring_service import ResumeTailoringService


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    return tmp_path / "job_hunting_test.db"


@pytest.fixture
def storage(test_db_path: Path) -> JobHuntingStorage:
    return JobHuntingStorage(test_db_path)


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("ALEX_CONFIG_FILE", str(tmp_path / "config" / "api_keys.json"))
    app = create_app(data_dir=tmp_path, api_token="test-token")
    with TestClient(app) as test_client:
        yield test_client


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# 1. Deduplication Tests
# ---------------------------------------------------------------------------

def test_normalize_text():
    assert normalize_text("  Google, Inc.  ") == "google inc"
    assert normalize_text("Full-Stack Developer!!!") == "full stack developer"
    assert normalize_text(None) == ""


def test_compute_job_content_hash_consistency():
    hash1 = compute_job_content_hash("Stripe", "Full Stack Engineer", "Remote")
    hash2 = compute_job_content_hash("stripe", "full-stack engineer", "remote worldwide")
    # Same normalized parameters yield identical hash
    assert hash1 == hash2

    diff_hash = compute_job_content_hash("Vercel", "Full Stack Engineer", "Remote")
    assert hash1 != diff_hash


# ---------------------------------------------------------------------------
# 2. Storage CRUD Tests
# ---------------------------------------------------------------------------

def test_storage_candidate_profile(storage: JobHuntingStorage):
    assert storage.get_candidate_profile("non_existent") is None

    profile = CandidateProfile(
        id="cand_1",
        full_name="Alex Developer",
        email="alex@example.com",
        location="Remote",
        headline="React & Node Developer",
        summary="Passionate developer with 3 years experience.",
        total_years_experience=3.0,
    )
    saved = storage.save_candidate_profile(profile)
    assert saved.id == "cand_1"

    fetched = storage.get_candidate_profile("cand_1")
    assert fetched is not None
    assert fetched.full_name == "Alex Developer"
    assert fetched.email == "alex@example.com"


def test_storage_job_and_deduplication(storage: JobHuntingStorage):
    c_hash = compute_job_content_hash("Acme", "React Developer", "Remote")
    job = JobListing(
        id="job_1",
        source=JobSource.DIRECT_URL,
        source_url="https://example.com/job1",
        company_name="Acme",
        title="React Developer",
        location="Remote",
        modality=WorkModality.REMOTE,
        raw_description="Looking for React Developer",
        content_hash=c_hash,
    )
    storage.save_job(job)

    # Retrieval
    retrieved = storage.get_job("job_1")
    assert retrieved is not None
    assert retrieved.title == "React Developer"

    # Query by content hash
    by_hash = storage.get_job_by_hash(c_hash)
    assert by_hash is not None
    assert by_hash.id == "job_1"

    # Count
    assert storage.count_jobs() == 1

    # List jobs
    all_jobs = storage.list_jobs()
    assert len(all_jobs) == 1


# ---------------------------------------------------------------------------
# 3. Adapter Tests
# ---------------------------------------------------------------------------

def test_linkedin_alert_adapter_parsing_with_links():
    async def _run():
        adapter = LinkedInAlertJobAdapter()
        assert adapter.check_availability().available is True

        alert_email = """
        Jobs matching your alert:
        Full Stack Developer at TechCo
        Remote · Worldwide
        View job: https://www.linkedin.com/jobs/view/9876543210/?tracking=abc

        React Engineer at FrontendWorks
        New York, NY · Hybrid
        View job: https://www.linkedin.com/jobs/view/1234567890/
        """

        listings = await adapter.discover_or_ingest(alert_text=alert_email)
        assert len(listings) == 2

        job1 = listings[0]
        assert job1.external_id == "9876543210"
        assert "linkedin.com/jobs/view/9876543210" in job1.source_url
        assert job1.source == JobSource.LINKEDIN_ALERT

        job2 = listings[1]
        assert job2.external_id == "1234567890"

    asyncio.run(_run())


def test_linkedin_url_adapter_no_scraping():
    async def _run():
        adapter = LinkedInUrlJobAdapter()
        assert adapter.check_availability().available is True

        url = "https://www.linkedin.com/jobs/view/3948572019/?refId=foo&trackingId=bar"
        listings = await adapter.discover_or_ingest(
            url=url,
            optional_title="Next.js Developer",
            optional_company="Vercel Ecosystem Partner",
            optional_snippet="Building modern headless web applications.",
        )
        assert len(listings) == 1
        job = listings[0]
        assert job.external_id == "3948572019"
        assert job.source_url == "https://www.linkedin.com/jobs/view/3948572019/"
        assert job.title == "Next.js Developer"
        assert job.company_name == "Vercel Ecosystem Partner"

    asyncio.run(_run())


def test_direct_url_adapter():
    async def _run():
        adapter = DirectUrlJobAdapter()
        listings = await adapter.discover_or_ingest(
            url="https://jobs.lever.co/example/1234",
            title="Node.js Backend Engineer",
            company="API Scale Inc",
        )
        assert len(listings) == 1
        assert listings[0].title == "Node.js Backend Engineer"
        assert listings[0].company_name == "API Scale Inc"

    asyncio.run(_run())


def test_web_search_adapter_availability():
    # When no key or service is provided, reports unavailable cleanly
    adapter = WebSearchJobAdapter(web_search_service=None)
    status = adapter.check_availability()
    assert status.available is False
    assert "not initialized" in status.reason.lower()


# ---------------------------------------------------------------------------
# 4. Extraction Engine Tests
# ---------------------------------------------------------------------------

def test_extraction_heuristics():
    async def _run():
        service = JobExtractionService(settings_service=None)
        raw_jd = """
        Full Stack Developer (React / Node.js)
        Acme Innovations
        Location: Worldwide (Remote)
        Salary: $110,000 - $145,000 USD
        Experience: 3-5 years of experience in web application development.

        Requirements:
        - Proficient with React, Next.js, and TypeScript
        - Strong Node.js and Express or FastAPI backend knowledge
        - Experience with PostgreSQL and Docker
        """
        job = await service.extract_job_details(raw_jd, source_url="https://acme.com/jobs")
        assert "Developer" in job.title
        assert job.modality == WorkModality.REMOTE
        assert job.experience_required_min == 3
        assert job.experience_required_max == 5
        assert job.salary_min == 110000.0
        assert job.salary_max == 145000.0
        assert any("React" in s for s in job.required_skills)
        assert any("Node" in s or "Typescript" in s for s in job.required_skills)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 5. Matching & Compatibility Tests
# ---------------------------------------------------------------------------

def test_job_matching_service(storage: JobHuntingStorage):
    matching_service = JobMatchingService(storage=storage)
    profile_service = CandidateProfileService(storage=storage)

    profile = profile_service.get_profile()
    # Candidate profile has React, Next.js, Node.js, TypeScript (3.5 yrs experience)

    job = JobListing(
        id="match_test_job",
        source=JobSource.DIRECT_URL,
        source_url="https://test.com/job",
        company_name="CloudCo",
        title="Full Stack Developer",
        location="Remote",
        modality=WorkModality.REMOTE,
        experience_required_min=2,
        experience_required_max=5,
        required_skills=["React", "Node.js", "TypeScript", "GraphQL"],
        raw_description="Looking for React and Node.js engineer with 2-5 years experience.",
        content_hash="hash_match_1",
    )
    storage.save_job(job)

    score = matching_service.calculate_match(job=job, profile=profile)
    assert score.overall_score >= 70
    assert score.experience_score == 100
    assert "React" in score.matching_skills
    assert "Node.Js" in score.matching_skills or "Node.js" in score.matching_skills
    assert "Graphql" in score.missing_skills or "GraphQL" in score.missing_skills
    assert score.recommended_action in ("HIGH_MATCH_APPLY", "CONSIDER_TAILORING")


# ---------------------------------------------------------------------------
# 6. Resume Tailoring & Anti-Hallucination Tests
# ---------------------------------------------------------------------------

def test_resume_tailoring_service(storage: JobHuntingStorage):
    async def _run():
        tailoring_service = ResumeTailoringService(storage=storage)
        profile_service = CandidateProfileService(storage=storage)
        profile = profile_service.get_profile()

        job = JobListing(
            id="tailor_test_job",
            source=JobSource.DIRECT_URL,
            source_url="https://stripe.com/jobs/1",
            company_name="Stripe",
            title="Full Stack Developer",
            location="Remote",
            modality=WorkModality.REMOTE,
            required_skills=["React", "Node.js", "TypeScript"],
            raw_description="Build developer infrastructure with React and Node.",
            content_hash="hash_tailor_1",
        )
        storage.save_job(job)

        doc = await tailoring_service.generate_tailored_package(job=job, profile=profile)
        assert doc.id is not None
        assert "Stripe" in doc.resume_markdown
        assert "Stripe" in doc.cover_letter_markdown
        assert profile.full_name in doc.resume_markdown
        assert len(doc.customizations_summary) > 0

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 7. Approval & Application Lifecycle Gate Tests
# ---------------------------------------------------------------------------

def test_application_approval_enforcement(storage: JobHuntingStorage):
    approval_svc = ApprovalManagementService(storage=storage)
    app_svc = from_storage_app_service(storage, approval_svc)

    # Insert prerequisite job first to satisfy foreign key
    test_job = JobListing(
        id="job_app_test",
        source=JobSource.DIRECT_URL,
        source_url="https://test.com/app-job",
        company_name="AppTest Inc",
        title="Software Engineer",
        location="Remote",
        modality=WorkModality.REMOTE,
        raw_description="Test description",
        content_hash="hash_app_test_unique",
    )
    storage.save_job(test_job)

    app = app_svc.get_or_create_application(job_id="job_app_test")
    assert app.status == ApplicationStatus.DISCOVERED

    # Attempting to mark as APPLIED without approval must raise ApprovalRequiredError
    with pytest.raises(ApprovalRequiredError):
        app_svc.update_status(app.id, ApplicationStatus.APPLIED)

    # Request approval
    approval_req = approval_svc.request_approval(app.id, action="SUBMIT_APPLICATION", channel=ApprovalChannel.UI)
    assert approval_req.approval_status == ApprovalStatus.PENDING

    # Reject approval
    approval_svc.record_decision(app.id, approved=False, confirmation_text="Not interested in this compensation")
    with pytest.raises(ApprovalRequiredError):
        app_svc.update_status(app.id, ApplicationStatus.APPLIED)

    # Approve explicitly
    approval_svc.record_decision(app.id, approved=True, confirmation_text="Approved by user click in HUD")

    # Now status update to APPLIED succeeds!
    updated = app_svc.update_status(app.id, ApplicationStatus.APPLIED)
    assert updated.status == ApplicationStatus.APPLIED
    assert updated.applied_at is not None

    # Check timeline events
    timeline = app_svc.get_timeline(app.id)
    assert len(timeline) >= 3
    event_types = [e.event_type for e in timeline]
    assert "APPLICATION_CREATED" in event_types
    assert "APPROVAL_REQUESTED" in event_types
    assert "APPROVAL_DECIDED" in event_types
    assert "STATUS_CHANGED" in event_types


def from_storage_app_service(storage, approval_svc):
    from app.services.job_hunting.application_service import ApplicationManagementService
    return ApplicationManagementService(storage, approval_svc)


# ---------------------------------------------------------------------------
# 8. REST API Integration Endpoints Tests
# ---------------------------------------------------------------------------

def test_api_candidate_profile_endpoints(client: TestClient):
    # GET profile
    res = client.get("/api/job-hunting/profile", headers=auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert "target_roles" in data["preferences"]
    assert "React Developer" in data["preferences"]["target_roles"]

    # PUT preferences
    new_prefs = {
        "target_roles": ["Full Stack Developer", "Next.js Developer"],
        "min_years_experience": 2,
        "max_years_experience": 5,
        "modalities": ["remote", "hybrid"],
        "target_locations": ["Worldwide"],
        "preferred_currency": "USD",
        "keywords": ["React 19", "Next.js", "Node.js"],
        "excluded_keywords": ["PHP"],
        "auto_discovery_enabled": True,
        "discovery_interval_hours": 24,
    }
    put_res = client.put("/api/job-hunting/preferences", json=new_prefs, headers=auth_headers())
    assert put_res.status_code == 200
    assert put_res.json()["preferences"]["target_roles"] == ["Full Stack Developer", "Next.js Developer"]


def test_api_adapters_endpoint(client: TestClient):
    res = client.get("/api/job-hunting/adapters", headers=auth_headers())
    assert res.status_code == 200
    adapters = res.json()
    assert len(adapters) >= 3
    names = [a["adapter_name"] for a in adapters]
    assert any("LinkedIn" in n for n in names)


def test_api_ingest_linkedin_url(client: TestClient):
    payload = {
        "url": "https://www.linkedin.com/jobs/view/3948572019/",
        "optional_title": "Senior React Engineer",
        "optional_company": "Innovative Labs",
        "optional_snippet": "Modern React 19 architecture.",
        "modality": "remote",
    }
    res = client.post("/api/job-hunting/ingest/linkedin-url", json=payload, headers=auth_headers())
    assert res.status_code == 200
    job = res.json()
    assert job["external_id"] == "3948572019"
    assert job["title"] == "Senior React Engineer"

    # Get job by ID
    get_res = client.get(f"/api/job-hunting/jobs/{job['id']}", headers=auth_headers())
    assert get_res.status_code == 200
    assert get_res.json()["id"] == job["id"]


def test_api_match_and_tailor_flow(client: TestClient):
    # Ingest direct URL
    ingest_res = client.post(
        "/api/job-hunting/ingest/url",
        json={
            "url": "https://jobs.github.com/react-role",
            "title": "Full Stack Developer",
            "company": "GitHub Partner",
            "raw_text": "Requirements: React, Node.js, TypeScript. 2-5 years experience.",
            "modality": "remote",
        },
        headers=auth_headers(),
    )
    assert ingest_res.status_code == 200
    job_id = ingest_res.json()["id"]

    # Calculate match
    match_res = client.post(f"/api/job-hunting/jobs/{job_id}/match", headers=auth_headers())
    assert match_res.status_code == 200
    match_data = match_res.json()
    assert match_data["overall_score"] >= 50

    # Tailor resume package
    tailor_res = client.post(f"/api/job-hunting/jobs/{job_id}/tailor-resume", headers=auth_headers())
    assert tailor_res.status_code == 200
    doc_data = tailor_res.json()
    assert "resume_markdown" in doc_data
    assert "cover_letter_markdown" in doc_data

    # Check applications list
    apps_res = client.get("/api/job-hunting/applications", headers=auth_headers())
    assert apps_res.status_code == 200
    apps = apps_res.json()
    assert len(apps) >= 1
    app = [a for a in apps if a["job_id"] == job_id][0]

    # Try to set status to applied without approval -> Forbidden (403)
    apply_fail = client.patch(
        f"/api/job-hunting/applications/{app['id']}/status",
        json={"status": "applied"},
        headers=auth_headers(),
    )
    assert apply_fail.status_code == 403
    assert "Approval Required" in apply_fail.json()["detail"]

    # Give user approval
    approval_res = client.post(
        f"/api/job-hunting/applications/{app['id']}/approval",
        json={
            "approved": True,
            "channel": "ui",
            "confirmation_text": "User reviewed tailored resume and approved application",
        },
        headers=auth_headers(),
    )
    assert approval_res.status_code == 200
    assert approval_res.json()["approval_status"] == "APPROVED"

    # Now set status to applied -> Success (200)
    apply_success = client.patch(
        f"/api/job-hunting/applications/{app['id']}/status",
        json={"status": "applied", "notes": "Submitted through portal"},
        headers=auth_headers(),
    )
    assert apply_success.status_code == 200
    assert apply_success.json()["status"] == "applied"

    # Get timeline
    timeline_res = client.get(f"/api/job-hunting/applications/{app['id']}/timeline", headers=auth_headers())
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()
    assert len(timeline) >= 3
