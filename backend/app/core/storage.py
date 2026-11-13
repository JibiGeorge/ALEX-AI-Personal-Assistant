import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any


class StorageError(RuntimeError):
    """Raised when persisted application data cannot be read or written."""


class JsonDocumentStore:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._lock = RLock()

    def read(self, filename: str, default: dict[str, Any]) -> dict[str, Any]:
        path = self._path(filename)
        with self._lock:
            if not path.exists():
                return default.copy()
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise StorageError(f"Could not read {filename}: {exc}") from exc
            if not isinstance(value, dict):
                raise StorageError(f"Stored document {filename} must be a JSON object")
            return value

    def write(self, filename: str, value: dict[str, Any]) -> None:
        path = self._path(filename)
        temporary: str | None = None
        try:
            with self._lock:
                self._data_dir.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self._data_dir,
                    prefix=f".{filename}.",
                    suffix=".tmp",
                    delete=False,
                ) as stream:
                    temporary = stream.name
                    json.dump(value, stream, indent=2, ensure_ascii=False)
                    stream.flush()
                    os.fsync(stream.fileno())
                if os.name != "nt":
                    os.chmod(temporary, 0o600)
                os.replace(temporary, path)
        except OSError as exc:
            raise StorageError(f"Could not write {filename}: {exc}") from exc
        finally:
            if temporary and os.path.exists(temporary):
                try:
                    os.unlink(temporary)
                except OSError:
                    pass

    def _path(self, filename: str) -> Path:
        if Path(filename).name != filename:
            raise ValueError("Storage filenames must be simple names")
        return self._data_dir / filename
