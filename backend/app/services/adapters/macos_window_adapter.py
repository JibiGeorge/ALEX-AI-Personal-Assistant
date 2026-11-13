from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any, Callable

logger = logging.getLogger(__name__)


class MacOSWindowAdapter:
    """Native macOS Window Management Adapter using Quartz, AppKit, and osascript.

    Provides high-performance C-level window enumeration via Quartz CGWindowListCopyWindowInfo,
    process activation via AppKit NSRunningApplication, and polite application termination
    via AppleEvent quit signals.
    """

    def __init__(
        self,
        quartz_module: Any = None,
        appkit_module: Any = None,
        osascript_runner: Callable[[list[str]], tuple[int, str, str]] | None = None,
    ) -> None:
        self._quartz = quartz_module
        self._appkit = appkit_module
        self._osascript_runner = osascript_runner

    @property
    def is_available(self) -> bool:
        """Return True if running on macOS or mock modules are supplied."""
        if self._quartz is not None or self._appkit is not None or self._osascript_runner is not None:
            return True
        return sys.platform == "darwin"

    def _get_quartz(self) -> Any:
        if self._quartz is not None:
            return self._quartz
        if sys.platform != "darwin":
            return None
        try:
            import Quartz  # pylint: disable=import-outside-toplevel
            self._quartz = Quartz
            return Quartz
        except ImportError:
            return None

    def _get_appkit(self) -> Any:
        if self._appkit is not None:
            return self._appkit
        if sys.platform != "darwin":
            return None
        try:
            import AppKit  # pylint: disable=import-outside-toplevel
            self._appkit = AppKit
            return AppKit
        except ImportError:
            return None

    def _run_osascript(self, script: str) -> tuple[int, str, str]:
        """Execute an AppleScript command safely with timeout."""
        if self._osascript_runner is not None:
            return self._osascript_runner(["osascript", "-e", script])

        try:
            proc = subprocess.run(
                ["/usr/bin/osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except Exception as exc:
            logger.debug("osascript execution failed: %s", exc)
            return 1, "", str(exc)

    def list_windows(self) -> list[dict[str, Any]]:
        """Enumerate all visible on-screen application windows on macOS.

        Returns list of dicts:
            [{"window_id": str(number), "title": str, "process_id": int, "application": str}]
        """
        quartz = self._get_quartz()
        if quartz is not None:
            try:
                # OptionOnScreenOnly | ExcludeDesktopElements
                options = getattr(quartz, "kCGWindowListOptionOnScreenOnly", 1) | getattr(
                    quartz, "kCGWindowListExcludeDesktopElements", 16
                )
                null_id = getattr(quartz, "kCGNullWindowID", 0)
                raw_windows = quartz.CGWindowListCopyWindowInfo(options, null_id) or []

                windows: list[dict[str, Any]] = []
                for win in raw_windows:
                    layer = win.get("kCGWindowLayer", -1)
                    # Normal application windows sit at layer 0
                    if layer != 0:
                        continue

                    bounds = win.get("kCGWindowBounds", {})
                    # Skip invisible / microscopic utility elements
                    if bounds.get("Height", 0) <= 10 or bounds.get("Width", 0) <= 10:
                        continue

                    w_id = win.get("kCGWindowNumber")
                    owner_pid = win.get("kCGWindowOwnerPID")
                    owner_name = win.get("kCGWindowOwnerName", "unknown")
                    title = win.get("kCGWindowName") or owner_name

                    if not title or not w_id:
                        continue

                    windows.append({
                        "window_id": str(w_id),
                        "title": str(title).strip()[:300],
                        "process_id": int(owner_pid) if owner_pid is not None else -1,
                        "application": str(owner_name).strip(),
                    })
                return windows
            except Exception as exc:
                logger.warning("Quartz window enumeration failed; falling back: %s", exc)

        # Fallback via System Events osascript
        return self._list_windows_osascript_fallback()

    def _list_windows_osascript_fallback(self) -> list[dict[str, Any]]:
        """Fallback window enumeration using AppleScript."""
        script = (
            'tell application "System Events"\n'
            '  set appList to {}\n'
            '  repeat with p in (every process whose background only is false)\n'
            '    try\n'
            '      set end of appList to (name of p & "::" & (unix id of p as string))\n'
            '    end try\n'
            '  end repeat\n'
            '  return appList\n'
            'end tell'
        )
        rc, stdout, _ = self._run_osascript(script)
        if rc != 0 or not stdout:
            return []

        windows: list[dict[str, Any]] = []
        entries = [item.strip() for item in stdout.split(",") if item.strip()]
        for entry in entries:
            parts = entry.split("::")
            if len(parts) >= 2:
                app_name = parts[0].strip()
                try:
                    pid = int(parts[1].strip())
                except ValueError:
                    pid = -1
                windows.append({
                    "window_id": str(pid),
                    "title": app_name,
                    "process_id": pid,
                    "application": app_name,
                })
        return windows

    def get_active_window(self) -> dict[str, Any] | None:
        """Get the currently frontmost active window on macOS."""
        appkit = self._get_appkit()
        if appkit is not None:
            try:
                ws = appkit.NSWorkspace.sharedWorkspace()
                front_app = ws.frontmostApplication()
                if front_app is not None:
                    front_pid = front_app.processIdentifier()
                    front_name = str(front_app.localizedName())
                    # Look up window in list_windows
                    for win in self.list_windows():
                        if win["process_id"] == front_pid:
                            return win
                    return {
                        "window_id": str(front_pid),
                        "title": front_name,
                        "process_id": front_pid,
                        "application": front_name,
                    }
            except Exception as exc:
                logger.debug("AppKit active window query failed: %s", exc)

        # Fallback to first on-screen window
        windows = self.list_windows()
        return windows[0] if windows else None

    def focus_window(self, identifier: str | int) -> dict[str, Any]:
        """Bring a target macOS application or window to the foreground."""
        windows = self.list_windows()
        target_window: dict[str, Any] | None = None

        ident_str = str(identifier).strip()

        # Match by window_id
        for win in windows:
            if win["window_id"] == ident_str:
                target_window = win
                break

        # Match by title or application substring
        if target_window is None:
            matches = [
                win for win in windows
                if ident_str.casefold() in win["title"].casefold()
                or ident_str.casefold() in win["application"].casefold()
            ]
            if not matches:
                raise ValueError(f"No visible window matches '{identifier}'.")
            if len(matches) > 1:
                # Check for exact case-insensitive match
                exact_matches = [
                    win for win in matches
                    if ident_str.casefold() == win["title"].casefold()
                    or ident_str.casefold() == win["application"].casefold()
                ]
                if len(exact_matches) == 1:
                    target_window = exact_matches[0]
                else:
                    raise ValueError(
                        f"More than one window matches '{identifier}'; use a more specific title or window ID."
                    )
            else:
                target_window = matches[0]

        pid = target_window["process_id"]
        app_name = target_window["application"]

        # 1. Attempt AppKit activation
        appkit = self._get_appkit()
        if appkit is not None and pid > 0:
            try:
                app = appkit.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                if app is not None:
                    ignoring_others = getattr(appkit, "NSApplicationActivateIgnoringOtherApps", 1 << 1)
                    success = app.activateWithOptions_(ignoring_others)
                    if success:
                        return {
                            "operation": "focus_window",
                            "window": target_window,
                            "focused": True,
                        }
            except Exception as exc:
                logger.debug("AppKit activation failed: %s", exc)

        # 2. Fallback to osascript activation
        script = f'tell application "{app_name}" to activate'
        rc, _, err = self._run_osascript(script)
        if rc == 0:
            return {
                "operation": "focus_window",
                "window": target_window,
                "focused": True,
            }

        # 3. Secondary osascript by unix PID via System Events
        if pid > 0:
            script_pid = (
                f'tell application "System Events" to set frontmost of the '
                f'first process whose unix id is {pid} to true'
            )
            rc, _, err = self._run_osascript(script_pid)
            if rc == 0:
                return {
                    "operation": "focus_window",
                    "window": target_window,
                    "focused": True,
                }

        raise RuntimeError(f"macOS did not allow '{app_name}' to receive focus: {err}")

    def close_window(self, identifier: str | int, timeout: float = 6.0) -> dict[str, Any]:
        """Politely ask a macOS application to quit.

        Sends standard AppleEvent quit signal, allowing the application to prompt
        for unsaved work. Never escalates to SIGKILL.
        """
        windows = self.list_windows()
        target_window: dict[str, Any] | None = None

        ident_str = str(identifier).strip()

        # Match by window_id
        for win in windows:
            if win["window_id"] == ident_str:
                target_window = win
                break

        # Match by title or application
        if target_window is None:
            matches = [
                win for win in windows
                if ident_str.casefold() in win["title"].casefold()
                or ident_str.casefold() in win["application"].casefold()
            ]
            if not matches:
                raise ValueError(f"No visible window matches '{identifier}'.")
            target_window = matches[0]

        pid = target_window["process_id"]
        app_name = target_window["application"]

        # 1. Attempt AppKit polite termination
        appkit = self._get_appkit()
        if appkit is not None and pid > 0:
            try:
                app = appkit.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                if app is not None:
                    terminated = app.terminate()
                    if terminated:
                        return {
                            "operation": "close_window",
                            "window": target_window,
                            "closed": True,
                            "method": "AppKit.terminate",
                            "timeout": timeout,
                        }
            except Exception as exc:
                logger.debug("AppKit polite termination failed: %s", exc)

        # 2. Fallback to AppleScript polite quit
        script = f'tell application "{app_name}" to quit'
        rc, _, err = self._run_osascript(script)
        if rc != 0:
            raise RuntimeError(f"Failed to politely quit macOS application '{app_name}': {err}")

        return {
            "operation": "close_window",
            "window": target_window,
            "closed": True,
            "method": "osascript.quit",
            "timeout": timeout,
        }

