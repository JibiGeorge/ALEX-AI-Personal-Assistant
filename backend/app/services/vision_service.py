"""
Vision Service (TASK-GAP-07 / GAP-07).

Webcam Video Frame and Screen Capture:
- OpenCV (cv2) based video frame capture from webcams
- Camera auto-detection and probing across indices (0-5)
- Native OS video capture backends (AVFoundation on macOS, DirectShow on Windows, V4L2 on Linux)
- Automatic frame exposure warmup and JPEG optimization (max 1280x720, quality 82)
- Screen capture fallback via PyAutoGUI / PIL
- Five-Word Outcome Contract adherence (done on capture, unverified when cv2 is missing, failed on hardware open errors)
"""

from __future__ import annotations

import base64
from importlib.util import find_spec
import io
import logging
from pathlib import Path
import platform
import time
from typing import Any, Dict, List, Optional, Tuple

from app.actions.base import ActionOutcomeResponse, done, failed, unverified
from app.schemas.vision import VisionCaptureParameters

logger = logging.getLogger(__name__)

_OS = platform.system()  # "Darwin" | "Windows" | "Linux"
DEFAULT_CAPTURES_DIR = Path.home() / "Desktop"

_IMG_MAX_W = 1280
_IMG_MAX_H = 720
_JPEG_QUALITY = 82


class VisionService:
    """Service providing webcam frame capture and desktop visual analysis."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self._output_dir = output_dir or DEFAULT_CAPTURES_DIR
        self._cached_camera_index: Optional[int] = None

    @property
    def is_cv2_installed(self) -> bool:
        """Check whether opencv-python (cv2) is importable."""
        return find_spec("cv2") is not None

    def execute(self, params: VisionCaptureParameters) -> ActionOutcomeResponse:
        """Execute a vision frame capture operation."""
        source = (params.source or "camera").lower().strip()
        save_to_disk = params.save_to_disk
        custom_path = Path(params.output_path).expanduser().resolve() if params.output_path else None
        include_b64 = params.include_base64

        if source in ("probe_cameras", "list_cameras", "probe"):
            return self.probe_cameras()

        if source in ("screen", "desktop"):
            return self.capture_screen(save_to_disk=save_to_disk, custom_path=custom_path, include_base64=include_b64)

        if source in ("camera", "webcam"):
            return self.capture_camera(
                camera_index=params.camera_index,
                save_to_disk=save_to_disk,
                custom_path=custom_path,
                include_base64=include_b64,
            )

        return failed(
            "vision.capture",
            error=f"Unsupported vision source: '{source}'.",
            message=f"Supported sources are: camera, screen, probe_cameras.",
        )

    # -------------------------------------------------------------------------
    # Camera Capture
    # -------------------------------------------------------------------------

    def capture_camera(
        self,
        camera_index: Optional[int] = None,
        save_to_disk: bool = True,
        custom_path: Optional[Path] = None,
        include_base64: bool = False,
    ) -> ActionOutcomeResponse:
        """Capture a single frame from the connected webcam."""
        if not self.is_cv2_installed:
            return unverified(
                "vision.capture",
                "Webcam frame capture requires OpenCV (cv2), which is not installed. "
                "Run: pip install opencv-python",
                cv2_required=True,
            )

        try:
            import cv2
            import numpy as np

            idx = camera_index if camera_index is not None else self._get_camera_index()
            backend = self._cv2_backend(cv2)

            cap = cv2.VideoCapture(idx, backend)
            if not cap.isOpened():
                cap.release()
                return failed(
                    "vision.capture",
                    error=f"Camera index {idx} could not be opened.",
                    message=f"Unable to access camera index {idx}. Check hardware permissions or test another index.",
                )

            # Warm up camera sensor for auto-exposure & white balance
            for _ in range(5):
                cap.read()

            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                return failed(
                    "vision.capture",
                    error="Camera returned an empty frame.",
                    message="Camera device responded but provided no image frame.",
                )

            # Compress and resize frame
            h, w = frame.shape[:2]
            target_w, target_h = w, h
            if w > _IMG_MAX_W or h > _IMG_MAX_H:
                scale = min(_IMG_MAX_W / w, _IMG_MAX_H / h)
                target_w, target_h = int(w * scale), int(h * scale)
                frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
            jpeg_bytes = buf.tobytes()

            saved_path: Optional[str] = None
            if save_to_disk:
                path = custom_path or (self._output_dir / f"webcam_capture_{int(time.time())}.jpg")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(jpeg_bytes)
                saved_path = str(path)

            data: Dict[str, Any] = {
                "source": "camera",
                "camera_index": idx,
                "width": target_w,
                "height": target_h,
                "format": "image/jpeg",
                "size_bytes": len(jpeg_bytes),
                "saved_to": saved_path,
            }
            if include_base64:
                data["base64"] = base64.b64encode(jpeg_bytes).decode("ascii")

            dest_desc = f" saved to {saved_path}" if saved_path else ""
            return done(
                "vision.capture",
                f"Captured webcam frame ({target_w}x{target_h}){dest_desc}.",
                data=data,
            )

        except Exception as exc:
            logger.exception("Webcam capture error")
            return failed("vision.capture", error=str(exc), message=f"Failed to capture camera frame: {exc}")

    # -------------------------------------------------------------------------
    # Screen Capture Fallback
    # -------------------------------------------------------------------------

    def capture_screen(
        self,
        save_to_disk: bool = True,
        custom_path: Optional[Path] = None,
        include_base64: bool = False,
    ) -> ActionOutcomeResponse:
        """Capture current desktop screen."""
        try:
            import pyautogui

            shot = pyautogui.screenshot()
            w, h = shot.size
            if w > _IMG_MAX_W or h > _IMG_MAX_H:
                shot.thumbnail((_IMG_MAX_W, _IMG_MAX_H))

            buf = io.BytesIO()
            shot.save(buf, format="JPEG", quality=_JPEG_QUALITY)
            jpeg_bytes = buf.getvalue()

            saved_path: Optional[str] = None
            if save_to_disk:
                path = custom_path or (self._output_dir / f"screen_capture_{int(time.time())}.jpg")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(jpeg_bytes)
                saved_path = str(path)

            data: Dict[str, Any] = {
                "source": "screen",
                "width": shot.width,
                "height": shot.height,
                "format": "image/jpeg",
                "size_bytes": len(jpeg_bytes),
                "saved_to": saved_path,
            }
            if include_base64:
                data["base64"] = base64.b64encode(jpeg_bytes).decode("ascii")

            dest_desc = f" saved to {saved_path}" if saved_path else ""
            return done(
                "vision.capture",
                f"Captured desktop screenshot ({shot.width}x{shot.height}){dest_desc}.",
                data=data,
            )
        except Exception as exc:
            logger.exception("Screen capture error")
            return failed("vision.capture", error=str(exc), message=f"Screen capture failed: {exc}")

    # -------------------------------------------------------------------------
    # Camera Probing & Hardware Helpers
    # -------------------------------------------------------------------------

    def probe_cameras(self) -> ActionOutcomeResponse:
        """Probe available video capture devices."""
        if not self.is_cv2_installed:
            return unverified(
                "vision.capture",
                "Camera probing requires OpenCV (cv2), which is not installed. Run: pip install opencv-python",
                cv2_required=True,
            )

        try:
            import cv2
            backend = self._cv2_backend(cv2)
            available: List[int] = []

            for idx in range(6):
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        available.append(idx)
                    cap.release()

            return done(
                "vision.capture",
                f"Found {len(available)} available camera device(s): {available}",
                data={"available_cameras": available, "count": len(available)},
            )
        except Exception as exc:
            return failed("vision.capture", error=str(exc), message=f"Failed probing camera devices: {exc}")

    def _cv2_backend(self, cv2_module: Any) -> int:
        """Select preferred OS camera backend."""
        if _OS == "Darwin":
            return getattr(cv2_module, "CAP_AVFOUNDATION", cv2_module.CAP_ANY)
        elif _OS == "Windows":
            return getattr(cv2_module, "CAP_DSHOW", cv2_module.CAP_ANY)
        else:
            return getattr(cv2_module, "CAP_V4L2", cv2_module.CAP_ANY)

    def _get_camera_index(self) -> int:
        """Return auto-detected or cached camera index."""
        if self._cached_camera_index is not None:
            return self._cached_camera_index

        if not self.is_cv2_installed:
            return 0

        try:
            import cv2
            backend = self._cv2_backend(cv2)
            for idx in range(6):
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        self._cached_camera_index = idx
                        return idx
        except Exception:
            pass

        self._cached_camera_index = 0
        return 0

