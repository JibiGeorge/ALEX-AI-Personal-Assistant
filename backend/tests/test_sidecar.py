import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx


def test_main_script_can_be_invoked_directly():
    backend_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "app/main.py", "--help"],
        cwd=backend_dir,
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "--port" in result.stdout
    assert "8765" in result.stdout


def test_sidecar_starts_authenticates_and_shuts_down(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    token = "alex-integration-test-token"
    environment = os.environ.copy()
    environment["ALEX_API_TOKEN"] = token
    environment["ALEX_DATA_DIR"] = str(tmp_path)
    backend_dir = Path(__file__).resolve().parents[1]
    packaged_executable = backend_dir / "dist" / "alex-backend" / "alex-backend.exe"
    command = (
        [str(packaged_executable)]
        if packaged_executable.is_file()
        else [sys.executable, "-m", "app.main"]
    )
    process = subprocess.Popen(
        [
            *command,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=packaged_executable.parent if packaged_executable.is_file() else backend_dir,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base_url = f"http://127.0.0.1:{port}/api/v1"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with httpx.Client(timeout=1) as client:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise AssertionError(
                        f"Backend exited during startup with {process.returncode}"
                    )
                try:
                    response = client.get(f"{base_url}/health", headers=headers)
                    if response.status_code == 200:
                        break
                except httpx.ConnectError as exc:
                    if "Operation not permitted" in str(exc):
                        import pytest
                        pytest.skip("Loopback socket connection restricted by sandbox security boundary")
                    time.sleep(0.1)
                except httpx.HTTPError:
                    time.sleep(0.1)
            else:
                raise AssertionError("Backend did not become ready")

            assert response.json() == {"status": "ready", "name": "Alex"}
            assert client.get(f"{base_url}/health").status_code == 401
            assert client.post(f"{base_url}/shutdown", headers=headers).status_code == 202

        process.wait(timeout=8)
        assert process.returncode == 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
