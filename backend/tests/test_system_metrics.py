from app.services.system_metrics_service import SystemMetricsService
from app.schemas.system_metrics import SystemMetricsResponse
from app.services.system_monitor_service import SystemMonitorService


def test_system_metrics_report_live_host_information():
    service = SystemMetricsService()

    snapshot = service.snapshot()

    assert 0 <= snapshot.cpu_percent <= 100
    assert 0 <= snapshot.memory_percent <= 100
    assert snapshot.network_mb_per_sec is None or snapshot.network_mb_per_sec >= 0
    assert snapshot.operating_system
    assert snapshot.uptime_seconds >= 0
    assert snapshot.process_count > 0
    assert snapshot.gpu_percent is None or 0 <= snapshot.gpu_percent <= 100


def _metrics(
    *,
    cpu: float = 0,
    memory: float = 0,
    gpu: float | None = None,
    temperature: float | None = None,
) -> SystemMetricsResponse:
    return SystemMetricsResponse(
        cpu_percent=cpu,
        memory_percent=memory,
        network_mb_per_sec=0,
        operating_system="Windows",
        uptime_seconds=1,
        process_count=1,
        gpu_percent=gpu,
        temperature_c=temperature,
    )


def test_system_monitor_debounces_cpu_and_applies_per_metric_cooldown(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("app.services.system_monitor_service.time.monotonic", lambda: clock[0])
    service = SystemMonitorService()

    assert service.check(_metrics(cpu=95)) == []
    assert service.check(_metrics(cpu=95)) == []
    cpu_alert = service.check(_metrics(cpu=95))
    assert len(cpu_alert) == 1
    assert cpu_alert[0].metric == "cpu"
    assert service.check(_metrics(cpu=95)) == []

    first = service.check(_metrics(memory=92, temperature=90))
    assert {alert.metric for alert in first} == {"memory", "temperature"}
    assert service.check(_metrics(memory=92, temperature=90)) == []
    clock[0] += 301
    assert {alert.metric for alert in service.check(_metrics(memory=92, temperature=90))} == {
        "memory",
        "temperature",
    }


def test_system_monitor_ignores_unavailable_gpu_and_temperature():
    alerts = SystemMonitorService().check(_metrics(cpu=0, memory=0))
    assert alerts == []
