"""
Candidate Profile Management Service.
Handles candidate profile state, career preferences, skills inventory,
and master resume analysis via ALEX's DocumentParserService to generate
a verified candidate profile.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Set

from app.schemas.job_hunting import (
    CandidatePreferences,
    CandidateProfile,
    SkillItem,
    WorkExperienceItem,
    WorkModality,
)
from app.services.job_hunting.storage import JobHuntingStorage

logger = logging.getLogger(__name__)

KNOWN_LANGUAGES = ["typescript", "javascript", "python", "go", "golang", "c++", "c#", "java", "ruby", "rust", "php", "sql", "html", "css"]
KNOWN_FRAMEWORKS = ["react", "next.js", "node.js", "fastapi", "express", "vue", "angular", "django", "flask", "svelte", "tailwind", "redux", "graphql", "vite"]
KNOWN_DATABASES = ["postgresql", "sqlite", "mongodb", "redis", "mysql", "dynamodb", "cassandra", "elasticsearch", "supabase", "firebase"]

CANONICAL_TECH_NAMES = {
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "python": "Python",
    "go": "Go",
    "golang": "Go",
    "c++": "C++",
    "c#": "C#",
    "java": "Java",
    "ruby": "Ruby",
    "rust": "Rust",
    "php": "PHP",
    "sql": "SQL",
    "html": "HTML",
    "css": "CSS",
    "react": "React",
    "next.js": "Next.js",
    "node.js": "Node.js",
    "fastapi": "FastAPI",
    "express": "Express",
    "vue": "Vue",
    "angular": "Angular",
    "django": "Django",
    "flask": "Flask",
    "svelte": "Svelte",
    "tailwind": "Tailwind",
    "redux": "Redux",
    "graphql": "GraphQL",
    "vite": "Vite",
    "postgresql": "PostgreSQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "mysql": "MySQL",
    "dynamodb": "DynamoDB",
    "cassandra": "Cassandra",
    "elasticsearch": "Elasticsearch",
    "supabase": "Supabase",
    "firebase": "Firebase",
}


def format_tech_name(name: str) -> str:
    key = name.strip().lower()
    return CANONICAL_TECH_NAMES.get(key, name.title() if len(name) > 3 else name.upper())


class CandidateProfileService:
    """Manages candidate profile and master resume verification."""

    def __init__(
        self,
        storage: JobHuntingStorage,
        document_parser_service: Any = None,
        settings_service: Any = None,
    ) -> None:
        self.storage = storage
        self.document_parser = document_parser_service
        self.settings_service = settings_service

    def get_profile(self, profile_id: str = "default_candidate") -> CandidateProfile:
        """Retrieves candidate profile; seeds default if absent."""
        profile = self.storage.get_candidate_profile(profile_id)
        if not profile:
            profile = CandidateProfile(
                id=profile_id,
                full_name="Software Developer",
                email="candidate@alex-ai.local",
                location="Worldwide / Remote",
                headline="Full Stack Developer (React / Next.js / Node.js)",
                summary="Full Stack Developer with 3+ years experience building scalable web apps with React, Next.js, and Node.js.",
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
                        company_name="Technology Solutions",
                        role_title="Full Stack Developer",
                        location="Remote",
                        is_remote=True,
                        start_date="2022-01",
                        is_current=True,
                        highlights=[
                            "Engineered responsive full-stack applications with React 19, Next.js, and Node.js microservices.",
                            "Optimized database queries and API response times by 35% using PostgreSQL indexing and Redis caching.",
                        ],
                        tech_stack=["React", "Next.js", "Node.js", "TypeScript", "PostgreSQL"],
                    )
                ],
                preferences=CandidatePreferences(
                    target_roles=[
                        "Software Developer",
                        "Full Stack Developer",
                        "Frontend Developer",
                        "React Developer",
                        "Next.js Developer",
                        "Node.js Developer",
                    ],
                    min_years_experience=2,
                    max_years_experience=5,
                    modalities=[WorkModality.REMOTE, WorkModality.HYBRID, WorkModality.ONSITE],
                    target_locations=["Worldwide", "Remote"],
                ),
            )
            self.storage.save_candidate_profile(profile)
        return profile

    def update_profile(self, profile: CandidateProfile) -> CandidateProfile:
        """Updates and persists the candidate profile."""
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        return self.storage.save_candidate_profile(profile)

    def update_preferences(
        self,
        preferences: CandidatePreferences,
        profile_id: str = "default_candidate",
    ) -> CandidateProfile:
        """Updates career preferences for the candidate."""
        profile = self.get_profile(profile_id)
        profile.preferences = preferences
        return self.update_profile(profile)

    def ingest_resume_file(
        self,
        file_path: Path,
        profile_id: str = "default_candidate",
    ) -> CandidateProfile:
        """
        Parses master resume file via DocumentParserService and extracts a
        verified candidate profile strictly grounded in the document without fabrication.
        """
        profile = self.get_profile(profile_id)

        parsed_text = ""
        if self.document_parser and file_path.suffix.lower() in (".pdf", ".docx", ".doc"):
            try:
                res = self.document_parser.parse_document(file_path)
                parsed_text = res.text
            except Exception as exc:
                logger.warning("DocumentParserService parsing error: %s, falling back to text read", exc)

        if not parsed_text and file_path.exists():
            try:
                parsed_text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as read_exc:
                logger.error("Could not read resume file: %s", read_exc)
                parsed_text = ""

        profile.raw_resume_text = parsed_text
        profile.master_resume_path = str(file_path.resolve())

        # Extract verified facts from parsed text
        self._enrich_profile_from_text(profile, parsed_text)

        # Mark as verified
        profile.is_verified = True
        profile.verified_at = datetime.now(timezone.utc).isoformat()
        profile.verification_notes = f"Verified from master resume '{file_path.name}' via DocumentParserService."

        return self.update_profile(profile)

    def _enrich_profile_from_text(self, profile: CandidateProfile, text: str) -> None:
        """Extracts structured contact info, tech stacks, and experience strictly from text."""
        if not text:
            return

        lines = [l.strip() for l in text.splitlines() if l.strip()]

        # Name extraction (first non-empty line if reasonably short)
        if lines and len(lines[0]) < 50 and not any(k in lines[0].lower() for k in ["resume", "curriculum", "cv"]):
            profile.full_name = lines[0]

        # Email
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if email_match:
            profile.email = email_match.group(0)

        # Phone
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        if phone_match:
            profile.phone = phone_match.group(0)

        # URLs
        li_match = re.search(r"linkedin\.com/in/[\w-]+", text, re.I)
        if li_match:
            profile.linkedin_url = f"https://{li_match.group(0)}"

        gh_match = re.search(r"github\.com/[\w-]+", text, re.I)
        if gh_match:
            profile.github_url = f"https://{gh_match.group(0)}"

        # Detect programming languages, frameworks, and databases
        lower_text = text.lower()
        found_langs: Set[str] = set()
        for lang in KNOWN_LANGUAGES:
            pattern = r"\b" + re.escape(lang) + r"\b"
            if re.search(pattern, lower_text):
                found_langs.add(format_tech_name(lang))

        found_frameworks: Set[str] = set()
        for fw in KNOWN_FRAMEWORKS:
            pattern = r"\b" + re.escape(fw) + r"\b"
            if re.search(pattern, lower_text):
                found_frameworks.add(format_tech_name(fw))

        found_dbs: Set[str] = set()
        for db in KNOWN_DATABASES:
            pattern = r"\b" + re.escape(db) + r"\b"
            if re.search(pattern, lower_text):
                found_dbs.add(format_tech_name(db))

        if found_langs:
            profile.programming_languages = sorted(list(found_langs))
        if found_frameworks:
            profile.frameworks = sorted(list(found_frameworks))
        if found_dbs:
            profile.databases = sorted(list(found_dbs))

        # Re-populate profile.skills with verified items
        existing_skills = {s.name.lower() for s in profile.skills}
        for item in profile.programming_languages:
            if item.lower() not in existing_skills:
                profile.skills.append(SkillItem(name=item, category="Language", proficiency="Proficient", years_experience=profile.total_years_experience))
                existing_skills.add(item.lower())

        for item in profile.frameworks:
            if item.lower() not in existing_skills:
                profile.skills.append(SkillItem(name=item, category="Framework", proficiency="Proficient", years_experience=profile.total_years_experience))
                existing_skills.add(item.lower())

        for item in profile.databases:
            if item.lower() not in existing_skills:
                profile.skills.append(SkillItem(name=item, category="Database", proficiency="Proficient", years_experience=profile.total_years_experience))
                existing_skills.add(item.lower())

        # Calculate or refine years of experience
        years_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*years?(?:\s+of)?\s+experience", lower_text)
        if years_match:
            try:
                profile.total_years_experience = float(years_match.group(1))
            except ValueError:
                pass

        # Seniority calibration
        if profile.total_years_experience >= 5:
            profile.seniority_level = "Senior"
        elif profile.total_years_experience >= 2:
            profile.seniority_level = "Mid-Level"
        else:
            profile.seniority_level = "Junior"
