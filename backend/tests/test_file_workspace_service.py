import os

import pytest

from app.core.storage import StorageError
from app.services.file_workspace_service import (
    FileWorkspaceService,
    WorkspaceConflictError,
    WorkspacePathError,
)


def test_workspace_reads_lists_and_searches_bounded_text_files(tmp_path):
    service = FileWorkspaceService(tmp_path)
    (service.root / "notes").mkdir()
    (service.root / "notes" / "hello.txt").write_text("hello", encoding="utf-8")
    (service.root / ".private.txt").write_text("secret", encoding="utf-8")

    assert service.list_directory(".") == [{
        "name": "notes",
        "path": "notes",
        "kind": "directory",
        "size_bytes": None,
    }]
    assert service.read_text("notes/hello.txt") == {
        "path": "notes/hello.txt",
        "content": "hello",
    }
    assert service.find_files("hello", ".txt") == ["notes/hello.txt"]
    assert service.find_files() == ["notes/hello.txt"]


@pytest.mark.parametrize("path", [
    "../outside.txt",
    "folder/../../outside.txt",
    "/absolute.txt",
    "C:\\outside.txt",
    "\\\\server\\share\\outside.txt",
    "nested//file.txt",
])
def test_workspace_rejects_paths_outside_or_ambiguous(tmp_path, path):
    service = FileWorkspaceService(tmp_path)
    with pytest.raises(WorkspacePathError):
        service.read_text(path)


def test_workspace_rejects_symlinks(tmp_path):
    service = FileWorkspaceService(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    link = service.root / "linked.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("This platform does not allow creating file symlinks.")

    with pytest.raises(WorkspacePathError):
        service.read_text("linked.txt")
    assert service.list_directory(".") == []


def test_workspace_rejects_hard_linked_files(tmp_path):
    service = FileWorkspaceService(tmp_path)
    original = tmp_path / "outside.txt"
    original.write_text("private", encoding="utf-8")
    linked = service.root / "linked.txt"
    try:
        os.link(original, linked)
    except OSError:
        pytest.skip("This platform does not allow creating hard links.")

    with pytest.raises(WorkspacePathError, match="Hard-linked"):
        service.read_text("linked.txt")
    assert service.list_directory(".") == []


def test_file_mutations_can_be_undone_and_survive_service_restart(tmp_path):
    service = FileWorkspaceService(tmp_path)
    service.write_text("draft.txt", "first")
    service.write_text("draft.txt", "second")
    service.create_directory("notes")
    service.move_file("draft.txt", "notes/moved.txt")
    service.copy_file("notes/moved.txt", "copy.txt")
    service.rename_file("copy.txt", "renamed.txt")
    service.trash_file("renamed.txt")

    restarted = FileWorkspaceService(tmp_path)
    assert len(restarted.undo_history()) == 7
    for _ in range(7):
        assert restarted.undo()["status"] == "undone"

    assert not (restarted.root / "draft.txt").exists()
    assert not (restarted.root / "notes").exists()
    assert not (restarted.root / "copy.txt").exists()
    assert not (restarted.root / "renamed.txt").exists()
    assert restarted.undo_history() == []


def test_undo_refuses_to_overwrite_a_file_changed_after_write(tmp_path):
    service = FileWorkspaceService(tmp_path)
    service.write_text("draft.txt", "original")
    (service.root / "draft.txt").write_text("external edit", encoding="utf-8")

    with pytest.raises(WorkspaceConflictError, match="changed after"):
        service.undo()
    assert (service.root / "draft.txt").read_text(encoding="utf-8") == "external edit"
    assert len(service.undo_history()) == 1


def test_failed_journal_write_rolls_back_file_mutation(tmp_path, monkeypatch):
    service = FileWorkspaceService(tmp_path)

    def fail_record(*_):
        raise StorageError("journal unavailable")

    monkeypatch.setattr(service, "_record", fail_record)
    with pytest.raises(StorageError, match="journal unavailable"):
        service.write_text("draft.txt", "untracked")
    assert not (service.root / "draft.txt").exists()


def test_failed_undo_journal_write_rolls_back_the_undo(tmp_path, monkeypatch):
    service = FileWorkspaceService(tmp_path)
    service.write_text("draft.txt", "tracked")

    def fail_write(_):
        raise StorageError("journal unavailable")

    monkeypatch.setattr(service, "_write_records", fail_write)
    with pytest.raises(StorageError, match="journal unavailable"):
        service.undo()

    assert (service.root / "draft.txt").read_text(encoding="utf-8") == "tracked"
    assert len(service.undo_history()) == 1


def test_undo_history_is_limited_to_ten_entries(tmp_path):
    service = FileWorkspaceService(tmp_path)
    for index in range(11):
        service.write_text(f"file-{index}.txt", str(index))

    assert len(service.undo_history()) == 10
    assert (service.root / "file-0.txt").exists()
