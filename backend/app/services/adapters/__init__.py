"""Platform and external service adapters for Alex AI."""

from app.services.adapters.win32_window_adapter import Win32WindowAdapter
from app.services.adapters.macos_window_adapter import MacOSWindowAdapter
from app.services.adapters.linux_window_adapter import LinuxWindowAdapter
from app.services.adapters.nvml_adapter import NvmlAdapter, GpuMetrics
from app.services.adapters.system_tts_adapter import SystemTTSAdapter

__all__ = [
    "Win32WindowAdapter",
    "MacOSWindowAdapter",
    "LinuxWindowAdapter",
    "NvmlAdapter",
    "GpuMetrics",
    "SystemTTSAdapter",
]
