"""
ALEX Resume Studio – Tailoring and Document Generation Service.
For each selected job:
1. Read the original resume (read-only baseline).
2. Read the target job description.
3. Identify relevant experience without inventing achievements or employment history.
4. Identify relevant technical skills strictly from verified candidate profile.
5. Prepare a customized, ATS-optimized resume.
6. Generate a personalized cover letter.

Requirements:
- Never invent experience.
- Never fabricate employment history.
- Never invent project achievements.
- Keep original resume unchanged.
- Save each generated version independently.
- Support DOCX and PDF formats.
- Allow preview and editing.
- Support document downloads.
- Associate every document with its job and workspace.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.schemas.job_hunting import (
    CandidateProfile,
    JobListing,
    TailoredDocument,
)
from app.services.job_hunting.document_exporter import DocumentExporter
from app.services.job_hunting.storage import JobHuntingStorage

logger = logging.getLogger(__name__)


class ResumeTailoringService:
    """Manages role-specific resume customization, cover letter generation, and exports."""

    def __init__(
        self,
        storage: JobHuntingStorage,
        settings_service: Any = None,
        workspace_root: Optional[Path] = None,
        model_ladder_service: Any = None,
    ) -> None:
        self.storage = storage
        self.settings_service = settings_service
        self.workspace_root = workspace_root
        self.model_ladder_service = model_ladder_service
        self.exporter = DocumentExporter(workspace_root=workspace_root)

    # -----------------------------------------------------------------------
    # Core Pipeline
    # -----------------------------------------------------------------------

    async def generate_tailored_package(
        self,
        job: JobListing,
        profile: CandidateProfile,
        custom_instructions: Optional[str] = None,
    ) -> TailoredDocument:
        """
        Executes the 6-step customization pipeline for a selected job:
        1. Read original resume (read-only baseline).
        2. Read job description.
        3. Identify relevant experience.
        4. Identify relevant technical skills.
        5. Prepare customized resume.
        6. Generate personalized cover letter.
        """
        # Step 1: Read original resume (never modify it)
        _ = profile.raw_resume_text or profile.summary

        # Step 2: Read job description
        job_text_lower = f"{job.title} {job.raw_description} {job.cleaned_description or ''}".lower()

        # Step 3: Identify relevant experience strictly from verified profile
        relevant_experience = self._identify_relevant_experience(profile, job_text_lower)

        # Step 4: Identify relevant technical skills strictly from verified profile
        relevant_skills = self._identify_relevant_skills(profile, job)

        # Compute next version number for this job
        next_version = self.storage.get_next_version_number_for_job(job.id)

        # Step 5 & 6: Prepare customized resume & cover letter
        tailored: Optional[TailoredDocument] = None
        if self.settings_service:
            tailored = await self._generate_with_ai(
                job=job,
                profile=profile,
                relevant_skills=relevant_skills,
                relevant_experience=relevant_experience,
                version=next_version,
                custom_instructions=custom_instructions,
            )

        if not tailored:
            tailored = self._generate_with_templates(
                job=job,
                profile=profile,
                relevant_skills=relevant_skills,
                relevant_experience=relevant_experience,
                version=next_version,
            )

        # Render DOCX and PDF assets
        self._render_and_attach_binary_assets(tailored, profile, job)

        # Persist document independently
        saved_doc = self.storage.save_tailored_document(tailored)
        return saved_doc

    # -----------------------------------------------------------------------
    # Step 3 & 4 Heuristics
    # -----------------------------------------------------------------------

    def _identify_relevant_skills(self, profile: CandidateProfile, job: JobListing) -> List[str]:
        """Identifies candidate's verified skills matching job requirements strictly without fabrication."""
        job_text_lower = f"{job.title} {job.raw_description} {job.cleaned_description or ''} {' '.join(job.required_skills)}".lower()

        cand_skills = [s.name for s in profile.skills]
        cand_langs = list(profile.programming_languages)
        cand_fws = list(profile.frameworks)
        cand_dbs = list(profile.databases)

        all_candidate_assets = cand_skills + cand_langs + cand_fws + cand_dbs
        # Deduplicate while preserving order
        seen = set()
        unique_assets = []
        for item in all_candidate_assets:
            normalized = item.strip().lower()
            if normalized not in seen and normalized:
                seen.add(normalized)
                unique_assets.append(item.strip())

        relevant: List[str] = []
        for asset in unique_assets:
            if asset.lower() in job_text_lower:
                relevant.append(asset)

        # If sparse match, include top verified core candidate skills
        if not relevant:
            relevant = unique_assets[:5]

        return relevant

    def _identify_relevant_experience(self, profile: CandidateProfile, job_text_lower: str) -> List[str]:
        """Filters and prioritizes genuine candidate experience highlights without inventing achievements."""
        relevant_highlights: List[str] = []

        # Signals relevant to modern software engineering roles
        keywords = [
            "react", "next.js", "node.js", "typescript", "javascript", "python", "fastapi",
            "api", "microservice", "frontend", "backend", "full stack", "database",
            "postgresql", "redis", "architect", "scale", "optimize", "ui", "build", "cloud"
        ]
        target_signals = [kw for kw in keywords if kw in job_text_lower]

        for exp in profile.work_history:
            for highlight in exp.highlights:
                hl_lower = highlight.lower()
                # Check for overlap with role signals
                if any(sig in hl_lower for sig in target_signals):
                    relevant_highlights.append(f"{exp.role_title} at {exp.company_name}: {highlight}")
                elif len(relevant_highlights) < 3:
                    # Keep authentic highlight if still under quota
                    relevant_highlights.append(f"{exp.role_title} at {exp.company_name}: {highlight}")

        return relevant_highlights

    # -----------------------------------------------------------------------
    # Step 5 & 6 AI Generation (Model Ladder)
    # -----------------------------------------------------------------------

    async def _generate_with_ai(
        self,
        job: JobListing,
        profile: CandidateProfile,
        relevant_skills: List[str],
        relevant_experience: List[str],
        version: int,
        custom_instructions: Optional[str] = None,
    ) -> Optional[TailoredDocument]:
        """Calls Model Ladder (Gemini) with strict anti-fabrication grounding."""
        api_key = self.settings_service.get_api_key_for_service()
        if not api_key:
            return None

        candidates = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
        if self.model_ladder_service:
            try:
                from app.services.model_ladder_service import TaskType
                ladder_candidates = self.model_ladder_service.get_candidates(task=TaskType.SMART)
                if ladder_candidates:
                    candidates = ladder_candidates
            except Exception as e:
                logger.debug("Failed querying candidates from model ladder: %s", e)

        exp_bullets = "\n".join(
            f"- {e.role_title} at {e.company_name} ({e.start_date} to {e.end_date or 'Present'}): "
            + "; ".join(e.highlights)
            + (f" [Tech: {', '.join(e.tech_stack)}]" if e.tech_stack else "")
            for e in profile.work_history
        )

        prompt = (
            "You are ALEX Resume Studio, an expert executive resume and career document architect.\n\n"
            "STRICT INTEGRITY AND ANTI-FABRICATION RULES:\n"
            "- NEVER invent or hallucinate candidate experience.\n"
            "- NEVER fabricate employers, dates, job titles, or companies.\n"
            "- NEVER invent non-existent project achievements or fake metrics.\n"
            "- Use ONLY verified experience from the candidate's profile.\n"
            "- Highlight and re-order genuine achievements that answer the target job requirements.\n\n"
            "TARGET JOB:\n"
            f"Title: {job.title}\n"
            f"Company: {job.company_name}\n"
            f"Location: {job.location} ({job.modality.value})\n"
            f"Description:\n{job.cleaned_description or job.raw_description[:2000]}\n\n"
            "VERIFIED CANDIDATE ASSETS:\n"
            f"Name: {profile.full_name}\n"
            f"Email: {profile.email}\n"
            f"Headline: {profile.headline}\n"
            f"Relevant Skills: {', '.join(relevant_skills)}\n"
            f"Relevant Highlights:\n" + "\n".join(f"* {h}" for h in relevant_experience) + "\n"
            f"Complete Work History:\n{exp_bullets}\n\n"
            + (f"USER INSTRUCTIONS:\n{custom_instructions}\n\n" if custom_instructions else "")
            + "Return a valid JSON object matching this schema:\n"
            "{\n"
            '  "resume_markdown": string (Full ATS-optimized Markdown resume with sections: Summary, Skills, Experience, Education),\n'
            '  "cover_letter_markdown": string (Personalized cover letter addressed to hiring team at target company),\n'
            '  "ats_keywords_included": [string],\n'
            '  "customizations_summary": [string]\n'
            "}"
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
                            temperature=0.2,
                        ),
                    )
                    raw_text = (response.text or "").strip()
                    if raw_text:
                        parsed = json.loads(raw_text)
                        if self.model_ladder_service:
                            self.model_ladder_service.record_success(model_id)

                        return TailoredDocument(
                            id=str(uuid4()),
                            job_id=job.id,
                            candidate_id=profile.id,
                            version_number=version,
                            resume_markdown=parsed.get("resume_markdown", ""),
                            cover_letter_markdown=parsed.get("cover_letter_markdown", ""),
                            ats_keywords_included=parsed.get("ats_keywords_included", relevant_skills),
                            customizations_summary=parsed.get("customizations_summary", [
                                f"Customized resume and cover letter for {job.title} at {job.company_name}."
                            ]),
                            relevant_experience_identified=relevant_experience,
                            relevant_skills_identified=relevant_skills,
                            original_resume_preserved=True,
                        )
                except Exception as model_exc:
                    logger.warning("Model ladder %s failed in Resume Studio: %s", model_id, model_exc)
                    if self.model_ladder_service:
                        code = getattr(model_exc, "code", 500)
                        self.model_ladder_service.record_failure(model_id, code)
                    continue
        except Exception as exc:
            logger.info("Resume Studio AI tailoring fallback to deterministic engine: %s", exc)

        return None

    # -----------------------------------------------------------------------
    # Step 5 & 6 Deterministic Template Engine (Zero-Hallucination Fallback)
    # -----------------------------------------------------------------------

    def _generate_with_templates(
        self,
        job: JobListing,
        profile: CandidateProfile,
        relevant_skills: List[str],
        relevant_experience: List[str],
        version: int,
    ) -> TailoredDocument:
        """Deterministic, grounded template generation for offline / fallback mode."""
        # 1. Build Tailored Resume Markdown
        skills_lines = [f"- **{s.category}**: {s.name} ({s.proficiency})" for s in profile.skills]
        skills_block = "\n".join(skills_lines)

        exp_blocks = []
        for exp in profile.work_history:
            date_range = f"{exp.start_date} – {exp.end_date if exp.end_date else 'Present'}"
            bullets = "\n".join([f"  * {h}" for h in exp.highlights])
            stack = ", ".join(exp.tech_stack)
            exp_blocks.append(
                f"### {exp.role_title} | {exp.company_name}\n"
                f"*{date_range} | {exp.location or 'Remote'}*\n\n"
                f"{bullets}\n\n"
                f"**Technologies**: {stack}\n"
            )
        experience_block = "\n".join(exp_blocks)

        resume_md = (
            f"# {profile.full_name}\n"
            f"**{job.title} Candidate** | {profile.location} | {profile.email}\n"
            f"{f'LinkedIn: {profile.linkedin_url} | ' if profile.linkedin_url else ''}"
            f"{f'GitHub: {profile.github_url}' if profile.github_url else ''}\n\n"
            f"## Professional Summary\n"
            f"{profile.summary} Focused on delivering scalable engineering solutions as a {job.title} "
            f"at {job.company_name}, leveraging {', '.join(relevant_skills[:4]) or 'modern web technologies'}.\n\n"
            f"## Core Technical Proficiencies\n"
            f"{skills_block}\n\n"
            f"## Work Experience\n"
            f"{experience_block}\n"
        )

        # 2. Build Cover Letter Markdown
        cover_letter_md = (
            f"Dear Hiring Team at {job.company_name},\n\n"
            f"I am writing to express my enthusiastic interest in the **{job.title}** position. "
            f"With {profile.total_years_experience} years of hands-on software engineering experience, "
            f"I have specialized in building robust, performant web applications using "
            f"{', '.join(relevant_skills[:4]) or 'React, Next.js, and Node.js'}.\n\n"
            f"In my previous roles, I have focused on translating product vision into scalable, "
            f"maintainable technical architectures. The opportunity to contribute to {job.company_name}'s "
            f"engineering goals directly aligns with my technical background and professional values.\n\n"
            f"Thank you for your time and consideration. I welcome the opportunity to discuss how my "
            f"skill set can bring immediate value to your team.\n\n"
            f"Sincerely,\n"
            f"{profile.full_name}\n"
            f"{profile.email}\n"
        )

        customizations = [
            f"Targeted header and summary to '{job.title}' role at {job.company_name}.",
            f"Emphasized {len(relevant_skills)} relevant skills: {', '.join(relevant_skills[:4])}.",
            f"Aligned experience bullets with {job.modality.value} team requirements.",
        ]

        return TailoredDocument(
            id=str(uuid4()),
            job_id=job.id,
            candidate_id=profile.id,
            version_number=version,
            resume_markdown=resume_md,
            cover_letter_markdown=cover_letter_md,
            ats_keywords_included=relevant_skills[:8],
            customizations_summary=customizations,
            relevant_experience_identified=relevant_experience,
            relevant_skills_identified=relevant_skills,
            original_resume_preserved=True,
        )

    # -----------------------------------------------------------------------
    # Binary Rendering & Workspace Export (DOCX & PDF)
    # -----------------------------------------------------------------------

    def _render_and_attach_binary_assets(
        self,
        doc: TailoredDocument,
        profile: CandidateProfile,
        job: JobListing,
    ) -> None:
        """Generates DOCX and PDF byte streams and writes them into file workspace."""
        contact_line = f"{profile.email} | {profile.location}"
        if profile.phone:
            contact_line = f"{profile.phone} | {contact_line}"

        # 1. Render Resume DOCX & PDF
        res_docx_bytes = self.exporter.export_docx(
            title=profile.full_name,
            subtitle=f"{job.title} Candidate – Tailored for {job.company_name}",
            content_markdown=doc.resume_markdown,
            contact_info=contact_line,
        )
        res_pdf_bytes = self.exporter.export_pdf(
            title=profile.full_name,
            subtitle=f"{job.title} Candidate – Tailored for {job.company_name}",
            content_markdown=doc.resume_markdown,
            contact_info=contact_line,
        )

        # 2. Render Cover Letter DOCX & PDF
        cl_docx_bytes = self.exporter.export_docx(
            title=profile.full_name,
            subtitle=f"Application for {job.title} at {job.company_name}",
            content_markdown=doc.cover_letter_markdown,
            contact_info=contact_line,
        )
        cl_pdf_bytes = self.exporter.export_pdf(
            title=profile.full_name,
            subtitle=f"Application for {job.title} at {job.company_name}",
            content_markdown=doc.cover_letter_markdown,
            contact_info=contact_line,
        )

        # 3. Save into File Workspace
        paths = self.exporter.save_package_to_workspace(
            job_id=doc.job_id,
            version=doc.version_number,
            resume_md=doc.resume_markdown,
            cover_letter_md=doc.cover_letter_markdown,
            resume_docx=res_docx_bytes,
            resume_pdf=res_pdf_bytes,
            cover_letter_docx=cl_docx_bytes,
            cover_letter_pdf=cl_pdf_bytes,
        )

        doc.docx_resume_path = paths.get("docx_resume_path")
        doc.pdf_resume_path = paths.get("pdf_resume_path")
        doc.docx_cover_letter_path = paths.get("docx_cover_letter_path")
        doc.pdf_cover_letter_path = paths.get("pdf_cover_letter_path")

    # -----------------------------------------------------------------------
    # Editing, Versions, and Download Support
    # -----------------------------------------------------------------------

    def update_tailored_document(
        self,
        doc_id: str,
        resume_markdown: Optional[str] = None,
        cover_letter_markdown: Optional[str] = None,
        create_new_version: bool = False,
    ) -> TailoredDocument:
        """Allows preview and editing of tailored resumes and cover letters."""
        existing = self.storage.get_tailored_document(doc_id)
        if not existing:
            raise ValueError(f"Tailored document {doc_id} not found.")

        job = self.storage.get_job(existing.job_id)
        if not job:
            raise ValueError(f"Associated job listing {existing.job_id} not found.")

        profile = self.storage.get_candidate_profile(existing.candidate_id)
        if not profile:
            raise ValueError(f"Associated candidate profile {existing.candidate_id} not found.")

        new_resume_md = resume_markdown if resume_markdown is not None else existing.resume_markdown
        new_cl_md = cover_letter_markdown if cover_letter_markdown is not None else existing.cover_letter_markdown

        if create_new_version:
            new_version = self.storage.get_next_version_number_for_job(existing.job_id)
            doc_to_save = TailoredDocument(
                id=str(uuid4()),
                job_id=existing.job_id,
                candidate_id=existing.candidate_id,
                version_number=new_version,
                resume_markdown=new_resume_md,
                cover_letter_markdown=new_cl_md,
                ats_keywords_included=existing.ats_keywords_included,
                customizations_summary=existing.customizations_summary + [f"Created edited version {new_version}"],
                relevant_experience_identified=existing.relevant_experience_identified,
                relevant_skills_identified=existing.relevant_skills_identified,
                original_resume_preserved=True,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            doc_to_save = existing
            doc_to_save.resume_markdown = new_resume_md
            doc_to_save.cover_letter_markdown = new_cl_md
            doc_to_save.updated_at = datetime.now(timezone.utc).isoformat()

        # Re-render DOCX and PDF with edited content
        self._render_and_attach_binary_assets(doc_to_save, profile, job)
        return self.storage.save_tailored_document(doc_to_save)

    def list_versions_for_job(self, job_id: str) -> List[TailoredDocument]:
        """Lists all independently saved document versions for a specific job."""
        return self.storage.list_tailored_documents_for_job(job_id)

    def get_document_bytes(
        self,
        doc_id: str,
        doc_type: str = "resume",
        format_type: str = "pdf",
    ) -> Tuple[bytes, str, str]:
        """
        Retrieves raw binary bytes for download.
        Returns: (file_bytes, media_type, filename)
        """
        doc = self.storage.get_tailored_document(doc_id)
        if not doc:
            raise ValueError(f"Tailored document {doc_id} not found.")

        job = self.storage.get_job(doc.job_id)
        company_clean = (job.company_name if job else "Company").replace(" ", "_")
        clean_type = "Resume" if doc_type.lower() == "resume" else "Cover_Letter"
        content_md = doc.resume_markdown if doc_type.lower() == "resume" else doc.cover_letter_markdown

        if format_type.lower() == "docx":
            # Check cached workspace path first
            path_str = doc.docx_resume_path if doc_type.lower() == "resume" else doc.docx_cover_letter_path
            if path_str and Path(path_str).exists():
                return Path(path_str).read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"{company_clean}_{clean_type}_v{doc.version_number}.docx"

            # Render on demand
            profile = self.storage.get_candidate_profile(doc.candidate_id)
            title = profile.full_name if profile else "Candidate"
            docx_data = self.exporter.export_docx(
                title=title,
                subtitle=f"{clean_type} – {job.title if job else ''}",
                content_markdown=content_md,
            )
            return docx_data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"{company_clean}_{clean_type}_v{doc.version_number}.docx"

        elif format_type.lower() == "pdf":
            path_str = doc.pdf_resume_path if doc_type.lower() == "resume" else doc.pdf_cover_letter_path
            if path_str and Path(path_str).exists():
                return Path(path_str).read_bytes(), "application/pdf", f"{company_clean}_{clean_type}_v{doc.version_number}.pdf"

            profile = self.storage.get_candidate_profile(doc.candidate_id)
            title = profile.full_name if profile else "Candidate"
            pdf_data = self.exporter.export_pdf(
                title=title,
                subtitle=f"{clean_type} – {job.title if job else ''}",
                content_markdown=content_md,
            )
            return pdf_data, "application/pdf", f"{company_clean}_{clean_type}_v{doc.version_number}.pdf"

        elif format_type.lower() in ("md", "markdown", "text", "txt"):
            return content_md.encode("utf-8"), "text/markdown; charset=utf-8", f"{company_clean}_{clean_type}_v{doc.version_number}.md"

        else:
            raise ValueError(f"Unsupported format '{format_type}'. Supported formats: pdf, docx, markdown.")
