import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any

from launcher.constants import (
    BACKEND_HEALTH_TIMEOUT,
    FRONTEND_READINESS_TIMEOUT,
    POLL_INTERVAL,
)


def check_port_available(host: str, port: int) -> bool:
    """Return True if the specified host:port is free to bind."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(host: str, start_port: int, max_attempts: int = 50) -> int:
    """Find and return an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if check_port_available(host, port):
            return port
    # Fallback to ephemeral port allocation
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def check_backend_health(host: str, port: int, token: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    """Perform a single health check against the backend."""
    url = f"http://{host}:{port}/api/v1/health"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=1.5) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                return True, payload, None
            return False, None, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return False, None, f"HTTP {exc.code}: {exc.reason}"
    except urllib.error.URLError as exc:
        return False, None, str(exc.reason)
    except Exception as exc:
        return False, None, str(exc)


def wait_for_backend_health(
    host: str,
    port: int,
    token: str,
    timeout: float = BACKEND_HEALTH_TIMEOUT,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """Poll backend /api/v1/health until healthy or timeout."""
    deadline = time.monotonic() + timeout
    last_error: str | None = None

    while time.monotonic() < deadline:
        healthy, payload, err = check_backend_health(host, port, token)
        if healthy:
            return True, payload, None
        last_error = err
        time.sleep(POLL_INTERVAL)

    return False, None, last_error or "Timeout waiting for backend"


def check_frontend_ready(host: str, port: int) -> tuple[bool, str | None]:
    """Perform a single check against the frontend Vite server."""
    url = f"http://{host}:{port}/"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=1.5) as response:
            if response.status in (200, 304):
                return True, None
            return False, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        # Vite dev server might respond with 200 or 404 for certain routes, but is reachable
        if exc.code < 500:
            return True, None
        return False, f"HTTP {exc.code}: {exc.reason}"
    except urllib.error.URLError as exc:
        return False, str(exc.reason)
    except Exception as exc:
        return False, str(exc)


def wait_for_frontend_ready(
    host: str,
    port: int,
    timeout: float = FRONTEND_READINESS_TIMEOUT,
) -> tuple[bool, str | None]:
    """Poll frontend server until responsive or timeout."""
    deadline = time.monotonic() + timeout
    last_error: str | None = None

    while time.monotonic() < deadline:
        ready, err = check_frontend_ready(host, port)
        if ready:
            return True, None
        last_error = err
        time.sleep(POLL_INTERVAL)

    return False, last_error or "Timeout waiting for frontend"

