import argparse
import json
import logging
import os
import signal
import sys
import time
from typing import Any

from launcher.backend_manager import BackendManager
from launcher.constants import (
    DEFAULT_BACKEND_HOST,
    DEFAULT_BACKEND_PORT,
    DEFAULT_FRONTEND_HOST,
    DEFAULT_FRONTEND_PORT,
    VERSION,
    PROJECT_ROOT,
    BACKEND_DIR,
    FRONTEND_DIR,
)
from launcher.dependencies import DependencyVerifier
from launcher.doctor import Doctor
from launcher.electron_manager import ElectronManager
from launcher.environment import EnvironmentValidator
from launcher.frontend_manager import FrontendManager
from launcher.health import (
    check_port_available,
    find_available_port,
    wait_for_backend_health,
    wait_for_frontend_ready,
)
from launcher.process_manager import ProcessStateManager, is_pid_alive
from launcher.shutdown_manager import ShutdownManager
from launcher.terminal import (
    ServiceStatusEntry,
    bright_cyan,
    bright_green,
    bright_red,
    dim,
    print_banner,
    print_error,
    print_info,
    print_step,
    print_success,
    print_summary_table,
    print_warning,
)

logger = logging.getLogger("alex.launcher")


def _load_env_file(path: Any) -> None:
    if not os.path.isfile(path):
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(path, override=False)
    except Exception:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except Exception:
            pass


class LauncherCLI:
    def __init__(self) -> None:
        _load_env_file(PROJECT_ROOT / ".env")
        _load_env_file(BACKEND_DIR / ".env")
        _load_env_file(FRONTEND_DIR / ".env")
        self.state_manager = ProcessStateManager()
        self.shutdown_manager = ShutdownManager(self.state_manager)

    def run(self, argv: list[str] | None = None) -> int:
        parser = self._create_parser()
        args = parser.parse_args(argv)

        if not args.command:
            parser.print_help()
            return 0

        command_handler = getattr(self, f"handle_{args.command}", None)
        if not command_handler:
            parser.print_help()
            return 1

        return command_handler(args)

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="alex",
            description="Alex Unified Application Launcher — Manage the complete Alex desktop assistant stack.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  alex launch                 # Start backend, frontend, and Electron desktop window
  alex launch --no-electron   # Start backend and frontend in headless/web mode
  alex stop                   # Stop all running Alex services
  alex status                 # Check status of running services
  alex restart                # Restart all services
  alex doctor                 # Run system diagnostic checks
  alex --version              # Display launcher version
            """,
        )
        parser.add_argument(
            "-v",
            "--version",
            action="version",
            version=f"Alex v{VERSION}",
            help="Show launcher version and exit",
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Launch command
        launch_parser = subparsers.add_parser("launch", help="Start the complete Alex application")
        launch_parser.add_argument(
            "--host",
            default=DEFAULT_BACKEND_HOST,
            help=f"Backend loopback host (default: {DEFAULT_BACKEND_HOST})",
        )
        launch_parser.add_argument(
            "--port",
            type=int,
            default=DEFAULT_BACKEND_PORT,
            help=f"Backend loopback port (default: {DEFAULT_BACKEND_PORT})",
        )
        launch_parser.add_argument(
            "--frontend-host",
            default=DEFAULT_FRONTEND_HOST,
            help=f"Frontend host (default: {DEFAULT_FRONTEND_HOST})",
        )
        launch_parser.add_argument(
            "--frontend-port",
            type=int,
            default=DEFAULT_FRONTEND_PORT,
            help=f"Frontend port (default: {DEFAULT_FRONTEND_PORT})",
        )
        launch_parser.add_argument(
            "--no-electron",
            "--headless",
            action="store_true",
            help="Start backend and frontend without launching the Electron desktop window",
        )
        launch_parser.add_argument(
            "--skip-doctor",
            action="store_true",
            help="Skip dependency and environment verification before launch",
        )
        launch_parser.add_argument(
            "--force",
            action="store_true",
            help="Force launch even if an existing instance state is detected",
        )

        # Stop command
        stop_parser = subparsers.add_parser("stop", help="Stop running Alex services gracefully")
        stop_parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Forcibly kill any lingering Alex process trees",
        )

        # Status command
        status_parser = subparsers.add_parser("status", help="Show status of running Alex services")
        status_parser.add_argument(
            "--json",
            action="store_true",
            help="Output status as structured JSON",
        )

        # Restart command
        restart_parser = subparsers.add_parser("restart", help="Restart all Alex services")
        restart_parser.add_argument(
            "--port",
            type=int,
            default=DEFAULT_BACKEND_PORT,
            help="Backend port to bind",
        )
        restart_parser.add_argument(
            "--frontend-port",
            type=int,
            default=DEFAULT_FRONTEND_PORT,
            help="Frontend port to bind",
        )
        restart_parser.add_argument(
            "--no-electron",
            action="store_true",
            help="Restart without Electron window",
        )

        # Doctor command
        doctor_parser = subparsers.add_parser("doctor", help="Check environment and dependencies")
        doctor_parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Show detailed remediation notes for all checks",
        )

        return parser

    def handle_doctor(self, args: argparse.Namespace) -> int:
        doctor = Doctor()
        all_passed = doctor.print_report(verbose=args.verbose)
        return 0 if all_passed else 1

    def handle_status(self, args: argparse.Namespace) -> int:
        state = self.state_manager.load_state()

        if args.json:
            sanitized = None
            if state:
                sanitized = json.loads(json.dumps(state))
                if isinstance(sanitized.get("backend"), dict) and "token" in sanitized["backend"]:
                    raw_token = str(sanitized["backend"]["token"])
                    sanitized["backend"]["token"] = f"{raw_token[:4]}...****" if len(raw_token) > 8 else "****"
            print(json.dumps(sanitized or {"status": "stopped", "services": []}, indent=2))
            return 0

        if not state:
            print(f"\n  {bright_cyan('Alex Desktop Assistant')} — Service Status")
            print(f"  {dim('Status:')} {bright_red('STOPPED')} (No active services running)\n")
            return 0

        started_at = state.get("started_at", time.time())
        uptime_seconds = int(time.time() - started_at)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        services: list[ServiceStatusEntry] = []

        # Backend check
        if backend := state.get("backend"):
            b_pid = backend.get("pid", 0)
            b_port = backend.get("port", "")
            b_url = backend.get("url", "")
            is_up = is_pid_alive(int(b_pid))
            services.append(
                ServiceStatusEntry(
                    name="Backend API",
                    status="ONLINE" if is_up else "DOWN",
                    port=str(b_port),
                    pid=str(b_pid),
                    target=b_url,
                )
            )

        # Frontend check
        if frontend := state.get("frontend"):
            f_pid = frontend.get("pid", 0)
            f_port = frontend.get("port", "")
            f_url = frontend.get("url", "")
            is_up = is_pid_alive(int(f_pid))
            services.append(
                ServiceStatusEntry(
                    name="Frontend UI",
                    status="ONLINE" if is_up else "DOWN",
                    port=str(f_port),
                    pid=str(f_pid),
                    target=f_url,
                )
            )

        # Electron check
        if electron := state.get("electron"):
            e_pid = electron.get("pid", 0)
            is_up = is_pid_alive(int(e_pid))
            services.append(
                ServiceStatusEntry(
                    name="Electron App",
                    status="ONLINE" if is_up else "DOWN",
                    port="-",
                    pid=str(e_pid),
                    target="Desktop Window",
                )
            )

        print(f"\n  {bright_cyan('Alex Desktop Assistant')} — Service Status (Uptime: {uptime_str})")
        print_summary_table(services)
        return 0

    def handle_stop(self, args: argparse.Namespace) -> int:
        print_banner(VERSION)
        success, message = self.shutdown_manager.stop_from_state(force=args.force)
        if success:
            print_success(message)
            return 0
        print_info(message)
        return 0

    def handle_restart(self, args: argparse.Namespace) -> int:
        print_info("Restarting Alex application...")
        self.shutdown_manager.stop_from_state(force=True)
        time.sleep(1.0)
        return self.handle_launch(args)

    def handle_launch(self, args: argparse.Namespace) -> int:
        start_time = time.monotonic()
        total_steps = 4 if args.no_electron else 5

        print_banner(VERSION)

        # 0. Check for existing running instance
        existing_state = self.state_manager.load_state()
        if existing_state and not args.force:
            print_warning(
                f"An active Alex session was detected (PID {existing_state.get('launcher_pid')})."
            )
            print_info("Use 'alex status' to view services, or 'alex stop' before launching.")
            print_info("To override this check, run 'alex launch --force'.\n")
            return 1

        # 1. Environment & Dependency Validation
        print_step(1, total_steps, "Validating environment & dependencies...", "WAIT")
        env_validator = EnvironmentValidator()
        env_report = env_validator.validate()

        if not args.skip_doctor:
            if not env_report.all_ok:
                print_step(1, total_steps, "Environment validation failed", "FAIL")
                for err in env_report.errors:
                    print_error(err)
                return 1

            dep_verifier = DependencyVerifier(python_executable=env_report.python_executable)
            dep_report = dep_verifier.verify()
            if not dep_report.all_ok:
                print_step(1, total_steps, "Dependency verification failed", "FAIL")
                for err in dep_report.errors:
                    print_error(err)
                return 1

        print_step(1, total_steps, "Environment & dependencies verified", "OK")

        # 2. Port conflict detection & resolution
        backend_port = args.port
        if not check_port_available(args.host, backend_port):
            alt_port = find_available_port(args.host, backend_port + 1)
            print_warning(
                f"Backend port {backend_port} is busy. Automatically reassigning to available port {alt_port}."
            )
            backend_port = alt_port

        frontend_port = args.frontend_port
        if not check_port_available(args.frontend_host, frontend_port):
            alt_fport = find_available_port(args.frontend_host, frontend_port + 1)
            print_warning(
                f"Frontend port {frontend_port} is busy. Automatically reassigning to available port {alt_fport}."
            )
            frontend_port = alt_fport

        # 3. Start Python Backend
        print_step(
            2,
            total_steps,
            f"Starting Python FastAPI backend ({args.host}:{backend_port})...",
            "WAIT",
        )
        backend = BackendManager(
            python_executable=env_report.python_executable,
            host=args.host,
            port=backend_port,
        )
        try:
            backend.start()
        except Exception as exc:
            print_step(2, total_steps, "Could not start backend process", "FAIL")
            print_error(str(exc))
            return 1

        healthy, health_payload, health_err = wait_for_backend_health(
            args.host, backend_port, backend.token
        )
        if not healthy:
            print_step(2, total_steps, "Backend failed health check", "FAIL")
            print_error(
                f"Backend did not report healthy: {health_err}",
                detail=backend.get_logs(15),
            )
            backend.stop()
            return 1

        print_step(
            2,
            total_steps,
            "Python backend online and healthy",
            "OK",
            detail=backend.url,
        )

        # 4. Start React Frontend
        print_step(
            3,
            total_steps,
            f"Starting React/Vite frontend ({args.frontend_host}:{frontend_port})...",
            "WAIT",
        )
        frontend = FrontendManager(
            host=args.frontend_host,
            port=frontend_port,
        )
        try:
            frontend.start()
        except Exception as exc:
            print_step(3, total_steps, "Could not start frontend process", "FAIL")
            print_error(str(exc))
            backend.stop()
            return 1

        frontend_ready, frontend_err = wait_for_frontend_ready(
            args.frontend_host, frontend_port
        )
        if not frontend_ready:
            print_step(3, total_steps, "Frontend failed readiness check", "FAIL")
            print_error(
                f"Frontend did not become ready: {frontend_err}",
                detail=frontend.get_logs(15),
            )
            frontend.stop()
            backend.stop()
            return 1

        print_step(
            3,
            total_steps,
            "React frontend online and ready",
            "OK",
            detail=frontend.url,
        )

        # 5. Launch Electron Desktop Application
        electron: ElectronManager | None = None
        if not args.no_electron:
            print_step(4, total_steps, "Compiling and launching Electron desktop window...", "WAIT")
            electron = ElectronManager(
                backend_port=backend_port,
                backend_token=backend.token,
                frontend_url=frontend.url,
            )

            # Build Electron main process
            compiled_ok, build_msg = electron.build_electron()
            if not compiled_ok:
                print_step(4, total_steps, "Electron TypeScript compilation warning", "WARN", detail=build_msg)

            try:
                electron.start()
            except Exception as exc:
                print_step(4, total_steps, "Could not launch Electron", "FAIL")
                print_error(str(exc))
                frontend.stop()
                backend.stop()
                return 1

            time.sleep(0.5)
            if not electron.is_alive():
                print_step(4, total_steps, "Electron window exited unexpectedly", "FAIL")
                print_error("Electron process died immediately after launch.", detail=electron.get_logs(15))
                frontend.stop()
                backend.stop()
                return 1

            print_step(4, total_steps, "Electron desktop application launched", "OK", detail=f"PID {electron.pid}")

            # 6. Verify System Connectivity
            print_step(5, total_steps, "Verifying end-to-end system connectivity...", "WAIT")
            print_step(5, total_steps, "All services connected and responsive", "OK")

        # 7. Persist active state
        runtime_state = {
            "launcher_pid": os.getpid(),
            "started_at": time.time(),
            "status": "running",
            "backend": {
                "pid": backend.pid,
                "host": args.host,
                "port": backend_port,
                "url": backend.url,
                "token": backend.token,
            },
            "frontend": {
                "pid": frontend.pid,
                "host": args.frontend_host,
                "port": frontend_port,
                "url": frontend.url,
            },
            "electron": {
                "pid": electron.pid if electron else None,
            },
        }
        self.state_manager.save_state(runtime_state)

        # 8. Render startup summary table
        elapsed = time.monotonic() - start_time
        summary_services = [
            ServiceStatusEntry(
                name="Backend API",
                status="ONLINE",
                port=str(backend_port),
                pid=str(backend.pid),
                target=backend.url,
            ),
            ServiceStatusEntry(
                name="Frontend UI",
                status="ONLINE",
                port=str(frontend_port),
                pid=str(frontend.pid),
                target=frontend.url,
            ),
        ]
        if electron and electron.pid:
            summary_services.append(
                ServiceStatusEntry(
                    name="Electron App",
                    status="ONLINE",
                    port="-",
                    pid=str(electron.pid),
                    target="Desktop Window",
                )
            )

        print_summary_table(summary_services, startup_duration=elapsed)

        # 9. Supervise active processes until interrupt or exit
        return self._supervise_processes(backend, frontend, electron)

    def _supervise_processes(
        self,
        backend: BackendManager,
        frontend: FrontendManager,
        electron: ElectronManager | None,
    ) -> int:
        """Monitor running services and handle Ctrl+C or unexpected child termination."""
        shutdown_called = False

        def sig_handler(signum: int, frame: Any) -> None:
            nonlocal shutdown_called
            if shutdown_called:
                return
            shutdown_called = True
            self.shutdown_manager.shutdown_running_session(
                backend=backend,
                frontend=frontend,
                electron=electron,
            )
            sys.exit(0)

        # Register signal handlers
        try:
            signal.signal(signal.SIGINT, sig_handler)
            signal.signal(signal.SIGTERM, sig_handler)
        except Exception:
            pass

        try:
            while True:
                # 1. Check Backend
                if not backend.is_alive():
                    print_error("Backend sidecar terminated unexpectedly!", detail=backend.get_logs(15))
                    self.shutdown_manager.shutdown_running_session(
                        backend=backend,
                        frontend=frontend,
                        electron=electron,
                    )
                    return 1

                # 2. Check Frontend
                if not frontend.is_alive():
                    print_error("Frontend Vite server terminated unexpectedly!", detail=frontend.get_logs(15))
                    self.shutdown_manager.shutdown_running_session(
                        backend=backend,
                        frontend=frontend,
                        electron=electron,
                    )
                    return 1

                # 3. Check Electron
                if electron and not electron.is_alive():
                    print_info("Electron desktop window was closed by the user.")
                    self.shutdown_manager.shutdown_running_session(
                        backend=backend,
                        frontend=frontend,
                        electron=electron,
                    )
                    return 0

                time.sleep(0.5)

        except KeyboardInterrupt:
            sig_handler(signal.SIGINT, None)
            return 0


def main() -> None:
    cli = LauncherCLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

