from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import sys
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Standard Windows Constants
SW_RESTORE = 9
WM_CLOSE = 0x0010


class Win32WindowAdapter:
    """Native Windows Window Management Adapter using ctypes.

    Provides safe, polite window enumeration, focus raising (via AttachThreadInput
    queue sharing), and polite termination (via WM_CLOSE).
    """

    def __init__(
        self,
        user32: Any = None,
        kernel32: Any = None,
        process_name_resolver: Callable[[int], str] | None = None,
        ctypes_module: Any = None,
    ) -> None:
        self._user32 = user32
        self._kernel32 = kernel32
        self._process_name_resolver = process_name_resolver
        self._ctypes = ctypes_module or ctypes

    @property
    def is_available(self) -> bool:
        """Return True if running on Windows or if mock Win32 DLLs are supplied."""
        if self._user32 is not None:
            return True
        return sys.platform == "win32"

    def _get_libraries(self) -> tuple[Any, Any]:
        """Lazy load and return (user32, kernel32) DLL handles."""
        if self._user32 is not None and self._kernel32 is not None:
            return self._user32, self._kernel32

        if sys.platform != "win32":
            raise NotImplementedError(
                "Win32 window management is only supported natively on Windows."
            )

        try:
            user32 = self._ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = self._ctypes.WinDLL("kernel32", use_last_error=True)
            self._user32 = user32
            self._kernel32 = kernel32
            return user32, kernel32
        except Exception as exc:
            logger.exception("Failed to load Win32 user32/kernel32 libraries")
            raise RuntimeError(f"Could not initialize Win32 window adapter: {exc}") from exc

    def _resolve_process_name(self, pid: int) -> str:
        """Resolve process name given a process ID."""
        if self._process_name_resolver is not None:
            return self._process_name_resolver(pid)

        try:
            import psutil  # pylint: disable=import-outside-toplevel

            return psutil.Process(pid).name()
        except Exception:
            return "unknown"

    def list_windows(self) -> list[dict[str, Any]]:
        """Enumerate all visible top-level windows with non-empty titles.

        Returns list of dicts:
            [{"window_id": str(hwnd), "title": str, "process_id": int, "application": str}]
        """
        user32, _ = self._get_libraries()
        windows: list[dict[str, Any]] = []

        try:
            wt = getattr(self._ctypes, "wintypes", wintypes)
            callback_type = self._ctypes.WINFUNCTYPE(
                wt.BOOL, wt.HWND, wt.LPARAM
            )

            def enum_proc(hwnd: int, _lparam: int) -> bool:
                try:
                    if not user32.IsWindowVisible(hwnd):
                        return True
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length <= 0:
                        return True
                    title_buffer = self._ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, title_buffer, length + 1)
                    title = title_buffer.value.strip()
                    if not title:
                        return True

                    pid = wt.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, self._ctypes.byref(pid))
                    process_id = int(pid.value)
                    app_name = self._resolve_process_name(process_id)

                    windows.append({
                        "window_id": str(int(hwnd)),
                        "title": title[:300],
                        "process_id": process_id,
                        "application": app_name,
                    })
                except Exception as ex:
                    logger.debug("Error inspecting window %s: %s", hwnd, ex)
                return True

            cb = callback_type(enum_proc)
            user32.EnumWindows(cb, 0)
            return windows
        except Exception as exc:
            logger.exception("Win32 desktop window enumeration failed")
            raise RuntimeError(f"Could not inspect visible desktop windows: {exc}") from exc

    def get_active_window(self) -> dict[str, Any] | None:
        """Get the currently focused foreground window, or None."""
        user32, _ = self._get_libraries()
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        hwnd_str = str(int(hwnd))
        for win in self.list_windows():
            if win["window_id"] == hwnd_str:
                return win
        return None

    def focus_window(self, identifier: str | int) -> dict[str, Any]:
        """Bring a target window to the foreground and grant it focus.

        `identifier` can be a numeric window_id (as str or int) or a title substring.
        Uses AttachThreadInput to reliably bring background or minimized windows to front.
        """
        user32, kernel32 = self._get_libraries()
        windows = self.list_windows()
        target_window: dict[str, Any] | None = None

        ident_str = str(identifier).strip()

        # Check if identifier matches window_id directly
        for win in windows:
            if win["window_id"] == ident_str:
                target_window = win
                break

        # Otherwise match by title substring (case-insensitive)
        if target_window is None:
            matches = [
                win for win in windows
                if ident_str.casefold() in win["title"].casefold()
            ]
            if not matches:
                raise ValueError(f"No visible window matches '{identifier}'.")
            if len(matches) > 1:
                # Check for exact case-insensitive match
                exact_matches = [
                    win for win in matches
                    if ident_str.casefold() == win["title"].casefold()
                ]
                if len(exact_matches) == 1:
                    target_window = exact_matches[0]
                else:
                    raise ValueError(
                        f"More than one window matches '{identifier}'; use a more specific title or window ID."
                    )
            else:
                target_window = matches[0]

        hwnd = int(target_window["window_id"])

        # 1. Restore window if minimized
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)

        # 2. Attempt direct SetForegroundWindow
        if user32.SetForegroundWindow(hwnd):
            return {
                "operation": "focus_window",
                "window": target_window,
                "focused": True,
            }

        # 3. Borrow foreground thread's input queue if Windows prevents background focus stealing
        fore = user32.GetForegroundWindow()
        if fore:
            their_thread = user32.GetWindowThreadProcessId(fore, None)
            our_thread = kernel32.GetCurrentThreadId()
            if their_thread != our_thread:
                attached = bool(user32.AttachThreadInput(our_thread, their_thread, True))
                try:
                    user32.BringWindowToTop(hwnd)
                    success = bool(user32.SetForegroundWindow(hwnd))
                finally:
                    if attached:
                        user32.AttachThreadInput(our_thread, their_thread, False)
                if success:
                    return {
                        "operation": "focus_window",
                        "window": target_window,
                        "focused": True,
                    }

        raise RuntimeError(f"Windows did not allow window '{target_window['title']}' to receive focus.")

    def close_window(self, identifier: str | int, timeout: float = 6.0) -> dict[str, Any]:
        """Politely request a window to close by posting WM_CLOSE (0x0010).

        Does not kill or terminate processes forcibly, allowing applications
        to prompt users to save unsaved documents.
        """
        user32, _ = self._get_libraries()
        windows = self.list_windows()
        target_window: dict[str, Any] | None = None

        ident_str = str(identifier).strip()

        # Check by window_id
        for win in windows:
            if win["window_id"] == ident_str:
                target_window = win
                break

        # Otherwise match by title substring or application name
        if target_window is None:
            matches = [
                win for win in windows
                if ident_str.casefold() in win["title"].casefold()
                or ident_str.casefold() in win["application"].casefold()
            ]
            if not matches:
                raise ValueError(f"No visible window matches '{identifier}'.")
            target_window = matches[0]

        hwnd = int(target_window["window_id"])
        posted = user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        if not posted:
            raise RuntimeError(f"Failed to post WM_CLOSE to window '{target_window['title']}'.")

        return {
            "operation": "close_window",
            "window": target_window,
            "closed": True,
            "method": "WM_CLOSE",
            "timeout": timeout,
        }
