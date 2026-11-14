"""
Job Deduplication Engine.
Normalizes company name, title, and location to compute deterministic content hashes.
Prevents duplicate listings across multiple queries or ingest channels.
"""

from __future__ import annotations

import hashlib
import re
import urllib.parse
from typing import Any, Optional


def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    # Lowercase, replace hyphens and underscores with spaces, strip punctuation and extra whitespace
    cleaned = text.lower().strip()
    cleaned = cleaned.replace("-", " ").replace("_", " ")
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


AGGREGATOR_DOMAINS = {
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "remoteok.com",
    "remoteok.io",
    "ziprecruiter.com",
    "monster.com",
    "dice.com",
    "wellfound.com",
    "angel.co",
}


def extract_company_domain(company_name: str, url: Optional[str] = None) -> str:
    """
    Extracts canonical company domain or normalized identifier.
    e.g. 'https://boards.greenhouse.io/stripe' -> 'stripe'
    'https://jobs.lever.co/spotify/123' -> 'spotify'
    'Stripe, Inc.' -> 'stripe'
    """
    if url:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]

        # Greenhouse board token in path
        if "greenhouse.io" in netloc and path_parts:
            return path_parts[0]

        # Lever company ID in path
        if "lever.co" in netloc and path_parts:
            return path_parts[0]

        # If not a third-party job aggregator / platform
        if not any(agg in netloc for agg in AGGREGATOR_DOMAINS):
            domain_parts = netloc.split(".")
            if len(domain_parts) >= 2:
                # strip www or careers prefix
                sub = [p for p in domain_parts[:-1] if p not in ("www", "jobs", "careers", "boards")]
                if sub:
                    return sub[-1]

    # Fallback to normalized company name
    norm = normalize_text(company_name)
    for suffix in (" inc", " llc", " corp", " corporation", " ltd", " gmbh", " co"):
        if norm.endswith(suffix):
            norm = norm[: -len(suffix)].strip()
    return norm


def normalize_job_title(title: str) -> str:
    """
    Normalizes job titles by removing common tags and normalizing variations.
    e.g. 'Sr. React Engineer (Remote) - 100% remote' -> 'senior react engineer'
    """
    norm = title.lower()
    # Remove parenthetical tags like (Remote), [Hybrid], (m/f/d)
    norm = re.sub(r"\([^\)]*\)", "", norm)
    norm = re.sub(r"\[[^\]]*\]", "", norm)
    # Standardize abbreviations
    norm = re.sub(r"\bsr\b\.?", "senior", norm)
    norm = re.sub(r"\bjr\b\.?", "junior", norm)
    norm = re.sub(r"\bsw\b\.?", "software", norm)
    norm = re.sub(r"\bdev\b\.?", "developer", norm)
    norm = re.sub(r"\beng\b\.?", "engineer", norm)
    # Remove common location/employment noise words
    for noise in ("remote", "hybrid", "onsite", "full time", "fulltime", "part time", "contract"):
        norm = re.sub(rf"\b{noise}\b", "", norm)
    return normalize_text(norm)


def compute_job_content_hash(
    company_name: str,
    title: str,
    location: str,
    external_id: Optional[str] = None,
    source_url: Optional[str] = None,
) -> str:
    """
    Computes a deterministic SHA-256 hash identifying a unique job.
    Uses normalized company domain, normalized title, and standardized location.
    """
    c_norm = extract_company_domain(company_name, source_url) or normalize_text(company_name)
    t_norm = normalize_job_title(title)
    l_norm = normalize_text(location)

    # Standardize common location terms
    l_norm = l_norm.replace("remote", "").replace("worldwide", "").strip()

    raw_signature = f"{c_norm}|{t_norm}|{l_norm}"
    if external_id:
        raw_signature += f"|{external_id.strip()}"

    return hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()


def are_jobs_duplicate(job_a: Any, job_b: Any) -> bool:
    """
    Determines whether two job listings refer to the same physical opportunity.
    Checks content_hash, external_id, or normalized company domain + title.
    """
    if getattr(job_a, "content_hash", None) and getattr(job_b, "content_hash", None):
        if job_a.content_hash == job_b.content_hash:
            return True

    ext_a = getattr(job_a, "external_id", None)
    ext_b = getattr(job_b, "external_id", None)
    if ext_a and ext_b and ext_a.strip() == ext_b.strip():
        return True

    title_a = normalize_job_title(getattr(job_a, "title", ""))
    title_b = normalize_job_title(getattr(job_b, "title", ""))
    if not title_a or not title_b:
        return False

    domain_a = extract_company_domain(
        getattr(job_a, "company_name", ""),
        getattr(job_a, "source_url", None),
    )
    domain_b = extract_company_domain(
        getattr(job_b, "company_name", ""),
        getattr(job_b, "source_url", None),
    )

    if domain_a and domain_b and domain_a == domain_b:
        # Check title similarity or substring match
        if title_a == title_b or title_a in title_b or title_b in title_a:
            return True

    return False
