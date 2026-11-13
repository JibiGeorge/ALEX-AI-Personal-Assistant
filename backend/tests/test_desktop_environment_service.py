"""
Unit tests for DesktopEnvironmentService and desktop.environment action (TASK-GAP-06 / GAP-06).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.desktop_environment import register_desktop_environment_actions
from app.schemas.desktop_environment import DesktopActionParameters
from app.services.desktop_environment_service import DesktopEnvironmentService


def test_desktop_organize_by_type(tmp_path):
    # Populate mock desktop
    (tmp_path / "photo.png").write_bytes(b"image")
    (tmp_path / "notes.txt").write_bytes(b"notes")
    (tmp_path / "script.py").write_bytes(b"python")
    (tmp_path / "archive.zip").write_bytes(b"zip")

    service = DesktopEnvironmentService(desktop_dir=tmp_path)
    res = service.execute(DesktopActionParameters(action="organize", organize_mode="by_type"))

    assert res.status == ToolOutcome.DONE
    assert (tmp_path / "Images" / "photo.png").exists()
    assert (tmp_path / "Documents" / "notes.txt").exists()
    assert (tmp_path / "Code" / "script.py").exists()
    assert (tmp_path / "Archives" / "archive.zip").exists()
    assert res.data["count"] == 4


def test_desktop_clean(tmp_path):
    (tmp_path / "report.pdf").write_bytes(b"pdf")
    (tmp_path / "summary.docx").write_bytes(b"word")

    service = DesktopEnvironmentService(desktop_dir=tmp_path)
    res = service.execute(DesktopActionParameters(action="clean"))

    assert res.status == ToolOutcome.DONE
    assert res.data["archived_count"] == 2
    # Verify archive folder created
    archive_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and "Archive" in d.name]
    assert len(archive_dirs) == 1
    assert (archive_dirs[0] / "report.pdf").exists()


def test_desktop_list_and_stats(tmp_path):
    (tmp_path / "data.csv").write_bytes(b"1,2,3")
    (tmp_path / "subfolder").mkdir()

    service = DesktopEnvironmentService(desktop_dir=tmp_path)
    # List
    res_list = service.execute(DesktopActionParameters(action="list"))
    assert res_list.status == ToolOutcome.DONE
    assert res_list.data["count"] == 2

    # Stats
    res_stats = service.execute(DesktopActionParameters(action="stats"))
    assert res_stats.status == ToolOutcome.DONE
    assert res_stats.data["files"] == 1
    assert res_stats.data["directories"] == 1


def test_desktop_set_wallpaper_missing_file():
    service = DesktopEnvironmentService()
    res = service.execute(DesktopActionParameters(action="wallpaper", image_path="/path/to/missing_img.jpg"))

    assert res.status == ToolOutcome.FAILED
    assert "not exist" in res.message


def test_desktop_set_wallpaper_unsupported_ext(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("not an image")

    service = DesktopEnvironmentService(desktop_dir=tmp_path)
    res = service.execute(DesktopActionParameters(action="wallpaper", image_path=str(txt_file)))

    assert res.status == ToolOutcome.FAILED
    assert "Unsupported format" in res.message


@patch("subprocess.run")
def test_desktop_set_wallpaper_darwin_success(mock_sub, tmp_path):
    img_file = tmp_path / "scenery.jpg"
    img_file.write_bytes(b"\xff\xd8\xff")

    service = DesktopEnvironmentService(desktop_dir=tmp_path)
    with patch("app.services.desktop_environment_service._OS", "Darwin"), \
         patch.object(service, "_read_darwin_wallpaper", return_value="/Users/user/Desktop/scenery.jpg"):

        res = service.execute(DesktopActionParameters(action="wallpaper", image_path=str(img_file)))

        assert res.status == ToolOutcome.DONE
        assert "verified" in res.message.lower()


def test_desktop_unknown_action():
    service = DesktopEnvironmentService()
    res = service.execute(DesktopActionParameters(action="organise"))

    assert res.status == ToolOutcome.FAILED
    assert "Did you mean 'organize'?" in res.message


def test_desktop_action_registry_integration():
    service = DesktopEnvironmentService()
    registry = ActionRegistry()
    register_desktop_environment_actions(registry, service)

    defn = registry.get("desktop.environment")
    assert defn is not None
    assert defn.category == "system"
    assert defn.requires_confirmation is False

    view = defn.public_view()
    assert view["action_id"] == "desktop.environment"

