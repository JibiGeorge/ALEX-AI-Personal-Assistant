import json
import os
import socket
import sys
import tempfile
import urllib.error
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from launcher.backend_manager import BackendManager
from launcher.cli import LauncherCLI
from launcher.constants import (
    DEFAULT_BACKEND_PORT,
    DEFAULT_FRONTEND_PORT,
    VERSION,
    get_runtime_dir,
    get_state_file_path,
)
from launcher.dependencies import DependencyVerifier
from launcher.doctor import Doctor
from launcher.electron_manager import ElectronManager
from launcher.environment import EnvironmentValidator
from launcher.frontend_manager import FrontendManager
from launcher.health import (
    check_backend_health,
    check_frontend_ready,
    check_port_available,
    find_available_port,
    wait_for_backend_health,
    wait_for_frontend_ready,
)
from launcher.process_manager import ProcessStateManager, is_pid_alive, kill_process_tree
from launcher.shutdown_manager import ShutdownManager


class TestConstantsAndPaths:
    def test_runtime_dir_and_state_file_paths(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        runtime_dir = get_runtime_dir()
        state_file = get_state_file_path()

        assert runtime_dir == tmp_path
        assert state_file == tmp_path / "runtime.json"


class TestEnvironmentValidator:
    def test_find_python_finds_valid_interpreter(self):
        validator = EnvironmentValidator()
        python_exec, version = validator.find_python()

        assert python_exec
        assert isinstance(version, tuple)
        assert len(version) == 3
        assert version >= (3, 11)

    def test_validate_produces_structured_report(self):
        validator = EnvironmentValidator()
        report = validator.validate()

        assert report.python_ok is True
        assert report.platform_name in ("Windows", "Darwin", "Linux")
        assert isinstance(report.errors, list)
        assert isinstance(report.warnings, list)


class TestDependencyVerifier:
    def test_check_python_packages_returns_counts(self):
        validator = EnvironmentValidator()
        python_exec, _ = validator.find_python()
        verifier = DependencyVerifier(python_executable=python_exec)

        packages_ok, installed, missing = verifier.check_python_packages()
        assert isinstance(packages_ok, bool)
        assert installed >= 0
        assert isinstance(missing, list)

    def test_verify_returns_report(self):
        validator = EnvironmentValidator()
        python_exec, _ = validator.find_python()
        verifier = DependencyVerifier(python_executable=python_exec)

        report = verifier.verify()
        assert report.total_packages_count > 0
        assert isinstance(report.missing_backend_packages, list)


class TestHealthAndPorts:
    def test_check_port_available_on_ephemeral_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            bound_port = sock.getsockname()[1]

            # While bound, port should report not available
            assert check_port_available("127.0.0.1", bound_port) is False

        # Once closed, port should be available
        assert check_port_available("127.0.0.1", bound_port) is True

    def test_find_available_port_returns_open_port(self):
        port = find_available_port("127.0.0.1", 39120)
        assert port >= 39120
        assert check_port_available("127.0.0.1", port) is True

    def test_check_backend_health_success(self):
        fake_response = MagicMock()
        fake_response.status = 200
        fake_response.read.return_value = json.dumps({"status": "healthy"}).encode("utf-8")
        fake_response.__enter__.return_value = fake_response

        with patch("urllib.request.urlopen", return_value=fake_response):
            healthy, payload, err = check_backend_health("127.0.0.1", 8765, "test-token")
            assert healthy is True
            assert payload == {"status": "healthy"}
            assert err is None

    def test_check_backend_health_error(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            healthy, payload, err = check_backend_health("127.0.0.1", 8765, "test-token")
            assert healthy is False
            assert payload is None
            assert "Connection refused" in str(err)

    def test_wait_for_backend_health_timeout(self):
        with patch("launcher.health.check_backend_health", return_value=(False, None, "Refused")):
            healthy, payload, err = wait_for_backend_health("127.0.0.1", 8765, "token", timeout=0.1)
            assert healthy is False
            assert payload is None
            assert err is not None

    def test_check_frontend_ready_success(self):
        fake_response = MagicMock()
        fake_response.status = 200
        fake_response.__enter__.return_value = fake_response

        with patch("urllib.request.urlopen", return_value=fake_response):
            ready, err = check_frontend_ready("127.0.0.1", 5173)
            assert ready is True
            assert err is None


class TestProcessManager:
    def test_state_manager_save_load_clear(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        state_mgr = ProcessStateManager()

        test_state = {
            "launcher_pid": os.getpid(),  # Alive PID
            "started_at": 1000.0,
            "status": "running",
            "backend": {"pid": os.getpid(), "port": 8765, "url": "http://127.0.0.1:8765"},
        }
        state_mgr.save_state(test_state)

        loaded = state_mgr.load_state()
        assert loaded is not None
        assert loaded["launcher_pid"] == os.getpid()

        state_mgr.clear_state()
        assert state_mgr.load_state() is None

    def test_stale_state_is_cleaned_up(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        state_mgr = ProcessStateManager()

        dead_pid = 99999999
        test_state = {
            "launcher_pid": dead_pid,
            "backend": {"pid": dead_pid},
        }
        state_mgr.save_state(test_state)

        # Loading state should detect dead PIDs and purge state
        with patch("launcher.process_manager.is_pid_alive", return_value=False):
            loaded = state_mgr.load_state()
            assert loaded is None


class TestServiceManagers:
    def test_backend_manager_properties_and_url(self):
        bm = BackendManager(
            python_executable=sys.executable,
            host="127.0.0.1",
            port=8765,
            token="secure-token-123",
        )
        assert bm.url == "http://127.0.0.1:8765"
        assert bm.token == "secure-token-123"
        assert bm.pid is None
        assert bm.is_alive() is False

    def test_frontend_manager_properties_and_url(self):
        fm = FrontendManager(host="127.0.0.1", port=5173)
        assert fm.url == "http://127.0.0.1:5173"
        assert fm.pid is None
        assert fm.is_alive() is False

    def test_electron_manager_properties(self):
        em = ElectronManager(
            backend_port=8765,
            backend_token="token-xyz",
            frontend_url="http://127.0.0.1:5173",
        )
        assert em.backend_port == 8765
        assert em.backend_token == "token-xyz"
        assert em.frontend_url == "http://127.0.0.1:5173"
        assert em.pid is None
        assert em.is_alive() is False


class TestDoctor:
    def test_doctor_runs_all_checks(self):
        doctor = Doctor()
        all_passed, checks = doctor.run()

        titles = [c.title for c in checks]
        assert "Operating System" in titles
        assert "Python Runtime" in titles
        assert "Node.js Runtime" in titles
        assert "npm Package Manager" in titles
        assert "Virtual Environment" in titles
        assert "Backend Packages" in titles
        assert "Frontend Dependencies" in titles
        assert any("Backend Port" in t for t in titles)
        assert any("Frontend Port" in t for t in titles)
        assert "Credential Store" in titles
        assert len(checks) == 10


class TestLauncherCLI:
    def test_cli_version_flag(self, capsys):
        cli = LauncherCLI()
        with pytest.raises(SystemExit) as exc:
            cli.run(["--version"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert f"Alex v{VERSION}" in captured.out

    def test_cli_help_flag(self, capsys):
        cli = LauncherCLI()
        with pytest.raises(SystemExit) as exc:
            cli.run(["--help"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "launch" in captured.out
        assert "stop" in captured.out
        assert "status" in captured.out
        assert "restart" in captured.out
        assert "doctor" in captured.out

    def test_cli_status_when_stopped(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        cli = LauncherCLI()
        code = cli.run(["status"])
        assert code == 0
        captured = capsys.readouterr()
        assert "STOPPED" in captured.out

    def test_cli_status_json_output(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        cli = LauncherCLI()
        code = cli.run(["status", "--json"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data.get("status") == "stopped"

    def test_cli_status_json_masks_token(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        manager = ProcessStateManager()
        manager.save_state({
            "launcher_pid": os.getpid(),
            "status": "running",
            "backend": {
                "pid": os.getpid(),
                "port": 8765,
                "url": "http://127.0.0.1:8765",
                "token": "secret-super-sensitive-token-12345",
            },
        })
        cli = LauncherCLI()
        code = cli.run(["status", "--json"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "secret-super-sensitive-token-12345" not in captured.out
        assert data["backend"]["token"].endswith("****")

    def test_cli_stop_when_not_running(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        cli = LauncherCLI()
        code = cli.run(["stop"])
        assert code == 0
        captured = capsys.readouterr()
        assert "No active Alex services were found running" in captured.out

    def test_cli_doctor_command(self, capsys):
        cli = LauncherCLI()
        # Doctor should execute and print diagnostic summary
        with patch.object(Doctor, "run", return_value=(True, [])):
            code = cli.run(["doctor"])
            assert code == 0

    def test_launch_existing_instance_guard(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        manager = ProcessStateManager()
        manager.save_state({
            "launcher_pid": os.getpid(),
            "status": "running",
            "backend": {"pid": os.getpid()},
        })
        cli = LauncherCLI()
        code = cli.run(["launch"])
        assert code == 1
        captured = capsys.readouterr()
        assert "An active Alex session was detected" in captured.out

    def test_launch_backend_health_failure_cleans_up(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        cli = LauncherCLI()

        mock_backend = MagicMock()
        mock_backend.start.return_value = None
        mock_backend.token = "test-token"
        mock_backend.get_logs.return_value = "Python syntax error in backend"
        mock_backend.stop.return_value = True

        with patch("launcher.cli.BackendManager", return_value=mock_backend), \
             patch("launcher.cli.wait_for_backend_health", return_value=(False, None, "Timed out waiting for health endpoint")), \
             patch("launcher.cli.EnvironmentValidator.validate") as mock_env, \
             patch("launcher.cli.DependencyVerifier.verify") as mock_dep:
            mock_env.return_value = MagicMock(all_ok=True, python_executable="python")
            mock_dep.return_value = MagicMock(all_ok=True)

            code = cli.run(["launch", "--skip-doctor"])
            assert code == 1
            captured = capsys.readouterr()
            assert "Backend failed health check" in captured.out
            mock_backend.stop.assert_called_once()

    def test_launch_frontend_readiness_failure_cleans_up(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        cli = LauncherCLI()

        mock_backend = MagicMock()
        mock_backend.start.return_value = None
        mock_backend.token = "test-token"
        mock_backend.stop.return_value = True

        mock_frontend = MagicMock()
        mock_frontend.start.return_value = None
        mock_frontend.get_logs.return_value = "Vite build error"
        mock_frontend.stop.return_value = True

        with patch("launcher.cli.BackendManager", return_value=mock_backend), \
             patch("launcher.cli.FrontendManager", return_value=mock_frontend), \
             patch("launcher.cli.wait_for_backend_health", return_value=(True, {"status": "ok"}, None)), \
             patch("launcher.cli.wait_for_frontend_ready", return_value=(False, "Connection refused")), \
             patch("launcher.cli.EnvironmentValidator.validate") as mock_env, \
             patch("launcher.cli.DependencyVerifier.verify") as mock_dep:
            mock_env.return_value = MagicMock(all_ok=True, python_executable="python")
            mock_dep.return_value = MagicMock(all_ok=True)

            code = cli.run(["launch", "--skip-doctor"])
            assert code == 1
            captured = capsys.readouterr()
            assert "Frontend failed readiness check" in captured.out
            mock_frontend.stop.assert_called_once()
            mock_backend.stop.assert_called_once()

    def test_launch_electron_failure_cleans_up(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("ALEX_DATA_DIR", str(tmp_path))
        cli = LauncherCLI()

        mock_backend = MagicMock()
        mock_backend.start.return_value = None
        mock_backend.token = "test-token"
        mock_backend.stop.return_value = True

        mock_frontend = MagicMock()
        mock_frontend.start.return_value = None
        mock_frontend.url = "http://127.0.0.1:5173"
        mock_frontend.stop.return_value = True

        mock_electron = MagicMock()
        mock_electron.build_electron.return_value = (True, "OK")
        mock_electron.start.return_value = None
        mock_electron.is_alive.return_value = False  # Died immediately
        mock_electron.get_logs.return_value = "Electron crash on launch"

        with patch("launcher.cli.BackendManager", return_value=mock_backend), \
             patch("launcher.cli.FrontendManager", return_value=mock_frontend), \
             patch("launcher.cli.ElectronManager", return_value=mock_electron), \
             patch("launcher.cli.wait_for_backend_health", return_value=(True, {"status": "ok"}, None)), \
             patch("launcher.cli.wait_for_frontend_ready", return_value=(True, None)), \
             patch("launcher.cli.EnvironmentValidator.validate") as mock_env, \
             patch("launcher.cli.DependencyVerifier.verify") as mock_dep:
            mock_env.return_value = MagicMock(all_ok=True, python_executable="python")
            mock_dep.return_value = MagicMock(all_ok=True)

            code = cli.run(["launch", "--skip-doctor"])
            assert code == 1
            captured = capsys.readouterr()
            assert "Electron window exited unexpectedly" in captured.out
            mock_frontend.stop.assert_called_once()
            mock_backend.stop.assert_called_once()

