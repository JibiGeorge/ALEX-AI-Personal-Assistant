import asyncio
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.actions import ActionExecutor, ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.media import register_media_actions
from app.main import create_app
from app.services.media_service import MediaService, MediaState


def test_media_service_init_and_status():
    service = MediaService()
    status = service.get_status()

    assert isinstance(status, MediaState)
    assert not status.active
    assert not status.is_playing
    assert status.source == ""
    assert status.source_type == "none"


def test_resolve_local_file(tmp_path):
    clip = tmp_path / "sample.mp4"
    clip.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    service = MediaService()
    url, audio_url, title, source_type, error = service.resolve(str(clip))

    assert error is None
    assert source_type == "local"
    assert title == "sample.mp4"
    assert url.startswith("file://")
    assert audio_url == ""


def test_resolve_direct_url():
    service = MediaService()
    raw_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
    url, audio_url, title, source_type, error = service.resolve(raw_url)

    assert error is None
    assert source_type == "direct"
    assert url == raw_url
    assert "BigBuckBunny.mp4" in title


def test_resolve_youtube_with_mock():
    service = MediaService()

    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = {
        "title": "Mock Dune Trailer",
        "formats": [
            {
                "protocol": "https",
                "url": "https://googlevideo.com/videoplayback?id=123",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "height": 720,
                "tbr": 1200,
            }
        ],
    }

    with patch("yt_dlp.YoutubeDL", return_value=MagicMock(__enter__=MagicMock(return_value=mock_ydl_instance))):
        url, audio_url, title, source_type, error = service.resolve("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert error is None
        assert source_type == "youtube"
        assert title == "Mock Dune Trailer"
        assert "videoplayback" in url


def test_media_controls_lifecycle(tmp_path):
    clip = tmp_path / "test.mp4"
    clip.write_bytes(b"\x00")

    service = MediaService()

    # 1. Play
    state = service.play(str(clip), title="Test Video", muted=True)
    assert state.active is True
    assert state.is_playing is True
    assert state.is_muted is True
    assert state.title == "Test Video"

    # 2. Pause
    state = service.pause()
    assert state.active is True
    assert state.is_playing is False

    # 3. Resume
    state = service.resume()
    assert state.active is True
    assert state.is_playing is True

    # 4. Set Muted
    state = service.set_muted(False)
    assert state.is_muted is False

    # 5. Stop
    state = service.stop()
    assert state.active is False
    assert state.is_playing is False
    assert state.source == ""


def test_media_actions_registered_and_executed(tmp_path):
    import asyncio

    async def _run():
        registry = ActionRegistry()
        service = MediaService()
        register_media_actions(registry, service)
        executor = ActionExecutor(registry)

        clip = tmp_path / "movie.mp4"
        clip.write_bytes(b"\x00")

        # 1. media.play
        res = await executor.execute("media.play", {"source": str(clip), "title": "My Movie"})
        assert res.status == "success"
        assert "Playing" in res.message
        assert res.data["active"] is True

        # 2. media.status
        res = await executor.execute("media.status", {})
        assert res.status == "success"
        assert res.data["is_playing"] is True

        # 3. media.pause
        res = await executor.execute("media.pause", {})
        assert res.status == "success"
        assert res.data["is_playing"] is False

        # 4. media.resume
        res = await executor.execute("media.resume", {})
        assert res.status == "success"
        assert res.data["is_playing"] is True

        # 5. media.set_muted
        res = await executor.execute("media.set_muted", {"muted": False})
        assert res.status == "success"
        assert res.data["is_muted"] is False

        # 6. media.stop
        res = await executor.execute("media.stop", {})
        assert res.status == "success"
        assert res.data["active"] is False

    asyncio.run(_run())


def test_media_api_routes(tmp_path):
    app = create_app(data_dir=tmp_path, api_token="test-token")
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    clip = tmp_path / "api_clip.mp4"
    clip.write_bytes(b"\x00")

    # 1. GET /api/v1/media/status
    res = client.get("/api/v1/media/status", headers=headers)
    assert res.status_code == 200
    assert res.json()["active"] is False

    # 2. POST /api/v1/media/resolve
    res = client.post(
        "/api/v1/media/resolve",
        headers=headers,
        json={"source": str(clip)},
    )
    assert res.status_code == 200
    assert res.json()["source_type"] == "local"

    # 3. POST /api/v1/media/control (play)
    res = client.post(
        "/api/v1/media/control",
        headers=headers,
        json={"action": "play", "source": str(clip), "title": "API Clip"},
    )
    assert res.status_code == 200
    assert res.json()["active"] is True
    assert res.json()["title"] == "API Clip"

    # 4. POST /api/v1/media/control (stop)
    res = client.post(
        "/api/v1/media/control",
        headers=headers,
        json={"action": "stop"},
    )
    assert res.status_code == 200
    assert res.json()["active"] is False


def test_media_transcript_and_summarize_without_playback():
    media_service = MediaService()
    mock_youtube = MagicMock()
    mock_youtube.execute.side_effect = [
        MagicMock(status=ToolOutcome.DONE, message="Video transcript text", data={"characters": 21}, error=None),
        MagicMock(status=ToolOutcome.DONE, message="Video summary text", data={"summary": "..."}, error=None),
    ]
    media_service.set_youtube_transcript_service(mock_youtube)

    registry = ActionRegistry()
    register_media_actions(registry, media_service)
    executor = ActionExecutor(registry)

    async def _run():
        # Verify media is initially inactive
        assert media_service.get_status().active is False

        # 1. media.transcript
        res_t = await executor.execute("media.transcript", {"url_or_id": "dQw4w9WgXcQ"})
        assert res_t.status == "success"
        assert res_t.message == "Video transcript text"
        # Crucial check: media playback remains completely inactive!
        assert media_service.get_status().active is False
        assert media_service.get_status().is_playing is False

        # 2. media.summarize_video
        res_s = await executor.execute("media.summarize_video", {"url_or_id": "dQw4w9WgXcQ"})
        assert res_s.status == "success"
        assert res_s.message == "Video summary text"
        # Crucial check: media playback remains completely inactive!
        assert media_service.get_status().active is False
        assert media_service.get_status().is_playing is False

    asyncio.run(_run())
