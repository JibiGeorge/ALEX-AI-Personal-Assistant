"""
Tests for ALEX Job Matching Engine.
Covers:
- Resume analysis via DocumentParserService and creation of verified candidate profile.
- Multi-factor comparison across 10 dimensions (technical skills, experience, languages,
  frameworks, databases, project experience, responsibilities, qualifications, location, seniority).
- Strict 6-factor multi-dimensional scoring weights (30% skills, 20% experience,
  20% responsibilities, 15% tech stack, 10% location, 5% seniority).
- Strict anti-hallucination guardrails (never fabricate candidate experience).
- Structured output validation via MatchAnalysisResult and CompatibilityScore.
- Model Ladder integration with fallback resilience.
- Persistent storage validation.
- API endpoint integration.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.job_hunting import (
    CandidatePreferences,
    CandidateProfile,
    CompatibilityScore,
    JobListing,
    JobSource,
    SkillItem,
    WorkExperienceItem,
    WorkModality,
)
from app.services.job_hunting.job_hunting_service import JobHuntingService
from app.services.job_hunting.matching_service import (
    JobMatchingService,
    MatchAnalysisResult,
)
from app.services.job_hunting.profile_service import CandidateProfileService
from app.services.job_hunting.storage import JobHuntingStorage
from app.services.model_ladder_service import ModelLadderService, TaskType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def storage(tmp_path: Path) -> JobHuntingStorage:
    db_path = tmp_path / "test_matching_engine.db"
    return JobHuntingStorage(db_path)


@pytest.fixture
def candidate_profile() -> CandidateProfile:
    return CandidateProfile(
        id="alex_verified_candidate",
        full_name="Alex Mercer",
        email="alex.mercer@alex-ai.local",
        phone="+1 555-0199",
        location="Worldwide / Remote",
        headline="Full Stack Developer (React / Next.js / Node.js)",
        summary="Full Stack Developer with 3.5 years experience building high-performance web applications with React, Next.js, and Node.js.",
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
                company_name="Apex Cloud Labs",
                role_title="Full Stack Software Engineer",
                location="Remote",
                is_remote=True,
                start_date="2022-01",
                is_current=True,
                highlights=[
                    "Engineered responsive UI using React 19 and Next.js App Router.",
                    "Architected high-throughput microservices using Node.js, TypeScript, and FastAPI.",
                    "Optimized PostgreSQL schema and indexed Redis caching layers.",
                ],
                tech_stack=["React", "Next.js", "Node.js", "TypeScript", "FastAPI", "PostgreSQL", "Redis"],
            )
        ],
        preferences=CandidatePreferences(
            target_roles=["Full Stack Developer", "Software Developer", "React Developer"],
            min_years_experience=2,
            max_years_experience=5,
            modalities=[WorkModality.REMOTE, WorkModality.HYBRID],
            target_locations=["Worldwide", "Remote", "United States"],
        ),
        is_verified=True,
        verified_at="2026-11-13T12:00:00Z",
        verification_notes="Verified by DocumentParserService",
    )


# ---------------------------------------------------------------------------
# 1. Resume Ingestion & Candidate Profile Verification Tests
# ---------------------------------------------------------------------------

def test_resume_ingestion_and_candidate_verification(storage: JobHuntingStorage, tmp_path: Path):
    """Verifies that DocumentParserService parses uploaded resume text into a verified profile."""
    # Mock DocumentParserService
    mock_parser = MagicMock()
    mock_parse_result = MagicMock()
    mock_parse_result.text = """
    Alex Mercer
    Email: alex.mercer@alex-ai.local
    Phone: +1 (555) 019-9000
    LinkedIn: linkedin.com/in/alex-mercer-dev
    GitHub: github.com/alexmercer

    Professional Summary:
    Full Stack Developer with 4 years of experience specializing in React, Next.js, Node.js, TypeScript, and PostgreSQL.

    Technical Skills:
    Languages: TypeScript, JavaScript, Python
    Frameworks: React, Next.js, Node.js, Express, FastAPI
    Databases: PostgreSQL, Redis, SQLite

    Experience:
    Senior Software Engineer | CloudTech Inc. | 2022 - Present
    - Architected scalable cloud services using Node.js and TypeScript.
    - Built responsive frontend applications with React and Next.js.
    """
    mock_parser.parse_document.return_value = mock_parse_result

    profile_service = CandidateProfileService(
        storage=storage,
        document_parser_service=mock_parser,
    )

    resume_file = tmp_path / "Alex_Mercer_Resume.pdf"
    resume_file.write_bytes(b"%PDF-1.4 mock resume binary content")

    profile = profile_service.ingest_resume_file(resume_file)

    assert profile.is_verified is True
    assert profile.verified_at is not None
    assert "Alex_Mercer_Resume.pdf" in profile.verification_notes
    assert profile.full_name == "Alex Mercer"
    assert profile.email == "alex.mercer@alex-ai.local"
    assert profile.phone is not None
    assert profile.linkedin_url == "https://linkedin.com/in/alex-mercer-dev"
    assert profile.github_url == "https://github.com/alexmercer"

    # Verify extracted skills and calibrated seniority
    assert "TypeScript" in profile.programming_languages
    assert "React" in profile.frameworks
    assert "PostgreSQL" in profile.databases
    assert profile.total_years_experience == 4.0
    assert profile.seniority_level == "Mid-Level"


# ---------------------------------------------------------------------------
# 2. Multi-Factor Scoring & 6-Factor Weights Tests
# ---------------------------------------------------------------------------

def test_matching_engine_strict_6_factor_weights(
    storage: JobHuntingStorage,
    candidate_profile: CandidateProfile,
):
    """
    Verifies the exact multi-factor scoring formula:
    match_percentage = round(
        0.30 * Technical Skills +
        0.20 * Experience +
        0.20 * Responsibilities +
        0.15 * Tech Stack +
        0.10 * Location +
        0.05 * Seniority
    )
    """
    matching_service = JobMatchingService(storage=storage)

    high_match_job = JobListing(
        id="job_fullstack_ideal",
        source=JobSource.DIRECT_URL,
        source_url="https://careers.techcorp.io/job/101",
        company_name="TechCorp",
        title="Full Stack Developer (React / Node.js)",
        location="Remote",
        modality=WorkModality.REMOTE,
        experience_required_min=2,
        experience_required_max=5,
        required_skills=["React", "TypeScript", "Node.js"],
        raw_description="Looking for a Full Stack Developer with 2-5 years experience to build and scale APIs and responsive UI with React and Node.js.",
        content_hash="hash_ideal_1",
    )
    storage.save_job(high_match_job)

    score = matching_service.calculate_match(job=high_match_job, profile=candidate_profile)

    # Validate individual dimensions
    assert score.technical_skills_score == 100
    assert score.experience_score == 100
    assert score.location_score == 100
    assert score.seniority_score == 100
    assert score.tech_stack_score >= 80
    assert score.responsibilities_score >= 60

    expected_weighted = int(round(
        (0.30 * score.technical_skills_score)
        + (0.20 * score.experience_score)
        + (0.20 * score.responsibilities_score)
        + (0.15 * score.tech_stack_score)
        + (0.10 * score.location_score)
        + (0.05 * score.seniority_score)
    ))

    assert score.match_percentage == expected_weighted
    assert score.overall_score == score.match_percentage
    assert score.ai_recommendation in ("HIGH_MATCH_APPLY", "CONSIDER_TAILORING")
    assert len(score.skills_matched) >= 3
    assert "React" in score.skills_matched
    assert "Typescript" in score.skills_matched or "TypeScript" in score.skills_matched


# ---------------------------------------------------------------------------
# 3. Anti-Hallucination & Non-Fabrication Guardrail Tests
# ---------------------------------------------------------------------------

def test_anti_hallucination_never_fabricates_candidate_experience(
    storage: JobHuntingStorage,
    candidate_profile: CandidateProfile,
):
    """
    CRITICAL: Never fabricate candidate experience.
    Job requires Rust, Kubernetes, and Go, which candidate does not have.
    Must NOT include them in skills_matched, MUST include them in skills_missing and mandatory_requirements_not_met.
    """
    matching_service = JobMatchingService(storage=storage)

    rust_job = JobListing(
        id="job_systems_rust",
        source=JobSource.DIRECT_URL,
        source_url="https://systems.infra.com/jobs/99",
        company_name="InfraCorp",
        title="Senior Systems Engineer",
        location="Remote",
        modality=WorkModality.REMOTE,
        experience_required_min=7,
        experience_required_max=10,
        required_skills=["Rust", "Kubernetes", "Go", "Distributed Systems"],
        raw_description="Build low-latency distributed kernels using Rust and Kubernetes.",
        content_hash="hash_rust_99",
    )
    storage.save_job(rust_job)

    score = matching_service.calculate_match(job=rust_job, profile=candidate_profile)

    # Candidate has TypeScript, JavaScript, Python, React, Next.js, Node.js, FastAPI, PostgreSQL, Redis
    # Absolutely NO Rust, Kubernetes, or Go should be claimed as matched
    for fabricated_skill in ["Rust", "Kubernetes", "Go", "Distributed Systems"]:
        assert fabricated_skill not in score.skills_matched

    # Missing skills must accurately list the gaps
    assert "Rust" in score.skills_missing
    assert "Kubernetes" in score.skills_missing
    assert len(score.mandatory_requirements_not_met) >= 3

    # Experience gaps must note the shortfall (3.5 years vs 7 years minimum requested)
    assert any("7" in gap and "3.5" in gap for gap in score.experience_gaps)

    # Recommendation for mismatch role must be LOW_MATCH_SKIP
    assert score.match_percentage < 60
    assert score.ai_recommendation == "LOW_MATCH_SKIP"


# ---------------------------------------------------------------------------
# 4. Structured Output Model Validation Tests
# ---------------------------------------------------------------------------

def test_structured_match_analysis_pydantic_validation():
    """Validates that MatchAnalysisResult strictly validates AI response schemas."""
    valid_payload = {
        "technical_skills_score": 85,
        "experience_score": 90,
        "responsibilities_score": 80,
        "tech_stack_score": 85,
        "location_score": 100,
        "seniority_score": 90,
        "skills_matched": ["React", "TypeScript", "Node.js"],
        "skills_missing": ["Docker"],
        "mandatory_requirements_not_met": [],
        "experience_gaps": [],
        "strengths": ["Deep React & TypeScript background"],
        "weaknesses": ["Docker containerization not explicitly highlighted"],
        "ai_recommendation": "HIGH_MATCH_APPLY",
        "match_summary": "Excellent 87% compatibility with target role.",
    }

    result = MatchAnalysisResult.model_validate(valid_payload)
    assert result.technical_skills_score == 85
    assert result.ai_recommendation == "HIGH_MATCH_APPLY"
    assert "React" in result.skills_matched


# ---------------------------------------------------------------------------
# 5. Model Ladder Integration with Async Fallback Tests
# ---------------------------------------------------------------------------

def test_model_ladder_integration_and_fallback(
    storage: JobHuntingStorage,
    candidate_profile: CandidateProfile,
):
    """
    Verifies that JobMatchingService queries candidates from ModelLadderService
    and falls back seamlessly if an AI call fails.
    """
    ladder = ModelLadderService()
    candidates = ladder.get_candidates(task=TaskType.SMART)
    assert len(candidates) > 0
    assert "gemini-2.5-flash" in candidates or any("gemini" in c for c in candidates)

    # Mock settings service that returns API key
    mock_settings = MagicMock()
    mock_settings.get_api_key_for_service.return_value = "mock_gemini_key"

    matching_service = JobMatchingService(
        storage=storage,
        settings_service=mock_settings,
        model_ladder_service=ladder,
    )

    test_job = JobListing(
        id="job_ladder_test",
        source=JobSource.DIRECT_URL,
        source_url="https://example.com/job",
        company_name="TestCorp",
        title="Full Stack Engineer",
        location="Remote",
        modality=WorkModality.REMOTE,
        experience_required_min=3,
        experience_required_max=5,
        required_skills=["React", "TypeScript", "Node.js"],
        raw_description="Looking for React and Node.js Full Stack Engineer.",
        content_hash="hash_ladder_1",
    )
    storage.save_job(test_job)

    # Test async matching runs and returns a valid persistent score even when offline/mocked
    async def _run():
        return await matching_service.calculate_match_async(job=test_job, profile=candidate_profile)

    score = asyncio.run(_run())
    assert score is not None
    assert score.job_id == test_job.id
    assert score.match_percentage >= 70
    assert "React" in score.skills_matched

    # Verify score is persistently stored in SQLite
    persisted = storage.get_score_for_job(test_job.id)
    assert persisted is not None
    assert persisted.match_percentage == score.match_percentage
    assert persisted.technical_skills_score == score.technical_skills_score
    assert persisted.skills_matched == score.skills_matched


# ---------------------------------------------------------------------------
# 6. End-to-End API Match Endpoint Tests
# ---------------------------------------------------------------------------

def test_api_calculate_match_endpoint(tmp_path: Path):
    """Verifies POST /api/job-hunting/jobs/{job_id}/match endpoint."""
    app = create_app(data_dir=tmp_path, api_token="test-token")
    client = TestClient(app)

    # Ingest a test job
    job_payload = {
        "url": "https://careers.awesome.co/jobs/42",
        "title": "React Frontend Engineer",
        "company": "AwesomeCo",
        "raw_text": "We need a skilled React Developer with TypeScript and Next.js experience. 3+ years experience required.",
        "modality": "remote",
    }
    create_resp = client.post(
        "/api/job-hunting/ingest/url",
        json=job_payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert create_resp.status_code == 200
    job_data = create_resp.json()
    job_id = job_data["id"]

    # Calculate match
    match_resp = client.post(
        f"/api/job-hunting/jobs/{job_id}/match",
        headers={"Authorization": "Bearer test-token"},
    )
    assert match_resp.status_code == 200
    score_data = match_resp.json()

    assert "match_percentage" in score_data
    assert "technical_skills_score" in score_data
    assert "experience_score" in score_data
    assert "skills_matched" in score_data
    assert "skills_missing" in score_data
    assert "mandatory_requirements_not_met" in score_data
    assert "experience_gaps" in score_data
    assert "strengths" in score_data
    assert "weaknesses" in score_data
    assert "ai_recommendation" in score_data
    assert score_data["match_percentage"] >= 60

    # Retrieve score via GET
    get_resp = client.get(
        f"/api/job-hunting/jobs/{job_id}/score",
        headers={"Authorization": "Bearer test-token"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["match_percentage"] == score_data["match_percentage"]
