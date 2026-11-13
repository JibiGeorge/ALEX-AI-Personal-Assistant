import base64
import platform
import threading

import pytest

from app.services.computer_control_service import (
    ComputerControlService,
    ControlParameters,
)


class FakeImage:
    size = (1600, 900)

    def thumbnail(self, size):
        self.thumbnail_size = size
        self.size = (1280, 720)

    def convert(self, mode):
        assert mode == "RGB"
        return self

    def save(self, stream, *, format, quality):
        assert format == "JPEG"
        assert quality == 78
        stream.write(b"bounded-jpeg")


class FakeAdapter:
    FAILSAFE = False
    PAUSE = 0

    def __init__(self):
        self.calls = []
        self.clipboard = "clipboard sample"
        self.write_started = threading.Event()
        self.finish_write = threading.Event()
        self.block_write = False

    def size(self):
        return 800, 600

    def position(self):
        return (0, 0)

    def moveTo(self, x, y, duration=0):
        self.calls.append(("moveTo", x, y, duration))

    def click(self, x=None, y=None, button="left"):
        self.calls.append(("click", x, y, button))

    def doubleClick(self, x, y, button="left"):
        self.calls.append(("doubleClick", x, y, button))

    def rightClick(self, x, y):
        self.calls.append(("rightClick", x, y))

    def mouseDown(self, x, y, button="left"):
        self.calls.append(("mouseDown", x, y, button))

    def mouseUp(self, button="left"):
        self.calls.append(("mouseUp", button))

    def press(self, key):
        self.calls.append(("press", key))

    def write(self, text, interval=0):
        self.calls.append(("write", text, interval))
        if self.block_write:
            self.write_started.set()
            self.finish_write.wait(timeout=2)

    def hotkey(self, *keys):
        self.calls.append(("hotkey", *keys))

    def scroll(self, amount):
        self.calls.append(("scroll", amount))

    def hscroll(self, amount):
        self.calls.append(("hscroll", amount))

    def screenshot(self):
        return FakeImage()

    def clipboard_read(self):
        self.calls.append(("clipboard_read",))
        return self.clipboard

    def clipboard_write(self, text):
        self.calls.append(("clipboard_write", text))
        self.clipboard = text

    def active_window(self):
        self.calls.append(("active_window",))
        return {"title": "Safe Test Window", "application": "python.exe", "process_id": 42}

    def list_windows(self):
        self.calls.append(("list_windows",))
        return [{"title": "Safe Test Window", "application": "python.exe", "process_id": 42}]

    def focus_window(self, title):
        self.calls.append(("focus_window", title))
        return {"operation": "focus_window", "focused": True}

    def close_app(self, application):
        self.calls.append(("close_app", application))
        return {"operation": "close_app", "verified_closed": False}


@pytest.fixture
def controls():
    adapter = FakeAdapter()
    service = ComputerControlService(lambda: adapter)
    return service, adapter


def test_permission_is_off_by_default_and_enablement_sets_fail_safe(controls):
    service, adapter = controls
    assert service.status()["permission_enabled"] is False
    with pytest.raises(PermissionError, match="Grant desktop-control permission"):
        service.execute(ControlParameters(operation="click", x=1, y=1))

    status = service.set_permission(True)

    assert status["permission_enabled"] is True
    assert adapter.FAILSAFE is True
    assert adapter.PAUSE == 0.05
    assert status["adapter_available"] is True


_MODIFIER = "command" if platform.system() == "Darwin" else "ctrl"


@pytest.mark.parametrize(
    ("parameters", "expected_call"),
    [
        ({"operation": "move", "x": 4, "y": 5}, ("moveTo", 4, 5, 0)),
        ({"operation": "click", "x": 4, "y": 5}, ("click", 4, 5, "left")),
        ({"operation": "click_current"}, ("click", None, None, "left")),
        ({"operation": "double_click", "x": 4, "y": 5}, ("doubleClick", 4, 5, "left")),
        ({"operation": "right_click", "x": 4, "y": 5}, ("rightClick", 4, 5)),
        ({"operation": "press", "key": "enter"}, ("press", "enter")),
        ({"operation": "hotkey", "hotkey": "copy"}, ("hotkey", _MODIFIER, "c")),
        ({"operation": "scroll", "direction": "down", "amount": 3}, ("scroll", -3)),
        ({"operation": "scroll", "direction": "left", "amount": 2}, ("hscroll", -2)),
    ],
)
def test_executes_allowlisted_operations_with_explicit_values(controls, parameters, expected_call):
    service, adapter = controls
    service.set_permission(True)

    result = service.execute(ControlParameters.model_validate(parameters))

    assert result["operation"] == parameters["operation"]
    assert expected_call in adapter.calls


def test_drag_checks_emergency_stop_between_steps_and_releases_button(controls):
    service, adapter = controls
    service.set_permission(True)
    move_to = adapter.moveTo

    def stop_after_drag_start(x, y, duration=0):
        move_to(x, y, duration)
        if any(call[0] == "mouseDown" for call in adapter.calls):
            service.stop()

    adapter.moveTo = stop_after_drag_start

    with pytest.raises(InterruptedError, match="stopped by the user"):
        service.execute(ControlParameters(
            operation="drag",
            x=10,
            y=10,
            x2=400,
            y2=400,
        ))

    assert adapter.calls[-1] == ("mouseUp", "left")


def test_type_checks_emergency_stop_between_characters(controls):
    service, adapter = controls
    service.set_permission(True)
    adapter.block_write = True
    errors = []

    def run_type():
        try:
            service.execute(ControlParameters(operation="type", text="abc"))
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=run_type)
    thread.start()
    assert adapter.write_started.wait(timeout=1)
    with pytest.raises(RuntimeError, match="Wait for the active desktop operation"):
        service.set_permission(True)
    service.stop()
    adapter.finish_write.set()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], InterruptedError)
    assert [call[1] for call in adapter.calls if call[0] == "write"] == ["a"]
    assert ("mouseUp", "left") in adapter.calls


def test_emergency_stop_stays_latched_until_permission_is_regranted(controls):
    service, adapter = controls
    service.set_permission(True)

    stopped = service.stop()

    assert stopped["emergency_stop_requested"] is True
    with pytest.raises(InterruptedError, match="stopped by the user"):
        service.execute(ControlParameters(operation="click", x=1, y=1))
    assert not any(call[0] == "click" for call in adapter.calls)

    service.set_permission(True)
    service.execute(ControlParameters(operation="click", x=1, y=1))
    assert ("click", 1, 1, "left") in adapter.calls


def test_assistant_control_request_waits_for_one_time_user_approval(controls):
    service, adapter = controls
    parameters = ControlParameters(operation="click", x=12, y=34)
    with pytest.raises(PermissionError):
        service.request_control(parameters)

    service.set_permission(True)
    request = service.request_control(parameters)
    assert request["operation"] == "click"
    assert "no desktop input has occurred" in request["message"]
    assert adapter.calls == []
    assert service.pending_requests()[0]["request_id"] == request["request_id"]

    service.approve_request(request["request_id"])
    assert ("click", 12, 34, "left") in adapter.calls
    assert service.pending_requests() == []
    with pytest.raises(ValueError, match="missing, expired, or already handled"):
        service.approve_request(request["request_id"])


def test_rejected_assistant_request_is_consumed_without_desktop_input(controls):
    service, adapter = controls
    service.set_permission(True)
    request = service.request_control(ControlParameters(operation="click", x=12, y=34))

    result = service.dismiss_request(request["request_id"])

    assert result == {"request_id": request["request_id"], "dismissed": True}
    assert service.pending_requests() == []
    assert adapter.calls == []
    with pytest.raises(ValueError, match="missing, expired, or already handled"):
        service.dismiss_request(request["request_id"])


def test_emergency_stop_discards_pending_assistant_requests(controls):
    service, _ = controls
    service.set_permission(True)
    request = service.request_control(ControlParameters(operation="press", key="enter"))

    service.stop()

    assert service.pending_requests() == []
    with pytest.raises(ValueError, match="missing, expired, or already handled"):
        service.approve_request(request["request_id"])


def test_assistant_control_requests_expire_before_approval(controls, monkeypatch):
    service, adapter = controls
    service.set_permission(True)
    request = service.request_control(ControlParameters(operation="click", x=1, y=1))
    monkeypatch.setattr("app.services.computer_control_service.PENDING_REQUEST_TTL_SECONDS", 0)

    assert service.pending_requests() == []
    with pytest.raises(ValueError, match="missing, expired, or already handled"):
        service.approve_request(request["request_id"])
    assert not any(call[0] == "click" for call in adapter.calls)


def test_operation_watchdog_stops_at_the_next_safe_checkpoint(controls, monkeypatch):
    service, adapter = controls
    service.set_permission(True)
    adapter.block_write = True
    monkeypatch.setattr("app.services.computer_control_service.OPERATION_TIMEOUT_SECONDS", 0.01)
    errors = []

    def run_type():
        try:
            service.execute(ControlParameters(operation="type", text="abc"))
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=run_type)
    thread.start()
    assert adapter.write_started.wait(timeout=1)
    assert service._timed_out.wait(timeout=1)
    adapter.finish_write.set()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], TimeoutError)
    assert [call[1] for call in adapter.calls if call[0] == "write"] == ["a"]
    assert ("mouseUp", "left") in adapter.calls


def test_screenshot_is_encoded_in_memory_without_writing_a_file(controls):
    service, _ = controls
    service.set_permission(True)

    result = service.execute(ControlParameters(operation="screenshot"))

    assert result["mime_type"] == "image/jpeg"
    assert base64.b64decode(result["data_base64"]) == b"bounded-jpeg"


def test_coordinates_and_operation_parameters_are_validated(controls):
    service, adapter = controls
    service.set_permission(True)

    with pytest.raises(ValueError, match="within the primary display"):
        service.execute(ControlParameters(operation="click", x=800, y=1))
    with pytest.raises(ValueError, match="requires"):
        ControlParameters(operation="drag", x=1, y=1)
    with pytest.raises(ValueError, match="does not accept"):
        ControlParameters(operation="click", x=1, y=1, text="unexpected")
    with pytest.raises(ValueError, match="ASCII"):
        ControlParameters(operation="type", text="café")
    assert ControlParameters(operation="smart_type", text="café").text == "café"
    with pytest.raises(ValueError):
        ControlParameters(operation="hotkey", hotkey="close_window")
    with pytest.raises(ValueError):
        ControlParameters(operation="press", key="f4")
    with pytest.raises(ValueError):
        ControlParameters(operation="clipboard_write")
    with pytest.raises(ValueError):
        ControlParameters(operation="focus_window", title=" ")
    with pytest.raises(ValueError):
        ControlParameters(operation="wait", seconds=10.1)
    with pytest.raises(ValueError):
        ControlParameters(operation="user_data")
    with pytest.raises(ValueError):
        ControlParameters(operation="user_data", field=" ")
    with pytest.raises(ValueError):
        ControlParameters(operation="random_data", data_type=" ")
    assert adapter.calls == []


@pytest.mark.parametrize(
    ("parameters", "expected"),
    [
        ({"operation": "clipboard_read"}, ("clipboard_read",)),
        ({"operation": "clipboard_write", "clipboard_text": "new value"},
         ("clipboard_write", "new value")),
        ({"operation": "clipboard_paste", "clipboard_text": "paste value"},
         ("hotkey", _MODIFIER, "v")),
        ({"operation": "active_window"}, ("active_window",)),
        ({"operation": "list_windows"}, ("list_windows",)),
        ({"operation": "focus_window", "title": "Safe Test"},
         ("focus_window", "Safe Test")),
        ({"operation": "close_app", "application": "Editor"},
         ("close_app", "Editor")),
        ({"operation": "clear_field"}, ("press", "delete")),
        ({"operation": "smart_type", "text": "replacement", "clear_first": True},
         ("clipboard_write", "replacement")),
    ],
)
def test_additional_source_operations_are_executed_after_approval(controls, parameters, expected):
    service, adapter = controls
    service.set_permission(True)

    result = service.execute(ControlParameters.model_validate(parameters))

    assert result["operation"] == parameters["operation"]
    assert expected in adapter.calls


def test_smart_type_replaces_field_and_pastes_unicode_from_clipboard(controls):
    service, adapter = controls
    service.set_permission(True)

    result = service.execute(ControlParameters(operation="smart_type", text="café"))

    modifier = "command" if platform.system() == "Darwin" else "ctrl"
    assert adapter.calls == [
        ("hotkey", modifier, "a"),
        ("press", "delete"),
        ("clipboard_write", "café"),
        ("hotkey", modifier, "v"),
    ]
    assert result["characters_typed"] == 4
    assert result["field_cleared"] is True


def test_clipboard_read_is_bounded(controls):
    service, adapter = controls
    service.set_permission(True)
    adapter.clipboard = "x" * 2_001

    with pytest.raises(ValueError, match="2000-character"):
        service.execute(ControlParameters(operation="clipboard_read"))


def test_visual_search_returns_rescaled_coordinates_and_rejects_out_of_bounds(controls):
    adapter = FakeAdapter()
    service = ComputerControlService(
        lambda: adapter,
        screen_finder=lambda _image, _description, _width, _height: (320, 240),
    )
    service.set_permission(True)

    result = service.execute(ControlParameters(
        operation="screen_find",
        description="the safe test button",
    ))

    assert result["found"] is True
    assert (result["x"], result["y"]) == (400, 300)
    service.set_screen_finder(lambda *_: (1280, 720))
    with pytest.raises(ValueError, match="outside the captured image"):
        service.execute(ControlParameters(
            operation="screen_find",
            description="the safe test button",
        ))


def test_revoke_permission_stops_control_and_prevents_later_actions(controls):
    service, _ = controls
    service.set_permission(True)
    status = service.set_permission(False)

    assert status["permission_enabled"] is False
    with pytest.raises(PermissionError):
        service.execute(ControlParameters(operation="press", key="enter"))


def test_random_data_generates_synthetic_form_fields(controls):
    service, _ = controls
    service.set_permission(True)

    result_email = service.execute(ControlParameters(operation="random_data", data_type="email"))
    assert result_email["operation"] == "random_data"
    assert "@" in result_email["value"]

    result_name = service.execute(ControlParameters(operation="random_data", data_type="name"))
    assert len(result_name["value"].split()) == 2

    result_default = service.execute(ControlParameters(operation="random_data", data_type="address"))
    assert result_default["data_type"] == "address"
    assert len(result_default["value"]) > 0


def test_user_data_retrieves_memory_or_falls_back_to_synthetic(controls):
    service, _ = controls
    service.set_permission(True)
    memory_store = {"full_name": "Dr. Bruce Banner", "city": "New York"}
    service.set_user_data_provider(lambda f: memory_store.get(f.lower().strip()))

    from_mem = service.execute(ControlParameters(operation="user_data", field="full_name"))
    assert from_mem["operation"] == "user_data"
    assert from_mem["value"] == "Dr. Bruce Banner"
    assert from_mem["source"] == "memory"

    from_fallback = service.execute(ControlParameters(operation="user_data", field="email"))
    assert from_fallback["operation"] == "user_data"
    assert "@" in from_fallback["value"]
    assert from_fallback["source"] == "synthetic"
