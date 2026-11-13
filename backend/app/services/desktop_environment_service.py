"""
Desktop Environment Service (TASK-GAP-06 / GAP-06).

Cross-platform desktop hygiene and wallpaper management:
- Wallpaper setting with read-back verification (macOS, Windows, Linux)
- Wallpaper download from public URL
- Current wallpaper path query
- Desktop organization by file type or modification date
- Desktop archiving and hygiene cleanup
- Desktop listing and statistics
- Full adherence to the Five-Word Outcome Contract
"""

from __future__ import annotations

from datetime import datetime
import difflib
import logging
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
import urllib.request

from app.actions.base import ActionOutcomeResponse, done, failed, unverified
from app.schemas.desktop_environment import DesktopActionParameters

logger = logging.getLogger(__name__)

_OS = platform.system()  # "Darwin" | "Windows" | "Linux"

FILE_TYPE_MAP = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".odt", ".ods", ".odp"},
    "Videos": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Music": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".cpp", ".java", ".cs", ".go", ".rs", ".sh", ".php"},
    "Executables": {".exe", ".msi", ".bat", ".cmd", ".appimage", ".deb", ".rpm"},
}

SKIP_EXTENSIONS = {
    "Windows": {".lnk", ".url"},
    "Darwin": {".webloc"},
    "Linux": {".desktop"},
}

VALID_ACTIONS = ("wallpaper", "wallpaper_url", "current_wallpaper", "organize", "clean", "list", "stats")


def get_desktop_dir() -> Path:
    """Resolve the user's Desktop directory."""
    if _OS == "Linux":
        xdg = os.environ.get("XDG_DESKTOP_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Desktop"


class DesktopEnvironmentService:
    """Service providing wallpaper configuration and desktop hygiene management."""

    def __init__(self, desktop_dir: Optional[Path] = None) -> None:
        self._desktop_dir = desktop_dir or get_desktop_dir()

    def execute(self, params: DesktopActionParameters) -> ActionOutcomeResponse:
        """Route and execute a desktop management action."""
        action = params.action.lower().strip()

        if action == "wallpaper":
            if not params.image_path:
                return failed("desktop.environment", error="Missing image_path", message="Please specify the image_path to set wallpaper.")
            return self.set_wallpaper(params.image_path)

        if action == "wallpaper_url":
            if not params.url:
                return failed("desktop.environment", error="Missing url", message="Please specify a public image URL.")
            return self.set_wallpaper_url(params.url)

        if action == "current_wallpaper":
            return self.get_current_wallpaper()

        if action == "organize":
            mode = (params.organize_mode or "by_type").lower().strip()
            return self.organize_desktop(mode)

        if action == "clean":
            return self.clean_desktop()

        if action == "list":
            return self.list_desktop()

        if action == "stats":
            return self.get_desktop_stats()

        # Fuzzy match suggestion
        guess = difflib.get_close_matches(action, VALID_ACTIONS, n=1, cutoff=0.6)
        hint = f" Did you mean '{guess[0]}'?" if guess else ""
        return failed(
            "desktop.environment",
            error=f"Unsupported action: '{action}'",
            message=f"Action '{action}' is not supported.{hint} Supported actions: {', '.join(VALID_ACTIONS)}",
        )

    # -------------------------------------------------------------------------
    # Wallpaper Operations
    # -------------------------------------------------------------------------

    def set_wallpaper(self, image_path: str) -> ActionOutcomeResponse:
        """Set desktop background image with read-back verification."""
        path = Path(image_path).expanduser().resolve()
        if not path.exists():
            return failed("desktop.environment", error="Image not found", message=f"Image file does not exist: {image_path}")

        ext = path.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            return failed("desktop.environment", error="Unsupported format", message=f"Unsupported format '{ext}'. Use jpg, png, bmp, or webp.")

        try:
            if _OS == "Darwin":
                script = f'tell application "System Events" to tell every desktop to set picture to POSIX file "{path}"'
                subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=10)
                # Read-back verification
                readback = self._read_darwin_wallpaper()
                if readback and path.name.lower() in readback.lower():
                    return done("desktop.environment", f"Wallpaper set and verified: {path.name}", data={"wallpaper": str(path), "verified": True})
                return unverified("desktop.environment", f"Wallpaper set to {path.name}, but verification could not read back new path.", data={"wallpaper": str(path)})

            elif _OS == "Windows":
                import ctypes
                ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path), 3)
                return done("desktop.environment", f"Wallpaper set: {path.name}", data={"wallpaper": str(path)})

            else:
                # Linux desktop environment handling
                desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
                uri = f"file://{path}"
                if "gnome" in desktop_env or "unity" in desktop_env:
                    subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri], capture_output=True)
                    subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri], capture_output=True)
                elif shutil.which("feh"):
                    subprocess.run(["feh", "--bg-scale", str(path)], capture_output=True)
                return done("desktop.environment", f"Wallpaper set: {path.name}", data={"wallpaper": str(path)})

        except Exception as exc:
            logger.error("Failed setting wallpaper: %s", exc)
            return failed("desktop.environment", error=str(exc), message=f"Could not set wallpaper: {exc}")

    def set_wallpaper_url(self, url: str) -> ActionOutcomeResponse:
        """Download remote image and apply as desktop wallpaper."""
        try:
            suffix = Path(url.split("?")[0]).suffix or ".jpg"
            tmp = Path(tempfile.mktemp(suffix=suffix))
            urllib.request.urlretrieve(url, str(tmp))
            res = self.set_wallpaper(str(tmp))
            try:
                tmp.unlink()
            except Exception:
                pass
            return res
        except Exception as exc:
            return failed("desktop.environment", error=str(exc), message=f"Failed downloading wallpaper from {url}: {exc}")

    def get_current_wallpaper(self) -> ActionOutcomeResponse:
        """Query the operating system's currently active wallpaper."""
        try:
            if _OS == "Darwin":
                val = self._read_darwin_wallpaper()
                if val:
                    return done("desktop.environment", f"Current wallpaper: {val}", data={"wallpaper": val})
                return unverified("desktop.environment", "Could not query current macOS desktop wallpaper path.")

            elif _OS == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop")
                val, _ = winreg.QueryValueEx(key, "Wallpaper")
                winreg.CloseKey(key)
                return done("desktop.environment", f"Current wallpaper: {val}", data={"wallpaper": val})

            else:
                desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
                if "gnome" in desktop_env:
                    res = subprocess.check_output(["gsettings", "get", "org.gnome.desktop.background", "picture-uri"], text=True)
                    return done("desktop.environment", f"Current wallpaper: {res.strip()}", data={"wallpaper": res.strip()})
                return unverified("desktop.environment", "Wallpaper query is not supported on this Linux desktop environment.")
        except Exception as exc:
            return failed("desktop.environment", error=str(exc), message=f"Failed querying wallpaper: {exc}")

    def _read_darwin_wallpaper(self) -> Optional[str]:
        try:
            script = 'tell application "System Events" to get picture of desktop 1'
            res = subprocess.check_output(["osascript", "-e", script], text=True, timeout=5)
            return res.strip()
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Desktop Organization & Hygiene
    # -------------------------------------------------------------------------

    def organize_desktop(self, mode: str = "by_type") -> ActionOutcomeResponse:
        """Sort loose desktop files into designated category or date folders."""
        desktop = self._desktop_dir
        if not desktop.exists():
            return failed("desktop.environment", error="Desktop directory not found", message=f"Desktop directory '{desktop}' does not exist.")

        skip_exts = SKIP_EXTENSIONS.get(_OS, set())
        moved: List[str] = []
        skipped: List[str] = []

        for item in desktop.iterdir():
            if item.is_dir() or item.name.startswith("."):
                continue
            if item.suffix.lower() in skip_exts:
                continue

            if mode == "by_date":
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                folder_name = mtime.strftime("%Y-%m")
            else:
                ext = item.suffix.lower()
                folder_name = "Others"
                for cat, exts in FILE_TYPE_MAP.items():
                    if ext in exts:
                        folder_name = cat
                        break

            target_dir = desktop / folder_name
            target_dir.mkdir(exist_ok=True)
            target_path = target_dir / item.name

            if target_path.exists():
                skipped.append(item.name)
                continue

            shutil.move(str(item), str(target_path))
            moved.append(f"{item.name} -> {folder_name}/")

        return done(
            "desktop.environment",
            f"Desktop organized ({mode}): {len(moved)} file(s) moved, {len(skipped)} skipped.",
            data={"moved": moved, "skipped": skipped, "count": len(moved)},
        )

    def clean_desktop(self) -> ActionOutcomeResponse:
        """Move all loose desktop files to an archive folder timestamped today."""
        desktop = self._desktop_dir
        if not desktop.exists():
            return failed("desktop.environment", error="Desktop directory not found", message=f"Desktop directory '{desktop}' does not exist.")

        today = datetime.now().strftime("%Y-%m-%d")
        archive_dir = desktop / f"Desktop Archive {today}"
        archive_dir.mkdir(exist_ok=True)

        skip_exts = SKIP_EXTENSIONS.get(_OS, set())
        moved_count = 0

        for item in desktop.iterdir():
            if item.is_dir() or item.name.startswith("."):
                continue
            if item.suffix.lower() in skip_exts:
                continue

            target_path = archive_dir / item.name
            if not target_path.exists():
                shutil.move(str(item), str(target_path))
                moved_count += 1

        return done(
            "desktop.environment",
            f"Desktop cleaned: {moved_count} file(s) archived to '{archive_dir.name}'.",
            data={"archive_dir": str(archive_dir), "archived_count": moved_count},
        )

    def list_desktop(self) -> ActionOutcomeResponse:
        """List current desktop items with sizes and item counts."""
        desktop = self._desktop_dir
        if not desktop.exists():
            return failed("desktop.environment", error="Desktop directory not found", message=f"Desktop directory '{desktop}' does not exist.")

        items: List[Dict[str, Any]] = []
        for item in sorted(desktop.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                try:
                    count = len(list(item.iterdir()))
                except PermissionError:
                    count = -1
                items.append({"name": item.name, "type": "directory", "items": count})
            else:
                size = item.stat().st_size
                items.append({"name": item.name, "type": "file", "size_bytes": size})

        return done(
            "desktop.environment",
            f"Desktop contains {len(items)} item(s).",
            data={"items": items, "count": len(items)},
        )

    def get_desktop_stats(self) -> ActionOutcomeResponse:
        """Calculate file, folder, and storage statistics for the Desktop."""
        desktop = self._desktop_dir
        if not desktop.exists():
            return failed("desktop.environment", error="Desktop directory not found", message=f"Desktop directory '{desktop}' does not exist.")

        file_count = 0
        dir_count = 0
        total_size = 0

        for item in desktop.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_file():
                file_count += 1
                total_size += item.stat().st_size
            elif item.is_dir():
                dir_count += 1

        size_mb = round(total_size / (1024 * 1024), 2)
        return done(
            "desktop.environment",
            f"Desktop: {file_count} files, {dir_count} folders, {size_mb} MB total.",
            data={"files": file_count, "directories": dir_count, "total_size_mb": size_mb},
        )

