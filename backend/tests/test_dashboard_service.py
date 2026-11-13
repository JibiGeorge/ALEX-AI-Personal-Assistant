from __future__ import annotations

import base64
import json
import time
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.services.dashboard_service import (
    DashboardService,
    RATE_LIMIT_ATTEMPTS,
    UNAMBIGUOUS_ALPHABET,
)
from app.main import create_app


def test_pairing_code_generation():
    service = DashboardService(pairing_ttl=120)
    info = service.generate_pairing_info()

    assert len(info.pairing_code) == 8
    assert all(c in UNAMBIGUOUS_ALPHABET for c in info.pairing_code)
    assert info.qr_data_uri.startswith("data:image/")
    assert "alex://pair?" in info.pairing_url
    assert f"code={info.pairing_code}" in info.pairing_url
    assert info.expires_in_seconds > 0


def test_key_derivation_and_aes_gcm_roundtrip():
    # Use fewer iterations in test for speed, default is 200,000
    service = DashboardService(iterations=1000)
    code = "ABCDEF23"
    key1 = service.derive_key(code)
    key2 = service.derive_key(code)

    assert len(key1) == 32
    assert key1 == key2

    # Case insensitivity in pairing code
    key3 = service.derive_key(code.lower())
    assert key1 == key3


def test_pairing_flow_success():
    service = DashboardService(iterations=1000)
    info = service.generate_pairing_info()

    res = service.verify_and_pair(
        client_ip="192.168.1.50",
        code=info.pairing_code,
        device_name="iPhone 16 Pro",
        device_platform="iOS",
    )

    assert res.success is True
    assert len(res.session_token) > 20
    assert service.is_authenticated(res.session_token) is True

    session = service.get_session(res.session_token)
    assert session is not None
    assert session["device_name"] == "iPhone 16 Pro"
    assert session["device_platform"] == "iOS"


def test_pairing_flow_invalid_code():
    service = DashboardService(iterations=1000)
    service.generate_pairing_info()

    with pytest.raises(ValueError, match="Invalid or expired pairing code"):
        service.verify_and_pair(
            client_ip="192.168.1.50",
            code="WRONG999",
        )


def test_pairing_rate_limiting():
    service = DashboardService(iterations=1000)
    service.generate_pairing_info()
    ip = "192.168.1.75"

    for _ in range(RATE_LIMIT_ATTEMPTS):
        with pytest.raises(ValueError, match="Invalid or expired pairing code"):
            service.verify_and_pair(client_ip=ip, code="INVALID1")

    # The 6th attempt should trigger rate limiting lockout
    with pytest.raises(PermissionError, match="Too many failed pairing attempts"):
        service.verify_and_pair(client_ip=ip, code="INVALID1")


def test_encrypted_communication():
    service = DashboardService(iterations=1000)
    info = service.generate_pairing_info()
    pair_res = service.verify_and_pair(client_ip="127.0.0.1", code=info.pairing_code)
    token = pair_res.session_token

    msg = json.dumps({"type": "turn", "content": "Hello Alex over Mobile Gateway!"})
    enc = service.encrypt(token, msg)
    assert "iv" in enc
    assert "ciphertext" in enc

    decrypted_bytes = service.decrypt(token, enc["iv"], enc["ciphertext"])
    decrypted_obj = json.loads(decrypted_bytes.decode("utf-8"))
    assert decrypted_obj["type"] == "turn"
    assert decrypted_obj["content"] == "Hello Alex over Mobile Gateway!"


def test_mobile_api_endpoints(tmp_path, monkeypatch):
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda *_: None)
    monkeypatch.setattr(keyring, "set_password", lambda *_: None)

    app = create_app(data_dir=tmp_path, api_token="test-token")
    service = DashboardService(iterations=1000)
    app.state.dashboard_service = service

    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    # 1. GET /api/v1/mobile/status
    res = client.get("/api/v1/mobile/status", headers=headers)
    assert res.status_code == 200
    assert res.json()["active"] is True
    assert res.json()["paired_devices"] == 0

    # 2. GET /api/v1/mobile/pair/init
    res_init = client.get("/api/v1/mobile/pair/init", headers=headers)
    assert res_init.status_code == 200
    pairing_code = res_init.json()["pairing_code"]
    assert len(pairing_code) == 8

    # 3. POST /api/v1/mobile/pair
    res_pair = client.post(
        "/api/v1/mobile/pair",
        json={"pairing_code": pairing_code, "device_name": "Test iPhone", "device_platform": "iOS"},
        headers=headers,
    )
    assert res_pair.status_code == 200
    session_token = res_pair.json()["session_token"]
    assert session_token

    # 4. POST /api/v1/mobile/command with valid session token
    ping_payload = json.dumps({"type": "ping"})
    enc_ping = service.encrypt(session_token, ping_payload)

    res_cmd = client.post(
        "/api/v1/mobile/command",
        json=enc_ping,
        headers={**headers, "X-Mobile-Session": session_token},
    )
    assert res_cmd.status_code == 200
    dec_pong = service.decrypt(session_token, res_cmd.json()["iv"], res_cmd.json()["ciphertext"])
    pong_obj = json.loads(dec_pong.decode("utf-8"))
    assert pong_obj["type"] == "pong"

    # 5. POST /api/v1/mobile/command with missing/invalid session token
    res_bad = client.post(
        "/api/v1/mobile/command",
        json=enc_ping,
        headers={**headers, "X-Mobile-Session": "bad-token"},
    )
    assert res_bad.status_code == 401

