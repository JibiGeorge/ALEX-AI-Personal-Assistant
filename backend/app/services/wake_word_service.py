"""
Local Wake-Word Engine ("Hey Alex") (TASK-P4-03 / CAT-38).

Provides low-latency, zero-cloud background wake-word detection using openwakeword ONNX models.

Architectural Guarantees:
1. Zero Cost When Off: `openwakeword` is imported lazily inside `start()`, never at module import time.
2. Zero Audio Path Latency: `feed()` is non-blocking (`put_nowait`), dropping frames if the queue is saturated.
3. Offline Security: Audio processed by this service never leaves the machine; zero outbound network calls while running.
4. Debounce & Queue Drain: Prevents multi-firing on a single activation utterance.
"""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
import logging
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

DEFAULT_WAKE_MODEL = "hey_jarvis"
FALLBACK_WAKE_MODEL = "alexa"
DEFAULT_THRESHOLD = 0.5
SAMPLE_RATE = 16_000
DEBOUNCE_SECONDS = 1.5


def is_openwakeword_installed() -> bool:
    """Check if openwakeword package is importable without loading models."""
    try:
        return find_spec("openwakeword") is not None
    except Exception:
        return False


def is_model_ready(model_name: Optional[str] = None) -> bool:
    """Deterministic, lightweight check verifying required model files exist on disk."""
    if not is_openwakeword_installed():
        return False
    try:
        import openwakeword
        models_dir = Path(openwakeword.__file__).resolve().parent / "resources" / "models"
        if not models_dir.is_dir():
            return False

        # If specific model requested, check it; otherwise check hey_jarvis or alexa
        targets = [model_name] if model_name else [DEFAULT_WAKE_MODEL, FALLBACK_WAKE_MODEL]
        has_wake = any(
            any(models_dir.glob(f"{tgt}*.onnx")) or any(models_dir.glob(f"{tgt}*.tflite"))
            for tgt in targets
        )
        has_mel = any(models_dir.glob("melspectrogram*"))
        has_emb = any(models_dir.glob("embedding_model*"))
        return bool(has_wake and has_mel and has_emb)
    except Exception:
        return False


def install_and_download(
    model_names: Optional[List[str]] = None,
    logger_func: Callable[[str], None] = logger.info,
    notify: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str]:
    """
    One-click setup for wake word: pip-install openwakeword if missing,
    then download pretrained melspectrogram/embedding and wake models. Never raises.
    """
    _tell = notify or (lambda _: None)
    targets = model_names or [DEFAULT_WAKE_MODEL]
    try:
        if not is_openwakeword_installed():
            logger_func("Wake word: installing openwakeword (one-time)...")
            _tell("Wake word: installing openwakeword (one-time)...")
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", "openwakeword"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if r.returncode != 0:
                tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
                return False, f"pip install failed: {tail[0][:160]}"

        logger_func(f"Wake word: downloading models {targets}...")
        _tell("Wake word: downloading models...")
        try:
            import openwakeword.utils as _u
            try:
                _u.download_models(targets)
            except TypeError:
                _u.download_models()  # fallback for older signatures
        except Exception as e:
            return False, f"model download failed: {e}"

        if not is_model_ready():
            return False, "installed, but the wake model could not be loaded."

        logger_func("Wake word: ready.")
        _tell("Wake word installed and ready.")
        return True, "Wake word installed and ready."
    except Exception as exc:
        return False, f"setup error: {exc}"


class WakeWordStatus(BaseModel):
    """Status metadata for the wake-word listener."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    running: bool
    ready: bool
    model: str
    threshold: float
    last_detected_at: Optional[float] = None


class WakeWordService:
    """Manages the background wake-word detection thread and non-blocking audio queue."""

    def __init__(
        self,
        model_name: str = DEFAULT_WAKE_MODEL,
        threshold: float = DEFAULT_THRESHOLD,
        on_wake: Optional[Callable[[], None]] = None,
        enabled: bool = False,
    ) -> None:
        self.model_name = model_name.strip().lower() or DEFAULT_WAKE_MODEL
        self.threshold = max(0.1, min(1.0, float(threshold)))
        self._on_wake = on_wake
        self._enabled = enabled

        self._queue: queue.Queue = queue.Queue(maxsize=60)
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._model: Optional[Any] = None
        self._ready: bool = False
        self._last_detected_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_on_wake(self, callback: Callable[[], None]) -> None:
        """Register or update wake callback."""
        self._on_wake = callback

    def set_enabled(self, enabled: bool) -> bool:
        """Enable or disable wake-word listening."""
        self._enabled = enabled
        if enabled:
            return self.start()
        else:
            self.stop()
            return True

    def get_status(self) -> WakeWordStatus:
        """Get current status snapshot."""
        return WakeWordStatus(
            enabled=self._enabled,
            running=self._running,
            ready=self._ready,
            model=self.model_name,
            threshold=self.threshold,
            last_detected_at=self._last_detected_time if self._last_detected_time > 0 else None,
        )

    def start(self) -> bool:
        """Start the background inference worker. Safe to call repeatedly."""
        with self._lock:
            if self._running:
                return True

            if not is_openwakeword_installed():
                logger.warning("openwakeword is not installed. Wake-word disabled.")
                return False

            try:
                from openwakeword.model import Model
                logger.info("Initializing openwakeword Model for '%s'...", self.model_name)
                self._model = Model(
                    wakeword_models=[self.model_name],
                    inference_framework="onnx",
                )
            except Exception as exc:
                logger.warning("Could not initialize wake-word model '%s': %s", self.model_name, exc)
                self._model = None
                self._ready = False
                return False

            self._running = True
            self._ready = True
            self._thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="AlexWakeWordWorker",
            )
            self._thread.start()
            logger.info("Wake-word listener started for model '%s' (threshold: %.2f)", self.model_name, self.threshold)
            return True

    def stop(self) -> None:
        """Stop the background inference worker cleanly."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            try:
                self._queue.put_nowait(None)
            except Exception:
                pass
            self._model = None
            self._ready = False
            logger.info("Wake-word listener stopped.")

    def feed(self, pcm_frame: Union[bytes, np.ndarray]) -> None:
        """Non-blocking ingest of 16 kHz int16 audio frames from microphone callback."""
        if not self._running:
            return
        try:
            if isinstance(pcm_frame, bytes):
                arr = np.frombuffer(pcm_frame, dtype=np.int16)
            elif isinstance(pcm_frame, np.ndarray):
                arr = pcm_frame[:, 0] if pcm_frame.ndim > 1 else pcm_frame
                arr = arr.astype(np.int16, copy=False)
            else:
                return

            self._queue.put_nowait(arr)
        except queue.Full:
            # Drop frame rather than blocking real-time audio pipeline
            pass
        except Exception as exc:
            logger.debug("Error feeding wake-word frame: %s", exc)

    def _drain_queue(self) -> None:
        """Clear queued audio to prevent duplicate activations from the same spoken utterance."""
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

    def _worker_loop(self) -> None:
        """Background thread worker pulling frames and computing predictions."""
        logger.debug("WakeWord background worker loop running.")
        while self._running:
            try:
                frame = self._queue.get()
                if frame is None or not self._running:
                    break

                if self._model is None:
                    continue

                scores = self._model.predict(np.asarray(frame, dtype=np.int16))
                score = 0.0

                if isinstance(scores, dict):
                    # Match target wake model key case-insensitively (jarvis, alexa, etc.)
                    for k, v in scores.items():
                        k_lower = k.lower()
                        if (
                            "jarvis" in k_lower
                            or "alexa" in k_lower
                            or self.model_name in k_lower
                        ):
                            score = max(score, float(v))
                    # Fallback to maximum score in dictionary if model name key wasn't matched directly
                    if score == 0.0 and scores:
                        score = max(float(v) for v in scores.values())

                now = time.monotonic()
                if score >= self.threshold and (now - self._last_detected_time) >= DEBOUNCE_SECONDS:
                    self._last_detected_time = now
                    logger.info("Wake word detected! (score: %.3f >= threshold: %.2f)", score, self.threshold)
                    self._drain_queue()
                    if self._on_wake is not None:
                        try:
                            self._on_wake()
                        except Exception as cb_exc:
                            logger.exception("Error in wake callback: %s", cb_exc)
            except Exception as exc:
                if self._running:
                    logger.debug("Error in wake-word worker loop: %s", exc)
                time.sleep(0.01)

    def install(self, notify: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """Download openwakeword pretrained models."""
        return install_and_download([self.model_name], notify=notify)

    def probe(self) -> Tuple[bool, str]:
        """Probe wake-word status and readiness."""
        if not is_openwakeword_installed():
            return False, "openwakeword is not installed"
        if not self._ready:
            return True, f"openwakeword installed (model: {self.model_name}; listener inactive)"
        return True, f"Wake word active (listening for '{self.model_name}', threshold: {self.threshold})"


class WakeWordDetector:
    """Drop-in adapter providing full functional parity with Mark-LVI WakeWordDetector."""

    def __init__(
        self,
        on_detect: Callable[[], None],
        threshold: float = DEFAULT_THRESHOLD,
        model_name: str = DEFAULT_WAKE_MODEL,
        logger: Callable[[str], None] = print,
        notify: Optional[Callable[[str], None]] = None,
    ):
        self._service = WakeWordService(
            model_name=model_name,
            threshold=threshold,
            on_wake=on_detect,
            enabled=False,
        )
        self._logger = logger
        self._notify = notify or (lambda _: None)

    def start(self) -> bool:
        ok = self._service.start()
        if not ok:
            self._logger("Wake word: could not load model")
            self._notify("Wake word unavailable — use the WAKE NOW button.")
        return ok

    def stop(self) -> None:
        self._service.stop()

    @property
    def ready(self) -> bool:
        return self._service.is_ready

    def feed(self, frame_int16: Any) -> None:
        self._service.feed(frame_int16)


