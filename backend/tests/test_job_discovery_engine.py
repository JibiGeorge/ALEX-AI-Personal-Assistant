"""
Comprehensive Test Suite for ALEX Job Hunting Discovery Engine.
Tests all source adapters, deduplication, expiry detection, search filters,
source attribution, verbatim description storage, discovery history, and scheduling.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.job_hunting import (
    ApplicationStatus,
    JobListing,
    JobSource,
    WorkModality,
)
from app.services.job_hunting.adapters import (
    CompanyCareersJobAdapter,
    DirectUrlJobAdapter,
    ExpiryChecker,
    GreenhouseJobAdapter,
    LeverJobAdapter,
    LinkedInAlertJobAdapter,
    LinkedInDataExportAdapter,
    LinkedInUrlJobAdapter,
    RemoteOKJobAdapter,
    WebSearchJobAdapter,
)
from app.services.job_hunting.deduplication import (
    are_jobs_duplicate,
    compute_job_content_hash,
    extract_company_domain,
    normalize_job_title,
    normalize_text,
)
from app.services.job_hunting.discovery_service import JobDiscoveryService
from app.services.job_hunting.profile_service import CandidateProfileService
from app.services.job_hunting.scheduler import JobDiscoveryScheduler
from app.services.job_hunting.storage import JobHuntingStorage


@pytest.fixture
def storage(tmp_path: Path) -> JobHuntingStorage:
    return JobHuntingStorage(tmp_path / "discovery_test.db")


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("ALEX_CONFIG_FILE", str(tmp_path / "config" / "api_keys.json"))
    app = create_app(data_dir=tmp_path, api_token="test-token")
    with TestClient(app) as test_client:
        yield test_client


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# 1. LinkedIn Source Adapters Tests (Zero Scraping / User-Provided Ingestion)
# ---------------------------------------------------------------------------

def test_adapter_linkedin_alert():
    async def _run():
        adapter = LinkedInAlertJobAdapter()
        assert adapter.check_availability().available is True
        assert adapter.source_name == JobSource.LINKEDIN_ALERT

        raw_alert = """
        Your Daily Job Alert:
        Senior Frontend Developer at Stripe
        Remote · Worldwide
        View job: https://www.linkedin.com/jobs/view/4011223344/

        Full Stack Engineer (React/Node) at Vercel
        San Francisco, CA · Hybrid
        View job: https://www.linkedin.com/jobs/view/4055667788/?refId=abc
        """

        jobs = await adapter.discover_or_ingest(alert_text=raw_alert)
        assert len(jobs) == 2

        # Source attribution & original URL
        j1 = jobs[0]
        assert j1.source == JobSource.LINKEDIN_ALERT
        assert j1.external_id == "4011223344"
        assert j1.source_url == "https://www.linkedin.com/jobs/view/4011223344/"
        assert j1.raw_description  # Verbatim description stored

        j2 = jobs[1]
        assert j2.external_id == "4055667788"
        assert j2.source_url == "https://www.linkedin.com/jobs/view/4055667788/"

    asyncio.run(_run())


def test_adapter_linkedin_url():
    async def _run():
        adapter = LinkedInUrlJobAdapter()
        assert adapter.check_availability().available is True
        assert adapter.source_name == JobSource.LINKEDIN_URL

        # Test canonicalization of query parameter format
        url = "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=3888999111&origin=JOB_ALERT"
        jobs = await adapter.discover_or_ingest(
            url=url,
            optional_title="React Developer",
            optional_company="Ecosystem Core",
            optional_snippet="Building reactive interfaces with React 19.",
            modality=WorkModality.REMOTE,
        )
        assert len(jobs) == 1
        job = jobs[0]
        assert job.source == JobSource.LINKEDIN_URL
        assert job.external_id == "3888999111"
        assert job.source_url == "https://www.linkedin.com/jobs/view/3888999111/"
        assert job.title == "React Developer"
        assert job.company_name == "Ecosystem Core"
        assert "React 19" in job.raw_description

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 2. Greenhouse Public Board Adapter Tests
# ---------------------------------------------------------------------------

def test_adapter_greenhouse_mock_success():
    async def _run():
        adapter = GreenhouseJobAdapter()
        assert adapter.check_availability().available is True
        assert adapter.source_name == JobSource.GREENHOUSE

        mock_payload = {
            "jobs": [
                {
                    "id": 991100,
                    "title": "Full Stack Developer (React / Next.js)",
                    "location": {"name": "Remote, Global"},
                    "absolute_url": "https://boards.greenhouse.io/techcorp/jobs/991100",
                    "content": "<p>We are seeking a <strong>Full Stack Developer</strong> with 2-5 years experience.</p>",
                    "updated_at": "2026-11-10T12:00:00Z",
                },
                {
                    "id": 991101,
                    "title": "Data Scientist",
                    "location": {"name": "New York, NY"},
                    "absolute_url": "https://boards.greenhouse.io/techcorp/jobs/991101",
                    "content": "<p>Python data role.</p>",
                    "updated_at": "2026-11-09T10:00:00Z",
                },
            ]
        }

        mock_resp = httpx.Response(200, json=mock_payload, request=httpx.Request("GET", "https://test"))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            # Ingest with role filter
            jobs = await adapter.discover_or_ingest(board_token="techcorp", filter_role="Full Stack")
            assert len(jobs) == 1
            job = jobs[0]
            assert job.source == JobSource.GREENHOUSE
            assert job.external_id == "991100"
            assert job.source_url == "https://boards.greenhouse.io/techcorp/jobs/991100"
            assert job.title == "Full Stack Developer (React / Next.js)"
            assert job.modality == WorkModality.REMOTE
            assert "<strong>Full Stack Developer</strong>" in job.raw_description
            assert "Full Stack Developer" in job.cleaned_description

    asyncio.run(_run())


def test_adapter_greenhouse_genuine_error():
    async def _run():
        adapter = GreenhouseJobAdapter()
        # Missing board token raises ValueError
        with pytest.raises(ValueError, match="Greenhouse board_token is required"):
            await adapter.discover_or_ingest(board_token="")

        # 404 response raises genuine descriptive error
        mock_resp = httpx.Response(404, request=httpx.Request("GET", "https://test"))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(RuntimeError, match="not found"):
                await adapter.discover_or_ingest(board_token="non_existent_company_xyz")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 3. Lever Public Postings Adapter Tests
# ---------------------------------------------------------------------------

def test_adapter_lever_mock_success():
    async def _run():
        adapter = LeverJobAdapter()
        assert adapter.check_availability().available is True
        assert adapter.source_name == JobSource.LEVER

        mock_payload = [
            {
                "id": "lev-12345",
                "text": "Frontend Developer - React 19",
                "categories": {"location": "Remote - Worldwide", "commitment": "Full-Time"},
                "hostedUrl": "https://jobs.lever.co/mediaapp/lev-12345",
                "descriptionPlain": "Build high performance user interfaces using React, Next.js, and TypeScript.",
                "createdAt": 1731500000000,
            }
        ]

        mock_resp = httpx.Response(200, json=mock_payload, request=httpx.Request("GET", "https://test"))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            jobs = await adapter.discover_or_ingest(company_id="mediaapp")
            assert len(jobs) == 1
            job = jobs[0]
            assert job.source == JobSource.LEVER
            assert job.external_id == "lev-12345"
            assert job.source_url == "https://jobs.lever.co/mediaapp/lev-12345"
            assert job.title == "Frontend Developer - React 19"
            assert job.modality == WorkModality.REMOTE
            assert "React 19" in job.title

    asyncio.run(_run())


def test_adapter_lever_genuine_error():
    async def _run():
        adapter = LeverJobAdapter()
        with pytest.raises(ValueError, match="Lever company_id is required"):
            await adapter.discover_or_ingest(company_id="")

        mock_resp = httpx.Response(404, request=httpx.Request("GET", "https://test"))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(RuntimeError, match="not found"):
                await adapter.discover_or_ingest(company_id="non_existent_lever_comp")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 4. Public API & Careers Page Adapters Tests
# ---------------------------------------------------------------------------

def test_adapter_company_careers_and_direct():
    async def _run():
        careers_adapter = CompanyCareersJobAdapter()
        assert careers_adapter.source_name == JobSource.COMPANY_CAREERS
        jobs = await careers_adapter.discover_or_ingest(
            url="https://company.com/careers/software-dev",
            title="Software Developer",
            company="Global Tech",
            raw_text="Full time software developer role.",
        )
        assert len(jobs) == 1
        assert jobs[0].source == JobSource.COMPANY_CAREERS
        assert jobs[0].source_url == "https://company.com/careers/software-dev"

        direct_adapter = DirectUrlJobAdapter()
        assert direct_adapter.source_name == JobSource.DIRECT_URL
        d_jobs = await direct_adapter.discover_or_ingest(
            url="https://direct.com/job/42",
            title="Node.js Developer",
            company="Backend Systems",
        )
        assert len(d_jobs) == 1
        assert d_jobs[0].source == JobSource.DIRECT_URL

    asyncio.run(_run())


def test_adapter_remoteok():
    async def _run():
        adapter = RemoteOKJobAdapter()
        assert adapter.check_availability().available is True
        assert adapter.source_name == JobSource.PUBLIC_API

        mock_data = [
            {"legal": "disclosure"},
            {
                "id": "rok-999",
                "position": "Full Stack React / Node Developer",
                "company": "Distributed Labs",
                "location": "Worldwide",
                "url": "https://remoteok.com/l/rok-999",
                "description": "<p>2-5 years experience needed.</p>",
                "tags": ["react", "node", "typescript"],
            },
        ]
        mock_resp = httpx.Response(200, json=mock_data, request=httpx.Request("GET", "https://remoteok.com/api"))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            jobs = await adapter.discover_or_ingest(query="react")
            assert len(jobs) == 1
            assert jobs[0].source == JobSource.PUBLIC_API
            assert jobs[0].external_id == "rok-999"
            assert "react" in jobs[0].required_skills

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 5. Expiry Detection Engine Tests
# ---------------------------------------------------------------------------

def test_expiry_checker():
    async def _run():
        # Case 1: 404 Not Found indicates expired listing
        mock_404 = httpx.Response(404, request=httpx.Request("GET", "https://job.test/closed"))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_404):
            is_expired, code, reason = await ExpiryChecker.check_url_active("https://job.test/closed")
            assert is_expired is True
            assert code == 404

        # Case 2: 200 OK but page states "position has been filled"
        mock_closed = httpx.Response(
            200,
            text="<html><body>This position has been filled. Thank you for your interest.</body></html>",
            request=httpx.Request("GET", "https://job.test/filled"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_closed):
            is_expired, code, reason = await ExpiryChecker.check_url_active("https://job.test/filled")
            assert is_expired is True
            assert "position has been filled" in reason

        # Case 3: Active listing
        mock_active = httpx.Response(
            200,
            text="<html><body><h1>Full Stack Developer</h1><button>Apply Now</button></body></html>",
            request=httpx.Request("GET", "https://job.test/active"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_active):
            is_expired, code, reason = await ExpiryChecker.check_url_active("https://job.test/active")
            assert is_expired is False
            assert code == 200

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 6. Duplicate Detection & Search Filters Tests
# ---------------------------------------------------------------------------

def test_storage_filters_and_deduplication(storage: JobHuntingStorage):
    # Create distinct jobs
    h1 = compute_job_content_hash("Stripe", "React Developer", "Remote", "101")
    j1 = JobListing(
        id="j_react",
        source=JobSource.GREENHOUSE,
        external_id="101",
        source_url="https://boards.greenhouse.io/stripe/101",
        company_name="Stripe",
        title="React Developer",
        location="Remote",
        modality=WorkModality.REMOTE,
        salary_min=120000.0,
        salary_max=160000.0,
        experience_required_min=2,
        experience_required_max=4,
        raw_description="Original verbatim JD for Stripe React role.",
        content_hash=h1,
    )
    storage.save_job(j1)

    h2 = compute_job_content_hash("Spotify", "Node.js Developer", "New York", "202")
    j2 = JobListing(
        id="j_node",
        source=JobSource.LEVER,
        external_id="202",
        source_url="https://jobs.lever.co/spotify/202",
        company_name="Spotify",
        title="Node.js Developer",
        location="New York",
        modality=WorkModality.HYBRID,
        salary_min=140000.0,
        salary_max=180000.0,
        experience_required_min=3,
        experience_required_max=5,
        raw_description="Original verbatim JD for Spotify Node role.",
        content_hash=h2,
    )
    storage.save_job(j2)

    # 1. Filter by modality
    remote_jobs = storage.list_jobs(modality=WorkModality.REMOTE)
    assert len(remote_jobs) == 1
    assert remote_jobs[0].company_name == "Stripe"

    # 2. Filter by source
    lever_jobs = storage.list_jobs(source=JobSource.LEVER)
    assert len(lever_jobs) == 1
    assert lever_jobs[0].company_name == "Spotify"

    # 3. Filter by min salary
    high_pay_jobs = storage.list_jobs(min_salary=170000.0)
    assert len(high_pay_jobs) == 1
    assert high_pay_jobs[0].title == "Node.js Developer"

    # 4. Filter by experience range
    exp_jobs = storage.list_jobs(experience_min=2, experience_max=3)
    assert len(exp_jobs) >= 1

    # 5. Mark expiry and filter by is_expired
    storage.mark_job_expiry(job_id="j_react", is_expired=True, checked_at="2026-11-13T12:00:00Z")
    expired_list = storage.list_jobs(is_expired=True)
    assert len(expired_list) == 1
    assert expired_list[0].id == "j_react"

    active_list = storage.list_jobs(is_expired=False)
    assert len(active_list) == 1
    assert active_list[0].id == "j_node"


# ---------------------------------------------------------------------------
# 7. Discovery Run History & Scheduling Tests
# ---------------------------------------------------------------------------

def test_discovery_history_and_scheduler(storage: JobHuntingStorage):
    async def _run():
        discovery_svc = JobDiscoveryService(storage=storage)
        profile_svc = CandidateProfileService(storage=storage)

        # Trigger discovery
        mock_jobs = [
            {
                "id": "1",
                "position": "Frontend Developer",
                "company": "ACME",
                "location": "Worldwide",
                "url": "https://remoteok.com/l/1",
                "description": "Frontend role",
                "tags": ["react"],
            }
        ]
        mock_resp = httpx.Response(200, json=mock_data_helper(mock_jobs), request=httpx.Request("GET", "https://test"))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            jobs = await discovery_svc.discover_jobs(query="Frontend Developer")
            assert len(jobs) >= 1

        # Verify discovery run history logged
        runs = discovery_svc.list_discovery_runs()
        assert len(runs) >= 1
        assert runs[0].status in ("completed", "partial")
        assert runs[0].jobs_found >= 1

        # Test scheduler configuration
        scheduler = JobDiscoveryScheduler(discovery_service=discovery_svc, profile_service=profile_svc)
        cfg = scheduler.get_config()
        assert cfg.enabled is True
        assert cfg.interval_hours == 12

        updated_cfg = scheduler.update_config(enabled=False, interval_hours=24)
        assert updated_cfg.enabled is False
        assert updated_cfg.interval_hours == 24

    asyncio.run(_run())


def mock_data_helper(items):
    return [{"legal": "disclosure"}] + items


# ---------------------------------------------------------------------------
# 8. REST Endpoints Integration Tests (Discovery Engine)
# ---------------------------------------------------------------------------

def test_api_discovery_engine_endpoints(client: TestClient):
    # Ingest greenhouse mock
    mock_gh = {
        "jobs": [
            {
                "id": 556677,
                "title": "Software Developer (React)",
                "location": {"name": "Remote"},
                "absolute_url": "https://boards.greenhouse.io/gitlab/jobs/556677",
                "content": "<p>Developer position.</p>",
            }
        ]
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=httpx.Response(200, json=mock_gh)):
        gh_res = client.post(
            "/api/job-hunting/ingest/greenhouse",
            json={"board_token": "gitlab", "filter_role": "React"},
            headers=auth_headers(),
        )
        assert gh_res.status_code == 200
        jobs = gh_res.json()
        assert len(jobs) == 1
        assert jobs[0]["source"] == "greenhouse"
        job_id = jobs[0]["id"]

    # Ingest lever mock
    mock_lev = [
        {
            "id": "lev-9988",
            "text": "Full Stack Developer",
            "categories": {"location": "Remote"},
            "hostedUrl": "https://jobs.lever.co/spotify/lev-9988",
            "descriptionPlain": "Full stack role description.",
        }
    ]
    mock_lever_resp = httpx.Response(200, json=mock_lev, request=httpx.Request("GET", "https://api.lever.co"))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_lever_resp):
        lev_res = client.post(
            "/api/job-hunting/ingest/lever",
            json={"company_id": "spotify"},
            headers=auth_headers(),
        )
        if lev_res.status_code != 200:
            print("LEVER FAILURE DETAIL:", lev_res.json())
        assert lev_res.status_code == 200
        assert len(lev_res.json()) == 1
        assert lev_res.json()[0]["source"] == "lever"

    # Check expiry endpoint
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=httpx.Response(404)):
        exp_res = client.post(f"/api/job-hunting/jobs/{job_id}/check-expiry", headers=auth_headers())
        assert exp_res.status_code == 200
        assert exp_res.json()["is_expired"] is True

    # Check discovery history endpoint
    hist_res = client.get("/api/job-hunting/discovery/history", headers=auth_headers())
    assert hist_res.status_code == 200
    assert "runs" in hist_res.json()

    # Check discovery schedule endpoints
    sched_get = client.get("/api/job-hunting/discovery/schedule", headers=auth_headers())
    assert sched_get.status_code == 200
    assert sched_get.json()["enabled"] is True

    sched_put = client.put(
        "/api/job-hunting/discovery/schedule",
        json={"enabled": True, "interval_hours": 6},
        headers=auth_headers(),
    )
    assert sched_put.status_code == 200
    assert sched_put.json()["interval_hours"] == 6

    # Test filtered job query
    filtered_res = client.get(
        "/api/job-hunting/jobs?source=greenhouse&is_expired=true",
        headers=auth_headers(),
    )
    assert filtered_res.status_code == 200
    assert filtered_res.json()["total"] >= 1


# ---------------------------------------------------------------------------
# Phase 6: Compliance & LinkedIn Data Export Ingestion Tests
# ---------------------------------------------------------------------------

def test_adapter_linkedin_data_export_csv():
    async def _run():
        adapter = LinkedInDataExportAdapter()
        assert adapter.check_availability().available is True

        csv_content = """Job Title,Company Name,Job Url,Saved Date
Staff Frontend Engineer,Stripe,https://www.linkedin.com/jobs/view/9988776655/,2026-05-10
Principal Systems Architect,Cloudflare,https://www.linkedin.com/jobs/view/1122334455/?refId=feed,2026-05-11
"""
        jobs = await adapter.discover_or_ingest(file_text=csv_content, filename="Saved Jobs.csv")
        assert len(jobs) == 2

        j1 = jobs[0]
        assert j1.title == "Staff Frontend Engineer"
        assert j1.company_name == "Stripe"
        assert j1.external_id == "9988776655"
        assert j1.source_url == "https://www.linkedin.com/jobs/view/9988776655/"
        assert j1.source == JobSource.LINKEDIN_URL

        j2 = jobs[1]
        assert j2.title == "Principal Systems Architect"
        assert j2.company_name == "Cloudflare"
        assert j2.external_id == "1122334455"

    asyncio.run(_run())


def test_adapter_linkedin_data_export_zip():
    import io
    import zipfile

    async def _run():
        adapter = LinkedInDataExportAdapter()
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "Saved Jobs.csv",
                "Job Title,Company Name,Job Url,Saved Date\nLead React Architect,Vercel,https://www.linkedin.com/jobs/view/3344556677/,2026-05-12\n",
            )
        zip_bytes = zip_buf.getvalue()

        jobs = await adapter.discover_or_ingest(file_bytes=zip_bytes, filename="linkedin_archive.zip")
        assert len(jobs) == 1
        assert jobs[0].company_name == "Vercel"
        assert jobs[0].title == "Lead React Architect"
        assert jobs[0].external_id == "3344556677"

    asyncio.run(_run())


def test_cross_source_deduplication():
    # 1. Title normalization (standardizes Sr. -> senior, removes parenthetical noise)
    assert normalize_job_title("Senior Frontend Engineer (Remote)") == "senior frontend engineer"
    assert normalize_job_title("Sr. Frontend Engineer") == "senior frontend engineer"
    assert normalize_job_title("Staff Full Stack Developer - Hybrid") == "staff full stack developer"

    # 2. Company domain normalization
    assert extract_company_domain("Stripe, Inc.", "https://boards.greenhouse.io/stripe/jobs/123") == "stripe"
    assert extract_company_domain("Vercel Technologies", "https://jobs.lever.co/vercel/abc-123") == "vercel"

    # 3. Cross-source duplicate detection
    job_gh = JobListing(
        id="gh-1",
        title="Senior Frontend Engineer (Remote)",
        company_name="Stripe",
        location="Remote",
        source=JobSource.GREENHOUSE,
        source_url="https://boards.greenhouse.io/stripe/jobs/123",
        external_id="gh-123",
        raw_description="Build modern checkout interfaces at scale.",
        content_hash=compute_job_content_hash("Stripe", "Senior Frontend Engineer (Remote)", "Remote", "gh-123"),
    )
    job_li = JobListing(
        id="li-1",
        title="Sr. Frontend Engineer",
        company_name="Stripe, Inc.",
        location="Remote",
        source=JobSource.LINKEDIN_ALERT,
        source_url="https://www.linkedin.com/jobs/view/456",
        external_id="456",
        raw_description="Different description from exported alert snippet.",
        content_hash=compute_job_content_hash("Stripe, Inc.", "Sr. Frontend Engineer", "Remote", "456"),
    )
    assert are_jobs_duplicate(job_gh, job_li) is True

    # Non-duplicate: different company
    job_other = JobListing(
        id="oth-1",
        title="Senior Frontend Engineer",
        company_name="Datadog",
        location="Remote",
        source=JobSource.LEVER,
        source_url="https://jobs.lever.co/datadog/789",
        external_id="789",
        raw_description="Datadog role description.",
        content_hash=compute_job_content_hash("Datadog", "Senior Frontend Engineer", "Remote", "789"),
    )
    assert are_jobs_duplicate(job_gh, job_other) is False


def test_api_linkedin_data_export(client: TestClient):
    csv_bytes = b"Job Title,Company Name,Job Url,Saved Date\nPlatform Engineer,GitHub,https://www.linkedin.com/jobs/view/7788990011/,2026-05-13\n"
    res = client.post(
        "/api/job-hunting/ingest/linkedin-data-export",
        files={"file": ("Saved Jobs.csv", csv_bytes, "text/csv")},
        headers=auth_headers(),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data) == 1
    assert data[0]["company_name"] == "GitHub"
    assert data[0]["title"] == "Platform Engineer"


def test_api_export_and_purge_career_data(client: TestClient):
    # 1. Export data endpoint
    res_exp = client.get("/api/job-hunting/data/export", headers=auth_headers())
    assert res_exp.status_code == 200
    export_payload = res_exp.json()
    assert "version" in export_payload
    assert "exported_at" in export_payload
    assert "jobs" in export_payload

    # 2. Purge data endpoint
    res_purge = client.post("/api/job-hunting/data/purge", headers=auth_headers())
    assert res_purge.status_code == 200
    purge_payload = res_purge.json()
    assert "job_listings" in purge_payload


