import asyncio
import keyring
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.storage import JsonDocumentStore
from app.services.memory_service import MemoryService
from app.services.reminder_service import ReminderService
from app.services.settings_service import SettingsService
from app.services.system_metrics_service import SystemMetricsService
from app.services.system_verification_service import SystemVerificationService


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(keyring, "get_password", lambda *_: None)
    monkeypatch.setattr(keyring, "set_password", lambda *_: None)
    monkeypatch.setenv("ALEX_CONFIG_FILE", str(tmp_path / "config" / "api_keys.json"))
    app = create_app(data_dir=tmp_path, api_token="test-token")
    with TestClient(app) as test_client:
        yield test_client


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_system_verification_service_direct_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(keyring, "get_password", lambda *_: None)
    monkeypatch.setattr(keyring, "set_password", lambda *_: None)
    monkeypatch.setenv("ALEX_CONFIG_FILE", str(tmp_path / "config" / "api_keys.json"))

    store = JsonDocumentStore(tmp_path)
    settings_service = SettingsService(tmp_path / "settings.json")
    system_metrics = SystemMetricsService()
    memory_service = MemoryService(store)
    reminder_service = ReminderService(store)

    service = SystemVerificationService(
        settings_service=settings_service,
        system_metrics_service=system_metrics,
        memory_service=memory_service,
        reminder_service=reminder_service,
    )

    report = asyncio.run(service.verify_all())

    # Hardware assertions
    assert report.hardware.os_name in ["macOS", "Windows", "Linux"]
    assert report.hardware.cpu_logical_cores >= 1
    assert report.hardware.ram_total_gb > 0
    assert report.hardware.ram_available_gb >= 0
    assert report.hardware.disk_total_gb > 0
    assert report.hardware.process_count >= 1
    assert report.hardware.uptime_seconds >= 0

    # Application assertions
    assert report.application.app_name == "ALEX"
    assert report.application.python_version
    assert report.application.python_executable
    assert report.application.fastapi_version
    assert "fastapi" in report.application.dependencies_installed
    assert report.application.workspace_readable is True
    assert report.application.workspace_writable is True
    assert report.application.secrets_sanitized is True

    # Backend & Database assertions
    assert report.backend_database.backend_online is True
    assert report.backend_database.loopback_endpoint == "127.0.0.1:8765"
    assert "JSON Document Store" in report.backend_database.database_type
    assert report.backend_database.memory_store_accessible is True
    assert report.backend_database.reminder_store_accessible is True

    # AI Engine assertions
    assert report.ai_engines.cloud_provider == "Google Gemini"
    assert isinstance(report.ai_engines.ollama_installed, bool)
    assert isinstance(report.ai_engines.ollama_running, bool)
    assert isinstance(report.ai_engines.cloud_credentials_configured, bool)

    # Score
    assert 0 <= report.overall_score <= 100
    assert report.status in ["nominal", "warning", "error"]


def test_system_verification_api_endpoint(client):
    response = client.get("/api/v1/system/verification", headers=auth_headers())
    assert response.status_code == 200
    data = response.json()

    assert "hardware" in data
    assert "application" in data
    assert "backend_database" in data
    assert "ai_engines" in data
    assert "overall_score" in data
    assert data["hardware"]["cpu_logical_cores"] >= 1
    assert data["application"]["app_name"] == "ALEX"
    assert data["backend_database"]["loopback_endpoint"] == "127.0.0.1:8765"
