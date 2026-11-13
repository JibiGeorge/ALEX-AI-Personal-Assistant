import platform
import sys
from dataclasses import dataclass
from typing import Sequence

from launcher.constants import DEFAULT_BACKEND_PORT, DEFAULT_FRONTEND_PORT, VERSION
from launcher.dependencies import DependencyVerifier
from launcher.environment import EnvironmentValidator
from launcher.health import check_port_available
from launcher.terminal import (
    bold,
    bright_cyan,
    bright_green,
    bright_red,
    cyan,
    dim,
    yellow,
)


@dataclass
class DoctorCheck:
    title: str
    status: str  # "PASS", "WARN", "FAIL"
    message: str
    remediation: str = ""


class Doctor:
    def __init__(self) -> None:
        self.env_validator = EnvironmentValidator()

    def run(self, verbose: bool = False) -> tuple[bool, list[DoctorCheck]]:
        checks: list[DoctorCheck] = []

        # 1. OS Info
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        checks.append(DoctorCheck("Operating System", "PASS", os_info))

        # 2. Environment Report
        env_report = self.env_validator.validate()

        # Python Check
        py_ver_str = f"{env_report.python_version[0]}.{env_report.python_version[1]}.{env_report.python_version[2]}"
        if env_report.python_ok:
            checks.append(
                DoctorCheck(
                    "Python Runtime",
                    "PASS",
                    f"Python {py_ver_str} ({env_report.python_executable})",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    "Python Runtime",
                    "FAIL",
                    f"Python {py_ver_str} ({env_report.python_executable})",
                    "Install Python 3.11 or newer from https://www.python.org",
                )
            )

        # Node Check
        if env_report.node_ok:
            checks.append(
                DoctorCheck(
                    "Node.js Runtime",
                    "PASS",
                    f"{env_report.node_version} ({env_report.node_executable})",
                )
            )
        elif env_report.node_executable:
            checks.append(
                DoctorCheck(
                    "Node.js Runtime",
                    "FAIL",
                    f"{env_report.node_version} (Node 20+ required)",
                    "Upgrade Node.js to version 20+ from https://nodejs.org",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    "Node.js Runtime",
                    "FAIL",
                    "Node.js not found in PATH",
                    "Install Node.js 20+ from https://nodejs.org",
                )
            )

        # npm Check
        if env_report.npm_ok:
            checks.append(
                DoctorCheck(
                    "npm Package Manager",
                    "PASS",
                    f"v{env_report.npm_version} ({env_report.npm_executable})",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    "npm Package Manager",
                    "FAIL",
                    "npm not found",
                    "Install npm or ensure it is in your system PATH",
                )
            )

        # 3. Dependencies
        dep_verifier = DependencyVerifier(python_executable=env_report.python_executable)
        dep_report = dep_verifier.verify()

        # Virtual Environment
        if dep_report.backend_venv_exists:
            checks.append(
                DoctorCheck("Virtual Environment", "PASS", "Found backend/.venv")
            )
        else:
            checks.append(
                DoctorCheck(
                    "Virtual Environment",
                    "WARN",
                    "backend/.venv not found; using active interpreter",
                    f"Run: {env_report.python_executable} -m venv backend/.venv",
                )
            )

        # Backend Packages
        if dep_report.backend_packages_ok:
            checks.append(
                DoctorCheck(
                    "Backend Packages",
                    "PASS",
                    f"{dep_report.installed_packages_count}/{dep_report.total_packages_count} required packages verified",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    "Backend Packages",
                    "FAIL",
                    f"Missing: {', '.join(dep_report.missing_backend_packages)}",
                    f"Run: {env_report.python_executable} -m pip install -r backend/requirements.txt",
                )
            )

        # Frontend Packages
        if dep_report.frontend_node_modules_exists and dep_report.electron_installed and dep_report.vite_installed:
            checks.append(
                DoctorCheck("Frontend Dependencies", "PASS", "node_modules with Vite and Electron verified")
            )
        else:
            checks.append(
                DoctorCheck(
                    "Frontend Dependencies",
                    "FAIL",
                    "node_modules or Electron/Vite missing",
                    "Run 'npm install' inside the frontend/ directory",
                )
            )

        # 4. Port Availability
        backend_port_ok = check_port_available("127.0.0.1", DEFAULT_BACKEND_PORT)
        if backend_port_ok:
            checks.append(DoctorCheck(f"Backend Port {DEFAULT_BACKEND_PORT}", "PASS", "Port is available"))
        else:
            checks.append(
                DoctorCheck(
                    f"Backend Port {DEFAULT_BACKEND_PORT}",
                    "WARN",
                    "Port is currently in use",
                    f"Another process is using port {DEFAULT_BACKEND_PORT}. Use --port <port> or stop the existing process.",
                )
            )

        frontend_port_ok = check_port_available("127.0.0.1", DEFAULT_FRONTEND_PORT)
        if frontend_port_ok:
            checks.append(DoctorCheck(f"Frontend Port {DEFAULT_FRONTEND_PORT}", "PASS", "Port is available"))
        else:
            checks.append(
                DoctorCheck(
                    f"Frontend Port {DEFAULT_FRONTEND_PORT}",
                    "WARN",
                    "Port is currently in use",
                    f"Another process is using port {DEFAULT_FRONTEND_PORT}. Use --frontend-port <port>.",
                )
            )

        # 5. OS Credential Store
        try:
            import keyring
            backend_keyring = keyring.get_keyring()
            keyring_name = type(backend_keyring).__name__
            checks.append(DoctorCheck("Credential Store", "PASS", f"Available ({keyring_name})"))
        except Exception as exc:
            checks.append(
                DoctorCheck(
                    "Credential Store",
                    "WARN",
                    f"Unavailable ({exc})",
                    "Ensure the OS keyring/credential manager service is enabled",
                )
            )

        all_passed = not any(c.status == "FAIL" for c in checks)
        return all_passed, checks

    def print_report(self, verbose: bool = False) -> bool:
        print(f"\n  {bold('Alex Desktop Assistant')} {dim(f'v{VERSION}')} — System Doctor Diagnostic\n")

        all_passed, checks = self.run(verbose=verbose)

        for check in checks:
            if check.status == "PASS":
                badge = bright_green("[PASS]")
            elif check.status == "WARN":
                badge = yellow("[WARN]")
            else:
                badge = bright_red("[FAIL]")

            print(f"  {badge} {bold(check.title):<24} {dim(check.message)}")
            if check.remediation and (check.status != "PASS" or verbose):
                print(f"         {cyan('Fix:')} {check.remediation}")

        passed_count = sum(1 for c in checks if c.status == "PASS")
        warn_count = sum(1 for c in checks if c.status == "WARN")
        fail_count = sum(1 for c in checks if c.status == "FAIL")

        print(f"\n  {dim('────────────────────────────────────────────────────────────────────────')}")
        if all_passed:
            if warn_count > 0:
                print(f"  {yellow('✔')} {bold('Ready with warnings:')} {passed_count} passed, {warn_count} warning(s).")
            else:
                print(f"  {bright_green('✔')} {bold('All checks passed:')} {passed_count}/{len(checks)} checks verified. System is ready.")
        else:
            print(f"  {bright_red('✖')} {bold('Issues detected:')} {fail_count} failure(s), {warn_count} warning(s). Follow fixes above.")
        print()
        return all_passed

