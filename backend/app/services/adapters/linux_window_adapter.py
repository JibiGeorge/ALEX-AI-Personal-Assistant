from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import sys
from typing import Any, Callable

logger = logging.getLogger(__name__)


class LinuxWindowAdapter:
    """Native Linux EWMH / X11 Window Management Adapter using wmctrl and xdotool.

    Provides EWMH-compliant window enumeration, activation (_NET_ACTIVE_WINDOW),
    and polite termination (_NET_CLOSE_WINDOW). Supports Wayland detection and
    safe degradation when running without an X11 server.
    """

    def __init__(
        self,
        runner: Callable[[list[str]], tuple[int, str, str]] | None = None,
        which_resolver: Callable[[str], str | None] | None = None,
        session_detector: Callable[[], str] | None = None,
        process_name_resolver: Callable[[int], str] | None = None,
    ) -> None:
        self._runner = runner
        self._which = which_resolver or shutil.which
        self._session_detector = session_detector
        self._process_name_resolver = process_name_resolver

    @property
    def is_available(self) -> bool:
        """Return True if running on Linux with tools or if mock runner is supplied."""
        if self._runner is not None:
            return True
        if not sys.platform.startswith("linux"):
            return False
        # Available if wmctrl or xdotool is present or in an active graphical session
        return bool(self._which("wmctrl") or self._which("xdotool") or self.session_type)

    @property
    def session_type(self) -> str:
        """Detect active Linux display session type: 'x11', 'wayland', or 'headless'."""
        if self._session_detector is not None:
            return self._session_detector()

        session = (os.environ.get("XDG_SESSION_TYPE") or "").strip().lower()
        if session in ("wayland", "x11"):
            return session
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        if os.environ.get("DISPLAY"):
            return "x11"
        return "headless"

    def _run(self, cmd: list[str]) -> tuple[int, str, str]:
        """Execute external command safely with timeout."""
        if self._runner is not None:
            return self._runner(cmd)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except FileNotFoundError:
            return 127, "", f"Command not found: {cmd[0]}"
        except Exception as exc:
            logger.debug("Linux window command %s failed: %s", cmd, exc)
            return 1, "", str(exc)

    def _resolve_process_name(self, pid: int) -> str:
        if self._process_name_resolver is not None:
            return self._process_name_resolver(pid)

        try:
            import psutil  # pylint: disable=import-outside-toplevel
            return psutil.Process(pid).name()
        except Exception:
            return "unknown"

    def list_windows(self) -> list[dict[str, Any]]:
        """Enumerate all visible top-level desktop windows on Linux.

        Uses EWMH `wmctrl -l -p`. Format:
            <window_id> <desktop_num> <pid> <client_machine> <title>
        Returns list of dicts:
            [{"window_id": str, "title": str, "process_id": int, "application": str}]
        """
        windows: list[dict[str, Any]] = []

        if self._which("wmctrl") or self._runner is not None:
            rc, stdout, _ = self._run(["wmctrl", "-l", "-p"])
            if rc == 0 and stdout:
                for line in stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(None, 4)
                    if len(parts) < 4:
                        continue

                    w_id = parts[0]
                    desktop_id = parts[1]
                    try:
                        pid = int(parts[2])
                    except ValueError:
                        pid = -1

                    client = parts[3]
                    title = parts[4].strip() if len(parts) >= 5 else client

                    # Skip desktop background layer windows (often desktop -1 and generic name)
                    if desktop_id == "-1" and title.lower() in ("desktop", "desktop window", "plasma"):
                        continue

                    app_name = self._resolve_process_name(pid)
                    if app_name == "unknown":
                        app_name = client

                    windows.append({
                        "window_id": w_id,
                        "title": title[:300],
                        "process_id": pid,
                        "application": app_name,
                    })
                return windows

        # Fallback if wmctrl is not installed: probe via xdotool
        if self._which("xdotool") or self._runner is not None:
            rc, stdout, _ = self._run(["xdotool", "search", "--onlyvisible", "--name", ".*"])
            if rc == 0 and stdout:
                for w_id in stdout.splitlines():
                    w_id = w_id.strip()
                    if not w_id:
                        continue
                    # Get title
                    _, title_out, _ = self._run(["xdotool", "getwindowname", w_id])
                    # Get PID
                    _, pid_out, _ = self._run(["xdotool", "getwindowpid", w_id])
                    try:
                        pid = int(pid_out) if pid_out else -1
                    except ValueError:
                        pid = -1

                    title = title_out or "Window"
                    app_name = self._resolve_process_name(pid)
                    windows.append({
                        "window_id": w_id,
                        "title": title[:300],
                        "process_id": pid,
                        "application": app_name,
                    })
                return windows

        if self.session_type == "wayland":
            logger.info("Window enumeration unavailable in native Wayland without XWayland/wmctrl")
            return []

        return []

    def get_active_window(self) -> dict[str, Any] | None:
        """Get the currently active foreground window on Linux."""
        # 1. Probe via xdotool getactivewindow
        if self._which("xdotool") or self._runner is not None:
            rc, stdout, _ = self._run(["xdotool", "getactivewindow"])
            if rc == 0 and stdout:
                active_id = stdout.strip()
                # Check match in list_windows
                windows = self.list_windows()
                for win in windows:
                    # Match decimal or hex ID
                    try:
                        if int(win["window_id"], 0) == int(active_id, 0):
                            return win
                    except (ValueError, TypeError):
                        if win["window_id"] == active_id:
                            return win

                # Fallback to querying xdotool name directly
                _, title, _ = self._run(["xdotool", "getwindowname", active_id])
                _, pid_str, _ = self._run(["xdotool", "getwindowpid", active_id])
                try:
                    pid = int(pid_str) if pid_str else -1
                except ValueError:
                    pid = -1
                return {
                    "window_id": active_id,
                    "title": title or "Active Window",
                    "process_id": pid,
                    "application": self._resolve_process_name(pid),
                }

        # 2. Fallback to first on-screen window
        windows = self.list_windows()
        return windows[0] if windows else None

    def focus_window(self, identifier: str | int) -> dict[str, Any]:
        """Bring a target Linux application or window to the foreground."""
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

        w_id = target_window["window_id"]
        pid = target_window["process_id"]

        # 1. Attempt wmctrl -ia <w_id> (activate by numeric/hex ID)
        if self._which("wmctrl") or self._runner is not None:
            rc, _, _ = self._run(["wmctrl", "-ia", w_id])
            if rc == 0:
                return {
                    "operation": "focus_window",
                    "window": target_window,
                    "focused": True,
                }

        # 2. Attempt xdotool windowactivate <w_id>
        if self._which("xdotool") or self._runner is not None:
            rc, _, _ = self._run(["xdotool", "windowactivate", w_id])
            if rc == 0:
                return {
                    "operation": "focus_window",
                    "window": target_window,
                    "focused": True,
                }

        # 3. Attempt xdotool search by PID
        if pid > 0 and (self._which("xdotool") or self._runner is not None):
            rc, _, _ = self._run(["xdotool", "search", "--pid", str(pid), "windowactivate"])
            if rc == 0:
                return {
                    "operation": "focus_window",
                    "window": target_window,
                    "focused": True,
                }

        # 4. Attempt wmctrl -a <title>
        if self._which("wmctrl") or self._runner is not None:
            rc, _, _ = self._run(["wmctrl", "-a", target_window["title"]])
            if rc == 0:
                return {
                    "operation": "focus_window",
                    "window": target_window,
                    "focused": True,
                }

        raise RuntimeError(
            f"Linux desktop did not allow window '{target_window['title']}' to receive focus "
            "(neither wmctrl nor xdotool succeeded)."
        )

    def close_window(self, identifier: str | int, timeout: float = 6.0) -> dict[str, Any]:
        """Politely request a Linux application window to close.

        Sends EWMH `_NET_CLOSE_WINDOW` via `wmctrl -ic` or `xdotool windowclose`.
        Falls back to polite SIGTERM. Never escalates to SIGKILL.
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

        w_id = target_window["window_id"]
        pid = target_window["process_id"]

        # 1. EWMH polite close via wmctrl -ic <w_id>
        if self._which("wmctrl") or self._runner is not None:
            rc, _, _ = self._run(["wmctrl", "-ic", w_id])
            if rc == 0:
                return {
                    "operation": "close_window",
                    "window": target_window,
                    "closed": True,
                    "method": "wmctrl -ic (_NET_CLOSE_WINDOW)",
                    "timeout": timeout,
                }

        # 2. Polite close via xdotool windowclose <w_id>
        if self._which("xdotool") or self._runner is not None:
            rc, _, _ = self._run(["xdotool", "windowclose", w_id])
            if rc == 0:
                return {
                    "operation": "close_window",
                    "window": target_window,
                    "closed": True,
                    "method": "xdotool windowclose",
                    "timeout": timeout,
                }

        # 3. Polite SIGTERM (never SIGKILL)
        if pid > 0:
            try:
                os.kill(pid, signal.SIGTERM)
                return {
                    "operation": "close_window",
                    "window": target_window,
                    "closed": True,
                    "method": "SIGTERM",
                    "timeout": timeout,
                }
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to politely terminate Linux process {pid}: {exc}"
                ) from exc

        raise RuntimeError(
            f"Failed to politely close window '{target_window['title']}'."
        )

