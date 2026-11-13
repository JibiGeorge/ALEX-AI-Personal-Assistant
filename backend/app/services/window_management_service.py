from __future__ import annotations

import logging
import sys
from typing import Any

from app.services.adapters.win32_window_adapter import Win32WindowAdapter
from app.services.adapters.macos_window_adapter import MacOSWindowAdapter
from app.services.adapters.linux_window_adapter import LinuxWindowAdapter

logger = logging.getLogger(__name__)


class WindowManagementService:
    """Unified cross-platform window management service.

    Dispatches window inspection, focus raising, and polite termination
    to the appropriate native platform adapter.
    """

    def __init__(
        self,
        adapter: Any = None,
    ) -> None:
        self._adapter = adapter
        if self._adapter is None:
            if sys.platform == "win32":
                self._adapter = Win32WindowAdapter()
            elif sys.platform == "darwin":
                self._adapter = MacOSWindowAdapter()
            elif sys.platform.startswith("linux"):
                self._adapter = LinuxWindowAdapter()

    @property
    def platform_name(self) -> str:
        if sys.platform == "win32":
            return "windows"
        if sys.platform == "darwin":
            return "macos"
        if sys.platform.startswith("linux"):
            return "linux"
        return "unknown"

    @property
    def is_available(self) -> bool:
        if self._adapter is not None:
            return getattr(self._adapter, "is_available", True)
        return False

    def get_platform_status(self) -> dict[str, Any]:
        return {
            "platform": self.platform_name,
            "available": self.is_available,
            "adapter": type(self._adapter).__name__ if self._adapter else None,
        }

    def _require_adapter(self) -> Any:
        if self._adapter is None or not self.is_available:
            raise NotImplementedError(
                f"Window management is not currently available on platform '{self.platform_name}'."
            )
        return self._adapter

    def list_windows(self) -> list[dict[str, Any]]:
        adapter = self._require_adapter()
        return adapter.list_windows()

    def get_active_window(self) -> dict[str, Any] | None:
        adapter = self._require_adapter()
        return adapter.get_active_window()

    def focus_window(self, identifier: str | int) -> dict[str, Any]:
        adapter = self._require_adapter()
        return adapter.focus_window(identifier)

    def close_window(self, identifier: str | int, timeout: float = 6.0) -> dict[str, Any]:
        adapter = self._require_adapter()
        return adapter.close_window(identifier, timeout=timeout)
