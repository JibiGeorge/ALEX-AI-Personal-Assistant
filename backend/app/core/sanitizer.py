"""
Prompt Injection Boundary Defanging & Sanitization Utility (TASK-P7-01 / CAT-23).

Enforces hard data/instruction separation by defanging XML delimiters (specifically </DATA>)
and wrapping all untrusted external content (web searches, uploaded/parsed documents, scraped files)
in standardized passive <DATA> envelopes.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Matches opening or closing <DATA ...> tags with arbitrary whitespace or attributes
_DATA_TAG_REGEX = re.compile(r"<\s*(/?)\s*data(\s*|\s+[^>]*)>", flags=re.IGNORECASE)

# Matches closing document or system tag delimiters commonly used in jailbreak attempts
_DELIMITER_TAG_REGEX = re.compile(
    r"<\s*(/?)\s*(document|system|instruction|prompt)(\s*|\s+[^>]*)>",
    flags=re.IGNORECASE,
)

# Common prompt injection override signatures
_INJECTION_SIGNATURE_REGEX = re.compile(
    r"(?:\bignore\b|\bdisregard\b|\bforget\b)\s+(?:all\s+)?(?:previous\s+)?(?:instructions|prompts|rules|directives)",
    flags=re.IGNORECASE,
)


def defang_data_tags(text: str) -> str:
    """Defangs <DATA> and </DATA> tags inside untrusted text to prevent boundary breakouts.

    Converts literal < and > to safe HTML entities &lt; and &gt; for all data delimiters.
    """
    if not text:
        return ""

    # Check and log injection attempt telemetry
    if _DATA_TAG_REGEX.search(text) or _INJECTION_SIGNATURE_REGEX.search(text):
        logger.warning("Detected potential prompt injection attempt in untrusted content payload.")

    # Defang <DATA> and </DATA>
    def _replace_data(match: re.Match[str]) -> str:
        slash = match.group(1) or ""
        attrs = match.group(2) or ""
        return f"&lt;{slash}data{attrs}&gt;"

    defanged = _DATA_TAG_REGEX.sub(_replace_data, text)

    # Defang other structural delimiter tags (<system>, </document>, etc.)
    def _replace_delims(match: re.Match[str]) -> str:
        slash = match.group(1) or ""
        tag = match.group(2) or ""
        attrs = match.group(3) or ""
        return f"&lt;{slash}{tag}{attrs}&gt;"

    return _DELIMITER_TAG_REGEX.sub(_replace_delims, defanged)


def wrap_untrusted_data(text: str, source: str = "untrusted_source") -> str:
    """Defangs untrusted text and encloses it in a strict passive <DATA> XML envelope."""
    clean_text = defang_data_tags(text)
    clean_source = source.replace('"', "").replace("'", "")
    return f'<DATA source="{clean_source}">\n{clean_text}\n</DATA>'


def sanitize_search_content(answer: str, sources: Optional[List[Dict[str, Any]]] = None) -> str:
    """Sanitizes grounded search answers and source snippets."""
    clean_answer = defang_data_tags(answer)
    return wrap_untrusted_data(clean_answer, source="web_search")


def sanitize_document_text(text: str, filename: str = "document") -> str:
    """Sanitizes text extracted from parsed documents (PDF, DOCX, XLSX, PPTX)."""
    clean_text = defang_data_tags(text)
    return wrap_untrusted_data(clean_text, source=f"file:{filename}")

