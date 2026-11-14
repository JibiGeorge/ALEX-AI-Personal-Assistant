"""
ALEX Job Matching and Compatibility Scoring Engine.
Compares candidate profile against discovered job listings across 6 distinct dimensions:
- Technical Skills (30%)
- Years of Experience (20%)
- Job Responsibilities (20%)
- Technology Stack: Languages, Frameworks, Databases (15%)
- Location Compatibility (10%)
- Seniority Alignment (5%)

Reuses existing model ladder for semantic analysis with structured Pydantic validation.
Never fabricates candidate experience. Saves all results in persistent storage.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job_hunting import (
    CandidateProfile,
    CompatibilityScore,
    JobListing,
    WorkModality,
)
from app.services.job_hunting.storage import JobHuntingStorage

logger = logging.getLogger(__name__)


class MatchAnalysisResult(BaseModel):
    """Pydantic model for structured AI Model Ladder output validation."""
    model_config = ConfigDict(extra="ignore")

    technical_skills_score: int = Field(default=0, ge=0, le=100)
    work_experience_score: int = Field(default=0, ge=0, le=100)
    experience_score: int = Field(default=0, ge=0, le=100)
    responsibilities_score: int = Field(default=0, ge=0, le=100)
    education_score: int = Field(default=85, ge=0, le=100)
    industry_score: int = Field(default=80, ge=0, le=100)
    tech_stack_score: int = Field(default=0, ge=0, le=100)
    location_score: int = Field(default=0, ge=0, le=100)
    seniority_score: int = Field(default=0, ge=0, le=100)

    skills_matched: List[str] = Field(default_factory=list)
    skills_missing: List[str] = Field(default_factory=list)
    mandatory_requirements_not_met: List[str] = Field(default_factory=list)
    experience_gaps: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    why_matched: str = ""
    why_not_matched: str = ""
    ai_recommendation: str = "CONSIDER_TAILORING"
    match_summary: str = ""


class JobMatchingService:
    """Multi-factor job compatibility matching engine with model ladder integration."""

    def __init__(
        self,
        storage: JobHuntingStorage,
        settings_service: Any = None,
        model_ladder_service: Any = None,
    ) -> None:
        self.storage = storage
        self.settings_service = settings_service
        if model_ladder_service is None:
            try:
                from app.services.model_ladder_service import model_ladder_service as default_ladder
                model_ladder_service = default_ladder
            except ImportError:
                model_ladder_service = None
        self.model_ladder_service = model_ladder_service

    async def calculate_match_async(
        self,
        job: JobListing,
        profile: CandidateProfile,
    ) -> CompatibilityScore:
        """Asynchronously calculates match using Model Ladder if available, with deterministic fallback."""
        ai_result = await self._evaluate_with_ai(job, profile)
        if ai_result:
            return self._build_and_persist_score(job, profile, ai_result)

        heuristic_result = self._evaluate_with_heuristics(job, profile)
        return self._build_and_persist_score(job, profile, heuristic_result)

    def calculate_match(
        self,
        job: JobListing,
        profile: CandidateProfile,
    ) -> CompatibilityScore:
        """Synchronous entrypoint; runs deterministic multi-factor match."""
        result = self._evaluate_with_heuristics(job, profile)
        return self._build_and_persist_score(job, profile, result)

    def _build_and_persist_score(
        self,
        job: JobListing,
        profile: CandidateProfile,
        analysis: MatchAnalysisResult,
    ) -> CompatibilityScore:
        # Check if user customized the factor weights
        user_weights = getattr(profile.preferences, "factor_weights", None)
        work_exp_score = analysis.work_experience_score or analysis.experience_score

        if user_weights:
            weights = user_weights
            w_tech = weights.get("technical_skills", 0.30)
            w_exp = weights.get("work_experience", weights.get("experience", 0.25))
            w_resp = weights.get("job_responsibilities", weights.get("responsibilities", 0.15))
            w_edu = weights.get("education", 0.10)
            w_ind = weights.get("industry", 0.10)
            w_loc = weights.get("location", 0.10)
            weighted_score = (
                (w_tech * analysis.technical_skills_score)
                + (w_exp * work_exp_score)
                + (w_resp * analysis.responsibilities_score)
                + (w_edu * analysis.education_score)
                + (w_ind * analysis.industry_score)
                + (w_loc * analysis.location_score)
            )
        else:
            # Standard multi-factor evaluation weights
            weights = {
                "technical_skills": 0.30,
                "experience": 0.20,
                "responsibilities": 0.20,
                "tech_stack": 0.15,
                "location": 0.10,
                "seniority": 0.05,
            }
            weighted_score = (
                (0.30 * analysis.technical_skills_score)
                + (0.20 * analysis.experience_score)
                + (0.20 * analysis.responsibilities_score)
                + (0.15 * analysis.tech_stack_score)
                + (0.10 * analysis.location_score)
                + (0.05 * analysis.seniority_score)
            )

        match_percentage = int(round(max(0, min(100, weighted_score))))

        # Guardrail: Do not classify a job as a strong match based only on its title.
        # If technical skills or experience is deficient (<50), cap at 70%
        if analysis.technical_skills_score < 50 or work_exp_score < 50:
            match_percentage = min(match_percentage, 70)

        # Match Tier categorization
        if match_percentage >= 85:
            match_tier = "excellent"
        elif match_percentage >= 70:
            match_tier = "good"
        elif match_percentage >= 50:
            match_tier = "potential"
        else:
            match_tier = "low"

        # Construct clear why matched / why not matched explanations
        why_matched_parts: List[str] = []
        if analysis.skills_matched:
            why_matched_parts.append(f"Strong overlap in core skills: {', '.join(analysis.skills_matched[:4])}")
        if work_exp_score >= 80:
            why_matched_parts.append(f"{profile.total_years_experience} years experience aligns with role expectations")
        if analysis.location_score >= 90:
            why_matched_parts.append(f"Ideal {job.modality.value.capitalize()} work arrangement fit")
        why_matched = analysis.why_matched or ("; ".join(why_matched_parts) if why_matched_parts else "Meets baseline criteria.")

        why_not_parts: List[str] = []
        if analysis.skills_missing:
            why_not_parts.append(f"Missing verification for: {', '.join(analysis.skills_missing[:3])}")
        if work_exp_score < 75:
            why_not_parts.append(f"Experience gap ({profile.total_years_experience} yrs vs requested {job.experience_required_min}-{job.experience_required_max} yrs)")
        if analysis.location_score < 80:
            why_not_parts.append(f"Location or work arrangement divergence ({job.location})")
        why_not_matched = analysis.why_not_matched or ("; ".join(why_not_parts) if why_not_parts else "No critical blockers.")

        summary = analysis.match_summary or f"{match_percentage}% compatibility ({match_tier.upper()}) across technical skills, experience, and role responsibilities."
        gap_summary = "; ".join(analysis.experience_gaps) if analysis.experience_gaps else "No critical experience gaps."

        score = CompatibilityScore(
            id=str(uuid4()),
            job_id=job.id,
            candidate_id=profile.id,
            match_percentage=match_percentage,
            overall_score=match_percentage,
            match_tier=match_tier,
            technical_skills_score=analysis.technical_skills_score,
            work_experience_score=work_exp_score,
            experience_score=work_exp_score,
            responsibilities_score=analysis.responsibilities_score,
            education_score=analysis.education_score,
            industry_score=analysis.industry_score,
            tech_stack_score=analysis.tech_stack_score,
            location_score=analysis.location_score,
            seniority_score=analysis.seniority_score,
            skills_score=analysis.technical_skills_score,
            location_modality_score=analysis.location_score,
            factor_weights=weights,
            skills_matched=analysis.skills_matched,
            skills_missing=analysis.skills_missing,
            matching_skills=analysis.skills_matched,
            missing_skills=analysis.skills_missing,
            mandatory_requirements_not_met=analysis.mandatory_requirements_not_met,
            experience_gaps=analysis.experience_gaps,
            experience_gap_analysis=gap_summary,
            strengths=analysis.strengths,
            weaknesses=analysis.weaknesses,
            why_matched=why_matched,
            why_not_matched=why_not_matched,
            ai_recommendation=analysis.ai_recommendation,
            recommended_action=analysis.ai_recommendation,
            match_summary=summary,
        )

        return self.storage.save_score(score)

    async def _evaluate_with_ai(
        self,
        job: JobListing,
        profile: CandidateProfile,
    ) -> Optional[MatchAnalysisResult]:
        """Queries existing Model Ladder (Gemini) for deep semantic comparison."""
        if not self.settings_service:
            return None

        api_key = self.settings_service.get_api_key_for_service()
        if not api_key:
            return None

        candidates: List[str] = []
        if self.model_ladder_service:
            try:
                from app.services.model_ladder_service import TaskType
                candidates = self.model_ladder_service.get_candidates(task=TaskType.SMART)
            except Exception as e:
                logger.debug("Failed querying candidates from model ladder: %s", e)

        if not candidates:
            candidates = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

        candidate_summary = (
            f"Candidate: {profile.full_name}\n"
            f"Headline: {profile.headline}\n"
            f"Total Experience: {profile.total_years_experience} years\n"
            f"Seniority: {profile.seniority_level}\n"
            f"Programming Languages: {', '.join(profile.programming_languages)}\n"
            f"Frameworks: {', '.join(profile.frameworks)}\n"
            f"Databases: {', '.join(profile.databases)}\n"
            f"Skills: {', '.join(s.name for s in profile.skills)}\n"
            f"Work Experience & Projects:\n"
            + "\n".join(
                f"- {e.role_title} at {e.company_name} ({e.start_date} to {e.end_date or 'Present'}): "
                + "; ".join(e.highlights)
                + (f" [Tech: {', '.join(e.tech_stack)}]" if e.tech_stack else "")
                for e in profile.work_history
            )
            + f"\nWork Modalities: {', '.join(m.value for m in profile.preferences.modalities)}\n"
            f"Target Locations: {', '.join(profile.preferences.target_locations)}"
        )

        job_summary = (
            f"Job Title: {job.title}\n"
            f"Company: {job.company_name}\n"
            f"Location & Modality: {job.location} ({job.modality.value})\n"
            f"Required Experience: {job.experience_required_min}-{job.experience_required_max} years\n"
            f"Required Skills: {', '.join(job.required_skills)}\n"
            f"Preferred Skills: {', '.join(job.preferred_skills)}\n"
            f"Job Description:\n{job.cleaned_description or job.raw_description[:2500]}"
        )

        prompt = (
            "You are the ALEX Career Matching Engine. Perform an objective, rigorous comparison "
            "between the candidate's verified profile and the target job description across 10 dimensions:\n"
            "1. Technical skills\n"
            "2. Years of experience\n"
            "3. Programming languages\n"
            "4. Frameworks\n"
            "5. Databases\n"
            "6. Project experience\n"
            "7. Job responsibilities\n"
            "8. Required qualifications\n"
            "9. Location compatibility\n"
            "10. Seniority\n\n"
            "Scoring weights to evaluate:\n"
            "- technical_skills_score: 30% weight\n"
            "- experience_score: 20% weight\n"
            "- responsibilities_score: 20% weight\n"
            "- tech_stack_score: 15% weight (languages, frameworks, databases)\n"
            "- location_score: 10% weight\n"
            "- seniority_score: 5% weight\n\n"
            "CRITICAL GUARDRAIL:\n"
            "- NEVER fabricate candidate experience or assume qualifications not present in the candidate profile.\n"
            "- Strictly score based on candidate ground truth.\n\n"
            "Evaluate and return a JSON object with integer scores (0-100) and analysis lists:\n"
            "{\n"
            '  "technical_skills_score": int (0-100),\n'
            '  "experience_score": int (0-100),\n'
            '  "responsibilities_score": int (0-100),\n'
            '  "tech_stack_score": int (0-100),\n'
            '  "location_score": int (0-100),\n'
            '  "seniority_score": int (0-100),\n'
            '  "skills_matched": [string],\n'
            '  "skills_missing": [string],\n'
            '  "mandatory_requirements_not_met": [string],\n'
            '  "experience_gaps": [string],\n'
            '  "strengths": [string],\n'
            '  "weaknesses": [string],\n'
            '  "ai_recommendation": string ("HIGH_MATCH_APPLY" | "CONSIDER_TAILORING" | "LOW_MATCH_SKIP"),\n'
            '  "match_summary": string\n'
            "}\n\n"
            f"<candidate_profile>\n{candidate_summary}\n</candidate_profile>\n\n"
            f"<job_description>\n{job_summary}\n</job_description>"
        )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            for model_id in candidates:
                model_name = model_id.split("/")[-1] if "/" in model_id else model_id
                if ":" in model_name:
                    continue

                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1,
                        ),
                    )
                    raw_text = (response.text or "").strip()
                    if raw_text:
                        parsed = json.loads(raw_text)
                        validated = MatchAnalysisResult.model_validate(parsed)
                        if self.model_ladder_service:
                            self.model_ladder_service.record_success(model_id)
                        return validated
                except Exception as model_exc:
                    logger.warning("Model ladder rung %s failed for matching: %s", model_id, model_exc)
                    if self.model_ladder_service:
                        code = getattr(model_exc, "code", 500)
                        self.model_ladder_service.record_failure(model_id, code)
                    continue
        except Exception as exc:
            logger.info("AI matching fallback to deterministic engine: %s", exc)

        return None

    def _evaluate_with_heuristics(
        self,
        job: JobListing,
        profile: CandidateProfile,
    ) -> MatchAnalysisResult:
        """
        Deterministic, robust multi-factor comparison engine.
        Compares across 10 distinct dimensions:
        1. Technical skills (30%)
        2. Years of experience (20%)
        3. Programming languages (part of 15% tech stack)
        4. Frameworks (part of 15% tech stack)
        5. Databases (part of 15% tech stack)
        6. Project experience (part of 20% responsibilities)
        7. Job responsibilities (part of 20% responsibilities)
        8. Required qualifications (part of 30% technical skills)
        9. Location compatibility (10%)
        10. Seniority (5%)
        """
        # Collect candidate technical assets strictly without fabrication
        cand_skills = {s.name.strip().lower() for s in profile.skills}
        cand_langs = {l.strip().lower() for l in profile.programming_languages}
        cand_fws = {f.strip().lower() for f in profile.frameworks}
        cand_dbs = {d.strip().lower() for d in profile.databases}
        all_tech = cand_skills | cand_langs | cand_fws | cand_dbs

        for exp in profile.work_history:
            for t in exp.tech_stack:
                all_tech.add(t.strip().lower())

        job_desc_lower = f"{job.title} {job.raw_description} {job.cleaned_description or ''}".lower()

        # 1. Technical Skills & Required Qualifications (30%)
        required = [s.strip().lower() for s in job.required_skills if s.strip()]
        matched: List[str] = []
        missing: List[str] = []
        mandatory_unmet: List[str] = []

        if required:
            for req in required:
                # Strictly check if candidate has this skill
                if any(req in t or t in req for t in all_tech):
                    matched.append(req.title())
                else:
                    missing.append(req.title())
                    mandatory_unmet.append(f"Requires hands-on proficiency in {req.title()}")
            tech_skills_score = int((len(matched) / len(required)) * 100)
        else:
            found = 0
            for t in all_tech:
                if t in job_desc_lower:
                    found += 1
                    matched.append(t.title())
            tech_skills_score = min(100, int((found / max(3, len(all_tech))) * 100))

        # Check preferred skills
        for pref in job.preferred_skills:
            pref_clean = pref.strip().lower()
            if pref_clean and any(pref_clean in t or t in pref_clean for t in all_tech):
                if pref.title() not in matched:
                    matched.append(pref.title())

        # 2. Years of Experience (20%)
        cand_exp = profile.total_years_experience
        req_min = job.experience_required_min
        req_max = job.experience_required_max
        experience_gaps: List[str] = []

        if cand_exp >= req_min:
            if cand_exp <= req_max + 1:
                exp_score = 100
            else:
                exp_score = 90
        else:
            shortfall = req_min - cand_exp
            exp_score = max(30, int(100 - (shortfall * 25)))
            experience_gaps.append(f"Candidate has {cand_exp} years; role requests minimum {req_min} years.")

        # 3. Responsibilities Overlap & Project Experience (20%)
        # Compare job description action verbs and responsibilities against work experience highlights
        cand_highlights = (
            f"{profile.headline} {profile.summary} "
            + " ".join(
                f"{h.role_title} {' '.join(h.highlights)} {' '.join(h.tech_stack)}"
                for h in profile.work_history
            )
        ).lower()

        overlap_signals = [
            "build", "architect", "engineer", "deploy", "design", "scale",
            "optimize", "api", "database", "ui", "frontend", "backend", "full stack",
            "microservice", "testing", "integrate", "maintain", "ci/cd", "responsive"
        ]
        target_signals = [s for s in overlap_signals if s in job_desc_lower]
        if target_signals:
            shared_signals = [s for s in target_signals if s in cand_highlights]
            resp_score = min(100, int((len(shared_signals) / max(2, len(target_signals))) * 100))
        else:
            resp_score = 75

        # 4. Technology Stack: Languages, Frameworks, Databases (15%)
        # Check programming languages, frameworks, and databases mentioned in job
        job_stack_items = set()
        for item in [
            "typescript", "javascript", "python", "go", "java", "c#", "rust",
            "react", "next.js", "node.js", "fastapi", "express", "vue", "angular",
            "postgresql", "sqlite", "mongodb", "redis", "mysql", "docker"
        ]:
            if item in job_desc_lower:
                job_stack_items.add(item)

        if job_stack_items:
            stack_matched = [s for s in job_stack_items if any(s in t or t in s for t in all_tech)]
            stack_missing = [s for s in job_stack_items if not any(s in t or t in s for t in all_tech)]
            tech_stack_score = int((len(stack_matched) / len(job_stack_items)) * 100)
            for m in stack_missing:
                if m.title() not in missing:
                    missing.append(m.title())
        else:
            tech_stack_score = 80

        # 5. Location Compatibility (10%)
        user_modalities = profile.preferences.modalities
        if job.modality in user_modalities or WorkModality.REMOTE in user_modalities:
            location_score = 100
        else:
            location_score = 50

        # Check target locations
        if profile.preferences.target_locations:
            job_loc_lower = job.location.lower()
            if any(loc.lower() in job_loc_lower or "remote" in job_loc_lower or "worldwide" in loc.lower() for loc in profile.preferences.target_locations):
                location_score = min(100, location_score + 10)

        # 6. Seniority Alignment (5%)
        title_lower = job.title.lower()
        if "senior" in title_lower or "lead" in title_lower or "principal" in title_lower:
            job_sen = "Senior"
        elif "junior" in title_lower or "entry" in title_lower or "intern" in title_lower:
            job_sen = "Junior"
        else:
            job_sen = "Mid-Level"

        if profile.seniority_level == job_sen:
            seniority_score = 100
        elif (profile.seniority_level == "Mid-Level" and job_sen in ("Junior", "Mid-Level")) or (profile.seniority_level == "Senior"):
            seniority_score = 90
        else:
            seniority_score = 60
            experience_gaps.append(f"Seniority alignment: Profile is '{profile.seniority_level}', role indicates '{job_sen}'.")

        # 7. Education & Qualifications (10%)
        edu_score = 90
        has_degree = bool(profile.education) or any(
            deg in f"{profile.headline} {profile.summary}".lower()
            for deg in ["bachelor", "master", "bs", "ms", "computer science", "b.tech", "degree"]
        )
        if "degree" in job_desc_lower or "bachelor" in job_desc_lower:
            edu_score = 100 if has_degree else 75
        else:
            edu_score = 95

        # 8. Industry Domain Alignment (10%)
        ind_score = 85
        if profile.industry_experience:
            for ind in profile.industry_experience:
                if ind.lower() in job_desc_lower or ind.lower() in job.company_name.lower():
                    ind_score = 100
                    break

        # Strengths & Weaknesses
        strengths: List[str] = []
        weaknesses: List[str] = []

        if matched:
            strengths.append(f"Strong alignment on primary technologies: {', '.join(matched[:3])}")
        if exp_score >= 90:
            strengths.append(f"Ideal {cand_exp} years experience within requested {req_min}-{req_max} year window.")
        if location_score >= 90:
            strengths.append(f"Full {job.modality.value.capitalize()} work arrangement compatibility.")
        if resp_score >= 80:
            strengths.append("High overlap in core software engineering responsibilities and projects.")

        if missing:
            weaknesses.append(f"Missing direct evidence for: {', '.join(missing[:3])}")
        if exp_score < 80:
            weaknesses.append(f"Years of experience below target minimum ({cand_exp} vs {req_min} yrs).")
        if location_score < 80:
            weaknesses.append(f"Work arrangement ({job.modality.value}) may not perfectly match preferred options.")

        # Overall Recommendation according to strict weights:
        # Technical (30%), Experience (25%), Responsibilities (15%), Education (10%), Industry (10%), Location (10%)
        weighted_total = (
            (0.30 * tech_skills_score)
            + (0.25 * exp_score)
            + (0.15 * resp_score)
            + (0.10 * edu_score)
            + (0.10 * ind_score)
            + (0.10 * location_score)
        )

        why_matched_text = "; ".join(strengths) if strengths else "Baseline qualifications satisfied."
        why_not_text = "; ".join(weaknesses) if weaknesses else "No significant gaps identified."

        if weighted_total >= 80:
            ai_rec = "HIGH_MATCH_APPLY"
            summary = f"Strong {int(weighted_total)}% match. High technical overlap with verified candidate skills."
        elif weighted_total >= 60:
            ai_rec = "CONSIDER_TAILORING"
            summary = f"Moderate {int(weighted_total)}% match. Tailoring resume to highlight {', '.join(missing[:2]) or 'requirements'} recommended."
        else:
            ai_rec = "LOW_MATCH_SKIP"
            summary = f"Low {int(weighted_total)}% match. Notable technical or experience gap."

        return MatchAnalysisResult(
            technical_skills_score=tech_skills_score,
            work_experience_score=exp_score,
            experience_score=exp_score,
            responsibilities_score=resp_score,
            education_score=edu_score,
            industry_score=ind_score,
            tech_stack_score=tech_stack_score,
            location_score=location_score,
            seniority_score=seniority_score,
            skills_matched=matched,
            skills_missing=missing,
            mandatory_requirements_not_met=mandatory_unmet,
            experience_gaps=experience_gaps,
            strengths=strengths,
            weaknesses=weaknesses,
            why_matched=why_matched_text,
            why_not_matched=why_not_text,
            ai_recommendation=ai_rec,
            match_summary=summary,
        )
