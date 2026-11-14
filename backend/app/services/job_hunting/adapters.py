"""
External Job Source Adapters for ALEX Job Hunting Module.
Supports LinkedIn alert parsing, LinkedIn URL ingestion, Web Search queries, and public APIs.
Strictly adheres to policy: NO automated LinkedIn scraping or account activity.
"""

from __future__ import annotations

import csv
import io
import logging
import re
import urllib.parse
import zipfile
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from app.schemas.job_hunting import (
    AdapterStatusReport,
    JobListing,
    JobSource,
    WorkModality,
)
from app.services.job_hunting.deduplication import compute_job_content_hash

logger = logging.getLogger(__name__)


class BaseJobSourceAdapter(ABC):
    """Abstract base class for external job source adapters."""

    @property
    @abstractmethod
    def source_name(self) -> JobSource:
        """Identifier for this job source."""
        pass

    @abstractmethod
    def check_availability(self) -> AdapterStatusReport:
        """Check if this adapter has required credentials and configuration."""
        pass

    @abstractmethod
    async def discover_or_ingest(self, **kwargs: Any) -> List[JobListing]:
        """Fetch or parse job listings from this source."""
        pass


class LinkedInAlertJobAdapter(BaseJobSourceAdapter):
    """
    Parses LinkedIn job alert email or text notifications provided by the user.
    Extracts individual job cards, titles, companies, locations, and view links.
    """

    @property
    def source_name(self) -> JobSource:
        return JobSource.LINKEDIN_ALERT

    def check_availability(self) -> AdapterStatusReport:
        return AdapterStatusReport(
            adapter_name="LinkedIn Alert Ingestion",
            available=True,
            description="Parses user-provided LinkedIn job alert notification emails and text.",
        )

    async def discover_or_ingest(self, **kwargs: Any) -> List[JobListing]:
        raw_text: str = kwargs.get("alert_text", "")
        default_modality: WorkModality = kwargs.get("default_modality", WorkModality.REMOTE)

        if not raw_text.strip():
            return []

        listings: List[JobListing] = []

        # Split into blocks based on common email patterns or URLs
        # LinkedIn alerts often feature blocks like:
        # "Title at Company"
        # "Location · Modality"
        # "View job: https://www.linkedin.com/comm/jobs/view/..."
        # Or simple lines:
        # Title
        # Company
        # Location
        # https://www.linkedin.com/jobs/view/1234567

        # 1. Regex find all LinkedIn job links
        job_link_pattern = re.compile(
            r"https?://(?:[a-zA-Z0-9-]+\.)?linkedin\.com/(?:comm/)?jobs/view/([0-9]+)[^\s]*",
            re.IGNORECASE,
        )

        matches = list(job_link_pattern.finditer(raw_text))

        if matches:
            # We have links! Segment text around them
            last_idx = 0
            for i, match in enumerate(matches):
                job_id = match.group(1)
                job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"

                # Text before this match (or between previous and this)
                segment = raw_text[last_idx:match.start()].strip()
                last_idx = match.end()

                lines = [l.strip() for l in segment.splitlines() if l.strip()]
                title = "Software Developer"
                company = "Hiring Organization"
                location = "Worldwide / Remote"

                # Heuristic: analyze last 3 lines before the link
                if len(lines) >= 2:
                    # Often line -2 is title, line -1 is company or vice versa
                    if " at " in lines[-1]:
                        parts = lines[-1].split(" at ", 1)
                        title, company = parts[0].strip(), parts[1].strip()
                    elif " · " in lines[-1] and len(lines) >= 3:
                        location = lines[-1]
                        company = lines[-2]
                        title = lines[-3]
                    else:
                        title = lines[-2]
                        company = lines[-1]
                elif len(lines) == 1:
                    if " at " in lines[0]:
                        parts = lines[0].split(" at ", 1)
                        title, company = parts[0].strip(), parts[1].strip()
                    else:
                        title = lines[0]

                content_hash = compute_job_content_hash(
                    company_name=company,
                    title=title,
                    location=location,
                    external_id=job_id,
                )

                listings.append(
                    JobListing(
                        id=str(uuid4()),
                        source=JobSource.LINKEDIN_ALERT,
                        external_id=job_id,
                        source_url=job_url,
                        company_name=company,
                        title=title,
                        location=location,
                        modality=default_modality,
                        raw_description=segment or f"Job listing {title} at {company}",
                        cleaned_description=segment,
                        content_hash=content_hash,
                    )
                )
        else:
            # Fallback: Parse line-by-line block (e.g. text copy-paste)
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            title = lines[0] if lines else "Software Developer"
            company = lines[1] if len(lines) > 1 else "Unknown Company"
            location = lines[2] if len(lines) > 2 else "Remote"

            content_hash = compute_job_content_hash(
                company_name=company,
                title=title,
                location=location,
            )

            listings.append(
                JobListing(
                    id=str(uuid4()),
                    source=JobSource.LINKEDIN_ALERT,
                    source_url="https://www.linkedin.com/jobs/",
                    company_name=company,
                    title=title,
                    location=location,
                    modality=default_modality,
                    raw_description=raw_text,
                    cleaned_description=raw_text,
                    content_hash=content_hash,
                )
            )

        return listings


class LinkedInUrlJobAdapter(BaseJobSourceAdapter):
    """
    Ingests a single user-provided LinkedIn job posting URL.
    Extracts canonical Job ID, cleans tracking params, and stores user metadata.
    Does NOT log into LinkedIn, scrape accounts, or automate user activity.
    """

    @property
    def source_name(self) -> JobSource:
        return JobSource.LINKEDIN_URL

    def check_availability(self) -> AdapterStatusReport:
        return AdapterStatusReport(
            adapter_name="LinkedIn URL Ingestion",
            available=True,
            description="Ingests user-supplied LinkedIn job URLs and extracts canonical IDs without scraping.",
        )

    async def discover_or_ingest(self, **kwargs: Any) -> List[JobListing]:
        url: str = kwargs.get("url", "").strip()
        optional_title: Optional[str] = kwargs.get("optional_title")
        optional_company: Optional[str] = kwargs.get("optional_company")
        optional_snippet: Optional[str] = kwargs.get("optional_snippet")
        modality: WorkModality = kwargs.get("modality", WorkModality.REMOTE)

        if not url:
            return []

        # Parse canonical Job ID from URL
        # Matches: /jobs/view/1234567890 or currentJobId=1234567890
        job_id: Optional[str] = None
        view_match = re.search(r"/jobs/view/([0-9]+)", url)
        if view_match:
            job_id = view_match.group(1)
        else:
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if "currentJobId" in query_params:
                job_id = query_params["currentJobId"][0]

        canonical_url = f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id else url

        title = optional_title or "Software Developer"
        company = optional_company or "LinkedIn Opportunity"
        location = "Worldwide / Remote"
        raw_desc = optional_snippet or f"LinkedIn Job Listing (ID: {job_id or 'unknown'}) at {canonical_url}"

        content_hash = compute_job_content_hash(
            company_name=company,
            title=title,
            location=location,
            external_id=job_id,
        )

        listing = JobListing(
            id=str(uuid4()),
            source=JobSource.LINKEDIN_URL,
            external_id=job_id,
            source_url=canonical_url,
            company_name=company,
            title=title,
            location=location,
            modality=modality,
            raw_description=raw_desc,
            cleaned_description=raw_desc,
            content_hash=content_hash,
        )
        return [listing]


class LinkedInDataExportAdapter(BaseJobSourceAdapter):
    """
    Parses user-uploaded official LinkedIn data exports (ZIP archive or CSV).
    Extracts saved jobs, applied jobs, and normalized listings without any scraping.
    """

    @property
    def source_name(self) -> JobSource:
        return JobSource.LINKEDIN_URL

    def check_availability(self) -> AdapterStatusReport:
        return AdapterStatusReport(
            adapter_name="LinkedIn Data Export Ingestion",
            available=True,
            description="Imports user-provided official LinkedIn archive files (Saved Jobs.csv, Job Applications.csv, or ZIP archive).",
        )

    def parse_csv_content(self, text: str, default_modality: WorkModality = WorkModality.REMOTE) -> List[JobListing]:
        listings: List[JobListing] = []
        try:
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                normalized_keys = {k.strip().lower(): v for k, v in row.items() if k}
                title = (
                    normalized_keys.get("job title")
                    or normalized_keys.get("title")
                    or normalized_keys.get("position")
                    or ""
                ).strip()
                company = (
                    normalized_keys.get("company name")
                    or normalized_keys.get("company")
                    or normalized_keys.get("employer")
                    or "LinkedIn Opportunity"
                ).strip()
                url = (
                    normalized_keys.get("job url")
                    or normalized_keys.get("job link")
                    or normalized_keys.get("url")
                    or normalized_keys.get("link")
                    or ""
                ).strip()
                loc = (
                    normalized_keys.get("location")
                    or normalized_keys.get("job location")
                    or "Worldwide / Remote"
                ).strip()
                saved_date = (
                    normalized_keys.get("date saved")
                    or normalized_keys.get("application date")
                    or normalized_keys.get("date")
                    or None
                )

                if not title:
                    continue

                job_id = None
                if url:
                    view_match = re.search(r"/jobs/view/([0-9]+)", url)
                    if view_match:
                        job_id = view_match.group(1)

                canonical_url = f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id else (url or "https://www.linkedin.com/jobs/")
                raw_desc = f"Exported LinkedIn opportunity: {title} at {company}. Location: {loc}."

                c_hash = compute_job_content_hash(
                    company_name=company,
                    title=title,
                    location=loc,
                    external_id=job_id,
                )

                listings.append(
                    JobListing(
                        id=str(uuid4()),
                        source=JobSource.LINKEDIN_URL,
                        external_id=job_id,
                        source_url=canonical_url,
                        company_name=company,
                        title=title,
                        location=loc or "Worldwide / Remote",
                        modality=default_modality,
                        raw_description=raw_desc,
                        cleaned_description=raw_desc,
                        posted_at=saved_date,
                        content_hash=c_hash,
                    )
                )
        except Exception as exc:
            logger.warning("Error parsing LinkedIn export CSV: %s", exc)

        return listings

    async def discover_or_ingest(self, **kwargs: Any) -> List[JobListing]:
        file_bytes: Optional[bytes] = kwargs.get("file_bytes")
        file_text: Optional[str] = kwargs.get("file_text")
        filename: str = kwargs.get("filename", "").lower()
        default_modality: WorkModality = kwargs.get("default_modality", WorkModality.REMOTE)

        all_listings: List[JobListing] = []

        if file_bytes and filename.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as z:
                    for name in z.namelist():
                        name_lower = name.lower()
                        if "saved jobs" in name_lower or "job applications" in name_lower or (name_lower.endswith(".csv") and "job" in name_lower):
                            with z.open(name) as f:
                                text = f.read().decode("utf-8", errors="replace")
                                all_listings.extend(self.parse_csv_content(text, default_modality))
            except Exception as exc:
                logger.warning("Failed to read LinkedIn ZIP export: %s", exc)
        elif file_bytes:
            text = file_bytes.decode("utf-8", errors="replace")
            all_listings.extend(self.parse_csv_content(text, default_modality))
        elif file_text:
            all_listings.extend(self.parse_csv_content(file_text, default_modality))

        return all_listings


class WebSearchJobAdapter(BaseJobSourceAdapter):
    """
    Discovers active jobs using ALEX's existing WebSearchService.
    Queries careers portals, Greenhouse, Lever, and job boards.
    """

    def __init__(self, web_search_service: Any) -> None:
        self.web_search_service = web_search_service

    @property
    def source_name(self) -> JobSource:
        return JobSource.WEB_SEARCH

    def check_availability(self) -> AdapterStatusReport:
        if not self.web_search_service:
            return AdapterStatusReport(
                adapter_name="Web Search Discovery",
                available=False,
                description="Queries job boards and company career sites using grounded web search.",
                reason="WebSearchService is not initialized.",
            )
        # Check settings
        settings = getattr(self.web_search_service, "_settings", None)
        api_key = settings.get_api_key_for_service() if settings else None
        if not api_key:
            return AdapterStatusReport(
                adapter_name="Web Search Discovery",
                available=False,
                description="Queries job boards and company career sites using grounded web search.",
                reason="Gemini API key is not configured in Settings.",
            )
        return AdapterStatusReport(
            adapter_name="Web Search Discovery",
            available=True,
            description="Queries job boards and company career sites using grounded web search.",
        )

    async def discover_or_ingest(self, **kwargs: Any) -> List[JobListing]:
        query = kwargs.get("query", "Full Stack Developer React Node.js 2-5 years remote")
        max_results = kwargs.get("max_results", 5)

        status = self.check_availability()
        if not status.available:
            logger.info("WebSearchJobAdapter unavailable: %s", status.reason)
            return []

        try:
            from app.schemas.search import WebSearchRequest
            search_request = WebSearchRequest(
                query=f"find job openings: {query} (site:greenhouse.io OR site:lever.co OR site:workable.com OR site:remoteok.com)",
                mode="grounded",
            )
            resp = await self.web_search_service.search(search_request)

            listings: List[JobListing] = []
            # Extract links or paragraphs
            text = resp.answer or ""
            # Search for URLs in sources or markdown links
            links = resp.sources or []

            # Create parsed listing from search response
            if text:
                content_hash = compute_job_content_hash(
                    company_name="Web Search Aggregate",
                    title=query,
                    location="Remote / Worldwide",
                )
                source_url = links[0] if links else "https://www.google.com/search?q=" + urllib.parse.quote(query)
                listings.append(
                    JobListing(
                        id=str(uuid4()),
                        source=JobSource.WEB_SEARCH,
                        source_url=source_url,
                        company_name="Discovered via Web Search",
                        title=query,
                        location="Remote / Worldwide",
                        modality=WorkModality.REMOTE,
                        raw_description=text,
                        cleaned_description=text,
                        content_hash=content_hash,
                    )
                )
            return listings
        except Exception as exc:
            logger.warning("Web search job discovery error: %s", exc)
            return []


class RemoteOKJobAdapter(BaseJobSourceAdapter):
    """
    Public API Adapter that queries remote developer jobs from public feeds (e.g. RemoteOK).
    Requires no user accounts or proprietary scraping.
    """

    @property
    def source_name(self) -> JobSource:
        return JobSource.PUBLIC_API

    def check_availability(self) -> AdapterStatusReport:
        return AdapterStatusReport(
            adapter_name="Remote Public Job API (RemoteOK)",
            available=True,
            description="Queries public developer job listings from verified remote feeds.",
        )

    async def discover_or_ingest(self, **kwargs: Any) -> List[JobListing]:
        query = kwargs.get("query", "react").lower()
        limit = kwargs.get("max_results", 5)

        url = "https://remoteok.com/api"
        headers = {"User-Agent": "ALEX-AI-Assistant/1.0 (Job Hunting Module; contact@alex-ai.local)"}

        listings: List[JobListing] = []
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # First element in RemoteOK API is usually a legal disclosure object
                    items = [d for d in data if isinstance(d, dict) and "position" in d]

                    # Filter by query
                    matched = [
                        it for it in items
                        if query in it.get("position", "").lower()
                        or any(query in tag.lower() for tag in it.get("tags", []))
                    ]

                    for item in matched[:limit]:
                        ext_id = str(item.get("id", ""))
                        title = item.get("position", "Software Developer")
                        company = item.get("company", "Remote Employer")
                        loc = item.get("location") or "Worldwide / Remote"
                        job_url = item.get("url") or f"https://remoteok.com/l/{ext_id}"
                        desc = item.get("description", "")
                        tags = item.get("tags", [])

                        c_hash = compute_job_content_hash(
                            company_name=company,
                            title=title,
                            location=loc,
                            external_id=ext_id,
                        )

                        listings.append(
                            JobListing(
                                id=str(uuid4()),
                                source=JobSource.PUBLIC_API,
                                external_id=ext_id,
                                source_url=job_url,
                                company_name=company,
                                title=title,
                                location=loc,
                                modality=WorkModality.REMOTE,
                                raw_description=desc,
                                cleaned_description=re.sub(r"<[^>]+>", " ", desc),
                                required_skills=tags[:6],
                                content_hash=c_hash,
                            )
                        )
        except Exception as exc:
            logger.info("RemoteOK public API request failed or timed out: %s", exc)

        return listings


class DirectUrlJobAdapter(BaseJobSourceAdapter):
    """
    Ingests general job postings directly provided by the user (Company careers or portal links).
    """

    @property
    def source_name(self) -> JobSource:
        return JobSource.DIRECT_URL

    def check_availability(self) -> AdapterStatusReport:
        return AdapterStatusReport(
            adapter_name="Direct Job URL Ingestion",
            available=True,
            description="Ingests arbitrary company career and job posting links with user notes.",
        )

    async def discover_or_ingest(self, **kwargs: Any) -> List[JobListing]:
        url = kwargs.get("url", "").strip()
        title = kwargs.get("title") or "Software Developer"
        company = kwargs.get("company") or "Direct Employer"
        raw_text = kwargs.get("raw_text") or f"Direct listing at {url}"
        modality = kwargs.get("modality", WorkModality.REMOTE)

        if not url:
            return []

        c_hash = compute_job_content_hash(
            company_name=company,
            title=title,
            location="Remote",
        )

        return [
            JobListing(
                id=str(uuid4()),
                source=JobSource.DIRECT_URL,
                source_url=url,
                company_name=company,
                title=title,
                location="Worldwide / Remote",
                modality=modality,
                raw_description=raw_text,
                cleaned_description=raw_text,
                content_hash=c_hash,
            )
        ]


class GreenhouseJobAdapter(BaseJobSourceAdapter):
    """
    Ingests public job listings from Greenhouse job boards.
    Queries the official Greenhouse public board API:
    https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
    """

    @property
    def source_name(self) -> JobSource:
        return JobSource.GREENHOUSE

    def check_availability(self) -> AdapterStatusReport:
        return AdapterStatusReport(
            adapter_name="Greenhouse Job Board Ingestion",
            available=True,
            description="Queries public Greenhouse company job boards (e.g. gitlab, stripe, figma) via official boards API.",
        )

    async def discover_or_ingest(self, **kwargs: Any) -> List[JobListing]:
        board_token = (kwargs.get("board_token") or "").strip().lower()
        filter_role = (kwargs.get("filter_role") or "").strip().lower()
        limit = kwargs.get("max_results", 15)

        if not board_token:
            raise ValueError("Greenhouse board_token is required (e.g. 'gitlab', 'stripe').")

        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        headers = {"User-Agent": "ALEX-AI-Assistant/1.0 (Job Hunting Module)"}

        listings: List[JobListing] = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    raise RuntimeError(f"Greenhouse board '{board_token}' was not found (404).")
                if resp.status_code != 200:
                    raise RuntimeError(f"Greenhouse API returned HTTP {resp.status_code} for board '{board_token}'.")

                data = resp.json()
                raw_jobs = data.get("jobs", [])

                for item in raw_jobs:
                    job_id = str(item.get("id", ""))
                    title = item.get("title", "Software Developer")
                    location_name = (item.get("location") or {}).get("name") or "Remote"
                    abs_url = item.get("absolute_url") or f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"
                    content_html = item.get("content") or ""
                    cleaned_desc = re.sub(r"<[^>]+>", " ", content_html).strip()

                    # Filter by role keywords if specified
                    if filter_role and filter_role not in title.lower() and filter_role not in cleaned_desc.lower():
                        continue

                    # Modality detection
                    modality = WorkModality.REMOTE
                    loc_lower = location_name.lower()
                    if "hybrid" in loc_lower or "hybrid" in title.lower():
                        modality = WorkModality.HYBRID
                    elif "onsite" in loc_lower or "on-site" in loc_lower:
                        modality = WorkModality.ONSITE

                    company_display = board_token.capitalize()
                    c_hash = compute_job_content_hash(
                        company_name=company_display,
                        title=title,
                        location=location_name,
                        external_id=job_id,
                    )

                    listings.append(
                        JobListing(
                            id=str(uuid4()),
                            source=JobSource.GREENHOUSE,
                            external_id=job_id,
                            source_url=abs_url,
                            company_name=company_display,
                            title=title,
                            location=location_name,
                            modality=modality,
                            raw_description=content_html or cleaned_desc or f"Role at {company_display}",
                            cleaned_description=cleaned_desc[:4000],
                            posted_at=item.get("updated_at"),
                            content_hash=c_hash,
                        )
                    )
                    if len(listings) >= limit:
                        break
        except httpx.RequestError as exc:
            raise RuntimeError(f"Network error connecting to Greenhouse board '{board_token}': {exc}") from exc

        return listings


class LeverJobAdapter(BaseJobSourceAdapter):
    """
    Ingests public job listings from Lever company job postings.
    Queries the official Lever public postings API:
    https://api.lever.co/v0/postings/{company_id}?mode=json
    """

    @property
    def source_name(self) -> JobSource:
        return JobSource.LEVER

    def check_availability(self) -> AdapterStatusReport:
        return AdapterStatusReport(
            adapter_name="Lever Postings Ingestion",
            available=True,
            description="Queries public Lever company job postings via official postings API.",
        )

    async def discover_or_ingest(self, **kwargs: Any) -> List[JobListing]:
        company_id = (kwargs.get("company_id") or "").strip().lower()
        filter_role = (kwargs.get("filter_role") or "").strip().lower()
        limit = kwargs.get("max_results", 15)

        if not company_id:
            raise ValueError("Lever company_id is required (e.g. 'spotify', 'netflix').")

        url = f"https://api.lever.co/v0/postings/{company_id}?mode=json"
        headers = {"User-Agent": "ALEX-AI-Assistant/1.0 (Job Hunting Module)"}

        listings: List[JobListing] = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    raise RuntimeError(f"Lever company postings for '{company_id}' not found (404).")
                if resp.status_code != 200:
                    raise RuntimeError(f"Lever API returned HTTP {resp.status_code} for '{company_id}'.")

                raw_jobs = resp.json()
                if not isinstance(raw_jobs, list):
                    return []

                for item in raw_jobs:
                    job_id = str(item.get("id", ""))
                    title = item.get("text", "Software Developer")
                    categories = item.get("categories") or {}
                    location_name = categories.get("location") or "Remote"
                    commitment = categories.get("commitment") or "Full-time"
                    hosted_url = item.get("hostedUrl") or f"https://jobs.lever.co/{company_id}/{job_id}"
                    desc_plain = item.get("descriptionPlain") or item.get("description") or ""

                    # Filter by role keywords if specified
                    if filter_role and filter_role not in title.lower() and filter_role not in desc_plain.lower():
                        continue

                    modality = WorkModality.REMOTE
                    loc_lower = location_name.lower()
                    if "hybrid" in loc_lower or "hybrid" in title.lower():
                        modality = WorkModality.HYBRID
                    elif "onsite" in loc_lower or "on-site" in loc_lower:
                        modality = WorkModality.ONSITE

                    company_display = company_id.capitalize()
                    c_hash = compute_job_content_hash(
                        company_name=company_display,
                        title=title,
                        location=location_name,
                        external_id=job_id,
                    )

                    listings.append(
                        JobListing(
                            id=str(uuid4()),
                            source=JobSource.LEVER,
                            external_id=job_id,
                            source_url=hosted_url,
                            company_name=company_display,
                            title=title,
                            location=location_name,
                            modality=modality,
                            raw_description=desc_plain or f"Lever posting at {company_display}",
                            cleaned_description=desc_plain[:4000],
                            content_hash=c_hash,
                        )
                    )
                    if len(listings) >= limit:
                        break
        except httpx.RequestError as exc:
            raise RuntimeError(f"Network error connecting to Lever for '{company_id}': {exc}") from exc

        return listings


class CompanyCareersJobAdapter(BaseJobSourceAdapter):
    """
    Ingests job listings from public company careers pages.
    """

    @property
    def source_name(self) -> JobSource:
        return JobSource.COMPANY_CAREERS

    def check_availability(self) -> AdapterStatusReport:
        return AdapterStatusReport(
            adapter_name="Company Careers Page Ingestion",
            available=True,
            description="Ingests public company career portal links and descriptions.",
        )

    async def discover_or_ingest(self, **kwargs: Any) -> List[JobListing]:
        url = kwargs.get("url", "").strip()
        title = kwargs.get("title") or "Software Developer"
        company = kwargs.get("company") or "Company Careers"
        raw_text = kwargs.get("raw_text") or f"Careers listing at {url}"
        modality = kwargs.get("modality", WorkModality.REMOTE)

        if not url:
            return []

        c_hash = compute_job_content_hash(
            company_name=company,
            title=title,
            location="Remote",
        )

        return [
            JobListing(
                id=str(uuid4()),
                source=JobSource.COMPANY_CAREERS,
                source_url=url,
                company_name=company,
                title=title,
                location="Worldwide / Remote",
                modality=modality,
                raw_description=raw_text,
                cleaned_description=raw_text,
                content_hash=c_hash,
            )
        ]


class ExpiryChecker:
    """Checks whether an original job application URL is active or expired."""

    EXPIRY_PHRASES = (
        "no longer accepting applications",
        "this job has expired",
        "position has been filled",
        "job is closed",
        "posting is no longer active",
        "job is no longer available",
        "page not found",
        "404 not found",
    )

    @classmethod
    async def check_url_active(
        cls,
        source_url: str,
        timeout: float = 6.0,
    ) -> tuple[bool, Optional[int], Optional[str]]:
        """
        Returns (is_expired, status_code, reason).
        Performs non-intrusive HEAD or GET check.
        """
        if not source_url or not source_url.startswith("http"):
            return False, None, "Invalid URL"

        headers = {"User-Agent": "Mozilla/5.0 (compatible; ALEX-JobHunter/1.0)"}
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                # Try GET with limited bytes
                resp = await client.get(source_url, headers=headers)
                status_code = resp.status_code

                if status_code in (404, 410):
                    return True, status_code, f"HTTP status {status_code} indicates expired listing"

                # Check body text for expiry markers
                body_sample = resp.text[:4000].lower()
                for phrase in cls.EXPIRY_PHRASES:
                    if phrase in body_sample:
                        return True, status_code, f"Page contains expiry marker: '{phrase}'"

                return False, status_code, "URL appears active"
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response else None
            if code in (404, 410):
                return True, code, f"HTTP error {code}"
            return False, code, f"HTTP error {code}"
        except httpx.RequestError as exc:
            return False, None, f"Network verification warning: {exc}"
