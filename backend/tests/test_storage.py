import json

import pytest

from app.core.storage import JsonDocumentStore, StorageError


def test_store_writes_json_atomically(tmp_path):
    store = JsonDocumentStore(tmp_path)
    store.write("sample.json", {"ok": True})
    assert store.read("sample.json", {}) == {"ok": True}
    assert list(tmp_path.iterdir()) == [tmp_path / "sample.json"]


def test_store_reports_corrupt_json(tmp_path):
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    store = JsonDocumentStore(tmp_path)
    with pytest.raises(StorageError, match="Could not read"):
        store.read("broken.json", {})


def test_store_rejects_path_filename(tmp_path):
    store = JsonDocumentStore(tmp_path)
    with pytest.raises(ValueError, match="simple names"):
        store.read("../outside.json", {})
