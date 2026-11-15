"""
API Key & Configuration Store for ALEX-AI.

Mirrors and aligns with MARK-LVI configuration patterns:
- Multi-path resolution for config/api_keys.json (repo root, backend, runtime data dir, and sibling Mark-LVI).
- Seamless fallback across environment variables, OS keyring, and JSON config files.
- Resilient saving with automatic directory creation and non-fatal keyring fallback.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SERVICE_NAME = "Alex"
_GEMINI_KEY_NAME = "gemini-api-key"


def get_base_dirs() -> tuple[Path, Path]:
    """Return (alex_root, backend_root)."""
    current = Path(__file__).resolve()
    # current: ALEX-AI-main/backend/app/core/api_key_store.py
    backend_root = current.parents[2]
    alex_root = current.parents[3]
    return alex_root, backend_root


def get_config_search_paths() -> list[Path]:
    """Return ordered list of candidate paths for api_keys.json."""
    candidates: list[Path] = []

    # 1. Explicit override via environment (e.g. for testing or custom deployments)
    if custom := os.environ.get("ALEX_CONFIG_FILE"):
        candidates.append(Path(custom).expanduser().resolve())
        return candidates

    # 2. Runtime data directory (e.g. ~/.alex/config/api_keys.json)
    try:
        from app.core.config import get_runtime_settings
        data_dir = get_runtime_settings().resolved_data_dir()
        candidates.append(data_dir / "config" / "api_keys.json")
        candidates.append(data_dir / "api_keys.json")
    except Exception:
        pass

    # 3. Repository root & backend configs
    alex_root, backend_root = get_base_dirs()
    candidates.append(alex_root / "config" / "api_keys.json")
    candidates.append(backend_root / "config" / "api_keys.json")
    candidates.append(Path.cwd() / "config" / "api_keys.json")

    # 4. Sibling Mark-LVI workspace directories for parity and smooth local dev
    workspace_dir = alex_root.parent
    candidates.append(workspace_dir / "Mark-LVI-main" / "config" / "api_keys.json")
    candidates.append(workspace_dir / "Mark-LVI" / "config" / "api_keys.json")

    # Deduplicate while preserving order
    seen: set[Path] = set()
    result: list[Path] = []
    for p in candidates:
        try:
            resolved = p.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(resolved)
        except Exception:
            if p not in seen:
                seen.add(p)
                result.append(p)
    return result


def find_existing_config_file() -> Path | None:
    """Return the first candidate path that exists as a file, or None."""
    for path in get_config_search_paths():
        try:
            if path.is_file():
                return path
        except Exception:
            continue
    return None


def get_primary_config_file() -> Path:
    """Return the preferred path where api_keys.json should be created/saved."""
    if custom := os.environ.get("ALEX_CONFIG_FILE"):
        return Path(custom).expanduser().resolve()
    existing = find_existing_config_file()
    if existing:
        return existing
    alex_root, backend_root = get_base_dirs()
    target = alex_root / "config" / "api_keys.json"
    return target


def load_api_keys() -> dict[str, Any]:
    """Load configuration from api_keys.json if available. Never raises."""
    file_path = find_existing_config_file()
    if not file_path:
        return {}
    try:
        content = file_path.read_text(encoding="utf-8")
        return json.loads(content)
    except Exception as exc:
        logger.warning("Failed to load api_keys.json from %s: %s", file_path, exc)
        return {}


def save_api_keys(
    gemini_api_key: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> Path:
    """Persist api_keys to the primary config file and update extra fields."""
    target_file = get_primary_config_file()
    target_file.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {}
    if target_file.exists():
        try:
            data = json.loads(target_file.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    if gemini_api_key is not None:
        data["gemini_api_key"] = gemini_api_key.strip()

    if extra_fields:
        for k, v in extra_fields.items():
            if v is not None:
                data[k] = v

    # Auto-detect OS system if missing
    if "os_system" not in data:
        sys_name = platform.system().lower()
        if sys_name == "darwin":
            data["os_system"] = "mac"
        elif sys_name == "windows":
            data["os_system"] = "windows"
        else:
            data["os_system"] = "linux"

    target_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Saved api_keys to %s", target_file)
    return target_file


def resolve_gemini_key() -> str | None:
    """
    Resolve Gemini API key across tiered sources with JSON configuration file first:
    1. config/api_keys.json (gemini_api_key) - PRIMARY
    2. os.environ['GEMINI_API_KEY'] - Fallback
    3. OS Keyring (Alex / gemini-api-key) - Fallback
    4. ~/.alex/settings.json (values.gemini_api_key) - Fallback
    """
    # 1. Primary source: config/api_keys.json
    file_cfg = load_api_keys()
    if file_key := file_cfg.get("gemini_api_key"):
        if isinstance(file_key, str) and file_key.strip():
            return file_key.strip()

    # 2. Fallback: Environment variable
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    # 3. Fallback: System Keyring
    try:
        import keyring
        stored = keyring.get_password(_SERVICE_NAME, _GEMINI_KEY_NAME)
        if stored and stored.strip():
            return stored.strip()
    except Exception as exc:
        logger.debug("Keyring lookup did not provide key: %s", exc)

    # 4. Fallback: Settings JSON document
    try:
        from app.core.config import get_runtime_settings
        settings_file = get_runtime_settings().resolved_data_dir() / "settings.json"
        if settings_file.exists():
            data = json.loads(settings_file.read_text(encoding="utf-8"))
            val = data.get("values", {}).get("gemini_api_key")
            if val and str(val).strip():
                return str(val).strip()
    except Exception:
        pass

    return None


def read_gemini_key() -> str | None:
    """Read the Gemini API key directly from the primary JSON config file."""
    file_cfg = load_api_keys()
    if file_key := file_cfg.get("gemini_api_key"):
        if isinstance(file_key, str) and file_key.strip():
            return file_key.strip()
    return None


def sync_env_file(key: str) -> None:
    """Sync GEMINI_API_KEY into local .env files if present."""
    alex_root, backend_root = get_base_dirs()
    candidates = [
        alex_root / ".env",
        backend_root / ".env",
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                content = env_path.read_text(encoding="utf-8")
                lines = content.splitlines()
                found = False
                new_lines = []
                for line in lines:
                    if line.startswith("GEMINI_API_KEY="):
                        new_lines.append(f"GEMINI_API_KEY={key}")
                        found = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"GEMINI_API_KEY={key}")
                env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                logger.debug("Synced GEMINI_API_KEY to %s", env_path)
            except Exception as exc:
                logger.debug("Failed syncing GEMINI_API_KEY to %s: %s", env_path, exc)


def save_gemini_key(key: str) -> Path:
    """Save or update the Gemini API key into the primary JSON configuration file."""
    clean_key = key.strip()
    if not clean_key:
        raise ValueError("API key cannot be blank")
    target = save_api_keys(gemini_api_key=clean_key)
    os.environ["GEMINI_API_KEY"] = clean_key
    sync_env_file(clean_key)
    return target


def delete_gemini_key() -> bool:
    """Delete the Gemini API key from the primary JSON config file."""
    target_file = get_primary_config_file()
    if not target_file.exists():
        return False
    try:
        data = json.loads(target_file.read_text(encoding="utf-8"))
        if "gemini_api_key" in data:
            del data["gemini_api_key"]
            target_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        sync_env_file("")
        return True
    except Exception as exc:
        logger.warning("Failed to delete gemini_api_key from %s: %s", target_file, exc)
        return False


def is_configured() -> bool:
    """Return True if a valid Gemini API key is configured (>= 10 chars)."""
    key = resolve_gemini_key()
    return bool(key and len(key.strip()) >= 10)
