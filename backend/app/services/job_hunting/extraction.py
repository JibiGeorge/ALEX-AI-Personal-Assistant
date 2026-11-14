"""
Job Description Extraction Engine.
Extracts structured role attributes, required skills, experience bounds, and compensation
from raw job postings using ALEX's AI model ladder with deterministic heuristic fallbacks.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.schemas.job_hunting import (
    JobListing,
    JobSource,
    WorkModality,
)
from app.services.job_hunting.deduplication import compute_job_content_hash

logger = logging.getLogger(__name__)

# Common tech skills dictionary for regex/keyword fallback extraction
KNOWN_SKILLS = [
    "react", "next.js", "node.js", "typescript", "javascript", "python",
    "fastapi", "express", "vue", "angular", "redux", "graphql", "rest api",
    "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "git",
    "postgresql", "mysql", "mongodb", "redis", "sqlite", "tailwind",
    "html5", "css3", "sass", "webpack", "vite", "jest", "vitest",
    "playwright", "cypress", "microservices", "kafka", "electron"
]


class JobExtractionService:
    """Extracts structured job attributes from raw unstructured text."""

    def __init__(self, settings_service: Any = None) -> None:
        self.settings_service = settings_service

    async def extract_job_details(
        self,
        raw_text: str,
        source_url: str = "",
        source: JobSource = JobSource.MANUAL,
    ) -> JobListing:
        """
        Parses raw job description into a structured JobListing object.
        Tries AI Model Ladder first; falls back to deterministic parsing.
        """
        extracted = await self._extract_with_ai(raw_text)
        if not extracted:
            extracted = self._extract_with_heuristics(raw_text)

        title = extracted.get("title") or "Software Developer"
        company = extracted.get("company_name") or "Hiring Organization"
        location = extracted.get("location") or "Worldwide / Remote"
        modality_str = (extracted.get("modality") or "remote").lower()
        if "hybrid" in modality_str:
            modality = WorkModality.HYBRID
        elif "onsite" in modality_str or "on-site" in modality_str:
            modality = WorkModality.ONSITE
        else:
            modality = WorkModality.REMOTE

        content_hash = compute_job_content_hash(
            company_name=company,
            title=title,
            location=location,
        )

        return JobListing(
            id=str(uuid4()),
            source=source,
            source_url=source_url or "https://jobs.alex-ai.local",
            company_name=company,
            title=title,
            location=location,
            modality=modality,
            salary_min=extracted.get("salary_min"),
            salary_max=extracted.get("salary_max"),
            salary_currency=extracted.get("salary_currency") or "USD",
            experience_required_min=int(extracted.get("experience_required_min") or 2),
            experience_required_max=int(extracted.get("experience_required_max") or 5),
            raw_description=raw_text,
            cleaned_description=extracted.get("cleaned_description") or raw_text.strip(),
            required_skills=extracted.get("required_skills") or [],
            preferred_skills=extracted.get("preferred_skills") or [],
            benefits=extracted.get("benefits") or [],
            content_hash=content_hash,
        )

    async def _extract_with_ai(self, raw_text: str) -> Optional[Dict[str, Any]]:
        if not self.settings_service:
            return None

        api_key = self.settings_service.get_api_key_for_service()
        if not api_key:
            return None

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            prompt = (
                "You are an expert job description parser. Analyze the following job description "
                "and return a strictly valid JSON object with the following fields:\n"
                "- title (string)\n"
                "- company_name (string)\n"
                "- location (string)\n"
                "- modality (one of: 'remote', 'hybrid', 'onsite')\n"
                "- experience_required_min (integer)\n"
                "- experience_required_max (integer)\n"
                "- salary_min (float or null)\n"
                "- salary_max (float or null)\n"
                "- salary_currency (string, default 'USD')\n"
                "- required_skills (array of strings)\n"
                "- preferred_skills (array of strings)\n"
                "- cleaned_description (string summary)\n\n"
                f"<job_description>\n{raw_text[:4000]}\n</job_description>"
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            text = (response.text or "").strip()
            if text:
                return json.loads(text)
        except Exception as exc:
            logger.info("AI job extraction fallback to heuristics: %s", exc)
        return None

    def _extract_with_heuristics(self, raw_text: str) -> Dict[str, Any]:
        """Deterministic regex-based extraction for offline / fallback mode."""
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

        title = "Software Developer"
        company = "Hiring Organization"
        location = "Worldwide / Remote"
        modality = "remote"

        # Check for title/company patterns in the first few lines
        if len(lines) >= 1:
            title = lines[0]
        if len(lines) >= 2:
            company = lines[1]

        lower_text = raw_text.lower()

        # Modality detection
        if "hybrid" in lower_text:
            modality = "hybrid"
        elif "on-site" in lower_text or "onsite" in lower_text:
            modality = "onsite"
        elif "remote" in lower_text:
            modality = "remote"

        # Experience years detection (e.g. "2-5 years", "3+ years", "minimum 3 years")
        exp_min = 2
        exp_max = 5
        exp_match = re.search(r"(\d+)\s*[-to]+\s*(\d+)\s*(?:\+)?\s*years?", lower_text)
        if exp_match:
            exp_min = int(exp_match.group(1))
            exp_max = int(exp_match.group(2))
        else:
            single_exp = re.search(r"(\d+)\+?\s*years?(?:\s+of)?\s+experience", lower_text)
            if single_exp:
                exp_min = int(single_exp.group(1))
                exp_max = exp_min + 3

        # Salary detection (e.g. "$120,000 - $160,000", "$100k - $140k")
        salary_min: Optional[float] = None
        salary_max: Optional[float] = None
        sal_match = re.search(
            r"\$([0-9]{2,3}(?:,[0-9]{3})*|[0-9]{2,3}k?)\s*[-–to]+\s*\$([0-9]{2,3}(?:,[0-9]{3})*|[0-9]{2,3}k?)",
            lower_text,
        )
        if sal_match:
            def parse_num(val: str) -> float:
                val = val.replace(",", "")
                if val.endswith("k"):
                    return float(val[:-1]) * 1000
                return float(val)

            try:
                salary_min = parse_num(sal_match.group(1))
                salary_max = parse_num(sal_match.group(2))
            except ValueError:
                pass

        # Skill matching
        detected_skills: List[str] = []
        for skill in KNOWN_SKILLS:
            # Word boundary search
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, lower_text):
                # Normalize skill name capitalization
                detected_skills.append(skill.title() if len(skill) > 3 else skill.upper())

        return {
            "title": title[:100],
            "company_name": company[:100],
            "location": location[:100],
            "modality": modality,
            "experience_required_min": exp_min,
            "experience_required_max": exp_max,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": "USD",
            "required_skills": detected_skills[:8],
            "preferred_skills": detected_skills[8:14],
            "benefits": [],
            "cleaned_description": raw_text[:2000],
        }
