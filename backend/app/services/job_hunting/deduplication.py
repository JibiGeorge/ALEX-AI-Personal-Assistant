"""
Job Deduplication Engine.
Normalizes company name, title, and location to compute deterministic content hashes.
Prevents duplicate listings across multiple queries or ingest channels.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional


def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    # Lowercase, replace hyphens and underscores with spaces, strip punctuation and extra whitespace
    cleaned = text.lower().strip()
    cleaned = cleaned.replace("-", " ").replace("_", " ")
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return re.sub(r"\s+", " ", cleaned)


def compute_job_content_hash(
    company_name: str,
    title: str,
    location: str,
    external_id: Optional[str] = None,
) -> str:
    """
    Computes a deterministic SHA-256 hash identifying a unique job.
    If external_id is present and company is consistent, it folds it in;
    otherwise relies on normalized (company, title, location).
    """
    c_norm = normalize_text(company_name)
    t_norm = normalize_text(title)
    l_norm = normalize_text(location)

    # Standardize common location terms
    l_norm = l_norm.replace("remote", "").replace("worldwide", "").strip()

    raw_signature = f"{c_norm}|{t_norm}|{l_norm}"
    if external_id:
        raw_signature += f"|{external_id.strip()}"

    return hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()
