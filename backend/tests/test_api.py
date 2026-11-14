import asyncio
from datetime import datetime, timedelta, timezone
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import keyring
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app
from app.schemas.memory import MemoryWrite


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


def test_api_requires_token(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_api_rejects_non_ascii_token_without_auth_error(client):
    response = client.get(
        "/api/v1/health",
        headers={"Authorization": b"Bearer \xff"},
    )
    assert response.status_code == 401


def test_health_is_authenticated(client):
    response = client.get("/api/v1/health", headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "name": "Alex"}


def test_web_search_requires_authentication_and_gemini_key(client):
    body = {"query": "current news", "mode": "news"}
    assert client.post("/api/v1/web/search", json=body).status_code == 401
    response = client.post(
        "/api/v1/web/search",
        headers=auth_headers(),
        json=body,
    )
    assert response.status_code == 409
    assert "Gemini API key" in response.json()["detail"]


def test_web_search_validates_compare_inputs(client):
    response = client.post(
        "/api/v1/web/search",
        headers=auth_headers(),
        json={"query": "compare", "mode": "compare", "items": ["A", "A"]},
    )
    assert response.status_code == 422


def test_live_conversation_requires_loopback_token(client):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/conversation/live"):
            pass
    assert exc_info.value.code == 1008


def test_live_conversation_rejects_non_ascii_token(client):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/conversation/live?token=%F0%9F%94%92"):
            pass
    assert exc_info.value.code == 1008


def test_live_conversation_requires_a_configured_key(client):
    with client.websocket_connect("/api/v1/conversation/live?token=test-token") as websocket:
        assert websocket.receive_json() == {
            "type": "error",
            "message": "Configure a Gemini API key in Settings to use voice.",
        }


def test_live_conversation_streams_pcm_and_transcripts(client, monkeypatch):
    received_audio = []
    received_text = []

    class FakeSession:
        def __init__(self):
            self.messages = asyncio.Queue()

        async def send_realtime_input(self, *, audio):
            received_audio.append(audio)
            await self.messages.put(
                SimpleNamespace(
                    data=b"\x10\x00",
                    server_content=SimpleNamespace(
                        input_transcription=SimpleNamespace(text="Hello"),
                        output_transcription=SimpleNamespace(text="Hi there"),
                        turn_complete=True,
                    ),
                )
            )

        async def send_client_content(self, *, turns, turn_complete):
            assert turn_complete is True
            received_text.append(turns)
            await self.messages.put(
                SimpleNamespace(
                    data=b"\x10\x00",
                    server_content=SimpleNamespace(
                        input_transcription=None,
                        output_transcription=SimpleNamespace(text="Text reply"),
                        turn_complete=True,
                    ),
                )
            )

        async def receive(self):
            while True:
                message = await self.messages.get()
                if message is None:
                    return
                yield message

    session = FakeSession()

    class FakeSessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *_):
            await session.messages.put(None)

    class FakeLive:
        def connect(self, *, model, config):
            assert model == "models/gemini-3.1-flash-live-preview"
            assert config.input_audio_transcription is not None
            return FakeSessionContext()

    async def close_client():
        return None

    monkeypatch.setattr(keyring, "get_password", lambda *_: "test-key-that-is-long-enough")
    monkeypatch.setattr(
        "app.services.live_voice_service.genai.Client",
        lambda **kwargs: SimpleNamespace(
            aio=SimpleNamespace(live=FakeLive(), aclose=close_client)
        ),
    )

    with client.websocket_connect("/api/v1/conversation/live?token=test-token") as websocket:
        assert websocket.receive_json()["type"] == "connected"
        websocket.send_bytes(b"\x01\x00")
        assert websocket.receive_bytes() == b"\x10\x00"
        assert websocket.receive_json() == {
            "type": "turn_complete",
            "input_text": "Hello",
            "output_text": "Hi there",
            "interrupted": False,
        }
        websocket.send_text('{"type":"text","text":"Follow up"}')
        assert websocket.receive_bytes() == b"\x10\x00"
        assert websocket.receive_json() == {
            "type": "turn_complete",
            "input_text": "Follow up",
            "output_text": "Text reply",
            "interrupted": False,
        }
        websocket.send_text('{"type":"interrupt"}')
        assert websocket.receive_json() == {"type": "interrupted"}
        websocket.send_bytes(b"\x02\x00")
        assert websocket.receive_json() == {
            "type": "turn_complete",
            "input_text": "",
            "output_text": "",
            "interrupted": True,
        }
        websocket.send_bytes(b"\x03\x00")
        assert websocket.receive_bytes() == b"\x10\x00"
        assert websocket.receive_json() == {
            "type": "turn_complete",
            "input_text": "Hello",
            "output_text": "Hi there",
            "interrupted": False,
        }
        websocket.send_text('{"type":"stop"}')

    assert [audio.data for audio in received_audio] == [
        b"\x01\x00",
        b"\x02\x00",
        b"\x03\x00",
    ]
    assert received_text == [
        {"role": "user", "parts": [{"text": "Follow up"}]},
    ]
    assert all(audio.mime_type == "audio/pcm;rate=16000" for audio in received_audio)


def test_system_metrics_are_authenticated_and_validated(client):
    unauthenticated = client.get("/api/v1/system/metrics")
    assert unauthenticated.status_code == 401
    response = client.get("/api/v1/system/metrics", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["operating_system"]
    assert response.json()["process_count"] > 0


def test_system_alerts_require_authentication_and_return_alerts(client, monkeypatch):
    assert client.get("/api/v1/system/alerts").status_code == 401
    service = client.app.state.system_monitor_service
    monkeypatch.setattr(
        service,
        "check",
        lambda _: [
            {"metric": "memory", "value": 93, "message": "Memory usage is high."},
        ],
    )
    response = client.get("/api/v1/system/alerts", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["alerts"] == [
        {"metric": "memory", "value": 93, "message": "Memory usage is high."},
    ]


def test_action_registry_discovery_execution_confirmation_and_disable(client):
    headers = auth_headers()
    discovered = client.get("/api/v1/actions", headers=headers)
    assert discovered.status_code == 200
    actions = {item["action_id"]: item for item in discovered.json()["actions"]}
    assert {
        "computer.control",
        "computer.permission",
        "computer.request",
        "computer.pending",
        "computer.approve",
        "computer.dismiss",
        "computer.status",
        "computer.stop",
        "files.list",
        "files.read",
        "files.find",
        "files.create_directory",
        "files.write",
        "files.move",
        "files.copy",
        "files.rename",
        "files.trash",
        "files.undo_history",
        "files.undo",
        "documents.parse",
        "memory.recall",
        "system.get_metrics",
        "web.search",
        "media.play",
        "media.stop",
        "media.pause",
        "media.resume",
        "media.set_muted",
        "media.status",
        "media.transcript",
        "media.summarize_video",
        "window.list",
        "window.active",
        "window.focus",
        "window.close",
        "browser.control",
        "system.setting",
        "dev.agent",
        "code.helper",
        "message.send",
        "desktop.environment",
        "vision.capture",
        "elevenlabs.synthesize",
        "youtube.transcript",
        "reminder.schedule",
        "topic.monitor",
        "conversation.proactive_check",
        "travel.flights",
        "game.update",
        "job_search",
        "job_analyse",
        "job_match_resume",
        "job_prepare_application",
        "job_list_approvals",
        "job_track_application",
        "job_list_interviews",
        "job_hunting.discover",
        "job_hunting.match",
        "job_hunting.tailor_resume",
        "job_hunting.submit_application",
    } == set(actions)
    assert actions["system.get_metrics"]["enabled"] is True
    assert actions["job_hunting.submit_application"]["requires_confirmation"] is True
    assert actions["browser.control"]["requires_confirmation"] is True
    assert actions["system.setting"]["requires_confirmation"] is False
    assert actions["dev.agent"]["requires_confirmation"] is True
    assert actions["code.helper"]["requires_confirmation"] is True
    assert actions["message.send"]["requires_confirmation"] is True
    assert actions["desktop.environment"]["requires_confirmation"] is False
    assert actions["vision.capture"]["requires_confirmation"] is False
    assert actions["elevenlabs.synthesize"]["requires_confirmation"] is False
    assert actions["conversation.proactive_check"]["requires_confirmation"] is False
    assert actions["travel.flights"]["requires_confirmation"] is False
    assert actions["game.update"]["requires_confirmation"] is False
    assert actions["youtube.transcript"]["requires_confirmation"] is False
    assert actions["reminder.schedule"]["requires_confirmation"] is False
    assert actions["topic.monitor"]["requires_confirmation"] is False
    assert actions["media.transcript"]["requires_confirmation"] is False
    assert actions["media.summarize_video"]["requires_confirmation"] is False
    assert actions["memory.recall"]["requires_confirmation"] is False
    assert actions["web.search"]["requires_confirmation"] is True
    assert actions["files.read"]["requires_confirmation"] is False
    assert actions["files.write"]["requires_confirmation"] is True
    assert actions["computer.control"]["requires_confirmation"] is True
    assert actions["computer.permission"]["requires_confirmation"] is True
    assert actions["computer.request"]["requires_confirmation"] is False
    assert actions["computer.pending"]["requires_confirmation"] is False
    assert actions["computer.approve"]["requires_confirmation"] is True
    assert actions["computer.dismiss"]["requires_confirmation"] is True

    metrics = client.post(
        "/api/v1/actions/system.get_metrics/execute",
        headers=headers,
        json={"parameters": {}},
    )
    assert metrics.status_code == 200
    assert metrics.json()["status"] == "success"
    assert metrics.json()["data"]["operating_system"]

    client.app.state.memory_service.upsert(
        "preferences",
        "accent",
        MemoryWrite(value="cyan"),
    )
    recalled = client.post(
        "/api/v1/actions/memory.recall/execute",
        headers=headers,
        json={"parameters": {"query": "cyan"}},
    )
    assert recalled.json()["status"] == "success"
    assert recalled.json()["data"][0]["key"] == "accent"

    search = client.post(
        "/api/v1/actions/web.search/execute",
        headers=headers,
        json={"parameters": {"query": "example"}},
    )
    assert search.json()["status"] == "rejected"
    assert search.json()["error"] == "confirmation_required"

    invalid = client.post(
        "/api/v1/actions/web.search/execute",
        headers=headers,
        json={"parameters": {"mode": "unsupported"}, "confirmed": True},
    )
    assert invalid.json()["status"] == "rejected"

    disabled = client.patch(
        "/api/v1/actions/system.get_metrics",
        headers=headers,
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    unavailable = client.post(
        "/api/v1/actions/system.get_metrics/execute",
        headers=headers,
        json={"parameters": {}},
    )
    assert unavailable.json()["status"] == "rejected"
    assert client.get("/api/v1/actions/history", headers=headers).json()["executions"]


def test_workspace_actions_are_authenticated_scoped_and_confirmation_gated(client, tmp_path):
    headers = auth_headers()
    assert client.get("/api/v1/actions").status_code == 401
    workspace = client.app.state.file_workspace_service.root
    (workspace / "note.txt").write_text("workspace data", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("not available", encoding="utf-8")

    discovered = {
        item["action_id"]: item
        for item in client.get("/api/v1/actions", headers=headers).json()["actions"]
    }
    assert discovered["files.write"]["requires_confirmation"] is True
    assert discovered["files.read"]["requires_confirmation"] is False
    declarations = {
        declaration.name
        for declaration in client.app.state.action_registry.model_declarations()
    }
    assert {"files.list", "files.read", "files.find"} <= declarations
    assert "files.write" not in declarations
    assert "files.undo" not in declarations

    read = client.post(
        "/api/v1/actions/files.read/execute",
        headers=headers,
        json={"parameters": {"path": "note.txt"}},
    )
    assert read.json()["status"] == "success"
    assert read.json()["data"]["content"] == "workspace data"

    rejected = client.post(
        "/api/v1/actions/files.write/execute",
        headers=headers,
        json={"parameters": {"path": "new.txt", "content": "new"}},
    )
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["error"] == "confirmation_required"
    assert not (workspace / "new.txt").exists()

    written = client.post(
        "/api/v1/actions/files.write/execute",
        headers=headers,
        json={
            "parameters": {"path": "new.txt", "content": "new"},
            "confirmed": True,
        },
    )
    assert written.json()["status"] == "success"
    assert (workspace / "new.txt").read_text(encoding="utf-8") == "new"

    traversal = client.post(
        "/api/v1/actions/files.read/execute",
        headers=headers,
        json={"parameters": {"path": "../outside.txt"}},
    )
    assert traversal.json()["status"] == "failed"
    assert not (workspace / "outside.txt").exists()


def test_computer_control_actions_require_session_permission_and_user_confirmation(client):
    headers = auth_headers()
    calls = []

    class FakeController:
        FAILSAFE = False
        PAUSE = 0

        @staticmethod
        def size():
            return 500, 400

        def click(self, x, y, button="left"):
            calls.append(("click", x, y, button))

        def mouseUp(self, button="left"):
            calls.append(("mouseUp", button))

    service = client.app.state.computer_control_service
    adapter = FakeController()
    service._adapter_factory = lambda: adapter
    service._adapter_injected = True
    actions = client.get("/api/v1/actions", headers=headers).json()["actions"]
    declarations = {
        declaration.name
        for declaration in client.app.state.action_registry.model_declarations()
    }
    assert {"computer.status", "computer.stop", "computer.request", "computer.pending"} <= declarations
    assert "computer.control" not in declarations
    assert "computer.permission" not in declarations
    assert "computer.approve" not in declarations
    assert "computer.dismiss" not in declarations

    denied = client.post(
        "/api/v1/actions/computer.control/execute",
        headers=headers,
        json={"parameters": {"operation": "click", "x": 1, "y": 2}, "confirmed": True},
    ).json()
    assert denied["status"] == "failed"
    assert "Grant desktop-control permission" in denied["error"]
    assert calls == []

    unconfirmed = client.post(
        "/api/v1/actions/computer.permission/execute",
        headers=headers,
        json={"parameters": {"enabled": True}},
    ).json()
    assert unconfirmed["status"] == "rejected"

    enabled = client.post(
        "/api/v1/actions/computer.permission/execute",
        headers=headers,
        json={"parameters": {"enabled": True}, "confirmed": True},
    ).json()
    assert enabled["status"] == "success"
    assert enabled["data"]["permission_enabled"] is True

    invalid_coordinates = client.post(
        "/api/v1/actions/computer.control/execute",
        headers=headers,
        json={"parameters": {"operation": "click", "x": 500, "y": 2}, "confirmed": True},
    ).json()
    assert invalid_coordinates["status"] == "failed"
    assert calls == []

    completed = client.post(
        "/api/v1/actions/computer.control/execute",
        headers=headers,
        json={"parameters": {"operation": "click", "x": 1, "y": 2}, "confirmed": True},
    ).json()
    assert completed["status"] == "success"
    assert calls == [("click", 1, 2, "left")]

    stopped = client.post(
        "/api/v1/actions/computer.stop/execute",
        headers=headers,
        json={"parameters": {}},
    ).json()
    assert stopped["status"] == "success"
    assert calls[-1] == ("mouseUp", "left")

    latched = client.post(
        "/api/v1/actions/computer.control/execute",
        headers=headers,
        json={"parameters": {"operation": "click", "x": 1, "y": 2}, "confirmed": True},
    ).json()
    assert latched["status"] == "failed"
    assert "stopped by the user" in latched["error"]
    assert calls == [("click", 1, 2, "left"), ("mouseUp", "left")]

    rearmed = client.post(
        "/api/v1/actions/computer.permission/execute",
        headers=headers,
        json={"parameters": {"enabled": True}, "confirmed": True},
    ).json()
    assert rearmed["data"]["emergency_stop_requested"] is False
    executed_again = client.post(
        "/api/v1/actions/computer.control/execute",
        headers=headers,
        json={"parameters": {"operation": "click", "x": 1, "y": 2}, "confirmed": True},
    ).json()
    assert executed_again["status"] == "success"
    assert calls[-1] == ("click", 1, 2, "left")
    revoked = client.post(
        "/api/v1/actions/computer.permission/execute",
        headers=headers,
        json={"parameters": {"enabled": False}, "confirmed": True},
    ).json()
    assert revoked["data"]["permission_enabled"] is False
    denied_again = client.post(
        "/api/v1/actions/computer.control/execute",
        headers=headers,
        json={"parameters": {"operation": "click", "x": 1, "y": 2}, "confirmed": True},
    ).json()
    assert denied_again["status"] == "failed"


def test_backend_shutdown_revokes_desktop_control_permission(tmp_path, monkeypatch):
    monkeypatch.setattr(keyring, "get_password", lambda *_: None)
    monkeypatch.setattr(keyring, "set_password", lambda *_: None)
    app = create_app(data_dir=tmp_path, api_token="test-token")
    service = app.state.computer_control_service
    calls = []

    class FakeController:
        FAILSAFE = False
        PAUSE = 0

        def mouseUp(self, button="left"):
            calls.append(("mouseUp", button))

    adapter = FakeController()
    service._adapter_factory = lambda: adapter
    service._adapter_injected = True
    with TestClient(app):
        service.set_permission(True)

    assert service.status()["permission_enabled"] is False
    assert service.status()["emergency_stop_requested"] is True
    assert calls == [("mouseUp", "left")]


def test_model_can_request_control_but_only_user_confirmation_executes_it(client):
    headers = auth_headers()
    calls = []

    class FakeController:
        FAILSAFE = False
        PAUSE = 0

        @staticmethod
        def size():
            return 500, 400

        def click(self, x, y, button="left"):
            calls.append(("click", x, y, button))

        def mouseUp(self, button="left"):
            calls.append(("mouseUp", button))

    service = client.app.state.computer_control_service
    adapter = FakeController()
    service._adapter_factory = lambda: adapter
    service._adapter_injected = True
    declarations = {
        declaration.name
        for declaration in client.app.state.action_registry.model_declarations()
    }
    assert {"computer.request", "computer.pending"} <= declarations
    assert {
        "computer.control",
        "computer.permission",
        "computer.approve",
        "computer.dismiss",
    }.isdisjoint(declarations)

    enabled = client.post(
        "/api/v1/actions/computer.permission/execute",
        headers=headers,
        json={"parameters": {"enabled": True}, "confirmed": True},
    ).json()
    assert enabled["status"] == "success"
    requested = client.post(
        "/api/v1/actions/computer.request/execute",
        headers=headers,
        json={"parameters": {"operation": "click", "x": 20, "y": 30}},
    ).json()
    assert requested["status"] == "success"
    request_id = requested["data"]["request_id"]
    assert calls == []

    pending = client.post(
        "/api/v1/actions/computer.pending/execute",
        headers=headers,
        json={"parameters": {}},
    ).json()
    assert pending["data"][0]["request_id"] == request_id

    modified = client.post(
        "/api/v1/actions/computer.approve/execute",
        headers=headers,
        json={
            "parameters": {
                "request_id": request_id,
                "operation": "right_click",
            },
            "confirmed": True,
        },
    ).json()
    assert modified["status"] == "rejected"
    assert calls == []

    unconfirmed = client.post(
        "/api/v1/actions/computer.approve/execute",
        headers=headers,
        json={"parameters": {"request_id": request_id}},
    ).json()
    assert unconfirmed["status"] == "rejected"
    assert calls == []

    approved = client.post(
        "/api/v1/actions/computer.approve/execute",
        headers=headers,
        json={"parameters": {"request_id": request_id}, "confirmed": True},
    ).json()
    assert approved["status"] == "success"
    assert calls == [("click", 20, 30, "left")]
    replayed = client.post(
        "/api/v1/actions/computer.approve/execute",
        headers=headers,
        json={"parameters": {"request_id": request_id}, "confirmed": True},
    ).json()
    assert replayed["status"] == "failed"
    assert calls == [("click", 20, 30, "left")]

    rejected_request = client.post(
        "/api/v1/actions/computer.request/execute",
        headers=headers,
        json={"parameters": {"operation": "press", "key": "enter"}},
    ).json()["data"]
    rejected = client.post(
        "/api/v1/actions/computer.dismiss/execute",
        headers=headers,
        json={"parameters": {"request_id": rejected_request["request_id"]}, "confirmed": True},
    ).json()
    assert rejected["status"] == "success"
    assert calls == [("click", 20, 30, "left")]
    replayed_rejection = client.post(
        "/api/v1/actions/computer.dismiss/execute",
        headers=headers,
        json={"parameters": {"request_id": rejected_request["request_id"]}, "confirmed": True},
    ).json()
    assert replayed_rejection["status"] == "failed"
    assert calls == [("click", 20, 30, "left")]

    revoked = client.post(
        "/api/v1/actions/computer.permission/execute",
        headers=headers,
        json={"parameters": {"enabled": False}, "confirmed": True},
    ).json()
    assert revoked["data"]["permission_enabled"] is False
    unauthorized = client.post(
        "/api/v1/actions/computer.control/execute",
        headers=headers,
        json={"parameters": {"operation": "click", "x": 20, "y": 30}, "confirmed": True},
    ).json()
    assert unauthorized["status"] == "failed"
    assert calls.count(("click", 20, 30, "left")) == 1


def test_reminders_are_persistent_cancelable_and_delivered_once(client):
    headers = auth_headers()
    due_at = (datetime.now(timezone.utc) + timedelta(seconds=3)).isoformat()
    created = client.post(
        "/api/v1/reminders",
        headers=headers,
        json={"message": "Call back", "due_at": due_at},
    )
    assert created.status_code == 201
    reminder = created.json()
    assert reminder["message"] == "Call back"
    assert reminder["status"] == "pending"

    listed = client.get("/api/v1/reminders", headers=headers)
    assert listed.json()["reminders"] == [reminder]
    assert client.get("/api/v1/reminders/due", headers=headers).json()["reminders"] == []

    service = client.app.state.reminder_service
    stored = service.list()[0]
    service._write([stored.model_copy(update={"due_at": datetime.now(timezone.utc) - timedelta(seconds=1)})])

    due = client.get("/api/v1/reminders/due", headers=headers)
    assert [item["id"] for item in due.json()["reminders"]] == [reminder["id"]]
    delivered = client.post(
        f"/api/v1/reminders/{reminder['id']}/delivered",
        headers=headers,
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"
    assert client.get("/api/v1/reminders/due", headers=headers).json()["reminders"] == []
    assert client.get("/api/v1/reminders", headers=headers).json()["reminders"][0]["status"] == "delivered"

    future = client.post(
        "/api/v1/reminders",
        headers=headers,
        json={
            "message": "Cancel me",
            "due_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        },
    ).json()
    assert client.delete(
        f"/api/v1/reminders/{future['id']}",
        headers=headers,
    ).status_code == 204
    assert client.delete(
        f"/api/v1/reminders/{future['id']}",
        headers=headers,
    ).status_code == 404


def test_reminder_requires_future_timezone_aware_time_and_valid_message(client):
    headers = auth_headers()
    assert client.post(
        "/api/v1/reminders",
        headers=headers,
        json={"message": "No timezone", "due_at": "2030-01-01T10:00:00"},
    ).status_code == 422
    assert client.post(
        "/api/v1/reminders",
        headers=headers,
        json={
            "message": "Past",
            "due_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        },
    ).status_code == 422
    assert client.post(
        "/api/v1/reminders",
        headers=headers,
        json={
            "message": "x" * 201,
            "due_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        },
    ).status_code == 422
    assert client.post(
        "/api/v1/reminders",
        headers=headers,
        json={
            "message": "   ",
            "due_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        },
    ).status_code == 422


def test_shutdown_is_authenticated(client):
    response = client.post("/api/v1/shutdown", headers=auth_headers())
    assert response.status_code == 202
    assert response.json() == {"status": "shutting_down"}


def test_conversation_requires_a_configured_api_key(client):
    response = client.post(
        "/api/v1/conversation/turn",
        headers=auth_headers(),
        json={"text": "Hello"},
    )
    assert response.status_code == 409
    assert "API key" in response.json()["detail"]


def test_conversation_validates_input_and_preserves_id(client):
    conversation_id = uuid4()

    class FakeConversationService:
        def reply(self, text, received_id, assistant_name, user_name, attachment=None):
            assert text == "Hello"
            assert received_id is None
            assert assistant_name == "ALEX"
            assert user_name == ""
            assert attachment is None
            return {
                "conversation_id": conversation_id,
                "text": "Hello back.",
            }

    client.app.state.conversation_service = FakeConversationService()
    response = client.post(
        "/api/v1/conversation/turn",
        headers=auth_headers(),
        json={"text": " Hello "},
    )
    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": str(conversation_id),
        "text": "Hello back.",
    }

    invalid = client.post(
        "/api/v1/conversation/turn",
        headers=auth_headers(),
        json={"text": "  "},
    )
    assert invalid.status_code == 422


def test_conversation_rejects_attachment_paths_and_invalid_base64(client):
    response = client.post(
        "/api/v1/conversation/turn",
        headers=auth_headers(),
        json={
            "text": "Summarise this",
            "attachment": {
                "name": "..\\private.txt",
                "mime_type": "text/plain",
                "data_base64": "aGVsbG8=",
            },
        },
    )
    assert response.status_code == 422

    invalid_data = client.post(
        "/api/v1/conversation/turn",
        headers=auth_headers(),
        json={
            "text": "Summarise this",
            "attachment": {
                "name": "note.txt",
                "mime_type": "text/plain",
                "data_base64": "not-base64",
            },
        },
    )
    assert invalid_data.status_code == 422


def test_settings_are_validated_and_persisted(client):
    headers = auth_headers()
    response = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "assistant_name": "Nova",
            "accent_color": "#102030",
            "operating_system": "macOS",
            "voice_name": "Puck",
            "hud_style": "core",
        },
    )
    assert response.status_code == 200
    assert response.json()["settings"]["assistant_name"] == "Nova"
    assert response.json()["api_key_configured"] is False
    assert response.json()["settings"]["operating_system"] == "macOS"
    assert response.json()["settings"]["voice_name"] == "Puck"
    assert response.json()["settings"]["hud_style"] == "core"

    reread = client.get("/api/v1/settings", headers=headers)
    assert reread.json()["settings"]["accent_color"] == "#102030"
    assert reread.json()["settings"]["voice_name"] == "Puck"
    assert reread.json()["settings"]["hud_style"] == "core"


def test_settings_reject_invalid_fields(client):
    response = client.patch(
        "/api/v1/settings",
        headers=auth_headers(),
        json={"accent_color": "purple", "unexpected": True},
    )
    assert response.status_code == 422


def test_settings_reject_unsupported_voice(client):
    response = client.patch(
        "/api/v1/settings",
        headers=auth_headers(),
        json={"voice_name": "Unknown"},
    )
    assert response.status_code == 422


def test_audio_device_settings_are_bounded_and_persisted(client):
    headers = auth_headers()
    response = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "audio_input_device_id": "input-device-123",
            "audio_output_device_id": "output-device-456",
        },
    )
    assert response.status_code == 200
    reread = client.get("/api/v1/settings", headers=headers)
    assert reread.json()["settings"]["audio_input_device_id"] == "input-device-123"
    assert reread.json()["settings"]["audio_output_device_id"] == "output-device-456"

    invalid = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"audio_input_device_id": "x" * 513},
    )
    assert invalid.status_code == 422


def test_push_to_talk_setting_is_persisted_and_validated(client):
    headers = auth_headers()
    enabled = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"push_to_talk_enabled": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["settings"]["push_to_talk_enabled"] is True

    reread = client.get("/api/v1/settings", headers=headers)
    assert reread.json()["settings"]["push_to_talk_enabled"] is True

    invalid = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"push_to_talk_enabled": "yes"},
    )
    assert invalid.status_code == 422


def test_api_key_is_never_returned(client, monkeypatch):
    saved = {}
    monkeypatch.setattr(keyring, "set_password", lambda _, name, value: saved.update({name: value}))
    monkeypatch.setattr(
        keyring,
        "get_password",
        lambda _, name: saved.get(name),
    )
    response = client.put(
        "/api/v1/settings/api-key",
        headers=auth_headers(),
        json={"api_key": "a-valid-test-key-that-is-long-enough"},
    )
    assert response.status_code == 200
    assert response.json() == {"configured": True}
    settings = client.get("/api/v1/settings", headers=auth_headers())
    assert "api_key" not in settings.json()["settings"]
    assert "a-valid-test-key" not in settings.text


def test_memory_crud(client):
    headers = auth_headers()
    saved = client.put(
        "/api/v1/memory/preferences/theme",
        headers=headers,
        json={"value": "Prefers dark themes"},
    )
    assert saved.status_code == 200
    assert saved.json()["updated"] == date.today().isoformat()

    listed = client.get("/api/v1/memory", headers=headers)
    assert listed.json()["entries"][0]["key"] == "theme"

    deleted = client.delete(
        "/api/v1/memory/preferences/theme",
        headers=headers,
    )
    assert deleted.status_code == 204
    missing = client.delete(
        "/api/v1/memory/preferences/theme",
        headers=headers,
    )
    assert missing.status_code == 404


def test_memory_rejects_unknown_category(client):
    response = client.put(
        "/api/v1/memory/other/key",
        headers=auth_headers(),
        json={"value": "text"},
    )
    assert response.status_code == 422



def test_system_capabilities_endpoint(client):
    response = client.get("/api/v1/system/capabilities", headers=auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert "operating_system" in data
    assert "desktop_notifications" in data
    assert "window_management" in data
    assert "computer_control" in data
    assert "gemini_live_voice" in data
    assert "gemini_grounded_search" in data


def test_system_briefing_endpoint(client):
    response = client.get("/api/v1/system/briefing", headers=auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert "greeting" in data
    assert "system" in data
    assert "reminders" in data
    assert "known_identity_facts" in data


def test_memory_search_endpoint(client):
    headers = auth_headers()
    client.put(
        "/api/v1/memory/projects/alex_assistant",
        headers=headers,
        json={"value": "An intelligent desktop agent"},
    )
    search_res = client.get("/api/v1/memory/search?q=assistant", headers=headers)
    assert search_res.status_code == 200
    entries = search_res.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["key"] == "alex_assistant"
