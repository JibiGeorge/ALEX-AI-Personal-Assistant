import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from launcher.constants import BACKEND_DIR, PROJECT_ROOT


@dataclass
class EnvironmentReport:
    python_executable: str
    python_version: tuple[int, int, int]
    python_ok: bool
    node_executable: str | None
    node_version: str | None
    node_ok: bool
    npm_executable: str | None
    npm_version: str | None
    npm_ok: bool
    platform_name: str
    all_ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class EnvironmentValidator:
    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self.project_root = project_root
        self.backend_dir = project_root / "backend"
        self.frontend_dir = project_root / "frontend"

    def find_python(self) -> tuple[str, tuple[int, int, int]]:
        """Find the best Python executable for the Alex backend."""
        candidates: list[str] = []

        # 1. Explicit override
        if env_python := os.environ.get("ALEX_PYTHON"):
            candidates.append(env_python)

        # 2. Virtual environment inside backend/.venv
        if sys.platform == "win32":
            venv_python = self.backend_dir / ".venv" / "Scripts" / "python.exe"
        else:
            venv_python = self.backend_dir / ".venv" / "bin" / "python"
        if venv_python.exists():
            candidates.append(str(venv_python))

        # 3. Current interpreter if running under Python 3.11+
        candidates.append(sys.executable)

        # 4. System executables
        for name in ("python3", "python"):
            if found := shutil.which(name):
                candidates.append(found)

        for candidate in candidates:
            version = self._get_python_version(candidate)
            if version and version >= (3, 11):
                return candidate, version

        # Fallback to sys.executable
        return sys.executable, sys.version_info[:3]

    @staticmethod
    def _get_python_version(executable: str) -> tuple[int, int, int] | None:
        try:
            result = subprocess.run(
                [executable, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}')"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(".")
                if len(parts) >= 3:
                    return int(parts[0]), int(parts[1]), int(parts[2])
        except Exception:
            pass
        return None

    def find_node(self) -> tuple[str | None, str | None, bool]:
        """Verify Node.js version >= 20."""
        node = shutil.which("node")
        if not node:
            return None, None, False

        try:
            result = subprocess.run(
                [node, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                raw = result.stdout.strip()
                match = re.search(r"v?(\d+)\.(\d+)", raw)
                if match:
                    major = int(match.group(1))
                    return node, raw, major >= 20
                return node, raw, False
        except Exception:
            pass
        return node, None, False

    def find_npm(self) -> tuple[str | None, str | None, bool]:
        """Verify npm presence."""
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        npm = shutil.which(npm_cmd) or shutil.which("npm")
        if not npm:
            return None, None, False

        try:
            result = subprocess.run(
                [npm, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                raw = result.stdout.strip()
                return npm, raw, True
        except Exception:
            pass
        return npm, None, False

    def validate(self) -> EnvironmentReport:
        errors: list[str] = []
        warnings: list[str] = []

        python_exec, python_ver = self.find_python()
        python_ok = python_ver >= (3, 11)
        if not python_ok:
            errors.append(
                f"Python 3.11+ is required, but found {python_ver[0]}.{python_ver[1]}.{python_ver[2]} ({python_exec})."
            )

        node_exec, node_ver, node_ok = self.find_node()
        if not node_exec:
            errors.append("Node.js is not installed or not in PATH (Node.js 20+ required).")
        elif not node_ok:
            errors.append(f"Node.js 20+ is required, but found {node_ver} ({node_exec}).")

        npm_exec, npm_ver, npm_ok = self.find_npm()
        if not npm_exec:
            errors.append("npm package manager is not installed or not in PATH.")

        platform_name = platform.system()

        all_ok = python_ok and node_ok and npm_ok and len(errors) == 0

        return EnvironmentReport(
            python_executable=python_exec,
            python_version=python_ver,
            python_ok=python_ok,
            node_executable=node_exec,
            node_version=node_ver,
            node_ok=node_ok,
            npm_executable=npm_exec,
            npm_version=npm_ver,
            npm_ok=npm_ok,
            platform_name=platform_name,
            all_ok=all_ok,
            errors=errors,
            warnings=warnings,
        )

