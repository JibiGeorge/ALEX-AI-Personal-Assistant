import logging
import os
from typing import Any

import keyring
from pydantic import ValidationError

from app.core import gemini as core_gemini
from app.core.api_key_store import (
    is_configured as store_is_configured,
    load_api_keys,
    resolve_gemini_key,
    save_api_keys,
)
from app.core.storage import JsonDocumentStore, StorageError
from app.schemas.settings import AppSettings, SettingsUpdate

logger = logging.getLogger(__name__)
_DOCUMENT = "settings.json"
_SERVICE_NAME = "Alex"
_GEMINI_KEY_NAME = "gemini-api-key"


class CredentialStoreError(RuntimeError):
    """Raised when the operating system credential store is unavailable."""


class SettingsService:
    def __init__(self, store: JsonDocumentStore):
        self._store = store

    def get(self) -> tuple[AppSettings, bool]:
        document = self._store.read(_DOCUMENT, {"version": 1, "values": {}})
        values = dict(document.get("values", {}))

        # Overlay defaults from config/api_keys.json if present
        cfg = load_api_keys()
        if "assistant_name" not in values and cfg.get("assistant_name"):
            values["assistant_name"] = cfg["assistant_name"]
        if "user_name" not in values and cfg.get("user_name"):
            values["user_name"] = cfg["user_name"]
        if "voice_name" not in values and cfg.get("voice_name"):
            values["voice_name"] = cfg["voice_name"]
        if "hud_style" not in values and cfg.get("hud_style"):
            values["hud_style"] = cfg["hud_style"]

        try:
            settings = AppSettings.model_validate(values)
        except ValidationError as exc:
            raise StorageError("Stored application settings are invalid") from exc
        return settings, self.api_key_configured()

    def update(self, patch: SettingsUpdate) -> tuple[AppSettings, bool]:
        document = self._store.read(_DOCUMENT, {"version": 1, "values": {}})
        current = AppSettings.model_validate(document.get("values", {}))
        values = current.model_dump()
        values.update(patch.model_dump(exclude_unset=True, exclude_none=True))
        settings = AppSettings.model_validate(values)
        self._store.write(
            _DOCUMENT,
            {"version": 1, "values": settings.model_dump()},
        )

        # Sync relevant values to api_keys.json to keep Mark-LVI parity
        try:
            extra: dict[str, Any] = {}
            if patch.assistant_name is not None:
                extra["assistant_name"] = patch.assistant_name
            if patch.user_name is not None:
                extra["user_name"] = patch.user_name
            if patch.voice_name is not None:
                extra["voice_name"] = patch.voice_name
            if patch.hud_style is not None:
                extra["hud_style"] = patch.hud_style
            if patch.operating_system is not None:
                extra["os_system"] = "mac" if patch.operating_system == "macOS" else patch.operating_system.lower()
            if extra:
                save_api_keys(extra_fields=extra)
        except Exception as exc:
            logger.debug("Failed to sync settings to api_keys.json: %s", exc)

        return settings, self.api_key_configured()

    def api_key_configured(self) -> bool:
        if os.environ.get("GEMINI_API_KEY"):
            return True
        return store_is_configured()

    def save_api_key(self, api_key: str) -> bool:
        key = api_key.strip()
        if not key:
            raise ValueError("API key cannot be blank")

        file_saved = False
        keyring_saved = False

        # 1. Save to config/api_keys.json (Mark-LVI standard)
        try:
            save_api_keys(gemini_api_key=key)
            file_saved = True
        except Exception as exc:
            logger.warning("Failed to save api key to config file: %s", exc)

        # 2. Save to OS Keyring
        try:
            keyring.set_password(_SERVICE_NAME, _GEMINI_KEY_NAME, key)
            keyring_saved = True
        except Exception as exc:
            logger.warning("OS Credential store write failed: %s", exc)

        # 3. Invalidate core gemini cached key
        try:
            core_gemini.api_key(refresh=True)
        except Exception:
            pass

        if not file_saved and not keyring_saved:
            raise CredentialStoreError("Unable to persist API key to config file or OS credential store")

        return True

    def get_api_key_for_service(self) -> str | None:
        """Backend-only access for model services; never return through an API."""
        return resolve_gemini_key()
