import base64
import queue
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.wake_word_service import (
    DEBOUNCE_SECONDS,
    DEFAULT_THRESHOLD,
    DEFAULT_WAKE_MODEL,
    WakeWordService,
    WakeWordStatus,
    is_openwakeword_installed,
)


def test_wake_word_service_init_and_status():
    service = WakeWordService(model_name="alexa", threshold=0.55)
    status = service.get_status()

    assert isinstance(status, WakeWordStatus)
    assert status.model == "alexa"
    assert status.threshold == 0.55
    assert not status.enabled
    assert not status.running
    assert not status.ready
    assert status.last_detected_at is None


def test_wake_word_is_openwakeword_installed():
    installed = is_openwakeword_installed()
    assert isinstance(installed, bool)


def test_wake_word_feed_non_blocking_on_saturated_queue():
    service = WakeWordService()
    service._running = True  # simulate running without starting background thread

    # Queue maxsize is 60. Feed 100 frames to test saturation
    dummy_frame = np.zeros(1280, dtype=np.int16)
    start_time = time.monotonic()
    for _ in range(100):
        service.feed(dummy_frame)
    duration = time.monotonic() - start_time

    # Must be instantaneous (well under 50ms)
    assert duration < 0.2
    assert service._queue.qsize() <= 60


def test_wake_word_worker_triggers_on_high_score():
    callback_called = False

    def on_wake():
        nonlocal callback_called
        callback_called = True

    service = WakeWordService(model_name="alexa", threshold=0.5, on_wake=on_wake)

    mock_model = MagicMock()
    mock_model.predict.return_value = {"alexa": 0.88}

    with patch("openwakeword.model.Model", return_value=mock_model):
        started = service.start()
        assert started is True
        assert service.is_running is True

        # Feed frame to background thread
        frame = np.zeros(1280, dtype=np.int16)
        service.feed(frame)

        # Wait briefly for worker thread to process
        for _ in range(50):
            if callback_called:
                break
            time.sleep(0.02)

        service.stop()

    assert callback_called is True
    assert service.get_status().last_detected_at is not None
    assert service.is_running is False


def test_wake_word_debouncing_prevents_retrigger():
    trigger_count = 0

    def on_wake():
        nonlocal trigger_count
        trigger_count += 1

    service = WakeWordService(model_name="alexa", threshold=0.5, on_wake=on_wake)

    mock_model = MagicMock()
    mock_model.predict.return_value = {"alexa": 0.99}

    with patch("openwakeword.model.Model", return_value=mock_model):
        service.start()

        # Feed multiple frames rapidly
        for _ in range(5):
            service.feed(np.zeros(1280, dtype=np.int16))
            time.sleep(0.01)

        time.sleep(0.1)
        service.stop()

    # Even though 5 consecutive frames had score >= 0.5, debounce should restrict to 1
    assert trigger_count == 1


def test_wake_word_drain_clears_queue():
    service = WakeWordService()
    for i in range(10):
        service._queue.put(i)
    assert service._queue.qsize() == 10

    service._drain_queue()
    assert service._queue.empty()


def test_wake_word_api_routes(tmp_path):
    app = create_app(data_dir=tmp_path, api_token="test-token")
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    # 1. GET /api/v1/wake/status
    res = client.get("/api/v1/wake/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["model"] in ("hey_jarvis", "alexa")
    assert data["enabled"] is False

    # 2. POST /api/v1/wake/toggle (disable/reconfigure)
    res = client.post(
        "/api/v1/wake/toggle",
        headers=headers,
        json={"enabled": False, "model": "hey_jarvis", "threshold": 0.65},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["model"] == "hey_jarvis"
    assert data["threshold"] == 0.65
    assert data["enabled"] is False

    # 3. POST /api/v1/wake/feed (valid audio)
    raw_audio = b"\x00\x00" * 640
    b64_audio = base64.b64encode(raw_audio).decode("ascii")
    res = client.post(
        "/api/v1/wake/feed",
        headers=headers,
        json={"audio_base64": b64_audio},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["accepted"] is True
    assert data["bytes_fed"] == len(raw_audio)

    # 4. POST /api/v1/wake/feed (invalid base64 payload)
    res = client.post(
        "/api/v1/wake/feed",
        headers=headers,
        json={"audio_base64": "!!!not_base64"},
    )
    assert res.status_code == 400

    # 5. POST /api/v1/wake/install
    with patch("app.services.wake_word_service.install_and_download", return_value=(True, "Wake word installed")):
        res = client.post("/api/v1/wake/install", headers=headers)
        assert res.status_code == 200
        assert res.json()["ok"] is True


def test_wake_word_detector_drop_in_adapter():
    from app.services.wake_word_service import WakeWordDetector

    detected = False

    def on_detect():
        nonlocal detected
        detected = True

    detector = WakeWordDetector(on_detect=on_detect)
    assert detector.ready is False
    detector.feed(np.zeros(1280, dtype=np.int16))
    detector.stop()
    assert detector.ready is False

