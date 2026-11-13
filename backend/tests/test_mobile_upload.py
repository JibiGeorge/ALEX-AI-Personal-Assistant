from __future__ import annotations

import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.dashboard_service import DashboardService


@pytest.fixture
def mobile_client_setup(tmp_path, monkeypatch):
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda *_: None)
    monkeypatch.setattr(keyring, "set_password", lambda *_: None)

    app = create_app(data_dir=tmp_path, api_token="test-api-token")
    dashboard = DashboardService(iterations=1000)
    app.state.dashboard_service = dashboard

    # Pair a test mobile device
    info = dashboard.generate_pairing_info()
    pair_res = dashboard.verify_and_pair(
        client_ip="127.0.0.1",
        code=info.pairing_code,
        device_name="Test Phone",
        device_platform="iOS",
    )
    assert pair_res.success is True
    session_token = pair_res.session_token

    client = TestClient(app)
    return client, session_token, tmp_path / "uploads"


def test_mobile_file_upload_success(mobile_client_setup):
    client, session_token, uploads_dir = mobile_client_setup

    file_content = b"Hello, this is a test document uploaded from mobile companion."
    files = {"file": ("report.txt", io.BytesIO(file_content), "text/plain")}

    response = client.post(
        "/api/v1/mobile/upload",
        files=files,
        headers={"X-Mobile-Session": session_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["filename"] == "report.txt"
    assert data["size"] == len(file_content)

    saved_file = Path(data["saved_path"])
    assert saved_file.exists()
    assert saved_file.read_bytes() == file_content


def test_mobile_file_upload_sanitization_and_deduplication(mobile_client_setup):
    client, session_token, uploads_dir = mobile_client_setup

    # Path traversal attack attempt
    files = {"file": ("../../malicious.sh", io.BytesIO(b"echo 1"), "application/x-sh")}
    response = client.post(
        "/api/v1/mobile/upload",
        files=files,
        headers={"X-Mobile-Session": session_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "malicious.sh"
    assert ".." not in data["saved_path"]

    # Second upload with same name should deduplicate to malicious_1.sh
    files2 = {"file": ("malicious.sh", io.BytesIO(b"echo 2"), "application/x-sh")}
    res2 = client.post(
        "/api/v1/mobile/upload",
        files=files2,
        headers={"X-Mobile-Session": session_token},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["filename"] == "malicious_1.sh"


def test_mobile_list_and_download_uploads(mobile_client_setup):
    client, session_token, uploads_dir = mobile_client_setup

    # Upload two files
    f1 = io.BytesIO(b"File 1 content")
    f2 = io.BytesIO(b"File 2 content")
    client.post(
        "/api/v1/mobile/upload",
        files={"file": ("first.txt", f1, "text/plain")},
        headers={"X-Mobile-Session": session_token},
    )
    client.post(
        "/api/v1/mobile/upload",
        files={"file": ("second.txt", f2, "text/plain")},
        headers={"X-Mobile-Session": session_token},
    )

    # List uploads
    res = client.get(
        "/api/v1/mobile/uploads",
        headers={"X-Mobile-Session": session_token},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    filenames = [u["filename"] for u in data["uploads"]]
    assert "first.txt" in filenames
    assert "second.txt" in filenames

    # Download one
    dl_res = client.get(
        "/api/v1/mobile/uploads/first.txt",
        headers={"X-Mobile-Session": session_token},
    )
    assert dl_res.status_code == 200
    assert dl_res.content == b"File 1 content"


def test_legacy_upload_aliases(mobile_client_setup):
    client, session_token, _ = mobile_client_setup

    files = {"file": ("legacy.dat", io.BytesIO(b"legacy content"), "application/octet-stream")}
    res = client.post(
        "/api/upload",
        files=files,
        headers={"X-Mobile-Session": session_token},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "legacy.dat"

    # Download via legacy route
    dl_res = client.get(
        "/uploads/legacy.dat",
        headers={"X-Mobile-Session": session_token},
    )
    assert dl_res.status_code == 200
    assert dl_res.content == b"legacy content"


def test_mobile_upload_unauthorized_when_invalid_session(mobile_client_setup):
    client, _, _ = mobile_client_setup

    files = {"file": ("unauth.txt", io.BytesIO(b"secret"), "text/plain")}
    res = client.post(
        "/api/v1/mobile/upload",
        files=files,
        headers={"X-Mobile-Session": "invalid-session-token"},
    )
    assert res.status_code == 401
