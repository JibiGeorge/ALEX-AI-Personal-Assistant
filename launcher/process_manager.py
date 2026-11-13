import json
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Any

from launcher.constants import get_state_file_path

logger = logging.getLogger(__name__)


def is_pid_alive(pid: int) -> bool:
    """Check whether a process with the given PID is actively running."""
    if pid <= 0:
        return False

    if sys.platform == "win32":
        try:
            import ctypes
            # PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            # SYNCHRONIZE = 0x00100000
            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE,
                False,
                pid,
            )
            if not handle:
                return False
            # Check exit code
            exit_code = ctypes.c_ulong()
            ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            ctypes.windll.kernel32.CloseHandle(handle)
            # STILL_ACTIVE = 259
            return exit_code.value == 259
        except Exception:
            pass

        # Fallback using tasklist
        try:
            res = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            return str(pid) in res.stdout
        except Exception:
            return False

    # Unix
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_process_tree(pid: int, timeout: float = 3.0) -> bool:
    """Recursively terminate a process and all its child processes."""
    if pid <= 0 or not is_pid_alive(pid):
        return True

    # 1. Try psutil if available
    try:
        import psutil
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            parent.terminate()
            gone, alive = psutil.wait_procs([parent, *children], timeout=timeout)
            for p in alive:
                try:
                    p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return not is_pid_alive(pid)
        except psutil.NoSuchProcess:
            return True
        except Exception as exc:
            logger.debug("psutil process tree kill failed: %s", exc)
    except ImportError:
        pass

    # 2. Windows fallback using taskkill
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            return not is_pid_alive(pid)
        except Exception as exc:
            logger.debug("taskkill failed: %s", exc)

    # 3. Unix fallback using SIGTERM then SIGKILL
    try:
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
        except Exception:
            os.kill(pid, signal.SIGTERM)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not is_pid_alive(pid):
                return True
            time.sleep(0.1)

        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            os.kill(pid, signal.SIGKILL)
        return not is_pid_alive(pid)
    except Exception as exc:
        logger.debug("Unix kill failed: %s", exc)

    return not is_pid_alive(pid)


class ProcessStateManager:
    def __init__(self) -> None:
        self.state_file = get_state_file_path()

    def load_state(self) -> dict[str, Any] | None:
        """Load and validate existing runtime state from disk."""
        if not self.state_file.exists():
            return None
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return None

            # Verify if any registered service is actually alive
            pids_to_check: list[int] = []
            if launcher_pid := data.get("launcher_pid"):
                pids_to_check.append(int(launcher_pid))
            if backend := data.get("backend"):
                if b_pid := backend.get("pid"):
                    pids_to_check.append(int(b_pid))
            if frontend := data.get("frontend"):
                if f_pid := frontend.get("pid"):
                    pids_to_check.append(int(f_pid))
            if electron := data.get("electron"):
                if e_pid := electron.get("pid"):
                    pids_to_check.append(int(e_pid))

            any_alive = any(is_pid_alive(pid) for pid in pids_to_check)
            if not any_alive:
                # Stale state file from crashed or killed instance
                self.clear_state()
                return None

            return data
        except Exception as exc:
            logger.warning("Could not read state file: %s", exc)
            return None

    def save_state(self, state: dict[str, Any]) -> None:
        """Atomically persist runtime state to disk."""
        tmp_file = self.state_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            tmp_file.replace(self.state_file)
        except Exception as exc:
            logger.warning("Could not write state file: %s", exc)
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)

    def clear_state(self) -> None:
        """Remove runtime state file."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception as exc:
            logger.warning("Could not delete state file: %s", exc)

