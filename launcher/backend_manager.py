import os
import secrets
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from launcher.constants import BACKEND_DIR, DEFAULT_BACKEND_HOST, DEFAULT_BACKEND_PORT, get_runtime_dir
from launcher.process_manager import is_pid_alive, kill_process_tree


class BackendManager:
    def __init__(
        self,
        python_executable: str,
        host: str = DEFAULT_BACKEND_HOST,
        port: int = DEFAULT_BACKEND_PORT,
        token: str | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.python_executable = python_executable
        self.host = host
        self.port = port
        self.token = token or secrets.token_urlsafe(32)
        self.data_dir = data_dir or get_runtime_dir()
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
        """Launch the Python/FastAPI backend process."""
        args = [
            self.python_executable,
            "-m",
            "app.main",
            "--host",
            self.host,
            "--port",
            str(self.port),
        ]

        env = os.environ.copy()
        env["ALEX_API_TOKEN"] = self.token
        env["ALEX_DATA_DIR"] = str(self.data_dir)
        env["ALEX_LOG_LEVEL"] = env.get("ALEX_LOG_LEVEL", "INFO")
        env["PYTHONPATH"] = str(BACKEND_DIR) + os.pathsep + env.get("PYTHONPATH", "")

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        self.process = subprocess.Popen(
            args,
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=creation_flags,
        )

        # Background thread to capture log output for diagnostics
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

    def stop(self, timeout: float = 5.0) -> bool:
        """Gracefully shut down the backend, with fallback to process termination."""
        if not self.process or self.process.poll() is not None:
            return True

        # 1. Graceful HTTP shutdown request
        try:
            req = urllib.request.Request(
                f"{self.url}/api/v1/shutdown",
                headers={"Authorization": f"Bearer {self.token}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=1.5):
                pass
        except Exception:
            pass

        # Wait for exit
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                return True
            time.sleep(0.1)

        # 2. Forceful termination
        if self.process.pid:
            kill_process_tree(self.process.pid, timeout=2.0)

        return self.process.poll() is not None

