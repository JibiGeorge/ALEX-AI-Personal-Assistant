"""
Unit tests for YouTube Transcript Extractor & Video Summarizer Service (TASK-GAP-09 / GAP-09).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.youtube_transcript import register_youtube_actions
from app.schemas.youtube_transcript import YouTubeTranscriptParameters
from app.services.settings_service import SettingsService
from app.services.youtube_transcript_service import YouTubeTranscriptService


@pytest.fixture
def mock_settings(tmp_path: Path) -> SettingsService:
    store = MagicMock()
    settings = SettingsService(store)
    settings.get_api_key_for_service = MagicMock(return_value="test-gemini-key")
    return settings


@pytest.fixture
def youtube_service(mock_settings: SettingsService) -> YouTubeTranscriptService:
    return YouTubeTranscriptService(mock_settings)


# =============================================================================
# 1. Video ID Extraction Tests
# =============================================================================

def test_extract_video_id_various_formats(youtube_service: YouTubeTranscriptService):
    test_cases = [
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("http://youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]
    for url_input, expected_id in test_cases:
        assert youtube_service.extract_video_id(url_input) == expected_id

    assert youtube_service.extract_video_id(None) is None
    assert youtube_service.extract_video_id("") is None
    assert youtube_service.extract_video_id("not-a-valid-youtube-url") is None


# =============================================================================
# 2. Search Scraping Tests
# =============================================================================

def test_scrape_first_video_url_success(youtube_service: YouTubeTranscriptService):
    mock_html = """
    <html>
      "videoId":"shorts12345" ... /shorts/shorts12345
      "videoId":"valid123456"
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.text = mock_html

    with patch("httpx.Client.get", return_value=mock_resp):
        url = youtube_service.scrape_first_video_url("quantum computing")
        assert url == "https://www.youtube.com/watch?v=valid123456"


def test_scrape_first_video_url_empty_or_error(youtube_service: YouTubeTranscriptService):
    assert youtube_service.scrape_first_video_url("") is None
    with patch("httpx.Client.get", side_effect=Exception("Network error")):
        assert youtube_service.scrape_first_video_url("test") is None


# =============================================================================
# 3. Video Metadata Scraping Tests
# =============================================================================

def test_scrape_video_info(youtube_service: YouTubeTranscriptService):
    mock_html = """
    "title":{"runs":[{"text":"Awesome Video"}]}
    "ownerChannelName":"Science Channel"
    "viewCount":"1250000"
    "lengthSeconds":"365"
    "label":"45,000 likes"
    """
    mock_resp = MagicMock()
    mock_resp.text = mock_html

    with patch("httpx.Client.get", return_value=mock_resp):
        info = youtube_service.scrape_video_info("dQw4w9WgXcQ")
        assert info["video_id"] == "dQw4w9WgXcQ"
        assert info["title"] == "Awesome Video"
        assert info["channel"] == "Science Channel"
        assert info["views"] == "1,250,000"
        assert info["duration"] == "6:05"
        assert info["likes"] == "45,000 likes"


# =============================================================================
# 4. Trending Scraping Tests
# =============================================================================

def test_scrape_trending(youtube_service: YouTubeTranscriptService):
    mock_html = """
    "title":{"runs":[{"text":"Trending 1 - Major News"}]}
    "ownerText":{"runs":[{"text":"News Channel"}
    "title":{"runs":[{"text":"Trending 2 - Music Video"}]}
    "ownerText":{"runs":[{"text":"Vevo Channel"}
    """
    mock_resp = MagicMock()
    mock_resp.text = mock_html

    with patch("httpx.Client.get", return_value=mock_resp):
        trending = youtube_service.scrape_trending(region="US", max_results=2)
        assert len(trending) == 2
        assert trending[0]["rank"] == 1
        assert trending[0]["title"] == "Trending 1 - Major News"
        assert trending[0]["channel"] == "News Channel"
        assert trending[1]["rank"] == 2


# =============================================================================
# 5. Transcript Fetching Tests
# =============================================================================

def test_get_transcript_success(youtube_service: YouTubeTranscriptService):
    mock_transcript_obj = MagicMock()
    mock_transcript_obj.fetch.return_value = [
        {"text": "Welcome to the video."},
        {"text": "Today we discuss AI agents."},
    ]

    mock_transcript_list = MagicMock()
    mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript_obj

    mock_api = MagicMock()
    mock_api.list_transcripts.return_value = mock_transcript_list

    with patch("app.services.youtube_transcript_service.find_spec", return_value=MagicMock()):
        with patch.dict("sys.modules", {"youtube_transcript_api": MagicMock(YouTubeTranscriptApi=mock_api)}):
            text = youtube_service.get_transcript("dQw4w9WgXcQ", lang="en")
            assert text == "Welcome to the video. Today we discuss AI agents."


def test_get_transcript_auto_generated_fallback(youtube_service: YouTubeTranscriptService):
    mock_transcript_obj = MagicMock()
    mock_transcript_obj.fetch.return_value = [
        SimpleNamespace(text="Auto generated captions here.")
    ]

    mock_transcript_list = MagicMock()
    mock_transcript_list.find_manually_created_transcript.side_effect = Exception("No manual")
    mock_transcript_list.find_generated_transcript.return_value = mock_transcript_obj

    mock_api = MagicMock()
    mock_api.list_transcripts.return_value = mock_transcript_list

    with patch("app.services.youtube_transcript_service.find_spec", return_value=MagicMock()):
        with patch.dict("sys.modules", {"youtube_transcript_api": MagicMock(YouTubeTranscriptApi=mock_api)}):
            text = youtube_service.get_transcript("dQw4w9WgXcQ", lang="en")
            assert text == "Auto generated captions here."


def test_get_transcript_when_not_installed(youtube_service: YouTubeTranscriptService):
    with patch("app.services.youtube_transcript_service.find_spec", return_value=None):
        assert youtube_service.get_transcript("dQw4w9WgXcQ") is None


# =============================================================================
# 6. Summarization Tests
# =============================================================================

def test_summarize_with_gemini(youtube_service: YouTubeTranscriptService):
    mock_response = MagicMock()
    mock_response.text = "This video explains neural nets.\n- Point 1\n- Point 2"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.services.youtube_transcript_service.genai.Client", return_value=mock_client):
        summary = youtube_service.summarize("Transcript content...", "https://youtube.com/watch?v=123")
        assert "neural nets" in summary


def test_summarize_without_api_key(youtube_service: YouTubeTranscriptService):
    youtube_service._settings.get_api_key_for_service = MagicMock(return_value=None)
    summary = youtube_service.summarize("Transcript text " * 10, "https://youtube.com/watch?v=123")
    assert "Gemini API key is not configured" in summary


# =============================================================================
# 7. Summary Saving Tests
# =============================================================================

def test_save_summary(youtube_service: YouTubeTranscriptService, tmp_path: Path):
    target_file = tmp_path / "custom_summary.txt"
    saved = youtube_service.save_summary(
        summary="Summary of video",
        video_url="https://youtube.com/watch?v=123",
        output_path=str(target_file),
    )
    assert saved == str(target_file)
    assert target_file.exists()
    content = target_file.read_text(encoding="utf-8")
    assert "Alex — YouTube Summary" in content
    assert "Summary of video" in content


# =============================================================================
# 8. Action Execution Tests (Five-Word Contract)
# =============================================================================

def test_execute_trending(youtube_service: YouTubeTranscriptService):
    with patch.object(
        youtube_service,
        "scrape_trending",
        return_value=[{"rank": 1, "title": "Top Video", "channel": "Channel A"}],
    ):
        params = YouTubeTranscriptParameters(action="trending", region="US")
        res = youtube_service.execute(params)
        assert res.status == ToolOutcome.DONE
        assert "Top trending videos in US" in res.message
        assert res.data["trending"][0]["title"] == "Top Video"


def test_execute_info(youtube_service: YouTubeTranscriptService):
    with patch.object(
        youtube_service,
        "scrape_video_info",
        return_value={"title": "Amazing Video", "channel": "Top Creator", "views": "500K"},
    ):
        params = YouTubeTranscriptParameters(action="info", url_or_id="dQw4w9WgXcQ")
        res = youtube_service.execute(params)
        assert res.status == ToolOutcome.DONE
        assert "Amazing Video" in res.message


def test_execute_transcript_unverified_if_missing_library(youtube_service: YouTubeTranscriptService):
    with patch("app.services.youtube_transcript_service.find_spec", return_value=None):
        params = YouTubeTranscriptParameters(action="transcript", url_or_id="dQw4w9WgXcQ")
        res = youtube_service.execute(params)
        assert res.status == ToolOutcome.UNVERIFIED
        assert "youtube-transcript-api is not installed" in res.message


def test_execute_transcript_done(youtube_service: YouTubeTranscriptService):
    with patch("app.services.youtube_transcript_service.find_spec", return_value=MagicMock()):
        with patch.object(youtube_service, "get_transcript", return_value="Full transcript here."):
            params = YouTubeTranscriptParameters(action="transcript", url_or_id="dQw4w9WgXcQ")
            res = youtube_service.execute(params)
            assert res.status == ToolOutcome.DONE
            assert res.message == "Full transcript here."
            assert res.data["characters"] == len("Full transcript here.")


def test_execute_summarize_done_and_save(youtube_service: YouTubeTranscriptService, tmp_path: Path):
    out_file = tmp_path / "test_saved_summary.txt"
    with patch("app.services.youtube_transcript_service.find_spec", return_value=MagicMock()):
        with patch.object(youtube_service, "get_transcript", return_value="Transcript text"):
            with patch.object(youtube_service, "summarize", return_value="Clear video summary."):
                params = YouTubeTranscriptParameters(
                    action="summarize",
                    url_or_id="https://youtu.be/dQw4w9WgXcQ",
                    save_to_disk=True,
                    output_path=str(out_file),
                )
                res = youtube_service.execute(params)
                assert res.status == ToolOutcome.DONE
                assert "Clear video summary." in res.message
                assert str(out_file) in res.message
                assert out_file.exists()


def test_execute_play(youtube_service: YouTubeTranscriptService):
    with patch.object(youtube_service, "play_video") as mock_play:
        params = YouTubeTranscriptParameters(action="play", url_or_id="dQw4w9WgXcQ")
        res = youtube_service.execute(params)
        assert res.status == ToolOutcome.DONE
        assert "Playing:" in res.message
        mock_play.assert_called_once_with("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_execute_invalid_action(youtube_service: YouTubeTranscriptService):
    params = YouTubeTranscriptParameters(action="non_existent_action", url_or_id="dQw4w9WgXcQ")
    res = youtube_service.execute(params)
    assert res.status == ToolOutcome.FAILED
    assert "Unknown YouTube action" in res.message


# =============================================================================
# 9. ActionRegistry Registration Test
# =============================================================================

def test_action_registry_registration(youtube_service: YouTubeTranscriptService):
    registry = ActionRegistry()
    register_youtube_actions(registry, youtube_service)

    definitions = {d.action_id: d for d in registry.list()}
    assert "youtube.transcript" in definitions
    definition = definitions["youtube.transcript"]
    assert definition.category == "search"
    assert definition.requires_confirmation is False
    assert definition.timeout_seconds == 60.0
    assert definition.parameters == YouTubeTranscriptParameters
