import time
from threading import Lock

from app.schemas.system_alert import SystemAlert
from app.schemas.system_metrics import SystemMetricsResponse

_THRESHOLDS = {
    "cpu": 90.0,
    "memory": 90.0,
    "gpu": 95.0,
    "temperature": 85.0,
}
_ALERT_COOLDOWN_SECONDS = 300
_CPU_REQUIRED_STREAK = 3


class SystemMonitorService:
    def __init__(self) -> None:
        self._last_alert: dict[str, float] = {}
        self._cpu_streak = 0
        self._lock = Lock()

    def check(self, metrics: SystemMetricsResponse) -> list[SystemAlert]:
        with self._lock:
            return self._check(metrics)

    def _check(self, metrics: SystemMetricsResponse) -> list[SystemAlert]:
        now = time.monotonic()
        alerts: list[SystemAlert] = []
        if metrics.cpu_percent >= _THRESHOLDS["cpu"]:
            self._cpu_streak += 1
            if self._cpu_streak >= _CPU_REQUIRED_STREAK and self._can_alert("cpu", now):
                alerts.append(SystemAlert(
                    metric="cpu",
                    value=metrics.cpu_percent,
                    message=(
                        f"CPU usage has remained critically high ({metrics.cpu_percent:.0f}%). "
                        "Consider closing resource-intensive applications."
                    ),
                ))
                self._record("cpu", now)
                self._cpu_streak = 0
        else:
            self._cpu_streak = 0

        candidates = (
            ("memory", metrics.memory_percent, "%", "Memory usage is nearly exhausted."),
            ("gpu", metrics.gpu_percent, "%", "GPU load is critically high."),
            ("temperature", metrics.temperature_c, "°C", "System temperature is above the safe limit."),
        )
        for metric, value, unit, description in candidates:
            if (
                value is not None
                and value >= _THRESHOLDS[metric]
                and self._can_alert(metric, now)
            ):
                alerts.append(SystemAlert(
                    metric=metric,
                    value=value,
                    message=f"{description} Current reading: {value:.0f}{unit}.",
                ))
                self._record(metric, now)
        return alerts

    def _can_alert(self, metric: str, now: float) -> bool:
        return now - self._last_alert.get(metric, float("-inf")) >= _ALERT_COOLDOWN_SECONDS

    def _record(self, metric: str, now: float) -> None:
        self._last_alert[metric] = now
