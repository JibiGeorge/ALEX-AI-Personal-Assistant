from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.actions.action_executor import ActionExecutor
from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, done
from app.main import create_app
from app.schemas.mobile import ActionApprovalDecision
from app.services.dashboard_service import DashboardService


class DummyParams(BaseModel):
    target: str = "production-database"


def dummy_confirm_handler(params: DummyParams) -> ActionOutcomeResponse:
    return done(action="test.confirm_action", message=f"Executed on {params.target}")


@pytest.fixture
def approval_setup(tmp_path, monkeypatch):
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda *_: None)
    monkeypatch.setattr(keyring, "set_password", lambda *_: None)

    app = create_app(data_dir=tmp_path, api_token="test-secret-token")
    dashboard = DashboardService(iterations=1000)
    app.state.dashboard_service = dashboard

    # Register a confirmation-requiring action
    registry = app.state.action_registry
    registry.register(
        ActionDefinition(
            action_id="test.confirm_action",
            name="Confirm Action",
            description="Action that strictly requires user confirmation",
            category="test",
            parameters=DummyParams,
            handler=dummy_confirm_handler,
            requires_confirmation=True,
        )
    )

    executor = ActionExecutor(registry)
    executor.set_remote_authorizer(dashboard)
    app.state.action_executor = executor

    # Pair a test mobile device
    info = dashboard.generate_pairing_info()
    pair_res = dashboard.verify_and_pair(
        client_ip="127.0.0.1",
        code=info.pairing_code,
        device_name="Test iPhone",
        device_platform="iOS",
    )
    token = pair_res.session_token

    client = TestClient(app)
    return {
        "app": app,
        "client": client,
        "dashboard": dashboard,
        "executor": executor,
        "token": token,
        "headers": {"X-Mobile-Session": token},
    }


def test_remote_action_approval_unblocks_execution(approval_setup):
    async def run():
        executor = approval_setup["executor"]
        dashboard = approval_setup["dashboard"]

        # Start execution in background task (which will await remote approval)
        exec_task = asyncio.create_task(
            executor.execute("test.confirm_action", DummyParams(target="prod-server"), confirmed=False)
        )

        # Wait for approval request to be registered in dashboard
        pending = []
        for _ in range(50):
            pending = dashboard.list_pending_approvals()
            if pending:
                break
            await asyncio.sleep(0.02)

        assert len(pending) == 1
        req_id = pending[0]["request_id"]
        assert pending[0]["action_id"] == "test.confirm_action"
        assert pending[0]["params"]["target"] == "prod-server"

        # Approve remotely
        resolved = dashboard.resolve_approval(req_id, approved=True)
        assert resolved is True

        # Execution should now complete successfully
        result = await exec_task
        assert result.status == "success"
        assert "Executed on prod-server" in result.message

    asyncio.run(run())


def test_remote_action_rejection_blocks_execution(approval_setup):
    async def run():
        executor = approval_setup["executor"]
        dashboard = approval_setup["dashboard"]

        exec_task = asyncio.create_task(
            executor.execute("test.confirm_action", DummyParams(target="prod-server"), confirmed=False)
        )

        pending = []
        for _ in range(50):
            pending = dashboard.list_pending_approvals()
            if pending:
                break
            await asyncio.sleep(0.02)

        assert len(pending) == 1
        req_id = pending[0]["request_id"]

        # Deny remotely
        resolved = dashboard.resolve_approval(req_id, approved=False)
        assert resolved is True

        result = await exec_task
        assert result.status == "rejected"
        assert result.error == "confirmation_required"

    asyncio.run(run())


def test_remote_action_approval_timeout(approval_setup, monkeypatch):
    async def run():
        executor = approval_setup["executor"]
        dashboard = approval_setup["dashboard"]

        # Mock short timeout of 0.05 seconds
        orig_request = dashboard.request_action_approval

        async def short_timeout_request(action_id, params, timeout=15.0):
            return await orig_request(action_id, params, timeout=0.05)

        monkeypatch.setattr(dashboard, "request_action_approval", short_timeout_request)

        result = await executor.execute("test.confirm_action", DummyParams(target="timeout-test"), confirmed=False)
        assert result.status == "rejected"
        assert result.error == "confirmation_required"

    asyncio.run(run())


def test_hmac_decision_signature_verification(approval_setup):
    dashboard = approval_setup["dashboard"]
    token = approval_setup["token"]
    req_id = "test-req-12345"

    sig_approved = dashboard.sign_decision(token, req_id, approved=True)
    assert len(sig_approved) == 64  # SHA-256 hex string

    # Verify matching signature
    assert dashboard.verify_decision_signature(token, req_id, approved=True, signature=sig_approved) is True

    # Tampered decision fails
    assert dashboard.verify_decision_signature(token, req_id, approved=False, signature=sig_approved) is False

    # Tampered request_id fails
    assert dashboard.verify_decision_signature(token, "other-req", approved=True, signature=sig_approved) is False


def test_rest_approvals_api_endpoints(approval_setup):
    client = approval_setup["client"]
    dashboard = approval_setup["dashboard"]
    token = approval_setup["token"]
    headers = approval_setup["headers"]

    # Create a pending approval
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    fut = loop.create_future()
    req_id = "rest-req-abc"
    dashboard._pending_approvals[req_id] = {
        "request_id": req_id,
        "action_id": "test.confirm_action",
        "params": {"target": "critical-resource"},
        "created_at": time.time(),
        "timeout": 30.0,
        "future": fut,
    }

    # 1. GET /api/v1/mobile/status shows pending_approvals = 1
    res_status = client.get("/api/v1/mobile/status", headers=headers)
    assert res_status.status_code == 200
    assert res_status.json()["pending_approvals"] == 1

    # 2. GET /api/v1/mobile/approvals
    res_list = client.get("/api/v1/mobile/approvals", headers=headers)
    assert res_list.status_code == 200
    approvals = res_list.json()["approvals"]
    assert len(approvals) == 1
    assert approvals[0]["request_id"] == req_id
    assert approvals[0]["action_id"] == "test.confirm_action"

    # 3. Unauthorized POST returns 401
    res_unauth = client.post(
        f"/api/v1/mobile/approvals/{req_id}",
        json={"approved": True},
        headers={"X-Mobile-Session": "invalid-session"},
    )
    assert res_unauth.status_code == 401

    # 4. POST with valid signature
    sig = dashboard.sign_decision(token, req_id, approved=True)
    res_decide = client.post(
        f"/api/v1/mobile/approvals/{req_id}",
        json={"approved": True, "signature": sig},
        headers=headers,
    )
    assert res_decide.status_code == 200
    assert res_decide.json()["resolved"] is True
    assert fut.done() is True
    assert fut.result() is True

    # 5. Non-existent / already resolved returns 404
    res_repeat = client.post(
        f"/api/v1/mobile/approvals/{req_id}",
        json={"approved": True},
        headers=headers,
    )
    assert res_repeat.status_code == 404


def test_websocket_action_approval_flow(approval_setup):
    client = approval_setup["client"]
    dashboard = approval_setup["dashboard"]
    token = approval_setup["token"]

    # Connect WebSocket
    with client.websocket_connect(f"/api/v1/mobile/ws?token={token}") as ws:
        # Welcome message
        welcome_raw = ws.receive_text()
        welcome_frame = json.loads(welcome_raw)
        welcome_obj = json.loads(dashboard.decrypt(token, welcome_frame["iv"], welcome_frame["ciphertext"]).decode("utf-8"))
        assert welcome_obj["type"] == "connected"

        # Create pending approval
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        fut = loop.create_future()
        req_id = "ws-req-xyz"
        dashboard._pending_approvals[req_id] = {
            "request_id": req_id,
            "action_id": "files.delete",
            "params": {"path": "/tmp/test.txt"},
            "created_at": time.time(),
            "timeout": 30.0,
            "future": fut,
        }

        # Send encrypted approval message
        approval_msg = json.dumps({"type": "action_approval", "request_id": req_id, "approved": True})
        enc = dashboard.encrypt(token, approval_msg)
        ws.send_text(json.dumps(enc))

        # Receive encrypted ACK
        ack_raw = ws.receive_text()
        ack_frame = json.loads(ack_raw)
        ack_obj = json.loads(dashboard.decrypt(token, ack_frame["iv"], ack_frame["ciphertext"]).decode("utf-8"))
        assert ack_obj["type"] == "action_approval_ack"
        assert ack_obj["request_id"] == req_id
        assert ack_obj["resolved"] is True

        assert fut.done() is True
        assert fut.result() is True
