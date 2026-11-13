import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from launcher.constants import BACKEND_DIR, FRONTEND_DIR, PROJECT_ROOT

REQUIRED_PYTHON_PACKAGES = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("keyring", "keyring"),
    ("google.genai", "google-genai"),
    ("httpx", "httpx"),
    ("psutil", "psutil"),
    ("pyautogui", "pyautogui"),
    ("pyperclip", "pyperclip"),
]


@dataclass
class DependencyReport:
    backend_venv_exists: bool
    backend_packages_ok: bool
    installed_packages_count: int
    total_packages_count: int
    missing_backend_packages: list[str] = field(default_factory=list)
    frontend_node_modules_exists: bool = False
    electron_installed: bool = False
    vite_installed: bool = False
    all_ok: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DependencyVerifier:
    def __init__(
        self,
        python_executable: str,
        project_root: Path = PROJECT_ROOT,
    ) -> None:
        self.python_executable = python_executable
        self.project_root = project_root
        self.backend_dir = project_root / "backend"
        self.frontend_dir = project_root / "frontend"

    def check_backend_venv(self) -> bool:
        venv_dir = self.backend_dir / ".venv"
        return venv_dir.is_dir()

    def check_python_packages(self) -> tuple[bool, int, list[str]]:
        """Verify required Python packages are importable using target Python interpreter."""
        missing: list[str] = []
        installed = 0

        # Run a quick batch script to check all imports in one invocation
        check_code = (
            "import sys\n"
            "packages = ["
            + ", ".join(f'"{mod}"' for mod, _ in REQUIRED_PYTHON_PACKAGES)
            + "]\n"
            "missing = []\n"
            "for pkg in packages:\n"
            "    try:\n"
            "        __import__(pkg)\n"
            "    except Exception:\n"
            "        missing.append(pkg)\n"
            "print(','.join(missing))\n"
        )

        try:
            result = subprocess.run(
                [self.python_executable, "-c", check_code],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                missing_mods = set(
                    filter(None, result.stdout.strip().split(","))
                )
                for mod, pkg_name in REQUIRED_PYTHON_PACKAGES:
                    if mod in missing_mods:
                        missing.append(pkg_name)
                    else:
                        installed += 1
                return len(missing) == 0, installed, missing
        except Exception:
            pass

        # Fallback check
        for mod, pkg_name in REQUIRED_PYTHON_PACKAGES:
            try:
                res = subprocess.run(
                    [self.python_executable, "-c", f"import {mod}"],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                if res.returncode == 0:
                    installed += 1
                else:
                    missing.append(pkg_name)
            except Exception:
                missing.append(pkg_name)

        return len(missing) == 0, installed, missing

    def check_frontend_dependencies(self) -> tuple[bool, bool, bool]:
        node_modules = self.frontend_dir / "node_modules"
        has_node_modules = node_modules.is_dir()

        electron_dir = node_modules / "electron"
        vite_dir = node_modules / "vite"

        has_electron = electron_dir.is_dir()
        has_vite = vite_dir.is_dir()

        return has_node_modules, has_electron, has_vite

    def verify(self) -> DependencyReport:
        errors: list[str] = []
        warnings: list[str] = []

        venv_exists = self.check_backend_venv()
        if not venv_exists:
            warnings.append(
                f"Virtual environment not found at {self.backend_dir / '.venv'}. "
                "Using interpreter: " + self.python_executable
            )

        packages_ok, installed_cnt, missing_pkgs = self.check_python_packages()
        total_pkgs = len(REQUIRED_PYTHON_PACKAGES)

        if not packages_ok:
            errors.append(
                f"Missing {len(missing_pkgs)} required Python packages: {', '.join(missing_pkgs)}. "
                f"Run: {self.python_executable} -m pip install -r backend/requirements.txt"
            )

        has_modules, has_electron, has_vite = self.check_frontend_dependencies()
        if not has_modules:
            errors.append(
                "Frontend dependencies missing. Run 'npm install' inside the 'frontend/' directory."
            )
        else:
            if not has_electron:
                errors.append(
                    "Electron package not found in frontend/node_modules. Run 'npm install' in frontend/."
                )
            if not has_vite:
                errors.append(
                    "Vite package not found in frontend/node_modules. Run 'npm install' in frontend/."
                )

        all_ok = packages_ok and has_modules and has_electron and has_vite

        return DependencyReport(
            backend_venv_exists=venv_exists,
            backend_packages_ok=packages_ok,
            installed_packages_count=installed_cnt,
            total_packages_count=total_pkgs,
            missing_backend_packages=missing_pkgs,
            frontend_node_modules_exists=has_modules,
            electron_installed=has_electron,
            vite_installed=has_vite,
            all_ok=all_ok,
            errors=errors,
            warnings=warnings,
        )

