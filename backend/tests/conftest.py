import os
import pytest


@pytest.fixture(autouse=True)
def isolate_api_key_config(monkeypatch, tmp_path_factory):
    """Ensure backend unit tests run in isolated config sandbox by default."""
    # Only isolate if caller hasn't explicitly set a test config file
    if "ALEX_CONFIG_FILE" not in os.environ:
        tmp = tmp_path_factory.mktemp("config_isolation")
        monkeypatch.setenv("ALEX_CONFIG_FILE", str(tmp / "empty_keys.json"))

