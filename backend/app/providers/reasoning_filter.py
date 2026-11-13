"""
Reasoning Filter for AI Provider Streaming.

Strictly enforces the Private Reasoning Data Policy:
Intercepts chunk streams and strips all <think>, <thinking>, <reasoning>, <thought>
reasoning blocks across token boundaries so raw internal reasoning is never exposed
to the UI, TTS, or logs.
"""

from __future__ import annotations

from typing import Optional, Tuple

OPEN_TAGS = ("<think>", "<thinking>", "<reasoning>", "<thought>")
CLOSE_TAGS = ("</think>", "</thinking>", "</reasoning>", "</thought>")
MAX_TAG_LEN = max(len(t) for t in OPEN_TAGS + CLOSE_TAGS)


class ReasoningFilter:
    """Stateful stream filter that removes internal reasoning tags and all content inside them."""

    def __init__(self) -> None:
        self._in_think: bool = False
        self._buffer: str = ""

    def _find_earliest_tag(self, text_lower: str, start_pos: int, tags: Tuple[str, ...]) -> Tuple[int, str]:
        earliest_idx = -1
        found_tag = ""
        for tag in tags:
            idx = text_lower.find(tag, start_pos)
            if idx != -1 and (earliest_idx == -1 or idx < earliest_idx):
                earliest_idx = idx
                found_tag = tag
        return earliest_idx, found_tag

    def filter_chunk(self, chunk_text: str) -> str:
        """Process incoming chunk and return visible text with think blocks stripped."""
        if not chunk_text:
            return ""

        text = self._buffer + chunk_text
        self._buffer = ""
        text_lower = text.lower()
        output: list[str] = []
        i = 0
        n = len(text)

        while i < n:
            if not self._in_think:
                tag_idx, found_tag = self._find_earliest_tag(text_lower, i, OPEN_TAGS)
                if tag_idx == -1:
                    # Check for partial opening tag at the tail
                    partial_match = False
                    for length in range(1, min(MAX_TAG_LEN, n - i + 1)):
                        suffix = text_lower[n - length:]
                        if any(t.startswith(suffix) for t in OPEN_TAGS):
                            output.append(text[i:n - length])
                            self._buffer = text[n - length:]
                            partial_match = True
                            break
                    if not partial_match:
                        output.append(text[i:])
                    break
                else:
                    output.append(text[i:tag_idx])
                    self._in_think = True
                    i = tag_idx + len(found_tag)
            else:
                tag_idx, found_tag = self._find_earliest_tag(text_lower, i, CLOSE_TAGS)
                if tag_idx == -1:
                    # Check for partial closing tag at the tail
                    partial_match = False
                    for length in range(1, min(MAX_TAG_LEN, n - i + 1)):
                        suffix = text_lower[n - length:]
                        if any(t.startswith(suffix) for t in CLOSE_TAGS):
                            self._buffer = text[n - length:]
                            partial_match = True
                            break
                    break
                else:
                    self._in_think = False
                    i = tag_idx + len(found_tag)

        return "".join(output)

    def flush(self) -> str:
        """Flush any pending buffered text that was not a think tag."""
        if self._in_think:
            self._buffer = ""
            return ""
        flushed = self._buffer
        self._buffer = ""
        return flushed


