from pathlib import Path
import os
import sys

VERSION = "0.1.0"
APP_NAME = "Alex Desktop Assistant"

# Network Defaults
DEFAULT_BACKEND_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 8765
DEFAULT_FRONTEND_HOST = "127.0.0.1"
DEFAULT_FRONTEND_PORT = 5173

# Timeouts in seconds
BACKEND_HEALTH_TIMEOUT = 25.0
FRONTEND_READINESS_TIMEOUT = 30.0
SHUTDOWN_TIMEOUT = 5.0
POLL_INTERVAL = 0.25

# Project Paths
LAUNCHER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = LAUNCHER_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def get_runtime_dir() -> Path:
    """Return the user runtime directory for Alex state files."""
    override = os.environ.get("ALEX_DATA_DIR")
    if override:
        path = Path(override).expanduser().resolve()
    elif sys.platform == "win32":
        app_data = os.environ.get("APPDATA")
        path = (Path(app_data) / "Alex") if app_data else (Path.home() / ".alex")
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "Alex"
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        path = (Path(xdg) / "Alex") if xdg else (Path.home() / ".local" / "share" / "Alex")

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_state_file_path() -> Path:
    """Return the path to the runtime state JSON file."""
    return get_runtime_dir() / "runtime.json"

