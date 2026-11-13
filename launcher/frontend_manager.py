import os
import shutil
import subprocess
import sys
import threading
from typing import Any

from launcher.constants import DEFAULT_FRONTEND_HOST, DEFAULT_FRONTEND_PORT, FRONTEND_DIR
from launcher.process_manager import kill_process_tree


class FrontendManager:
    def __init__(
        self,
        host: str = DEFAULT_FRONTEND_HOST,
        port: int = DEFAULT_FRONTEND_PORT,
    ) -> None:
        self.host = host
        self.port = port
        self.process: subprocess.Popen[str] | None = None
        self._output_buffer: list[str] = []
        self._lock = threading.Lock()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def pid(self) -> int | None:
        return self.process.pid if self.process else None

    def start(self) -> subprocess.Popen[str]:
        """Launch the React/Vite development server."""
        # Find npx or npm
        is_win = sys.platform == "win32"
        npx = shutil.which("npx.cmd" if is_win else "npx") or shutil.which("npx")

        if npx:
            cmd = [npx, "vite", "--host", self.host, "--port", str(self.port)]
        else:
            npm = shutil.which("npm.cmd" if is_win else "npm") or shutil.which("npm")
            cmd = [npm or "npm", "run", "dev:vite"]

        env = os.environ.copy()

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
        """Terminate the frontend Vite process and any children."""
        if not self.process or self.process.poll() is not None:
            return True

        if self.process.pid:
            kill_process_tree(self.process.pid, timeout=timeout)

        return self.process.poll() is not None

