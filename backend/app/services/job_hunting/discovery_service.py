"""
Job Discovery Service.
Orchestrates discovery across external adapters (LinkedIn alerts, LinkedIn URLs,
Greenhouse boards, Lever postings, RemoteOK, Web Search, Company Careers).
Enforces deduplication, tracks discovery history, and supports expiry checks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.schemas.job_hunting import (
    AdapterStatusReport,
    BulkExpiryResponse,
    CandidateProfile,
    CheckExpiryResponse,
    DiscoveryRunRecord,
    JobListing,
    JobSource,
    WorkModality,
)
from app.services.job_hunting.adapters import (
    BaseJobSourceAdapter,
    CompanyCareersJobAdapter,
    DirectUrlJobAdapter,
    ExpiryChecker,
    GreenhouseJobAdapter,
    LeverJobAdapter,
    LinkedInAlertJobAdapter,
    LinkedInUrlJobAdapter,
    RemoteOKJobAdapter,
    WebSearchJobAdapter,
)
from app.services.job_hunting.storage import JobHuntingStorage

logger = logging.getLogger(__name__)


class JobDiscoveryService:
    """Coordinates job discovery across registered adapters with automatic deduplication."""

    def __init__(
        self,
        storage: JobHuntingStorage,
        web_search_service: Any = None,
    ) -> None:
        self.storage = storage
        self.adapters: Dict[JobSource, BaseJobSourceAdapter] = {
            JobSource.LINKEDIN_ALERT: LinkedInAlertJobAdapter(),
            JobSource.LINKEDIN_URL: LinkedInUrlJobAdapter(),
            JobSource.GREENHOUSE: GreenhouseJobAdapter(),
            JobSource.LEVER: LeverJobAdapter(),
            JobSource.WEB_SEARCH: WebSearchJobAdapter(web_search_service),
            JobSource.PUBLIC_API: RemoteOKJobAdapter(),
            JobSource.DIRECT_URL: DirectUrlJobAdapter(),
            JobSource.COMPANY_CAREERS: CompanyCareersJobAdapter(),
        }

    def list_adapters(self) -> List[AdapterStatusReport]:
        """Reports availability status and configuration for all adapters."""
        return [adapter.check_availability() for adapter in self.adapters.values()]

    async def discover_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        modalities: Optional[List[WorkModality]] = None,
        max_results: int = 15,
        profile: Optional[CandidateProfile] = None,
    ) -> List[JobListing]:
        """
        Executes discovery pass across available sources.
        Records a DiscoveryRunRecord in storage with genuine errors.
        Deduplicates against existing database entries before saving.
        """
        search_query = query
        if not search_query and profile:
            # Construct query from candidate preferences
            roles = " OR ".join(f'"{r}"' for r in profile.preferences.target_roles[:3])
            skills = " ".join(profile.preferences.keywords[:3])
            search_query = f"{roles} {skills}"
        if not search_query:
            search_query = "Full Stack Developer React Node.js"

        run_id = str(uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        errors: List[str] = []
        all_discovered: List[JobListing] = []

        # 1. Query Web Search adapter if configured
        web_adapter = self.adapters.get(JobSource.WEB_SEARCH)
        if web_adapter and web_adapter.check_availability().available:
            try:
                results = await web_adapter.discover_or_ingest(
                    query=search_query,
                    max_results=max_results,
                )
                all_discovered.extend(results)
            except Exception as exc:
                err_msg = f"WebSearchJobAdapter error: {exc}"
                logger.warning(err_msg)
                errors.append(err_msg)

        # 2. Query Public API adapter (RemoteOK)
        public_adapter = self.adapters.get(JobSource.PUBLIC_API)
        if public_adapter:
            try:
                keyword = "react"
                if profile and profile.preferences.keywords:
                    keyword = profile.preferences.keywords[0].lower()
                results = await public_adapter.discover_or_ingest(
                    query=keyword,
                    max_results=max_results,
                )
                all_discovered.extend(results)
            except Exception as exc:
                err_msg = f"Public API adapter error: {exc}"
                logger.info(err_msg)
                errors.append(err_msg)

        # 3. Deduplicate and store
        stored_listings: List[JobListing] = []
        new_jobs_count = 0
        for job in all_discovered:
            existing = self.storage.get_job_by_hash(job.content_hash)
            if existing:
                stored_listings.append(existing)
            else:
                saved = self.storage.save_job(job)
                stored_listings.append(saved)
                new_jobs_count += 1

        # 4. Save discovery run log
        finished_at = datetime.now(timezone.utc).isoformat()
        run_status = "completed" if not errors else ("partial" if stored_listings else "failed")
        run_record = DiscoveryRunRecord(
            id=run_id,
            source="all",
            query=search_query,
            started_at=started_at,
            finished_at=finished_at,
            status=run_status,
            jobs_found=len(all_discovered),
            new_jobs_stored=new_jobs_count,
            errors=errors,
        )
        self.storage.save_discovery_run(run_record)

        return stored_listings

    async def ingest_linkedin_alert(
        self,
        alert_text: str,
        default_modality: WorkModality = WorkModality.REMOTE,
    ) -> List[JobListing]:
        """Parses and stores job listings from user-provided LinkedIn alert text."""
        adapter = self.adapters[JobSource.LINKEDIN_ALERT]
        extracted = await adapter.discover_or_ingest(
            alert_text=alert_text,
            default_modality=default_modality,
        )

        stored: List[JobListing] = []
        for job in extracted:
            existing = self.storage.get_job_by_hash(job.content_hash)
            if existing:
                stored.append(existing)
            else:
                saved = self.storage.save_job(job)
                stored.append(saved)
        return stored

    async def ingest_linkedin_url(
        self,
        url: str,
        optional_title: Optional[str] = None,
        optional_company: Optional[str] = None,
        optional_snippet: Optional[str] = None,
        modality: WorkModality = WorkModality.REMOTE,
    ) -> JobListing:
        """Parses and stores a user-provided LinkedIn job URL without scraping."""
        adapter = self.adapters[JobSource.LINKEDIN_URL]
        results = await adapter.discover_or_ingest(
            url=url,
            optional_title=optional_title,
            optional_company=optional_company,
            optional_snippet=optional_snippet,
            modality=modality,
        )
        job = results[0]
        existing = self.storage.get_job_by_hash(job.content_hash)
        if existing:
            return existing
        return self.storage.save_job(job)

    async def ingest_greenhouse(
        self,
        board_token: str,
        filter_role: Optional[str] = None,
        max_results: int = 15,
    ) -> List[JobListing]:
        """Queries and stores public job listings from a company's Greenhouse board."""
        adapter = self.adapters[JobSource.GREENHOUSE]
        results = await adapter.discover_or_ingest(
            board_token=board_token,
            filter_role=filter_role,
            max_results=max_results,
        )

        stored: List[JobListing] = []
        for job in results:
            existing = self.storage.get_job_by_hash(job.content_hash)
            if existing:
                stored.append(existing)
            else:
                saved = self.storage.save_job(job)
                stored.append(saved)
        return stored

    async def ingest_lever(
        self,
        company_id: str,
        filter_role: Optional[str] = None,
        max_results: int = 15,
    ) -> List[JobListing]:
        """Queries and stores public job listings from a company's Lever postings."""
        adapter = self.adapters[JobSource.LEVER]
        results = await adapter.discover_or_ingest(
            company_id=company_id,
            filter_role=filter_role,
            max_results=max_results,
        )

        stored: List[JobListing] = []
        for job in results:
            existing = self.storage.get_job_by_hash(job.content_hash)
            if existing:
                stored.append(existing)
            else:
                saved = self.storage.save_job(job)
                stored.append(saved)
        return stored

    async def ingest_direct_url(
        self,
        url: str,
        title: Optional[str] = None,
        company: Optional[str] = None,
        raw_text: Optional[str] = None,
        modality: WorkModality = WorkModality.REMOTE,
    ) -> JobListing:
        """Ingests arbitrary job posting URL with optional user notes."""
        adapter = self.adapters[JobSource.DIRECT_URL]
        results = await adapter.discover_or_ingest(
            url=url,
            title=title,
            company=company,
            raw_text=raw_text,
            modality=modality,
        )
        job = results[0]
        existing = self.storage.get_job_by_hash(job.content_hash)
        if existing:
            return existing
        return self.storage.save_job(job)

    async def ingest_company_careers(
        self,
        url: str,
        title: Optional[str] = None,
        company: Optional[str] = None,
        raw_text: Optional[str] = None,
        modality: WorkModality = WorkModality.REMOTE,
    ) -> JobListing:
        """Ingests a public company careers page opportunity."""
        adapter = self.adapters[JobSource.COMPANY_CAREERS]
        results = await adapter.discover_or_ingest(
            url=url,
            title=title,
            company=company,
            raw_text=raw_text,
            modality=modality,
        )
        job = results[0]
        existing = self.storage.get_job_by_hash(job.content_hash)
        if existing:
            return existing
        return self.storage.save_job(job)

    # -----------------------------------------------------------------------
    # Expiry Verification
    # -----------------------------------------------------------------------

    async def check_job_expiry(self, job_id: str) -> CheckExpiryResponse:
        """Checks whether a single job's application URL is active or expired."""
        job = self.storage.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        is_expired, status_code, reason = await ExpiryChecker.check_url_active(job.source_url)
        now_iso = datetime.now(timezone.utc).isoformat()
        self.storage.mark_job_expiry(job_id=job.id, is_expired=is_expired, checked_at=now_iso)

        return CheckExpiryResponse(
            job_id=job.id,
            source_url=job.source_url,
            is_expired=is_expired,
            status_code=status_code,
            checked_at=now_iso,
            reason=reason,
        )

    async def bulk_check_expiry(self, limit: int = 20) -> BulkExpiryResponse:
        """Verifies active listings and marks any expired roles."""
        jobs = self.storage.list_jobs(is_expired=False, limit=limit)
        results: List[CheckExpiryResponse] = []
        expired_count = 0

        for job in jobs:
            try:
                res = await self.check_job_expiry(job.id)
                results.append(res)
                if res.is_expired:
                    expired_count += 1
            except Exception as exc:
                logger.warning("Error verifying expiry for job %s: %s", job.id, exc)

        return BulkExpiryResponse(
            total_checked=len(results),
            expired_count=expired_count,
            results=results,
        )

    def list_discovery_runs(self, limit: int = 50) -> List[DiscoveryRunRecord]:
        """Returns the audit history of discovery runs."""
        return self.storage.list_discovery_runs(limit=limit)
