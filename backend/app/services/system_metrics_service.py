import platform
import time
from typing import Optional

import psutil

from app.schemas.system_metrics import SystemMetricsResponse
from app.services.adapters.nvml_adapter import GpuMetrics, NvmlAdapter


class SystemMetricsService:
    def __init__(self, nvml_adapter: Optional[NvmlAdapter] = None) -> None:
        psutil.cpu_percent(interval=None)
        self._last_network = psutil.net_io_counters()
        self._last_network_time = time.monotonic()
        self._nvml_adapter = nvml_adapter if nvml_adapter is not None else NvmlAdapter()

    @property
    def nvml_adapter(self) -> NvmlAdapter:
        return self._nvml_adapter

    def get_gpu_metrics(self) -> Optional[GpuMetrics]:
        return self._nvml_adapter.get_metrics()

    def snapshot(self) -> SystemMetricsResponse:
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_percent = psutil.virtual_memory().percent
        now = time.monotonic()
        network = psutil.net_io_counters()
        network_mb_per_sec: float | None = None
        if network is not None:
            if self._last_network is not None:
                elapsed = max(now - self._last_network_time, 0.001)
                byte_delta = (
                    network.bytes_sent
                    + network.bytes_recv
                    - self._last_network.bytes_sent
                    - self._last_network.bytes_recv
                )
                network_mb_per_sec = max(byte_delta, 0) / elapsed / 1_000_000
            self._last_network = network
            self._last_network_time = now

        system = platform.system()
        operating_system = {
            "Darwin": "macOS",
            "Windows": "Windows",
            "Linux": "Linux",
        }.get(system, system)

        # GPU metrics via NVML ctypes adapter (zero subprocess)
        gpu_metrics = self._nvml_adapter.get_metrics()
        gpu_percent = gpu_metrics.gpu_percent if gpu_metrics else None
        gpu_temp = gpu_metrics.temperature_c if gpu_metrics else None

        # System temperature: peak reading across CPU thermal sensors and GPU
        cpu_temp = self._temperature()
        if cpu_temp is not None and gpu_temp is not None:
            temperature_c = max(cpu_temp, gpu_temp)
        elif cpu_temp is not None:
            temperature_c = cpu_temp
        else:
            temperature_c = gpu_temp

        return SystemMetricsResponse(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            network_mb_per_sec=network_mb_per_sec,
            operating_system=operating_system,
            uptime_seconds=max(int(time.time() - psutil.boot_time()), 0),
            process_count=len(psutil.pids()),
            gpu_percent=gpu_percent,
            temperature_c=temperature_c,
        )

    @staticmethod
    def _temperature() -> float | None:
        try:
            sensors = psutil.sensors_temperatures(fahrenheit=False)
        except (AttributeError, NotImplementedError, OSError):
            return None
        readings = [
            sensor.current
            for entries in sensors.values()
            for sensor in entries
            if sensor.current is not None
        ]
        return max(readings) if readings else None
