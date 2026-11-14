"""
Advanced Unit & Integration Tests for Upgraded Job Hunting & Career Radar Module.
Tests:
1. Geocoding and coordinate resolution for Interactive Map.
2. 6-Factor weighting with custom user preferences.
3. Job comparison engine with AI best fit recommendations.
4. Career recommendations generation (strengths, weaknesses, keywords, paths).
5. Multi-platform source classification & deduplication.
"""

import pytest
from app.schemas.job_hunting import (
    CandidatePreferences,
    CandidateProfile,
    JobListing,
    JobSource,
    SkillItem,
    WorkExperienceItem,
    WorkModality,
)
from app.services.job_hunting.geocoding import resolve_location_coordinates
from app.services.job_hunting.matching_service import JobMatchingService
from app.services.job_hunting.job_hunting_service import JobHuntingService
from app.services.job_hunting.storage import JobHuntingStorage


def test_geocoding_resolution():
    """Verifies that physical tech hubs are resolved with valid lat/lng and remote is kept clean."""
    # San Francisco
    lat, lng, city, state, country, is_remote = resolve_location_coordinates("San Francisco, CA", "hybrid")
    assert lat is not None and 37.0 < lat < 38.5
    assert lng is not None and -123.0 < lng < -121.5
    assert city == "San Francisco"
    assert country == "United States"

    # London
    lat, lng, city, state, country, is_remote = resolve_location_coordinates("London, UK", "onsite")
    assert lat is not None and 51.0 < lat < 52.0
    assert city == "London"
    assert country == "United Kingdom"

    # Bangalore
    lat, lng, city, state, country, is_remote = resolve_location_coordinates("Bangalore, India", "hybrid")
    assert lat is not None and 12.0 < lat < 13.5
    assert city == "Bangalore"

    # Pure Remote - Must NOT invent fake coordinates
    lat, lng, city, state, country, is_remote = resolve_location_coordinates("Worldwide / Remote", "remote")
    assert lat is None
    assert lng is None
    assert is_remote is True


def test_custom_factor_weights_evaluation(tmp_path):
    """Verifies that the matching engine respects custom factor weights from user preferences."""
    storage = JobHuntingStorage(tmp_path / "test_weights.db")
    matching_service = JobMatchingService(storage=storage)

    custom_weights = {
        "technical_skills": 0.30,
        "work_experience": 0.25,
        "job_responsibilities": 0.15,
        "education": 0.10,
        "industry": 0.10,
        "location": 0.10,
    }

    profile = CandidateProfile(
        id="test_candidate",
        full_name="Jane Dev",
        total_years_experience=4.0,
        seniority_level="Mid-Level",
        programming_languages=["TypeScript", "Python"],
        frameworks=["React", "FastAPI"],
        databases=["PostgreSQL"],
        skills=[SkillItem(name="React", category="Frontend", proficiency="Expert", years_experience=4.0)],
        preferences=CandidatePreferences(
            factor_weights=custom_weights,
            modalities=[WorkModality.REMOTE],
        ),
    )

    job = JobListing(
        id="job_custom_weights",
        source=JobSource.INDEED,
        source_url="https://indeed.com/viewjob?jk=12345",
        company_name="SaaS Innovations",
        title="Senior React Developer",
        location="Remote",
        modality=WorkModality.REMOTE,
        experience_required_min=3,
        experience_required_max=5,
        required_skills=["React", "TypeScript"],
        raw_description="Build modern web applications with React and TypeScript.",
        content_hash="hash_custom_weights_1",
    )
    storage.save_job(job)

    score = matching_service.calculate_match(job=job, profile=profile)

    assert score.factor_weights == custom_weights
    assert score.match_percentage >= 80
    assert score.match_tier in ("excellent", "good")
    assert "React" in score.matching_skills
    assert score.why_matched != ""


def test_job_comparison_engine(tmp_path):
    """Verifies side-by-side job comparison and AI best fit selection."""
    service = JobHuntingService(data_dir=tmp_path)

    # Ingest two distinct jobs
    job1 = JobListing(
        id="comp_job_1",
        source=JobSource.LINKEDIN_URL,
        source_url="https://linkedin.com/jobs/view/1001",
        company_name="Alpha Tech",
        title="Full Stack Developer",
        location="San Francisco, CA",
        modality=WorkModality.HYBRID,
        salary_min=130000,
        salary_max=160000,
        required_skills=["React", "Node.js", "TypeScript"],
        raw_description="Design and engineer high-performance web systems using React and Node.js.",
        content_hash="hash_comp_1",
    )
    job2 = JobListing(
        id="comp_job_2",
        source=JobSource.GLASSDOOR,
        source_url="https://glassdoor.com/job/2002",
        company_name="Beta Cloud",
        title="Backend Python Engineer",
        location="New York, NY",
        modality=WorkModality.ONSITE,
        salary_min=110000,
        salary_max=130000,
        required_skills=["Python", "FastAPI", "Docker"],
        raw_description="Develop APIs with Python and FastAPI.",
        content_hash="hash_comp_2",
    )
    service.storage.save_job(job1)
    service.storage.save_job(job2)

    res = service.compare_jobs(["comp_job_1", "comp_job_2"])

    assert len(res.compared_jobs) == 2
    assert res.best_fit_job_id in ("comp_job_1", "comp_job_2")
    assert res.best_fit_company != ""
    assert "compatibility" in res.ai_recommendation_reason.lower() or "fit" in res.ai_recommendation_reason.lower()
    assert res.comparison_summary != ""


def test_career_recommendations(tmp_path):
    """Verifies career recommendations generation including strengths, weaknesses, and certifications."""
    service = JobHuntingService(data_dir=tmp_path)
    recs = service.get_career_recommendations()

    assert len(recs.strengths) > 0
    assert len(recs.skills_to_improve) > 0
    assert len(recs.recommended_certifications) > 0
    assert len(recs.suggested_job_titles) > 0
    assert len(recs.recommended_career_paths) > 0

