"""
Unit tests for app.core.gemini module.
Verifies ladders, timeouts, error classification, cooldown tracking, and JSON parsing.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.core import gemini


def test_gemini_ladders_definition():
    assert gemini.FAST == "fast"
    assert gemini.SMART == "smart"
    assert gemini.SEARCH == "search"
    assert gemini.LIVE == "live"

    fast_ladder = gemini._LADDERS[gemini.FAST]
    assert fast_ladder[0] == gemini.LIVE
    assert "gemini-2.5-flash-lite" in fast_ladder
    assert "gemini-3.5-flash-lite" in fast_ladder

    smart_ladder = gemini._LADDERS[gemini.SMART]
    assert smart_ladder[0] == gemini.LIVE
    assert "gemini-2.5-flash" in smart_ladder
    assert "gemini-3.5-flash" in smart_ladder

    search_ladder = gemini._LADDERS[gemini.SEARCH]
    # Search ladder MUST NOT contain LIVE because Live doesn't support grounding metadata
    assert gemini.LIVE not in search_ladder
    assert search_ladder[0] == "gemini-2.5-flash"
    assert "gemini-3.5-flash" in search_ladder


def test_live_models_and_failure_cooldown():
    assert "models/gemini-3.1-flash-live-preview" in gemini.LIVE_MODELS
    assert "models/gemini-2.5-flash-native-audio-preview-12-2025" in gemini.LIVE_MODELS

    # Test error classifications
    assert gemini.is_quota_error("429 Resource Exhausted")
    assert gemini.is_quota_error("RESOURCE_EXHAUSTED: quota exceeded")
    assert not gemini.is_quota_error("500 Internal error")

    assert gemini.is_unavailable_error("503 Service Unavailable")
    assert gemini.is_unavailable_error("504 Gateway Timeout")
    assert gemini.is_unavailable_error("Deadline_Exceeded: timeout")

    assert gemini.is_gone_error("404 Not Found")
    assert gemini.is_gone_error("Model is not supported for this project")
    assert gemini.is_gone_error("403 Permission Denied")


def test_as_json_parsing_and_stripping():
    # Plain JSON
    assert gemini.parse_json('{"status": "ok"}') == {"status": "ok"}

    # Fenced JSON with code blocks and text
    fenced_output = """Here is the result:
```json
{
    "count": 42,
    "active": true
}
```
Done."""
    parsed = gemini.parse_json(fenced_output)
    assert parsed == {"count": 42, "active": True}

    # Array extraction
    fenced_array = "```[1, 2, 3]```"
    assert gemini.parse_json(fenced_array) == [1, 2, 3]

    # Non-json fallback
    assert gemini.parse_json("Invalid payload", default={"error": True}) == {"error": True}


def test_as_json_delegates_to_text_and_parses():
    with patch("app.core.gemini.text", return_value='```json\n{"reply": 1}\n```'):
        res = gemini.as_json("dummy prompt")
        assert res == {"reply": 1}


def test_text_fallback_on_empty():
    with patch("app.core.gemini.call", return_value=None):
        res = gemini.text("test prompt", default="fallback")
        assert res == "fallback"


def test_client_enforces_minimum_deadline():
    from google.genai import types as gtypes
    with patch("app.core.gemini.api_key", return_value="dummy-key"):
        with patch("google.genai.Client") as mock_client:
            gemini.client(timeout_ms=5_000)
            assert mock_client.called
            args, kwargs = mock_client.call_args
            http_options = kwargs.get("http_options")
            assert isinstance(http_options, gtypes.HttpOptions)
            assert http_options.timeout == gemini.MIN_TIMEOUT_MS
