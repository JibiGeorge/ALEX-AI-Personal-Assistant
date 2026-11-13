import pytest
from app.core.storage import JsonDocumentStore
from app.schemas.memory import MemoryWrite
from app.services.memory_service import MemoryService


def test_memory_service_crud_and_search(tmp_path):
    store = JsonDocumentStore(tmp_path)
    service = MemoryService(store)

    assert service.list_entries() == []

    # Insert items
    service.upsert("preferences", "editor", MemoryWrite(value="VSCode"))
    service.upsert("preferences", "shell", MemoryWrite(value="Powershell"))
    service.upsert("projects", "alex", MemoryWrite(value="Desktop assistant project"))
    service.upsert("identity", "preferred_editor", MemoryWrite(value="VSCode"))

    entries = service.list_entries()
    assert len(entries) == 4

    # Search: exact key match should score higher
    res_editor = service.search_entries("editor")
    assert len(res_editor) >= 2
    assert res_editor[0].key == "editor"

    # Search: value match
    res_project = service.search_entries("assistant")
    assert len(res_project) == 1
    assert res_project[0].key == "alex"

    # Search with category filter
    res_filtered = service.search_entries("VSCode", category="identity")
    assert len(res_filtered) == 1
    assert res_filtered[0].category == "identity"

    # Search empty string returns empty list
    assert service.search_entries("   ") == []

    # Delete
    assert service.delete("preferences", "editor") is True
    assert service.delete("preferences", "editor") is False
    assert len(service.list_entries()) == 3

