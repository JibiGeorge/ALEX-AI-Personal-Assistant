from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    data_dir: Path | None = None
    api_token: str | None = None
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="ALEX_",
        env_file=".env",
        extra="ignore",
    )

    def resolved_data_dir(self) -> Path:
        if self.data_dir is not None:
            return self.data_dir.expanduser().resolve()

        if app_data := _platform_data_dir():
            return app_data / "Alex"
        return Path.home() / ".alex"


def _platform_data_dir() -> Path | None:
    import os
    import sys

    if sys.platform == "win32":
        value = os.environ.get("APPDATA")
        return Path(value) if value else None
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    value = os.environ.get("XDG_DATA_HOME")
    return Path(value) if value else Path.home() / ".local" / "share"


@lru_cache(maxsize=1)
def get_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings()
