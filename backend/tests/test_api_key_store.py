"""
Unit tests for app.core.api_key_store and multi-tiered key resolution.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core import api_key_store
from app.core import gemini as core_gemini
from app.core.storage import JsonDocumentStore
from app.schemas.settings import SettingsUpdate
from app.services.settings_service import SettingsService


def test_resolve_key_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-test-key-1234567890")
    assert api_key_store.resolve_gemini_key() == "env-test-key-1234567890"
    assert api_key_store.is_configured() is True


def test_resolve_key_from_file(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with patch("keyring.get_password", return_value=None):
        config_file = tmp_path / "config" / "api_keys.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps({"gemini_api_key": "file-test-key-1234567890"}),
            encoding="utf-8",
        )

        with patch("app.core.api_key_store.get_config_search_paths", return_value=[config_file]):
            assert api_key_store.resolve_gemini_key() == "file-test-key-1234567890"
            assert api_key_store.is_configured() is True


def test_save_api_keys(tmp_path):
    target_file = tmp_path / "config" / "api_keys.json"
    with patch("app.core.api_key_store.get_primary_config_file", return_value=target_file):
        api_key_store.save_api_keys(
            gemini_api_key="new-key-1234567890",
            extra_fields={"assistant_name": "TEST_JARVIS", "voice_name": "Fenrir"},
        )
        assert target_file.exists()
        data = json.loads(target_file.read_text(encoding="utf-8"))
        assert data["gemini_api_key"] == "new-key-1234567890"
        assert data["assistant_name"] == "TEST_JARVIS"
        assert data["voice_name"] == "Fenrir"
        assert "os_system" in data


def test_settings_service_loads_and_saves_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    store = JsonDocumentStore(tmp_path)
    service = SettingsService(store)

    target_file = tmp_path / "config" / "api_keys.json"
    with patch("app.core.api_key_store.get_primary_config_file", return_value=target_file):
        with patch("app.core.api_key_store.get_config_search_paths", return_value=[target_file]):
            with patch("keyring.set_password") as mock_set:
                service.save_api_key("saved-key-abcdef-1234567890")
                assert mock_set.called

            assert service.api_key_configured() is True
            assert service.get_api_key_for_service() == "saved-key-abcdef-1234567890"

            # Verify core_gemini.api_key also resolves this key
            assert core_gemini.api_key(refresh=True) == "saved-key-abcdef-1234567890"

