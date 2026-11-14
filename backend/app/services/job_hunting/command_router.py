"""
Natural Language Command Router for ALEX Job Hunting Module.
Parses natural language text and voice transcripts into registered job actions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


def clean_voice_input(text: str) -> str:
    """Strips wake words, leading punctuation, and normalizes whitespace."""
    if not text:
        return ""
    cleaned = text.strip()
    # Strip common assistant wake prefixes
    cleaned = re.sub(
        r"^(?:alex|hey alex|ok alex|alexa|computer|jarvis)[,\s:]+\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    # Strip terminal punctuation
    cleaned = re.sub(r"[.!?]+$", "", cleaned).strip()
    return cleaned


def route_job_command(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Parses a natural language voice or chat prompt into a registered job action.

    Returns:
        (action_id, parameters_dict) if recognized, or None if not a job command.
    """
    cleaned = clean_voice_input(text)
    if not cleaned:
        return None

    lower = cleaned.lower()

    # 1. Compare / Match with resume
    # "Compare this job with my resume." / "Match this job against my resume."
    if re.search(
        r"\b(?:compare|match|evaluate|check)\s+(?:this\s+)?(?:job|role|posting)?\s*(?:with|against|to)\s+(?:my\s+)?(?:resume|profile|cv)\b",
        lower,
    ) or lower in ("compare this job with my resume", "match this job against my resume", "compare with resume"):
        return ("job_match_resume", {})

    # 2. Prepare application
    # "Prepare my application." / "Tailor my resume for this job."
    if re.search(
        r"\b(?:prepare|tailor|draft|create|generate)\s+(?:my\s+)?(?:application|package|resume and cover letter|tailored resume)\b",
        lower,
    ) or lower in ("prepare my application", "prepare application", "tailor my resume"):
        return ("job_prepare_application", {})

    # 3. Pending approvals
    # "Show my pending approvals." / "What applications need my approval?"
    if re.search(
        r"\b(?:show|list|view|check|get|what)\s+(?:are\s+)?(?:my\s+)?(?:pending\s+)?approvals\b",
        lower,
    ) or "need my approval" in lower or lower in ("show my pending approvals", "list approvals", "pending approvals"):
        return ("job_list_approvals", {})

    # 4. Interviews
    # "Show my interviews." / "List my upcoming interviews."
    if re.search(
        r"\b(?:show|list|view|check|get)\s+(?:my\s+)?(?:all\s+)?(?:upcoming\s+|scheduled\s+)?interviews\b",
        lower,
    ) or lower in ("show my interviews", "list my interviews", "interviews", "my interviews"):
        return ("job_list_interviews", {})

    # 5. Track applications
    # "Show my pending applications." / "Track my applications."
    if re.search(
        r"\b(?:show|list|view|track|check|get)\s+(?:my\s+)?(?:all\s+)?(?:pending\s+|active\s+)?applications\b",
        lower,
    ) or lower in ("show my pending applications", "track my applications", "my applications"):
        # If user explicitly asked for "pending applications", filter by status if appropriate or default
        status_filter = "applied" if "applied" in lower else None
        return ("job_track_application", {"status": status_filter} if status_filter else {})

    # 6. Analyse job posting / URL
    # "Analyse this LinkedIn job." / "Analyse this job: https://..."
    if re.search(
        r"\b(?:analyse|analyze|extract|inspect)\s+(?:this\s+)?(?:linkedin\s+)?(?:job|posting|listing|url|link)\b",
        lower,
    ) or lower.startswith("analyse this") or lower.startswith("analyze this"):
        # Extract any embedded URL
        url_match = re.search(r"https?://\S+", cleaned)
        url = url_match.group(0) if url_match else None
        return ("job_analyse", {"url": url} if url else {})

    # 7. Open / Access Job Hunting & Career Radar
    if (
        re.search(
            r"\b(?:open|show|launch|start|display|view|access)\s+(?:the\s+)?(?:job\s+hunting|career\s+radar|career\s+hub|job\s+search)\b",
            lower,
        )
        or lower in ("job hunting", "career radar", "career hub", "open job hunting", "open job hunting on hud", "job hunting on hud")
    ):
        return ("job_search", {"query": "Software Developer"})

    # 8. Job Search / Discover
    # "Alex, find full-stack developer jobs."
    # "Find remote React jobs worldwide."
    # "Search for software developer roles."
    search_match = re.search(
        r"^(?:find|search(?: for)?|discover|look for)\s+(.+?)(?:\s+jobs|\s+roles|\s+openings|\s+positions)?$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if search_match or any(k in lower for k in ("developer jobs", "react jobs", "engineer jobs", "software jobs")):
        raw_query = search_match.group(1).strip() if search_match else cleaned

        # Detect modalities (e.g. remote, hybrid)
        modalities = []
        if re.search(r"\bremote\b", raw_query, flags=re.IGNORECASE):
            modalities.append("remote")
            raw_query = re.sub(r"\bremote\b", "", raw_query, flags=re.IGNORECASE).strip()
        if re.search(r"\bhybrid\b", raw_query, flags=re.IGNORECASE):
            modalities.append("hybrid")
            raw_query = re.sub(r"\bhybrid\b", "", raw_query, flags=re.IGNORECASE).strip()

        # Detect location (e.g. worldwide, remote, us)
        location = None
        loc_match = re.search(r"\b(?:in|worldwide|globally|in the us|in europe)\b.*$", raw_query, flags=re.IGNORECASE)
        if loc_match:
            loc_str = loc_match.group(0).strip()
            if re.search(r"\bworldwide\b", loc_str, flags=re.IGNORECASE):
                location = "Worldwide"
            elif re.search(r"\bglobally\b", loc_str, flags=re.IGNORECASE):
                location = "Worldwide"
            else:
                location = re.sub(r"^(?:in|at)\s+", "", loc_str, flags=re.IGNORECASE).strip().title()
            raw_query = raw_query[:loc_match.start()].strip()

        # Clean query
        query = re.sub(r"\b(?:jobs|roles|openings|positions|opportunities)\b", "", raw_query, flags=re.IGNORECASE).strip()
        query = re.sub(r"\s+", " ", query).strip()

        if not query:
            query = "Software Developer"

        params: Dict[str, Any] = {"query": query}
        if location:
            params["location"] = location
        if modalities:
            params["modalities"] = modalities

        return ("job_search", params)

    return None

