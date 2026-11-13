"""
NVML Hardware Telemetry Adapter (TASK-P7-03 / CAT-35).

Provides low-overhead, zero-subprocess hardware telemetry for NVIDIA GPUs via direct ctypes C-bindings
to nvml.dll (Windows) or libnvidia-ml.so.1 (Linux).

Gracefully degrades on systems without NVIDIA hardware (e.g. macOS Apple Silicon, Intel iGPU).
"""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import threading
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

NVML_TEMPERATURE_GPU = 0
NVML_SUCCESS = 0


class _NvmlUtilization(ctypes.Structure):
    _fields_ = [
        ("gpu", ctypes.c_uint),
        ("memory", ctypes.c_uint),
    ]


class _NvmlMemory(ctypes.Structure):
    _fields_ = [
        ("total", ctypes.c_ulonglong),
        ("free", ctypes.c_ulonglong),
        ("used", ctypes.c_ulonglong),
    ]


@dataclass
class GpuMetrics:
    """Snapshot of GPU performance metrics."""

    gpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    temperature_c: Optional[float] = None
    memory_used_mb: Optional[float] = None
    memory_total_mb: Optional[float] = None
    device_name: Optional[str] = None
    device_count: int = 0


class NvmlAdapter:
    """Interrogates NVIDIA Management Library (NVML) directly via ctypes with zero subprocess calls."""

    def __init__(
        self,
        *,
        lib: Optional[Any] = None,
        lib_loader: Optional[Callable[[], Optional[Any]]] = None,
    ) -> None:
        self._lock = threading.Lock()
        self._custom_lib = lib
        self._lib_loader = lib_loader
        self._nvml_lib: Optional[Any] = None
        self._is_available: Optional[bool] = None
        self._device_count: int = 0
        self._device_handles: List[Any] = []

    def is_available(self) -> bool:
        """Check if NVML is initialized and devices are accessible."""
        if self._is_available is not None:
            return self._is_available
        with self._lock:
            return self._ensure_initialized()

    def _ensure_initialized(self) -> bool:
        """Attempt to load and initialize NVML library."""
        if self._is_available is not None:
            return self._is_available

        # 1. Custom injected library or loader
        if self._custom_lib is not None:
            self._nvml_lib = self._custom_lib
            self._is_available = self._init_nvml_handles()
            return self._is_available

        if self._lib_loader is not None:
            try:
                self._nvml_lib = self._lib_loader()
                if self._nvml_lib is not None:
                    self._is_available = self._init_nvml_handles()
                    return self._is_available
            except Exception as exc:
                logger.debug("Custom NVML loader failed: %s", exc)
                self._is_available = False
                return False

        # 2. Try pynvml if present
        try:
            import pynvml  # type: ignore

            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            if count > 0:
                self._nvml_lib = "pynvml"
                self._device_count = count
                self._device_handles = [
                    pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(count)
                ]
                self._is_available = True
                logger.debug("NVML initialized via pynvml (%d devices)", count)
                return True
        except Exception:
            pass

        # 3. Direct ctypes C-library loading
        lib = self._load_ctypes_library()
        if lib is None:
            self._is_available = False
            return False

        self._nvml_lib = lib
        self._is_available = self._init_nvml_handles()
        return self._is_available

    def _load_ctypes_library(self) -> Optional[Any]:
        """Locate and load nvml DLL or shared library without subprocesses."""
        sys_name = platform.system()
        candidates: List[str] = []

        if sys_name == "Windows":
            candidates = [
                "nvml.dll",
                os.path.expandvars(r"%SystemRoot%\System32\nvml.dll"),
                r"C:\Windows\System32\nvml.dll",
                os.path.expandvars(
                    r"%ProgramFiles%\NVIDIA Corporation\NVSMI\nvml.dll"
                ),
            ]
            loader_fn = getattr(ctypes, "WinDLL", ctypes.CDLL)
        elif sys_name == "Darwin":
            candidates = ["libnvidia-ml.dylib"]
            loader_fn = ctypes.CDLL
        else:  # Linux / Unix
            candidates = [
                "libnvidia-ml.so.1",
                "libnvidia-ml.so",
                "/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1",
                "/usr/lib64/libnvidia-ml.so.1",
            ]
            loader_fn = ctypes.CDLL

        for path in candidates:
            try:
                lib = loader_fn(path)
                return lib
            except Exception:
                continue

        return None

    def _init_nvml_handles(self) -> bool:
        """Call nvmlInit and cache device handles."""
        if self._nvml_lib is None:
            return False

        try:
            # Call nvmlInit_v2 or nvmlInit
            if hasattr(self._nvml_lib, "nvmlInit_v2"):
                res = self._nvml_lib.nvmlInit_v2()
            elif hasattr(self._nvml_lib, "nvmlInit"):
                res = self._nvml_lib.nvmlInit()
            else:
                res = 0

            if res != NVML_SUCCESS and res is not None:
                return False

            # Query device count
            count = ctypes.c_uint()
            if hasattr(self._nvml_lib, "nvmlDeviceGetCount_v2"):
                res = self._nvml_lib.nvmlDeviceGetCount_v2(ctypes.byref(count))
            elif hasattr(self._nvml_lib, "nvmlDeviceGetCount"):
                res = self._nvml_lib.nvmlDeviceGetCount(ctypes.byref(count))
            else:
                return False

            if res != NVML_SUCCESS and res is not None:
                return False

            self._device_count = count.value
            if self._device_count == 0:
                return False

            # Retrieve handles for all indices
            self._device_handles.clear()
            for i in range(self._device_count):
                handle = ctypes.c_void_p()
                if hasattr(self._nvml_lib, "nvmlDeviceGetHandleByIndex_v2"):
                    res = self._nvml_lib.nvmlDeviceGetHandleByIndex_v2(
                        ctypes.c_uint(i), ctypes.byref(handle)
                    )
                elif hasattr(self._nvml_lib, "nvmlDeviceGetHandleByIndex"):
                    res = self._nvml_lib.nvmlDeviceGetHandleByIndex(
                        ctypes.c_uint(i), ctypes.byref(handle)
                    )
                else:
                    res = 1

                if res == NVML_SUCCESS or res is None:
                    self._device_handles.append(handle)

            return len(self._device_handles) > 0

        except Exception as exc:
            logger.debug("Failed initializing NVML device handles: %s", exc)
            return False

    def get_metrics(self) -> Optional[GpuMetrics]:
        """Interrogate all GPU handles and return aggregated telemetry metrics."""
        if not self.is_available():
            return None

        with self._lock:
            if not self._device_handles:
                return None

            try:
                # If using pynvml wrapper
                if self._nvml_lib == "pynvml":
                    return self._query_pynvml()

                # Query primary GPU (index 0)
                handle = self._device_handles[0]

                # Utilization
                util = _NvmlUtilization()
                util_res = self._nvml_lib.nvmlDeviceGetUtilizationRates(
                    handle, ctypes.byref(util)
                )
                gpu_load = float(util.gpu) if (util_res == NVML_SUCCESS or util_res is None) else None

                # Temperature
                temp = ctypes.c_uint()
                temp_res = self._nvml_lib.nvmlDeviceGetTemperature(
                    handle, ctypes.c_uint(NVML_TEMPERATURE_GPU), ctypes.byref(temp)
                )
                temperature_c = float(temp.value) if (temp_res == NVML_SUCCESS or temp_res is None) else None

                # Memory
                mem = _NvmlMemory()
                mem_res = self._nvml_lib.nvmlDeviceGetMemoryInfo(
                    handle, ctypes.byref(mem)
                )
                mem_percent: Optional[float] = None
                mem_used_mb: Optional[float] = None
                mem_total_mb: Optional[float] = None
                if (mem_res == NVML_SUCCESS or mem_res is None) and mem.total > 0:
                    mem_used_mb = mem.used / (1024 * 1024)
                    mem_total_mb = mem.total / (1024 * 1024)
                    mem_percent = (mem.used / mem.total) * 100.0

                # Device Name
                name_buf = ctypes.create_string_buffer(96)
                name_res = self._nvml_lib.nvmlDeviceGetName(
                    handle, name_buf, ctypes.c_uint(96)
                )
                dev_name: Optional[str] = None
                if name_res == NVML_SUCCESS or name_res is None:
                    dev_name = name_buf.value.decode("utf-8", errors="replace").strip()

                return GpuMetrics(
                    gpu_percent=gpu_load,
                    memory_percent=mem_percent,
                    temperature_c=temperature_c,
                    memory_used_mb=mem_used_mb,
                    memory_total_mb=mem_total_mb,
                    device_name=dev_name,
                    device_count=self._device_count,
                )

            except Exception as exc:
                logger.debug("NVML metric collection failed: %s", exc)
                return None

    def _query_pynvml(self) -> Optional[GpuMetrics]:
        """Query via pynvml API if active."""
        try:
            import pynvml  # type: ignore

            handle = self._device_handles[0]
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="replace")

            mem_percent = (mem.used / mem.total * 100.0) if mem.total > 0 else None
            return GpuMetrics(
                gpu_percent=float(util.gpu),
                memory_percent=mem_percent,
                temperature_c=float(temp),
                memory_used_mb=mem.used / (1024 * 1024),
                memory_total_mb=mem.total / (1024 * 1024),
                device_name=name,
                device_count=self._device_count,
            )
        except Exception as exc:
            logger.debug("pynvml metric query failed: %s", exc)
            return None

    def get_gpu_percent(self) -> Optional[float]:
        """Convenience accessor for primary GPU utilization percent."""
        metrics = self.get_metrics()
        return metrics.gpu_percent if metrics else None

    def get_temperature_c(self) -> Optional[float]:
        """Convenience accessor for GPU temperature in Celsius."""
        metrics = self.get_metrics()
        return metrics.temperature_c if metrics else None

    def shutdown(self) -> None:
        """Release NVML resources."""
        with self._lock:
            if self._is_available and self._nvml_lib is not None:
                try:
                    if self._nvml_lib == "pynvml":
                        import pynvml  # type: ignore

                        pynvml.nvmlShutdown()
                    elif hasattr(self._nvml_lib, "nvmlShutdown"):
                        self._nvml_lib.nvmlShutdown()
                except Exception:
                    pass
            self._is_available = False
            self._device_handles.clear()

