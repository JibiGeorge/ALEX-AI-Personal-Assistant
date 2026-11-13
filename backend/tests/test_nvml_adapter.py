"""
Unit & Integration tests for NVML Telemetry Adapter (TASK-P7-03 / CAT-35).

Verifies ctypes C-bindings, zero subprocess execution, graceful degradation on non-NVIDIA
hardware, simulated NVIDIA GPU metrics, and SystemMetricsService integration.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.schemas.system_metrics import SystemMetricsResponse
from app.services.adapters.nvml_adapter import (
    NVML_SUCCESS,
    NVML_TEMPERATURE_GPU,
    GpuMetrics,
    NvmlAdapter,
    _NvmlMemory,
    _NvmlUtilization,
)
from app.services.system_metrics_service import SystemMetricsService


class FakeNvmlCtypesLibrary:
    """Simulates an NVIDIA Management Library (nvml.dll / libnvidia-ml.so) in ctypes."""

    def __init__(
        self,
        *,
        gpu_util: int = 65,
        mem_util: int = 42,
        temperature: int = 72,
        total_mem: int = 16 * 1024 * 1024 * 1024,
        used_mem: int = 8 * 1024 * 1024 * 1024,
        device_name: str = "NVIDIA GeForce RTX 4090",
        device_count: int = 1,
        fail_init: bool = False,
    ) -> None:
        self.gpu_util = gpu_util
        self.mem_util = mem_util
        self.temperature = temperature
        self.total_mem = total_mem
        self.used_mem = used_mem
        self.device_name = device_name
        self.device_count = device_count
        self.fail_init = fail_init
        self.shutdown_called = False

    def nvmlInit_v2(self) -> int:
        return 1 if self.fail_init else NVML_SUCCESS

    def nvmlDeviceGetCount_v2(self, count_ref: Any) -> int:
        ctypes.cast(count_ref, ctypes.POINTER(ctypes.c_uint)).contents.value = self.device_count
        return NVML_SUCCESS

    def nvmlDeviceGetHandleByIndex_v2(self, index: Any, handle_ref: Any) -> int:
        ctypes.cast(handle_ref, ctypes.POINTER(ctypes.c_void_p)).contents.value = 0x12345678
        return NVML_SUCCESS

    def nvmlDeviceGetUtilizationRates(self, handle: Any, util_ref: Any) -> int:
        target = ctypes.cast(util_ref, ctypes.POINTER(_NvmlUtilization)).contents
        target.gpu = self.gpu_util
        target.memory = self.mem_util
        return NVML_SUCCESS

    def nvmlDeviceGetTemperature(self, handle: Any, sensor: Any, temp_ref: Any) -> int:
        target = ctypes.cast(temp_ref, ctypes.POINTER(ctypes.c_uint)).contents
        target.value = self.temperature
        return NVML_SUCCESS

    def nvmlDeviceGetMemoryInfo(self, handle: Any, mem_ref: Any) -> int:
        target = ctypes.cast(mem_ref, ctypes.POINTER(_NvmlMemory)).contents
        target.total = self.total_mem
        target.used = self.used_mem
        target.free = self.total_mem - self.used_mem
        return NVML_SUCCESS

    def nvmlDeviceGetName(self, handle: Any, buf: Any, length: Any) -> int:
        raw_name = self.device_name.encode("utf-8")
        ctypes.memmove(buf, raw_name, min(len(raw_name) + 1, length.value if hasattr(length, "value") else int(length)))
        return NVML_SUCCESS

    def nvmlShutdown(self) -> int:
        self.shutdown_called = True
        return NVML_SUCCESS


def test_nvml_adapter_graceful_degradation_on_current_host() -> None:
    """Verify that on any host without NVIDIA card, the adapter degrades gracefully with no exceptions."""
    adapter = NvmlAdapter()
    available = adapter.is_available()
    metrics = adapter.get_metrics()

    if not available:
        assert metrics is None
        assert adapter.get_gpu_percent() is None
        assert adapter.get_temperature_c() is None
    else:
        assert metrics is not None
        assert 0 <= metrics.gpu_percent <= 100


def test_nvml_adapter_simulated_ctypes_metrics() -> None:
    """Verify full metric extraction from simulated NVML C library."""
    fake_lib = FakeNvmlCtypesLibrary()
    adapter = NvmlAdapter(lib=fake_lib)

    assert adapter.is_available() is True
    metrics = adapter.get_metrics()
    assert metrics is not None
    assert metrics.gpu_percent == 65.0
    assert metrics.temperature_c == 72.0
    assert metrics.memory_percent == 50.0  # 8GB / 16GB
    assert metrics.memory_used_mb == 8192.0
    assert metrics.memory_total_mb == 16384.0
    assert metrics.device_name == "NVIDIA GeForce RTX 4090"
    assert metrics.device_count == 1

    assert adapter.get_gpu_percent() == 65.0
    assert adapter.get_temperature_c() == 72.0

    adapter.shutdown()
    assert fake_lib.shutdown_called is True


def test_nvml_adapter_failed_init_handling() -> None:
    """Verify that initialization failure is handled cleanly and cached."""
    fake_lib = FakeNvmlCtypesLibrary(fail_init=True)
    adapter = NvmlAdapter(lib=fake_lib)

    assert adapter.is_available() is False
    assert adapter.get_metrics() is None
    assert adapter.get_gpu_percent() is None


def test_nvml_zero_subprocess_invariant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify invariant: NVML interrogation NEVER calls subprocess or CLI commands (nvidia-smi)."""
    def forbidden_call(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Subprocess call detected in NVML adapter!")

    monkeypatch.setattr(subprocess, "Popen", forbidden_call)
    monkeypatch.setattr(subprocess, "run", forbidden_call)
    monkeypatch.setattr(subprocess, "call", forbidden_call)
    monkeypatch.setattr(os, "system", forbidden_call)

    fake_lib = FakeNvmlCtypesLibrary()
    adapter = NvmlAdapter(lib=fake_lib)
    assert adapter.is_available() is True
    metrics = adapter.get_metrics()
    assert metrics is not None
    assert metrics.gpu_percent == 65.0


def test_system_metrics_service_wired_with_nvml() -> None:
    """Verify SystemMetricsService incorporates GPU load and peak temperature."""
    fake_lib = FakeNvmlCtypesLibrary(gpu_util=88, temperature=79)
    nvml_adapter = NvmlAdapter(lib=fake_lib)
    service = SystemMetricsService(nvml_adapter=nvml_adapter)

    snapshot = service.snapshot()
    assert isinstance(snapshot, SystemMetricsResponse)
    assert snapshot.gpu_percent == 88.0
    assert snapshot.temperature_c is not None
    assert snapshot.temperature_c >= 79.0  # At least the GPU temp


def test_system_metrics_service_with_unavailable_nvml() -> None:
    """Verify SystemMetricsService handles unavailable NVML gracefully."""
    fake_lib = FakeNvmlCtypesLibrary(fail_init=True)
    nvml_adapter = NvmlAdapter(lib=fake_lib)
    service = SystemMetricsService(nvml_adapter=nvml_adapter)

    snapshot = service.snapshot()
    assert isinstance(snapshot, SystemMetricsResponse)
    assert snapshot.gpu_percent is None

