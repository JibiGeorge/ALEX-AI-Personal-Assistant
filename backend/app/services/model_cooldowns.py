from __future__ import annotations

import threading
import time
from collections.abc import Iterable

_QUOTA_COOLDOWN_SECONDS = 5 * 60
_MISSING_MODEL_COOLDOWN_SECONDS = 6 * 60 * 60
_UNAVAILABLE_COOLDOWN_SECONDS = 30 * 60


class ModelCooldowns:
    def __init__(self) -> None:
        self._until: dict[str, float] = {}
        self._lock = threading.Lock()

    def candidates(self, models: Iterable[str]) -> list[str]:
        ordered = list(models)
        with self._lock:
            now = time.monotonic()
            self._until = {
                model: until for model, until in self._until.items() if until > now
            }
            available = [model for model in ordered if model not in self._until]
        return available or ordered

    def record_api_failure(self, model: str, status_code: int) -> None:
        if status_code == 429:
            cooldown = _QUOTA_COOLDOWN_SECONDS
        elif status_code == 404:
            cooldown = _MISSING_MODEL_COOLDOWN_SECONDS
        elif status_code in (503, 504):
            cooldown = _UNAVAILABLE_COOLDOWN_SECONDS
        else:
            return
        with self._lock:
            self._until[model] = time.monotonic() + cooldown

    def record_timeout(self, model: str) -> None:
        with self._lock:
            self._until[model] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS

    def record_success(self, model: str) -> None:
        with self._lock:
            self._until.pop(model, None)


model_cooldowns = ModelCooldowns()
