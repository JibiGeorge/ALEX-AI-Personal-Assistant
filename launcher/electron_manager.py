import os
import shutil
import subprocess
import sys
import threading
from typing import Any

from launcher.constants import FRONTEND_DIR
from launcher.process_manager import kill_process_tree


class ElectronManager:
    def __init__(
        self,
        backend_port: int,
        backend_token: str,
        frontend_url: str,
    ) -> None:
        self.backend_port = backend_port
        self.backend_token = backend_token
        self.frontend_url = frontend_url
        self.process: subprocess.Popen[str] | None = None
        self._output_buffer: list[str] = []
        self._lock = threading.Lock()

    @property
    def pid(self) -> int | None:
        return self.process.pid if self.process else None

    def build_electron(self) -> tuple[bool, str]:
        """Compile TypeScript for Electron main & preload if needed."""
        is_win = sys.platform == "win32"
        npx = shutil.which("npx.cmd" if is_win else "npx") or shutil.which("npx")
        if not npx:
            return False, "npx executable not found in PATH"

        try:
            res = subprocess.run(
                [npx, "tsc", "-p", "tsconfig.electron.json"],
                cwd=str(FRONTEND_DIR),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if res.returncode == 0:
                return True, "Electron TypeScript compiled successfully"
            return False, f"TypeScript compilation error:\n{res.stderr or res.stdout}"
        except Exception as exc:
            return False, f"Failed to run tsc: {exc}"

    def start(self) -> subprocess.Popen[str]:
        """Launch the Electron desktop application window."""
        is_win = sys.platform == "win32"
        npx = shutil.which("npx.cmd" if is_win else "npx") or shutil.which("npx")

        # Command to launch compiled electron main process
        if npx:
            cmd = [npx, "electron", "dist-electron/electron/main.js"]
        else:
            electron_bin = (
                FRONTEND_DIR / "node_modules" / ".bin" / ("electron.cmd" if is_win else "electron")
            )
            cmd = [str(electron_bin), "dist-electron/electron/main.js"]

        env = os.environ.copy()
        env["ALEX_BACKEND_PORT"] = str(self.backend_port)
        env["ALEX_API_TOKEN"] = self.backend_token
        env["ALEX_FRONTEND_URL"] = self.frontend_url
        env["ALEX_MANAGED_BY_LAUNCHER"] = "1"

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        self.process = subprocess.Popen(
            cmd,
            cwd=str(FRONTEND_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=creation_flags,
        )

        t_out = threading.Thread(target=self._capture_stream, args=(self.process.stdout,), daemon=True)
        t_err = threading.Thread(target=self._capture_stream, args=(self.process.stderr,), daemon=True)
        t_out.start()
        t_err.start()

        return self.process

    def _capture_stream(self, stream: Any) -> None:
        if not stream:
            return
        try:
            for line in iter(stream.readline, ""):
                with self._lock:
                    self._output_buffer.append(line)
                    if len(self._output_buffer) > 200:
                        self._output_buffer.pop(0)
        except Exception:
            pass

    def get_logs(self, max_lines: int = 30) -> str:
        with self._lock:
            return "".join(self._output_buffer[-max_lines:])

    def is_alive(self) -> bool:
        if not self.process:
            return False
        return self.process.poll() is None

    def stop(self, timeout: float = 3.0) -> bool:
        """Terminate the Electron application process."""
        if not self.process or self.process.poll() is not None:
            return True

        if self.process.pid:
            kill_process_tree(self.process.pid, timeout=timeout)

        return self.process.poll() is not None

