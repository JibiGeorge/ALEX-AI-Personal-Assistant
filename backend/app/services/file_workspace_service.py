import hashlib
import logging
import os
import shutil
import tempfile
import threading
from pathlib import Path, PurePosixPath
from typing import Callable
from uuid import uuid4

from app.core.storage import JsonDocumentStore, StorageError

_MAX_TEXT_BYTES = 1_000_000
_MAX_READ_BYTES = 1_000_000
_MAX_COPY_BYTES = 50_000_000
_MAX_ENTRIES = 200
_UNDO_LIMIT = 10
_JOURNAL = "workspace_undo.json"
logger = logging.getLogger(__name__)


class WorkspacePathError(ValueError):
    """Raised when a workspace path is invalid or escapes the approved root."""


class WorkspaceConflictError(RuntimeError):
    """Raised when an operation would overwrite or unexpectedly alter a file."""


class FileWorkspaceService:
    def __init__(self, data_dir: Path):
        workspace_path = data_dir / "workspace"
        undo_path = data_dir / "workspace_undo"
        if workspace_path.is_symlink() or undo_path.is_symlink():
            raise StorageError("Workspace and undo directories cannot be symbolic links.")
        self.root = workspace_path.resolve()
        self._undo_dir = undo_path.resolve()
        self._store = JsonDocumentStore(data_dir)
        self._lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)
        self._undo_dir.mkdir(parents=True, exist_ok=True)

    def list_directory(self, path: str = ".") -> list[dict[str, object]]:
        target = self._resolve(path, allow_root=True)
        if not target.is_dir():
            raise NotADirectoryError("The requested workspace path is not a directory.")
        entries = []
        for item in sorted(target.iterdir(), key=lambda entry: entry.name.casefold()):
            if self._is_link(item) or item.name.startswith("."):
                continue
            info = item.stat()
            if item.is_file() and info.st_nlink > 1:
                continue
            entries.append({
                "name": item.name,
                "path": item.relative_to(self.root).as_posix() or ".",
                "kind": "directory" if item.is_dir() else "file",
                "size_bytes": None if item.is_dir() else info.st_size,
            })
            if len(entries) >= _MAX_ENTRIES:
                break
        return entries

    def read_text(self, path: str) -> dict[str, object]:
        target = self._resolve(path, allow_root=False)
        if not target.is_file():
            raise FileNotFoundError("The requested workspace file does not exist.")
        size = target.stat().st_size
        if size > _MAX_READ_BYTES:
            raise ValueError("Files larger than 1 MiB cannot be read through this action.")
        data = target.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Only UTF-8 text files can be read through this action.") from exc
        return {"path": target.relative_to(self.root).as_posix(), "content": text}

    def find_files(
        self,
        query: str = "",
        extension: str = "",
        path: str = ".",
        limit: int = 50,
    ) -> list[str]:
        if not 1 <= limit <= 50:
            raise ValueError("Search result limit must be between 1 and 50.")
        start = self._resolve(path, allow_root=True)
        if not start.is_dir():
            raise NotADirectoryError("The requested workspace path is not a directory.")
        normalized_query = query.casefold()
        normalized_extension = extension.casefold()
        found: list[str] = []
        visited = 0
        for current, directories, filenames in os.walk(start, followlinks=False):
            current_path = Path(current)
            directories[:] = [
                name for name in directories
                if not name.startswith(".") and not self._is_link(current_path / name)
            ]
            for name in filenames:
                if name.startswith("."):
                    continue
                candidate = current_path / name
                visited += 1
                if visited > 10_000:
                    return found
                if self._is_link(candidate) or candidate.stat().st_nlink > 1:
                    continue
                if normalized_query not in name.casefold():
                    continue
                if normalized_extension and candidate.suffix.casefold() != normalized_extension:
                    continue
                found.append(candidate.relative_to(self.root).as_posix())
                if len(found) >= limit:
                    return found
        return found

    def create_directory(self, path: str) -> dict[str, str]:
        target = self._resolve(path, allow_root=False)
        with self._lock:
            if target.exists():
                raise WorkspaceConflictError("The requested path already exists.")
            if not target.parent.is_dir():
                raise FileNotFoundError("The parent directory must already exist.")
            target.mkdir(exist_ok=False)
            try:
                self._record({
                    "kind": "remove_empty_directory",
                    "path": self._relative(target),
                }, f"Created directory {self._relative(target)}")
            except Exception:
                target.rmdir()
                raise
        return {"path": self._relative(target), "status": "created"}

    def write_text(self, path: str, content: str) -> dict[str, str]:
        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_TEXT_BYTES:
            raise ValueError("Text content must be no larger than 1 MiB.")
        target = self._resolve(path, allow_root=False)
        with self._lock:
            if target.exists() and not target.is_file():
                raise WorkspaceConflictError("The target exists and is not a regular file.")
            previous = target.read_bytes() if target.exists() else None
            if previous is not None and len(previous) > _MAX_TEXT_BYTES:
                raise ValueError("Existing files larger than 1 MiB cannot be overwritten.")
            operation: dict[str, object]
            backup_path: Path | None = None
            if previous is None:
                operation = {
                    "kind": "remove_created_file",
                    "path": self._relative(target),
                    "after_sha256": self._sha256(encoded),
                }
            else:
                backup_name = f"{uuid4().hex}.bak"
                backup_path = self._backup_path(backup_name)
                self._atomic_write(backup_path, previous)
                operation = {
                    "kind": "restore_file",
                    "path": self._relative(target),
                    "backup": backup_name,
                    "after_sha256": self._sha256(encoded),
                }
            if not target.parent.is_dir():
                if backup_path is not None:
                    backup_path.unlink(missing_ok=True)
                raise FileNotFoundError("The parent directory must already exist.")
            self._atomic_write(target, encoded)
            try:
                self._record(operation, f"Wrote {self._relative(target)}")
            except Exception:
                if previous is None:
                    target.unlink(missing_ok=True)
                else:
                    self._atomic_write(target, previous)
                if backup_path is not None:
                    backup_path.unlink(missing_ok=True)
                raise
        return {"path": self._relative(target), "status": "written"}

    def move_file(self, source: str, destination: str) -> dict[str, str]:
        src = self._resolve(source, allow_root=False)
        dst = self._resolve(destination, allow_root=False)
        with self._lock:
            if not src.is_file():
                raise FileNotFoundError("The source must be an existing regular file.")
            if dst.is_dir():
                normalized_destination = destination.rstrip("/\\")
                dst = self._resolve(f"{normalized_destination}/{src.name}", allow_root=False)
            if dst.exists():
                raise WorkspaceConflictError("The destination already exists.")
            if src == dst or src in dst.parents:
                raise WorkspacePathError("A file cannot be moved into itself.")
            if not dst.parent.is_dir():
                raise FileNotFoundError("The destination directory must already exist.")
            before_hash = self._file_sha256(src)
            os.replace(src, dst)
            try:
                self._record({
                    "kind": "move_file_back",
                    "source": self._relative(src),
                    "destination": self._relative(dst),
                    "after_sha256": before_hash,
                }, f"Moved {self._relative(src)} to {self._relative(dst)}")
            except Exception:
                os.replace(dst, src)
                raise
        return {"source": self._relative(src), "destination": self._relative(dst)}

    def copy_file(self, source: str, destination: str) -> dict[str, str]:
        src = self._resolve(source, allow_root=False)
        dst = self._resolve(destination, allow_root=False)
        with self._lock:
            if not src.is_file():
                raise FileNotFoundError("The source must be an existing regular file.")
            if dst.is_dir():
                normalized_destination = destination.rstrip("/\\")
                dst = self._resolve(f"{normalized_destination}/{src.name}", allow_root=False)
            if dst.exists():
                raise WorkspaceConflictError("The destination already exists.")
            if not dst.parent.is_dir():
                raise FileNotFoundError("The destination directory must already exist.")
            if src.stat().st_size > _MAX_COPY_BYTES:
                raise ValueError("Files larger than 50 MiB cannot be copied through this action.")
            try:
                shutil.copyfile(src, dst)
                self._record({
                    "kind": "remove_created_file",
                    "path": self._relative(dst),
                    "after_sha256": self._file_sha256(dst),
                }, f"Copied {self._relative(src)} to {self._relative(dst)}")
            except Exception:
                dst.unlink(missing_ok=True)
                raise
        return {"source": self._relative(src), "destination": self._relative(dst)}

    def rename_file(self, path: str, new_name: str) -> dict[str, str]:
        src = self._resolve(path, allow_root=False)
        if not new_name or new_name in {".", ".."} or any(ch in new_name for ch in "/\\:"):
            raise WorkspacePathError("The new name must be a plain file name.")
        dst = self._resolve(f"{self._relative(src.parent)}/{new_name}", allow_root=False)
        with self._lock:
            if not src.is_file():
                raise FileNotFoundError("The source must be an existing regular file.")
            if dst.exists():
                raise WorkspaceConflictError("The destination already exists.")
            digest = self._file_sha256(src)
            os.replace(src, dst)
            try:
                self._record({
                    "kind": "move_file_back",
                    "source": self._relative(src),
                    "destination": self._relative(dst),
                    "after_sha256": digest,
                }, f"Renamed {self._relative(src)} to {new_name}")
            except Exception:
                os.replace(dst, src)
                raise
        return {"source": self._relative(src), "destination": self._relative(dst)}

    def trash_file(self, path: str) -> dict[str, str]:
        target = self._resolve(path, allow_root=False)
        with self._lock:
            if not target.is_file():
                raise FileNotFoundError("Only existing regular files can be moved to Alex Trash.")
            trash_name = f"{uuid4().hex}.trash"
            trash_path = self._undo_dir / trash_name
            os.replace(target, trash_path)
            try:
                self._record({
                    "kind": "restore_trashed_file",
                    "path": self._relative(target),
                    "trash": trash_name,
                }, f"Moved {self._relative(target)} to Alex Trash")
            except Exception:
                os.replace(trash_path, target)
                raise
        return {"path": self._relative(target), "status": "trashed"}

    def undo_history(self) -> list[dict[str, str]]:
        with self._lock:
            records = self._read_records()
            return [
                {"id": item["id"], "label": item["label"]}
                for item in reversed(records)
            ]

    def undo(self, operation_id: str | None = None) -> dict[str, str]:
        with self._lock:
            records = self._read_records()
            if not records:
                return {"status": "empty", "message": "There are no workspace changes to undo."}
            index = len(records) - 1
            if operation_id is not None:
                matches = [i for i, item in enumerate(records) if item["id"] == operation_id]
                if not matches:
                    raise KeyError("Undo entry not found or expired.")
                index = matches[0]
            record = records[index]
            operation = record["operation"]
            rollback = self._apply_undo(operation)
            del records[index]
            try:
                self._write_records(records)
            except Exception:
                rollback()
                raise
            self._cleanup_backup(operation)
            return {"status": "undone", "message": f"Undid: {record['label']}"}

    def _apply_undo(self, record: dict[str, object]) -> Callable[[], None]:
        kind = record["kind"]
        if kind == "remove_empty_directory":
            target = self._resolve(str(record["path"]), allow_root=False)
            if target.exists():
                target.rmdir()
                return lambda: target.mkdir()
            return lambda: None
        elif kind == "remove_created_file":
            target = self._resolve(str(record["path"]), allow_root=False)
            if target.exists():
                self._check_hash(target, str(record["after_sha256"]))
                content = target.read_bytes()
                target.unlink()
                return lambda: self._atomic_write(target, content)
            return lambda: None
        elif kind == "restore_file":
            target = self._resolve(str(record["path"]), allow_root=False)
            if not target.is_file():
                raise WorkspaceConflictError("The changed file no longer exists.")
            self._check_hash(target, str(record["after_sha256"]))
            backup = self._backup_path(str(record["backup"]))
            current = target.read_bytes()
            previous = backup.read_bytes()
            self._atomic_write(target, previous)
            return lambda: self._atomic_write(target, current)
        elif kind == "move_file_back":
            destination = self._resolve(str(record["destination"]), allow_root=False)
            source = self._resolve(str(record["source"]), allow_root=False)
            if not destination.is_file():
                raise WorkspaceConflictError("The moved file is no longer at its recorded destination.")
            self._check_hash(destination, str(record["after_sha256"]))
            if source.exists():
                raise WorkspaceConflictError("The original path is occupied; refusing to overwrite it.")
            if not source.parent.is_dir():
                raise WorkspaceConflictError("The original parent directory no longer exists.")
            os.replace(destination, source)
            return lambda: os.replace(source, destination)
        elif kind == "restore_trashed_file":
            trashed = self._backup_path(str(record["trash"]))
            target = self._resolve(str(record["path"]), allow_root=False)
            if target.exists():
                raise WorkspaceConflictError("The original path is occupied; refusing to overwrite it.")
            if not trashed.is_file():
                raise WorkspaceConflictError("The trashed file is no longer available.")
            if not target.parent.is_dir():
                raise WorkspaceConflictError("The original parent directory no longer exists.")
            os.replace(trashed, target)
            return lambda: os.replace(target, trashed)
        else:
            raise StorageError("Undo history contains an unsupported operation.")

    def _record(self, operation: dict[str, object], label: str) -> None:
        records = self._read_records()
        records.append({
            "id": uuid4().hex,
            "label": label[:200],
            "operation": operation,
        })
        removed = records[:-_UNDO_LIMIT]
        records = records[-_UNDO_LIMIT:]
        self._write_records(records)
        for item in removed:
            try:
                self._cleanup_backup(item["operation"])
            except OSError:
                logger.exception("Could not clean up expired workspace undo data")

    def _read_records(self) -> list[dict[str, object]]:
        document = self._store.read(_JOURNAL, {"version": 1, "entries": []})
        entries = document.get("entries")
        if document.get("version") != 1 or not isinstance(entries, list):
            raise StorageError("Workspace undo history is invalid.")
        if not all(
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and isinstance(item.get("label"), str)
            and isinstance(item.get("operation"), dict)
            for item in entries
        ):
            raise StorageError("Workspace undo history contains an invalid entry.")
        return entries

    def _write_records(self, records: list[dict[str, object]]) -> None:
        self._store.write(_JOURNAL, {"version": 1, "entries": records})

    def _cleanup_backup(self, record: dict[str, object]) -> None:
        for key in ("backup", "trash"):
            value = record.get(key)
            if isinstance(value, str):
                try:
                    path = self._backup_path(value)
                except StorageError:
                    logger.exception("Workspace undo history contains an invalid backup reference")
                    continue
                if path.is_file():
                    try:
                        path.unlink()
                    except OSError:
                        logger.exception("Could not remove workspace undo data %s", path.name)

    def _backup_path(self, name: str) -> Path:
        if Path(name).name != name or not name.endswith((".bak", ".trash")):
            raise StorageError("Workspace undo history contains an invalid backup reference.")
        return self._undo_dir / name

    def _resolve(self, raw_path: str, *, allow_root: bool) -> Path:
        if not isinstance(raw_path, str) or not raw_path or len(raw_path) > 1024:
            raise WorkspacePathError("Workspace path must contain 1 to 1024 characters.")
        normalized = raw_path.replace("\\", "/")
        pure = PurePosixPath(normalized)
        if pure.is_absolute() or any(part in {"..", ""} for part in normalized.split("/")):
            if raw_path != ".":
                raise WorkspacePathError("Absolute paths and parent-directory traversal are not allowed.")
        if ":" in normalized or normalized.startswith("//"):
            raise WorkspacePathError("Drive and network paths are not allowed.")
        parts = [] if raw_path == "." else [part for part in pure.parts if part not in {"", "."}]
        target = self.root.joinpath(*parts)
        cursor = self.root
        for part in parts:
            cursor = cursor / part
            if self._is_link(cursor):
                raise WorkspacePathError("Symbolic links are not allowed in the workspace.")
        resolved = target.resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise WorkspacePathError("Workspace path escapes the approved root.")
        if resolved.is_file() and resolved.stat().st_nlink > 1:
            raise WorkspacePathError("Hard-linked files are not allowed in the workspace.")
        if not allow_root and resolved == self.root:
            raise WorkspacePathError("The workspace root cannot be modified as a file.")
        return resolved

    def _relative(self, path: Path) -> str:
        if path == self.root:
            return "."
        return path.relative_to(self.root).as_posix()

    @staticmethod
    def _sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _check_hash(self, path: Path, expected: str) -> None:
        if not path.is_file() or self._file_sha256(path) != expected:
            raise WorkspaceConflictError(
                "The file changed after the action; refusing to overwrite newer data."
            )

    @staticmethod
    def _atomic_write(target: Path, content: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = stream.name
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _is_link(path: Path) -> bool:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        return bool(is_junction and is_junction())
