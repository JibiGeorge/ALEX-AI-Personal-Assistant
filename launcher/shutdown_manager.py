import logging
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from launcher.constants import SHUTDOWN_TIMEOUT
from launcher.process_manager import ProcessStateManager, is_pid_alive, kill_process_tree
from launcher.terminal import cyan, print_info, print_step, print_success, print_warning

logger = logging.getLogger(__name__)


class ShutdownManager:
    def __init__(self, state_manager: ProcessStateManager | None = None) -> None:
        self.state_manager = state_manager or ProcessStateManager()

    def shutdown_running_session(
        self,
        backend: Any | None = None,
        frontend: Any | None = None,
        electron: Any | None = None,
    ) -> bool:
        """Shut down services owned by an active launcher process."""
        print()
        print_info("Initiating graceful shutdown of all Alex services...")

        # 1. Stop Electron
        if electron:
            print_step(1, 3, "Stopping Electron desktop window...", "WAIT")
            electron.stop(timeout=2.0)
            print_step(1, 3, "Electron desktop window closed", "OK")

        # 2. Stop Frontend Vite server
        if frontend:
            print_step(2, 3, "Stopping React/Vite development server...", "WAIT")
            frontend.stop(timeout=2.0)
            print_step(2, 3, "React/Vite development server stopped", "OK")

        # 3. Stop Backend API
        if backend:
            print_step(3, 3, "Requesting graceful backend shutdown...", "WAIT")
            backend.stop(timeout=SHUTDOWN_TIMEOUT)
            print_step(3, 3, "Python backend sidecar stopped", "OK")

        self.state_manager.clear_state()
        print_success("All Alex services terminated cleanly.\n")
        return True

    def stop_from_state(self, force: bool = False) -> tuple[bool, str]:
        """Stop background Alex services identified in runtime.json."""
        state = self.state_manager.load_state()
        if not state:
            return False, "No active Alex services were found running."

        stopped_any = False

        # 1. Stop Electron
        if electron_info := state.get("electron"):
            if e_pid := electron_info.get("pid"):
                if is_pid_alive(int(e_pid)):
                    print_step(1, 3, f"Stopping Electron desktop (PID {e_pid})...", "WAIT")
                    kill_process_tree(int(e_pid), timeout=2.0)
                    print_step(1, 3, f"Electron desktop stopped", "OK")
                    stopped_any = True

        # 2. Stop Frontend
        if frontend_info := state.get("frontend"):
            if f_pid := frontend_info.get("pid"):
                if is_pid_alive(int(f_pid)):
                    print_step(2, 3, f"Stopping Frontend Vite server (PID {f_pid})...", "WAIT")
                    kill_process_tree(int(f_pid), timeout=2.0)
                    print_step(2, 3, f"Frontend Vite server stopped", "OK")
                    stopped_any = True

        # 3. Stop Backend
        if backend_info := state.get("backend"):
            b_pid = backend_info.get("pid")
            b_url = backend_info.get("url")
            b_token = backend_info.get("token")

            if b_url and b_token:
                try:
                    req = urllib.request.Request(
                        f"{b_url}/api/v1/shutdown",
                        headers={"Authorization": f"Bearer {b_token}"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=1.5):
                        pass
                except Exception:
                    pass

            if b_pid and is_pid_alive(int(b_pid)):
                print_step(3, 3, f"Stopping Backend sidecar (PID {b_pid})...", "WAIT")
                kill_process_tree(int(b_pid), timeout=2.5)
                print_step(3, 3, f"Backend sidecar stopped", "OK")
                stopped_any = True

        # 4. Stop Launcher itself if alive
        if launcher_pid := state.get("launcher_pid"):
            if int(launcher_pid) != sys.platform and is_pid_alive(int(launcher_pid)):
                kill_process_tree(int(launcher_pid), timeout=1.0)

        self.state_manager.clear_state()
        if stopped_any:
            return True, "All Alex services were stopped successfully."
        return True, "Cleaned up stale runtime state."

