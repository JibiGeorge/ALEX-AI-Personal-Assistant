import logging
from datetime import date
from typing import Any

from pydantic import ValidationError

from app.core.storage import JsonDocumentStore, StorageError
from app.schemas.memory import MemoryCategory, MemoryEntry, MemoryWrite

logger = logging.getLogger(__name__)
_DOCUMENT = "memory.json"
_CATEGORIES: tuple[MemoryCategory, ...] = (
    "identity",
    "preferences",
    "projects",
    "relationships",
    "wishes",
    "notes",
)


class MemoryService:
    def __init__(self, store: JsonDocumentStore):
        self._store = store

    def list_entries(self) -> list[MemoryEntry]:
        document = self._store.read(_DOCUMENT, {"version": 1, "entries": {}})
        raw_entries = document.get("entries", {})
        if not isinstance(raw_entries, dict):
            raise StorageError("Stored memory entries must be an object")

        result: list[MemoryEntry] = []
        try:
            for category, items in raw_entries.items():
                if category not in _CATEGORIES or not isinstance(items, dict):
                    raise StorageError("Stored memory contains an invalid category")
                for key, entry in items.items():
                    if not isinstance(entry, dict):
                        raise StorageError("Stored memory entry must be an object")
                    result.append(
                        MemoryEntry(
                            category=category,
                            key=key,
                            value=entry["value"],
                            updated=entry["updated"],
                        )
                    )
        except (KeyError, ValidationError, TypeError) as exc:
            raise StorageError("Stored memory entry is invalid") from exc
        return sorted(result, key=lambda item: (item.category, item.key.casefold()))

    def search_entries(
        self,
        query: str,
        category: MemoryCategory | None = None,
    ) -> list[MemoryEntry]:
        clean_query = query.strip().casefold()
        if not clean_query:
            return []

        all_entries = self.list_entries()
        scored: list[tuple[int, MemoryEntry]] = []

        for entry in all_entries:
            if category is not None and entry.category != category:
                continue

            key_cf = entry.key.casefold()
            val_cf = entry.value.casefold()

            score = 0
            if key_cf == clean_query:
                score += 100
            elif key_cf.startswith(clean_query):
                score += 80
            elif clean_query in key_cf:
                score += 60

            if val_cf == clean_query:
                score += 50
            elif clean_query in val_cf:
                score += 40

            if score > 0:
                scored.append((score, entry))

        # Sort descending by score, then category, then key
        scored.sort(key=lambda pair: (-pair[0], pair[1].category, pair[1].key.casefold()))
        return [entry for _, entry in scored]

    def upsert(
        self,
        category: MemoryCategory,
        key: str,
        item: MemoryWrite,
    ) -> MemoryEntry:
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError("Memory key cannot be blank")
        document = self._store.read(_DOCUMENT, {"version": 1, "entries": {}})
        entries = document.get("entries", {})
        if not isinstance(entries, dict):
            raise StorageError("Stored memory entries must be an object")
        category_entries = entries.setdefault(category, {})
        if not isinstance(category_entries, dict):
            raise StorageError("Stored memory category must be an object")

        value = item.value.strip()
        if not value:
            raise ValueError("Memory value cannot be blank")
        updated = date.today()
        category_entries[normalized_key] = {
            "value": value,
            "updated": updated.isoformat(),
        }
        self._store.write(_DOCUMENT, {"version": 1, "entries": entries})
        return MemoryEntry(
            category=category,
            key=normalized_key,
            value=value,
            updated=updated,
        )

    def delete(self, category: MemoryCategory, key: str) -> bool:
        document = self._store.read(_DOCUMENT, {"version": 1, "entries": {}})
        entries = document.get("entries", {})
        category_entries = entries.get(category, {})
        if not isinstance(category_entries, dict):
            raise StorageError("Stored memory category must be an object")
        if key not in category_entries:
            return False
        del category_entries[key]
        if not category_entries:
            entries.pop(category, None)
        self._store.write(_DOCUMENT, {"version": 1, "entries": entries})
        return True
