"""
Unit tests for VisionService and vision.capture action (TASK-GAP-07 / GAP-07).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.vision import register_vision_actions
from app.schemas.vision import VisionCaptureParameters
from app.services.vision_service import VisionService


def test_vision_capture_camera_missing_cv2():
    service = VisionService()
    with patch("app.services.vision_service.find_spec", return_value=None):
        params = VisionCaptureParameters(source="camera")
        res = service.execute(params)

        assert res.status == ToolOutcome.UNVERIFIED
        assert res.data.get("cv2_required") is True
        assert "pip install opencv-python" in res.message


def test_vision_capture_camera_mock_success(tmp_path):
    import numpy as np

    service = VisionService(output_dir=tmp_path)
    mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, mock_frame)

    mock_cv2 = MagicMock()
    mock_cv2.VideoCapture.return_value = mock_cap
    mock_cv2.imencode.return_value = (True, MagicMock(tobytes=lambda: b"\xff\xd8\xff\xe0"))

    with patch("app.services.vision_service.find_spec", return_value=MagicMock()), \
         patch.dict("sys.modules", {"cv2": mock_cv2, "numpy": np}):

        target_file = tmp_path / "webcam_test.jpg"
        params = VisionCaptureParameters(
            source="camera",
            camera_index=0,
            save_to_disk=True,
            output_path=str(target_file),
            include_base64=True,
        )
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert "webcam frame" in res.message.lower()
        assert target_file.exists()
        assert "base64" in res.data
        assert res.data["width"] == 640
        assert res.data["height"] == 480


def test_vision_capture_camera_open_failure(tmp_path):
    service = VisionService(output_dir=tmp_path)
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False

    mock_cv2 = MagicMock()
    mock_cv2.VideoCapture.return_value = mock_cap

    with patch("app.services.vision_service.find_spec", return_value=MagicMock()), \
         patch.dict("sys.modules", {"cv2": mock_cv2}):

        params = VisionCaptureParameters(source="camera", camera_index=9)
        res = service.execute(params)

        assert res.status == ToolOutcome.FAILED
        assert "unable to access camera" in res.message.lower()


def test_vision_capture_screen_success(tmp_path):
    from PIL import Image

    service = VisionService(output_dir=tmp_path)
    mock_img = Image.new("RGB", (800, 600), color="blue")

    with patch("pyautogui.screenshot", return_value=mock_img):
        target_file = tmp_path / "screen_test.jpg"
        params = VisionCaptureParameters(
            source="screen",
            save_to_disk=True,
            output_path=str(target_file),
            include_base64=False,
        )
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert "desktop screenshot" in res.message.lower()
        assert target_file.exists()
        assert res.data["width"] == 800
        assert res.data["height"] == 600


def test_vision_probe_cameras():
    service = VisionService()
    mock_cap = MagicMock()
    mock_cap.isOpened.side_effect = [True, False, False, False, False, False]
    mock_cap.read.return_value = (True, MagicMock())

    mock_cv2 = MagicMock()
    mock_cv2.VideoCapture.return_value = mock_cap

    with patch("app.services.vision_service.find_spec", return_value=MagicMock()), \
         patch.dict("sys.modules", {"cv2": mock_cv2}):

        params = VisionCaptureParameters(source="probe_cameras")
        res = service.execute(params)

        assert res.status == ToolOutcome.DONE
        assert 0 in res.data["available_cameras"]


def test_vision_unsupported_source():
    service = VisionService()
    params = VisionCaptureParameters(source="xray_scanner")
    res = service.execute(params)

    assert res.status == ToolOutcome.FAILED
    assert "Supported sources are" in res.message


def test_vision_action_registry_integration():
    service = VisionService()
    registry = ActionRegistry()
    register_vision_actions(registry, service)

    defn = registry.get("vision.capture")
    assert defn is not None
    assert defn.category == "vision"
    assert defn.requires_confirmation is False

    view = defn.public_view()
    assert view["action_id"] == "vision.capture"
    assert view["requires_confirmation"] is False
