"""
Tests for ALEX RESUME STUDIO for Job Hunting.
Covers:
- 6-step customization pipeline:
  1. Read original resume.
  2. Read job description.
  3. Identify relevant experience.
  4. Identify relevant technical skills.
  5. Prepare customized resume.
  6. Generate personalized cover letter.
- Anti-fabrication guarantees (never invent experience, employment history, achievements).
- Original resume preservation (original master resume remains untouched).
- Independent versioning (saving each generated version independently).
- DOCX and PDF rendering and validation.
- Preview and editing capabilities.
- Document download endpoints for DOCX, PDF, and Markdown.
- Integration with File Workspace and SQLite storage.
- Association of every document with its job.
"""

from __future__ import annotations

import asyncio
import io
from pathlib import Path
from unittest.mock import MagicMock

import docx
import pypdf
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.job_hunting import (
    CandidatePreferences,
    CandidateProfile,
    JobListing,
    JobSource,
    SkillItem,
    TailoredDocument,
    WorkExperienceItem,
    WorkModality,
)
from app.services.job_hunting.document_exporter import DocumentExporter
from app.services.job_hunting.job_hunting_service import JobHuntingService
from app.services.job_hunting.storage import JobHuntingStorage
from app.services.job_hunting.tailoring_service import ResumeTailoringService


@pytest.fixture
def storage(tmp_path: Path) -> JobHuntingStorage:
    return JobHuntingStorage(tmp_path / "test_resume_studio.db")


@pytest.fixture
def sample_profile(tmp_path: Path) -> CandidateProfile:
    master_path = tmp_path / "master_resume.pdf"
    master_path.write_bytes(b"%PDF-1.4 Original Master Resume Content")

    return CandidateProfile(
        id="candidate_alex_01",
        full_name="Alex Mercer",
        email="alex.mercer@alex-ai.local",
        phone="+1 555-0199",
        location="Worldwide / Remote",
        headline="Full Stack Developer (React / Next.js / Node.js)",
        summary="Full Stack Developer with 3.5 years experience building performant web applications with React, Next.js, and Node.js.",
        total_years_experience=3.5,
        seniority_level="Mid-Level",
        programming_languages=["TypeScript", "JavaScript", "Python"],
        frameworks=["React", "Next.js", "Node.js", "FastAPI"],
        databases=["PostgreSQL", "SQLite", "Redis"],
        skills=[
            SkillItem(name="React", category="Frontend", proficiency="Expert", years_experience=3.5),
            SkillItem(name="Next.js", category="Frontend", proficiency="Proficient", years_experience=2.5),
            SkillItem(name="Node.js", category="Backend", proficiency="Expert", years_experience=3.5),
            SkillItem(name="TypeScript", category="Language", proficiency="Expert", years_experience=3.0),
            SkillItem(name="FastAPI", category="Backend", proficiency="Proficient", years_experience=2.0),
            SkillItem(name="PostgreSQL", category="Database", proficiency="Proficient", years_experience=3.0),
        ],
        work_history=[
            WorkExperienceItem(
                company_name="Apex Labs",
                role_title="Full Stack Software Engineer",
                location="Remote",
                is_remote=True,
                start_date="2022-01",
                is_current=True,
                highlights=[
                    "Engineered responsive UI architectures using React 19 and Next.js.",
                    "Architected high-throughput microservices using Node.js and TypeScript.",
                    "Optimized PostgreSQL schema and indexed Redis caching layers.",
                ],
                tech_stack=["React", "Next.js", "Node.js", "TypeScript", "FastAPI", "PostgreSQL"],
            )
        ],
        master_resume_path=str(master_path.resolve()),
        raw_resume_text="Original Master Resume text for Alex Mercer...",
        is_verified=True,
    )


@pytest.fixture
def sample_job(storage: JobHuntingStorage) -> JobListing:
    job = JobListing(
        id="job_studio_target",
        source=JobSource.DIRECT_URL,
        source_url="https://cloudscale.io/careers/fullstack",
        company_name="CloudScale Systems",
        title="Full Stack React & Node Engineer",
        location="Remote",
        modality=WorkModality.REMOTE,
        experience_required_min=2,
        experience_required_max=5,
        required_skills=["React", "TypeScript", "Node.js", "PostgreSQL"],
        preferred_skills=["Next.js", "Redis"],
        raw_description="CloudScale Systems is looking for a Full Stack React & Node Engineer to scale our web applications.",
        content_hash="hash_studio_01",
    )
    storage.save_job(job)
    return job


# ---------------------------------------------------------------------------
# 1. 6-Step Pipeline & Non-Fabrication Tests
# ---------------------------------------------------------------------------

def test_resume_studio_6_step_pipeline_execution(
    storage: JobHuntingStorage,
    sample_profile: CandidateProfile,
    sample_job: JobListing,
    tmp_path: Path,
):
    """
    Verifies the 6-step customization pipeline:
    1. Reads original resume (leaves it unchanged).
    2. Reads job description.
    3. Identifies relevant experience.
    4. Identifies relevant technical skills.
    5. Prepares customized resume.
    6. Generates personalized cover letter.
    """
    storage.save_candidate_profile(sample_profile)
    workspace_dir = tmp_path / "workspace"

    service = ResumeTailoringService(
        storage=storage,
        workspace_root=workspace_dir,
    )

    # Record original master resume content before tailoring
    orig_path = Path(sample_profile.master_resume_path)
    orig_bytes = orig_path.read_bytes()

    async def _run():
        return await service.generate_tailored_package(job=sample_job, profile=sample_profile)

    doc = asyncio.run(_run())

    # Step 1 Check: Original resume preserved completely unchanged
    assert doc.original_resume_preserved is True
    assert orig_path.read_bytes() == orig_bytes

    # Step 2 & 3 Check: Relevant experience identified
    assert len(doc.relevant_experience_identified) > 0
    for exp in doc.relevant_experience_identified:
        # Must be authentic highlight from sample_profile
        assert "Apex Labs" in exp or "Full Stack" in exp

    # Step 4 Check: Relevant technical skills identified without fabrication
    assert len(doc.relevant_skills_identified) >= 3
    assert "React" in doc.relevant_skills_identified
    assert "Node.js" in doc.relevant_skills_identified
    assert "TypeScript" in doc.relevant_skills_identified

    # Step 5 Check: Customized resume markdown
    assert "CloudScale Systems" in doc.resume_markdown
    assert "Full Stack React & Node Engineer" in doc.resume_markdown
    assert "Apex Labs" in doc.resume_markdown

    # Step 6 Check: Personalized cover letter
    assert "CloudScale Systems" in doc.cover_letter_markdown
    assert "Full Stack React & Node Engineer" in doc.cover_letter_markdown
    assert "Alex Mercer" in doc.cover_letter_markdown


# ---------------------------------------------------------------------------
# 2. Anti-Hallucination & No Fabricated Experience Tests
# ---------------------------------------------------------------------------

def test_anti_hallucination_guarantee_no_fabricated_history(
    storage: JobHuntingStorage,
    sample_profile: CandidateProfile,
    tmp_path: Path,
):
    """
    Ensures that when a job demands skills the candidate lacks (e.g. C++, Solidity, Blockchain),
    the system NEVER invents jobs, employers, or project achievements.
    """
    storage.save_candidate_profile(sample_profile)
    blockchain_job = JobListing(
        id="job_blockchain_lead",
        source=JobSource.DIRECT_URL,
        source_url="https://crypto.xyz/jobs/1",
        company_name="BlockChain Co",
        title="Lead Solidity & Rust Protocol Engineer",
        location="Remote",
        modality=WorkModality.REMOTE,
        required_skills=["Solidity", "Rust", "C++", "Smart Contracts"],
        raw_description="Architect Layer-1 consensus protocols in Rust and Solidity.",
        content_hash="hash_crypto_1",
    )
    storage.save_job(blockchain_job)

    service = ResumeTailoringService(storage=storage, workspace_root=tmp_path / "workspace")

    async def _run():
        return await service.generate_tailored_package(job=blockchain_job, profile=sample_profile)

    doc = asyncio.run(_run())

    # Candidate only worked at "Apex Labs"
    assert "Apex Labs" in doc.resume_markdown
    # Must NOT invent fake companies
    assert "BlockChain Co" not in doc.resume_markdown.split("## Work Experience")[1]
    # Work experience must remain grounded in candidate ground truth
    assert "Engineered responsive UI" in doc.resume_markdown


# ---------------------------------------------------------------------------
# 3. Independent Versioning Tests
# ---------------------------------------------------------------------------

def test_independent_version_management(
    storage: JobHuntingStorage,
    sample_profile: CandidateProfile,
    sample_job: JobListing,
    tmp_path: Path,
):
    """Verifies that multiple versions for the same job are saved independently."""
    storage.save_candidate_profile(sample_profile)
    service = ResumeTailoringService(storage=storage, workspace_root=tmp_path / "workspace")

    async def _gen():
        v1 = await service.generate_tailored_package(job=sample_job, profile=sample_profile)
        v2 = await service.generate_tailored_package(job=sample_job, profile=sample_profile)
        v3 = await service.generate_tailored_package(job=sample_job, profile=sample_profile)
        return v1, v2, v3

    v1, v2, v3 = asyncio.run(_gen())

    assert v1.version_number == 1
    assert v2.version_number == 2
    assert v3.version_number == 3
    assert v1.id != v2.id != v3.id

    # Retrieve all versions for this job
    versions = service.list_versions_for_job(sample_job.id)
    assert len(versions) == 3
    assert [v.version_number for v in versions] == [1, 2, 3]


# ---------------------------------------------------------------------------
# 4. DOCX and PDF Generation & Validation Tests
# ---------------------------------------------------------------------------

def test_docx_and_pdf_document_generation(tmp_path: Path):
    """Verifies that DocumentExporter outputs structurally valid DOCX and PDF documents."""
    exporter = DocumentExporter(workspace_root=tmp_path / "workspace")

    md_content = """
    # Professional Summary
    Senior Full Stack Engineer with 3.5 years experience in React, Next.js, and Node.js.

    ## Technical Proficiencies
    - **Frontend**: React, Next.js, TypeScript, Tailwind CSS
    - **Backend**: Node.js, FastAPI, Express
    - **Databases**: PostgreSQL, Redis, SQLite

    ## Work Experience
    ### Full Stack Engineer | Apex Labs
    *2022 - Present | Remote*
    * Engineered microservices handling 10k requests/sec.
    * Reduced bundle sizes by 40% with Next.js code splitting.
    """

    # 1. Test DOCX
    docx_bytes = exporter.export_docx(
        title="Alex Mercer",
        subtitle="Full Stack Developer",
        content_markdown=md_content,
        contact_info="alex@alex-ai.local | +1 555-0199 | Remote",
    )
    assert len(docx_bytes) > 1000
    # Validate with python-docx
    doc = docx.Document(io.BytesIO(docx_bytes))
    paragraphs_text = [p.text for p in doc.paragraphs]
    assert any("Alex Mercer" in p for p in paragraphs_text)
    assert any("Apex Labs" in p for p in paragraphs_text)

    # 2. Test PDF
    pdf_bytes = exporter.export_pdf(
        title="Alex Mercer",
        subtitle="Full Stack Developer",
        content_markdown=md_content,
        contact_info="alex@alex-ai.local | +1 555-0199 | Remote",
    )
    assert len(pdf_bytes) > 500
    # Validate with pypdf
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    page1_text = reader.pages[0].extract_text()
    assert "Alex Mercer" in page1_text
    assert "Apex Labs" in page1_text


# ---------------------------------------------------------------------------
# 5. Preview, Editing, and In-Place vs New Version Tests
# ---------------------------------------------------------------------------

def test_preview_and_editing_tailored_documents(
    storage: JobHuntingStorage,
    sample_profile: CandidateProfile,
    sample_job: JobListing,
    tmp_path: Path,
):
    """Verifies preview and editing of tailored documents (in-place and as new version)."""
    storage.save_candidate_profile(sample_profile)
    service = ResumeTailoringService(storage=storage, workspace_root=tmp_path / "workspace")

    async def _run():
        return await service.generate_tailored_package(job=sample_job, profile=sample_profile)

    doc = asyncio.run(_run())

    # 1. Edit in-place
    updated_resume_md = doc.resume_markdown + "\n\n## Custom Section\nSpecialized Open Source Contributor."
    edited_doc = service.update_tailored_document(
        doc_id=doc.id,
        resume_markdown=updated_resume_md,
        create_new_version=False,
    )
    assert edited_doc.id == doc.id
    assert edited_doc.version_number == 1
    assert "Specialized Open Source Contributor" in edited_doc.resume_markdown

    # 2. Edit as new version
    v2_cl_md = "Dear Hiring Manager at CloudScale Systems,\nUpdated personalized introduction."
    v2_doc = service.update_tailored_document(
        doc_id=doc.id,
        cover_letter_markdown=v2_cl_md,
        create_new_version=True,
    )
    assert v2_doc.id != doc.id
    assert v2_doc.version_number == 2
    assert "Updated personalized introduction" in v2_doc.cover_letter_markdown

    # Both versions must be preserved in storage
    all_versions = service.list_versions_for_job(sample_job.id)
    assert len(all_versions) == 2


# ---------------------------------------------------------------------------
# 6. End-to-End API Download & Integration Tests
# ---------------------------------------------------------------------------

def test_api_resume_studio_endpoints_and_downloads(tmp_path: Path):
    """
    Tests end-to-end API endpoints for Resume Studio:
    - POST /api/job-hunting/jobs/{job_id}/tailor-resume
    - GET /api/job-hunting/jobs/{job_id}/tailored-documents
    - PUT /api/job-hunting/tailored-documents/{document_id}
    - GET /api/job-hunting/tailored-documents/{document_id}/download (pdf, docx, markdown)
    """
    app = create_app(data_dir=tmp_path, api_token="test-token")
    client = TestClient(app)

    # Ingest a job
    job_resp = client.post(
        "/api/job-hunting/ingest/url",
        json={
            "url": "https://techgig.io/careers/react-lead",
            "title": "Lead React Developer",
            "company": "TechGig",
            "raw_text": "We need a Lead React Developer experienced with TypeScript, Next.js, and Node.js microservices.",
            "modality": "remote",
        },
        headers={"Authorization": "Bearer test-token"},
    )
    assert job_resp.status_code == 200
    job_id = job_resp.json()["id"]

    # 1. Tailor Resume Package
    tailor_resp = client.post(
        f"/api/job-hunting/jobs/{job_id}/tailor-resume",
        headers={"Authorization": "Bearer test-token"},
    )
    assert tailor_resp.status_code == 200
    doc_data = tailor_resp.json()
    doc_id = doc_data["id"]
    assert doc_data["version_number"] == 1
    assert "TechGig" in doc_data["resume_markdown"]
    assert "TechGig" in doc_data["cover_letter_markdown"]

    # 2. List Versions
    list_resp = client.get(
        f"/api/job-hunting/jobs/{job_id}/tailored-documents",
        headers={"Authorization": "Bearer test-token"},
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total_versions"] >= 1

    # 3. Edit Document
    put_resp = client.put(
        f"/api/job-hunting/tailored-documents/{doc_id}",
        json={
            "resume_markdown": doc_data["resume_markdown"] + "\n\n## Certifications\nCertified AWS Cloud Developer.",
            "create_new_version": False,
        },
        headers={"Authorization": "Bearer test-token"},
    )
    assert put_resp.status_code == 200
    assert "Certified AWS Cloud Developer" in put_resp.json()["resume_markdown"]

    # 4. Download DOCX Resume
    dl_docx_resp = client.get(
        f"/api/job-hunting/tailored-documents/{doc_id}/download?format=docx&doc_type=resume",
        headers={"Authorization": "Bearer test-token"},
    )
    assert dl_docx_resp.status_code == 200
    assert "wordprocessingml.document" in dl_docx_resp.headers["content-type"]
    assert len(dl_docx_resp.content) > 1000

    # 5. Download PDF Resume
    dl_pdf_resp = client.get(
        f"/api/job-hunting/tailored-documents/{doc_id}/download?format=pdf&doc_type=resume",
        headers={"Authorization": "Bearer test-token"},
    )
    assert dl_pdf_resp.status_code == 200
    assert "application/pdf" in dl_pdf_resp.headers["content-type"]
    assert len(dl_pdf_resp.content) > 500

    # 6. Download PDF Cover Letter
    dl_cl_pdf_resp = client.get(
        f"/api/job-hunting/tailored-documents/{doc_id}/download?format=pdf&doc_type=cover_letter",
        headers={"Authorization": "Bearer test-token"},
    )
    assert dl_cl_pdf_resp.status_code == 200
    assert "application/pdf" in dl_cl_pdf_resp.headers["content-type"]
    assert len(dl_cl_pdf_resp.content) > 500

    # 7. Download Markdown
    dl_md_resp = client.get(
        f"/api/job-hunting/tailored-documents/{doc_id}/download?format=markdown&doc_type=resume",
        headers={"Authorization": "Bearer test-token"},
    )
    assert dl_md_resp.status_code == 200
    assert "text/markdown" in dl_md_resp.headers["content-type"]
    assert "TechGig" in dl_md_resp.text

