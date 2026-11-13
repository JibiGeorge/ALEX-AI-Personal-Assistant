import importlib
import importlib.util
import logging
import os
import platform
import random
import string
import threading
import time
from base64 import b64encode
from io import BytesIO
from typing import Callable, Literal, Protocol
from uuid import uuid4

import psutil
from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)

OPERATION_TIMEOUT_SECONDS = 12
PENDING_REQUEST_TTL_SECONDS = 300
MAX_PENDING_REQUESTS = 5
MAX_CLIPBOARD_CHARS = 4_000
MAX_CLIPBOARD_READ_CHARS = 2_000
MAX_WINDOW_RESULTS = 50

_FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn",
    "Avery", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Harper",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson",
]
_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "proton.me", "mail.com"]


def _generate_random_data(data_type: str) -> str:
    dt = (data_type or "name").lower().strip()
    if dt in ("first_name", "firstname"):
        return random.choice(_FIRST_NAMES)
    if dt in ("last_name", "lastname"):
        return random.choice(_LAST_NAMES)
    if dt in ("name", "full_name", "fullname"):
        return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"
    if dt == "email":
        first = random.choice(_FIRST_NAMES).lower()
        last = random.choice(_LAST_NAMES).lower()
        num = random.randint(10, 999)
        return f"{first}.{last}{num}@{random.choice(_DOMAINS)}"
    if dt == "username":
        return f"{random.choice(_FIRST_NAMES).lower()}{random.randint(100, 9999)}"
    if dt == "password":
        chars = string.ascii_letters + string.digits + "!@#$%"
        raw = (
            random.choice(string.ascii_uppercase)
            + random.choice(string.digits)
            + random.choice("!@#$%")
            + "".join(random.choices(chars, k=9))
        )
        return "".join(random.sample(raw, len(raw)))
    if dt == "phone":
        return f"+1{random.randint(200, 999)}{random.randint(1_000_000, 9_999_999)}"
    if dt == "birthday":
        y = random.randint(1980, 2000)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        return f"{m:02d}/{d:02d}/{y}"
    if dt == "address":
        num = random.randint(100, 9999)
        street = random.choice(["Main St", "Oak Ave", "Park Blvd", "Elm St", "Cedar Ln"])
        return f"{num} {street}"
    if dt in ("zip_code", "zip", "postal_code"):
        return str(random.randint(10000, 99999))
    if dt == "city":
        return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"])
    return f"random_{dt}_{random.randint(1000, 9999)}"

Operation = Literal[
    "move",
    "click",
    "click_current",
    "double_click",
    "right_click",
    "drag",
    "type",
    "press",
    "hotkey",
    "scroll",
    "screenshot",
    "clipboard_read",
    "clipboard_write",
    "clipboard_paste",
    "active_window",
    "list_windows",
    "focus_window",
    "close_app",
    "screen_find",
    "clear_field",
    "smart_type",
    "wait",
    "random_data",
    "user_data",
]
KeyName = Literal[
    "enter",
    "tab",
    "esc",
    "backspace",
    "delete",
    "space",
    "up",
    "down",
    "left",
    "right",
    "home",
    "end",
    "pageup",
    "pagedown",
]
HotkeyName = Literal["copy", "paste", "select_all", "undo", "redo", "save", "find"]
ScrollDirection = Literal["up", "down", "left", "right"]


class ControlParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Operation
    x: int | None = Field(default=None, ge=0, le=100_000)
    y: int | None = Field(default=None, ge=0, le=100_000)
    x2: int | None = Field(default=None, ge=0, le=100_000)
    y2: int | None = Field(default=None, ge=0, le=100_000)
    text: str | None = Field(default=None, min_length=1, max_length=250)
    key: KeyName | None = None
    hotkey: HotkeyName | None = None
    direction: ScrollDirection | None = None
    amount: int | None = Field(default=None, ge=1, le=10)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    application: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=160)
    clipboard_text: str | None = Field(default=None, min_length=1, max_length=MAX_CLIPBOARD_CHARS)
    clear_first: bool | None = None
    seconds: float | None = Field(default=None, gt=0, le=10)
    data_type: str | None = Field(default=None, min_length=1, max_length=50)
    field: str | None = Field(default=None, min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_operation_fields(self) -> "ControlParameters":
        required: dict[str, set[str]] = {
            "move": {"x", "y"},
            "click": {"x", "y"},
            "click_current": set(),
            "double_click": {"x", "y"},
            "right_click": {"x", "y"},
            "drag": {"x", "y", "x2", "y2"},
            "type": {"text"},
            "press": {"key"},
            "hotkey": {"hotkey"},
            "scroll": {"direction", "amount"},
            "screenshot": set(),
            "clipboard_read": set(),
            "clipboard_write": {"clipboard_text"},
            "clipboard_paste": {"clipboard_text"},
            "active_window": set(),
            "list_windows": set(),
            "focus_window": {"title"},
            "close_app": {"application"},
            "screen_find": {"description"},
            "clear_field": set(),
            "smart_type": {"text"},
            "wait": {"seconds"},
            "random_data": {"data_type"},
            "user_data": {"field"},
        }
        allowed = {
            "move": {"x", "y"},
            "click": {"x", "y"},
            "click_current": set(),
            "double_click": {"x", "y"},
            "right_click": {"x", "y"},
            "drag": {"x", "y", "x2", "y2"},
            "type": {"text"},
            "press": {"key"},
            "hotkey": {"hotkey"},
            "scroll": {"direction", "amount"},
            "screenshot": set(),
            "clipboard_read": set(),
            "clipboard_write": {"clipboard_text"},
            "clipboard_paste": {"clipboard_text"},
            "active_window": set(),
            "list_windows": set(),
            "focus_window": {"title"},
            "close_app": {"application"},
            "screen_find": {"description"},
            "clear_field": set(),
            "smart_type": {"text", "clear_first"},
            "wait": {"seconds"},
            "random_data": {"data_type"},
            "user_data": {"field"},
        }
        supplied = {
            name for name in allowed[self.operation]
            if getattr(self, name) is not None and name != "clear_first"
        }
        missing = required[self.operation] - supplied
        unexpected = {
            name for name in (
                "x", "y", "x2", "y2", "text", "key", "hotkey", "direction", "amount",
                "title", "application", "description", "clipboard_text", "clear_first", "seconds", "data_type", "field",
            )
            if getattr(self, name) is not None and name not in allowed[self.operation]
        }
        if missing:
            raise ValueError(f"{self.operation} requires: {', '.join(sorted(missing))}.")
        if unexpected:
            raise ValueError(
                f"{self.operation} does not accept: {', '.join(sorted(unexpected))}."
            )
        if self.text is not None and self.operation == "type" and not self.text.isascii():
            raise ValueError("Text input currently supports ASCII characters only.")
        if self.text is not None and any(ord(char) < 32 and char not in "\t\n\r" for char in self.text):
            raise ValueError("Text input cannot contain control characters.")
        if self.clipboard_text is not None and any(
            ord(char) < 32 and char not in "\t\n\r" for char in self.clipboard_text
        ):
            raise ValueError("Clipboard text cannot contain control characters.")
        for field_name in ("title", "application", "description", "data_type", "field"):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} cannot be blank.")
        return self


class PermissionParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class StopParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ControlAdapter(Protocol):
    FAILSAFE: bool
    PAUSE: float

    def size(self) -> tuple[int, int]: ...
    def position(self) -> object: ...
    def moveTo(self, x: int, y: int, duration: float = 0) -> None: ...
    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None: ...
    def doubleClick(self, x: int, y: int, button: str = "left") -> None: ...
    def rightClick(self, x: int, y: int) -> None: ...
    def mouseDown(self, x: int, y: int, button: str = "left") -> None: ...
    def mouseUp(self, button: str = "left") -> None: ...
    def press(self, key: str) -> None: ...
    def write(self, text: str, interval: float = 0) -> None: ...
    def hotkey(self, *keys: str) -> None: ...
    def scroll(self, amount: int) -> None: ...
    def hscroll(self, amount: int) -> None: ...
    def screenshot(self) -> object: ...
    def clipboard_read(self) -> str: ...
    def clipboard_write(self, text: str) -> None: ...
    def active_window(self) -> dict[str, object] | None: ...
    def list_windows(self) -> list[dict[str, object]]: ...
    def focus_window(self, title: str) -> dict[str, object]: ...
    def close_app(self, application: str) -> dict[str, object]: ...


class PyAutoGuiAdapter:
    def __init__(self, module: object) -> None:
        self._module = module
        self.FAILSAFE = True
        self.PAUSE = 0.05

    @property
    def FAILSAFE(self) -> bool:
        return self._module.FAILSAFE

    @FAILSAFE.setter
    def FAILSAFE(self, enabled: bool) -> None:
        self._module.FAILSAFE = enabled

    @property
    def PAUSE(self) -> float:
        return self._module.PAUSE

    @PAUSE.setter
    def PAUSE(self, pause: float) -> None:
        self._module.PAUSE = pause

    def __getattr__(self, name: str) -> object:
        return getattr(self._module, name)

    @staticmethod
    def _require_windows() -> tuple[object, object]:
        if platform.system() != "Windows":
            raise NotImplementedError(
                "Active-window inspection and window management are currently supported on Windows only."
            )
        import ctypes
        from ctypes import wintypes

        return ctypes, wintypes

    @classmethod
    def _windows(cls) -> list[dict[str, object]]:
        ctypes, wintypes = cls._require_windows()
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            windows: list[dict[str, object]] = []
            callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def collect(hwnd: int, _parameter: int) -> bool:
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                title_buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title_buffer, length + 1)
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                try:
                    process_name = psutil.Process(pid.value).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    process_name = "unknown"
                windows.append({
                    "window_id": str(int(hwnd)),
                    "title": title_buffer.value[:300],
                    "process_id": int(pid.value),
                    "application": process_name,
                })
                return True

            callback = callback_type(collect)
            if not user32.EnumWindows(callback, 0):
                raise OSError(ctypes.get_last_error(), "Could not enumerate desktop windows")
            return windows
        except Exception as exc:
            logger.exception("Windows desktop enumeration failed")
            raise RuntimeError("Could not inspect visible desktop windows.") from exc

    def active_window(self) -> dict[str, object] | None:
        ctypes, _ = self._require_windows()
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        handle = int(user32.GetForegroundWindow())
        if not handle:
            return None
        return next(
            (window for window in self._windows() if window["window_id"] == str(handle)),
            None,
        )

    def list_windows(self) -> list[dict[str, object]]:
        return self._windows()

    def focus_window(self, title: str) -> dict[str, object]:
        ctypes, _ = self._require_windows()
        matches = [
            item for item in self._windows()
            if title.strip().casefold() in str(item["title"]).casefold()
        ]
        if not matches:
            raise ValueError("No visible window matches that title.")
        if len(matches) != 1:
            raise ValueError("More than one window matches; use a more specific title.")
        window = matches[0]
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        handle = int(window["window_id"])
        user32.ShowWindow(handle, 9)
        if not user32.SetForegroundWindow(handle):
            raise RuntimeError("Windows did not allow that window to receive focus.")
        if int(user32.GetForegroundWindow()) != handle:
            raise RuntimeError("The target window did not become the active window.")
        return {"operation": "focus_window", "window": window, "focused": True}

    def close_app(self, application: str) -> dict[str, object]:
        ctypes, wintypes = self._require_windows()
        windows = self._windows()
        query = application.strip().casefold()
        matches = [
            item for item in windows
            if query in str(item["application"]).casefold()
            or query in str(item["title"]).casefold()
        ]
        process_groups: dict[str, list[dict[str, object]]] = {}
        for item in matches:
            process_groups.setdefault(str(item["application"]).casefold(), []).append(item)
        if not process_groups:
            raise ValueError("No visible application matches that name.")
        if len(process_groups) != 1:
            raise ValueError("Multiple applications match; use a more specific name.")

        selected = next(iter(process_groups.values()))
        selected_pids = {int(window["process_id"]) for window in selected}
        protected_pids = {os.getpid()}
        try:
            process = psutil.Process()
            protected_pids.update(parent.pid for parent in process.parents())
            protected_pids.update(child.pid for child in process.children(recursive=True))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.warning("Could not enumerate the Alex process ancestry for close protection")
        if selected_pids & protected_pids:
            raise PermissionError("Alex and its parent application cannot be closed from desktop control.")

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        target_pids = selected_pids
        sent = 0

        def request_close(hwnd: int, _parameter: int) -> bool:
            nonlocal sent
            if not user32.IsWindowVisible(hwnd):
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if int(pid.value) in target_pids:
                user32.PostMessageW(hwnd, 0x0010, 0, 0)
                sent += 1
            return True

        callback = callback_type(request_close)
        if not user32.EnumWindows(callback, 0):
            raise OSError(ctypes.get_last_error(), "Could not send a polite window-close request")
        if sent == 0:
            raise RuntimeError("No matching application windows accepted a close request.")

        target_handles = {str(item["window_id"]) for item in selected}
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            current_handles = {str(item["window_id"]) for item in self._windows()}
            if not target_handles & current_handles:
                break
            time.sleep(0.1)
        current_handles = {str(item["window_id"]) for item in self._windows()}
        verified = not bool(target_handles & current_handles)
        return {
            "operation": "close_app",
            "application": selected[0]["application"],
            "windows_requested": sent,
            "verified_closed": verified,
        }

    @staticmethod
    def clipboard_read() -> str:
        try:
            clipboard = importlib.import_module("pyperclip")
            value = clipboard.paste()
        except ImportError as exc:
            raise RuntimeError("Clipboard access is unavailable; install Pyperclip.") from exc
        if not isinstance(value, str):
            raise RuntimeError("The system clipboard does not contain text.")
        return value

    @staticmethod
    def clipboard_write(text: str) -> None:
        try:
            clipboard = importlib.import_module("pyperclip")
            clipboard.copy(text)
        except ImportError as exc:
            raise RuntimeError("Clipboard access is unavailable; install Pyperclip.") from exc


class ComputerControlService:
    def __init__(
        self,
        adapter_factory: Callable[[], ControlAdapter] | None = None,
        screen_finder: Callable[[bytes, str, int, int], tuple[int, int] | None] | None = None,
        user_data_provider: Callable[[str], str | None] | None = None,
    ) -> None:
        self._adapter_factory = adapter_factory or self._load_adapter
        self._adapter_injected = adapter_factory is not None
        self._adapter: ControlAdapter | None = None
        self._permission_enabled = False
        self._operation_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._timed_out = threading.Event()
        self._active_operation: str | None = None
        self._active_operation_token: object | None = None
        self._pending_requests: dict[str, tuple[float, ControlParameters]] = {}
        self._user_data_provider = user_data_provider
        self._screen_finder = screen_finder

    def set_screen_finder(
        self,
        screen_finder: Callable[[bytes, str, int, int], tuple[int, int] | None],
    ) -> None:
        self._screen_finder = screen_finder

    def set_user_data_provider(
        self,
        provider: Callable[[str], str | None],
    ) -> None:
        self._user_data_provider = provider

    def status(self) -> dict[str, object]:
        with self._state_lock:
            available = (
                self._adapter is not None
                or self._adapter_injected
                or importlib.util.find_spec("pyautogui") is not None
            )
            return {
                "permission_enabled": self._permission_enabled,
                "adapter_available": available,
                "platform": platform.system(),
                "active_operation": self._active_operation,
                "emergency_stop_requested": self._stop_requested.is_set(),
            }

    def set_permission(self, enabled: bool) -> dict[str, object]:
        if enabled:
            if not self._operation_lock.acquire(blocking=False):
                raise RuntimeError("Wait for the active desktop operation to stop before re-arming permission.")
            try:
                adapter = self._get_adapter()
                adapter.FAILSAFE = True
                adapter.PAUSE = 0.05
                self._stop_requested.clear()
                self._timed_out.clear()
                with self._state_lock:
                    self._permission_enabled = True
            finally:
                self._operation_lock.release()
        else:
            self.stop()
            with self._state_lock:
                self._permission_enabled = False
        logger.info("Desktop-control session permission %s", "granted" if enabled else "revoked")
        return self.status()

    def stop(self) -> dict[str, object]:
        with self._state_lock:
            self._stop_requested.set()
            self._pending_requests.clear()
        release_error: str | None = None
        adapter = self._adapter
        if adapter is not None:
            try:
                adapter.mouseUp()
            except Exception as exc:
                release_error = f"{type(exc).__name__}: {exc}"
                logger.exception("Could not release the mouse during emergency stop")
        logger.warning("Desktop-control emergency stop requested")
        result = self.status()
        result["release_error"] = release_error
        return result

    def request_control(self, parameters: ControlParameters) -> dict[str, object]:
        with self._state_lock:
            if not self._permission_enabled:
                raise PermissionError("Grant desktop-control permission before asking Alex to control the computer.")
            if self._stop_requested.is_set():
                raise InterruptedError("Re-arm desktop-control permission before requesting an operation.")
            now = time.monotonic()
            self._expire_pending_requests(now)
            if len(self._pending_requests) >= MAX_PENDING_REQUESTS:
                raise RuntimeError("Too many pending desktop-control requests.")
            request_id = str(uuid4())
            self._pending_requests[request_id] = (now, parameters)
            return {
                "request_id": request_id,
                "status": "pending",
                "message": "Awaiting explicit user approval in Alex Controls; no desktop input has occurred.",
                "operation": parameters.operation,
                "parameters": parameters.model_dump(exclude_none=True),
                "expires_in_seconds": PENDING_REQUEST_TTL_SECONDS,
            }

    def pending_requests(self) -> list[dict[str, object]]:
        with self._state_lock:
            now = time.monotonic()
            self._expire_pending_requests(now)
            return [
                {
                    "request_id": request_id,
                    "operation": parameters.operation,
                    "parameters": parameters.model_dump(exclude_none=True),
                    "expires_in_seconds": max(
                        0,
                        int(PENDING_REQUEST_TTL_SECONDS - (now - created_at)),
                    ),
                }
                for request_id, (created_at, parameters) in self._pending_requests.items()
            ]

    def approve_request(self, request_id: str) -> dict[str, object]:
        with self._state_lock:
            now = time.monotonic()
            self._expire_pending_requests(now)
            request = self._pending_requests.pop(request_id, None)
        if request is None:
            raise ValueError("Desktop-control request is missing, expired, or already handled.")
        return self.execute(request[1])

    def dismiss_request(self, request_id: str) -> dict[str, object]:
        with self._state_lock:
            now = time.monotonic()
            self._expire_pending_requests(now)
            dismissed = self._pending_requests.pop(request_id, None)
        if dismissed is None:
            raise ValueError("Desktop-control request is missing, expired, or already handled.")
        return {"request_id": request_id, "dismissed": True}

    def execute(self, parameters: ControlParameters) -> dict[str, object]:
        with self._state_lock:
            if not self._permission_enabled:
                raise PermissionError("Grant desktop-control permission in the Controls panel first.")
        if not self._operation_lock.acquire(blocking=False):
            raise RuntimeError("Another desktop-control operation is already running.")

        operation = parameters.operation
        started = time.monotonic()
        operation_token = object()
        with self._state_lock:
            self._active_operation = operation
            self._active_operation_token = operation_token
        timeout = threading.Timer(
            OPERATION_TIMEOUT_SECONDS,
            self._timeout_operation,
            args=(operation_token, operation),
        )
        timeout.daemon = True
        timeout.start()
        logger.info("Desktop-control operation started: %s", operation)
        try:
            adapter = self._get_adapter()
            result = self._perform(adapter, parameters)
            self._ensure_running()
            logger.info(
                "Desktop-control operation finished: %s (%.3fs)",
                operation,
                time.monotonic() - started,
            )
            return result
        except Exception:
            logger.exception("Desktop-control operation failed: %s", operation)
            raise
        finally:
            timeout.cancel()
            with self._state_lock:
                self._active_operation = None
                self._active_operation_token = None
            self._operation_lock.release()

    def _perform(
        self,
        adapter: ControlAdapter,
        parameters: ControlParameters,
    ) -> dict[str, object]:
        self._ensure_running()
        operation = parameters.operation
        if operation == "screenshot":
            image = adapter.screenshot()
            image.thumbnail((1280, 720))
            stream = BytesIO()
            image.convert("RGB").save(stream, format="JPEG", quality=78)
            image_data = stream.getvalue()
            if len(image_data) > 8 * 1024 * 1024:
                raise ValueError("Screenshot exceeds the 8 MiB result limit.")
            return {
                "operation": operation,
                "mime_type": "image/jpeg",
                "data_base64": b64encode(image_data).decode("ascii"),
            }

        if operation in {"active_window", "list_windows", "focus_window", "close_app"}:
            if operation == "active_window":
                return {"operation": operation, "window": adapter.active_window()}
            if operation == "list_windows":
                windows = adapter.list_windows()
                return {"operation": operation, "windows": windows[:MAX_WINDOW_RESULTS]}
            if operation == "focus_window":
                return adapter.focus_window(parameters.title)
            return adapter.close_app(parameters.application)

        if operation in {"clipboard_read", "clipboard_write", "clipboard_paste"}:
            if operation == "clipboard_read":
                text = adapter.clipboard_read()
                if len(text) > MAX_CLIPBOARD_READ_CHARS:
                    raise ValueError("Clipboard content exceeds the 2000-character read limit.")
                return {"operation": operation, "text": text}
            adapter.clipboard_write(parameters.clipboard_text)
            if operation == "clipboard_paste":
                self._ensure_running()
                modifier = "command" if platform.system() == "Darwin" else "ctrl"
                adapter.hotkey(modifier, "v")
            return {
                "operation": operation,
                "characters_written": len(parameters.clipboard_text),
                "pasted": operation == "clipboard_paste",
            }

        if operation == "screen_find":
            if self._screen_finder is None:
                raise RuntimeError("Visual screen finding is unavailable until Gemini is configured.")
            image = adapter.screenshot()
            width, height = image.size
            image.thumbnail((1280, 720))
            resized_width, resized_height = image.size
            stream = BytesIO()
            image.convert("RGB").save(stream, format="JPEG", quality=78)
            self._ensure_running()
            point = self._screen_finder(
                stream.getvalue(),
                parameters.description,
                resized_width,
                resized_height,
            )
            if point is None:
                return {"operation": operation, "found": False}
            x, y = point
            if not (0 <= x < resized_width and 0 <= y < resized_height):
                raise ValueError("Visual search returned coordinates outside the captured image.")
            original_x = round(x * width / resized_width)
            original_y = round(y * height / resized_height)
            self._validate_point(adapter, original_x, original_y)
            return {
                "operation": operation,
                "found": True,
                "x": original_x,
                "y": original_y,
                "description": parameters.description,
            }

        if operation == "click_current":
            self._ensure_running()
            adapter.click(button="left")
            return {"operation": operation, "target": "current_pointer"}

        if operation in {"move", "click", "double_click", "right_click", "drag"}:
            self._validate_point(adapter, parameters.x, parameters.y)
            if operation == "drag":
                self._validate_point(adapter, parameters.x2, parameters.y2)
            x = parameters.x
            y = parameters.y
            if operation == "move":
                adapter.moveTo(x, y, duration=0)
            elif operation == "click":
                adapter.click(x, y, button="left")
            elif operation == "double_click":
                adapter.doubleClick(x, y, button="left")
            elif operation == "right_click":
                adapter.rightClick(x, y)
            else:
                self._drag(adapter, x, y, parameters.x2, parameters.y2)
            return {"operation": operation, "x": x, "y": y}

        if operation == "type":
            typed = 0
            for character in parameters.text:
                self._ensure_running()
                adapter.write(character, interval=0)
                typed += 1
            return {"operation": operation, "characters_typed": typed}

        if operation == "smart_type":
            clear_first = parameters.clear_first is not False
            if clear_first:
                self._clear_field(adapter)
            self._ensure_running()
            adapter.clipboard_write(parameters.text)
            self._ensure_running()
            modifier = "command" if platform.system() == "Darwin" else "ctrl"
            adapter.hotkey(modifier, "v")
            return {
                "operation": operation,
                "characters_typed": len(parameters.text),
                "field_cleared": clear_first,
            }

        if operation == "clear_field":
            self._clear_field(adapter)
            return {"operation": operation, "field_cleared": True}

        if operation == "wait":
            deadline = time.monotonic() + parameters.seconds
            while True:
                self._ensure_running()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(0.05, remaining))
            return {"operation": operation, "seconds": parameters.seconds}

        if operation == "press":
            self._ensure_running()
            adapter.press(parameters.key)
            return {"operation": operation, "key": parameters.key}

        if operation == "hotkey":
            self._ensure_running()
            keys = self._hotkey_keys(parameters.hotkey)
            adapter.hotkey(*keys)
            return {"operation": operation, "shortcut": parameters.hotkey}

        if operation == "scroll":
            self._ensure_running()
            amount = parameters.amount
            if parameters.direction == "up":
                adapter.scroll(amount)
            elif parameters.direction == "down":
                adapter.scroll(-amount)
            elif parameters.direction == "right":
                adapter.hscroll(amount)
            else:
                adapter.hscroll(-amount)
            return {
                "operation": operation,
                "direction": parameters.direction,
                "amount": amount,
            }
        if operation == "random_data":
            self._ensure_running()
            data_type = (parameters.data_type or "name").strip()
            value = _generate_random_data(data_type)
            return {
                "operation": operation,
                "data_type": data_type,
                "value": value,
            }

        if operation == "user_data":
            self._ensure_running()
            target_field = (parameters.field or "name").strip()
            from_memory = False
            value = None
            if self._user_data_provider is not None:
                try:
                    value = self._user_data_provider(target_field)
                    if value and isinstance(value, str) and value.strip():
                        from_memory = True
                        value = value.strip()
                    else:
                        value = None
                except Exception:
                    logger.warning("Could not read user data for field: %s", target_field)
            if not value:
                value = _generate_random_data(target_field)
            return {
                "operation": operation,
                "field": target_field,
                "value": value,
                "source": "memory" if from_memory else "synthetic",
            }

        raise ValueError("Unsupported computer-control operation.")

    def _clear_field(self, adapter: ControlAdapter) -> None:
        self._ensure_running()
        modifier = "command" if platform.system() == "Darwin" else "ctrl"
        adapter.hotkey(modifier, "a")
        self._ensure_running()
        adapter.press("delete")

    def _drag(
        self,
        adapter: ControlAdapter,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ) -> None:
        distance = max(abs(x2 - x1), abs(y2 - y1))
        steps = max(1, min(30, distance // 40))
        adapter.moveTo(x1, y1, duration=0)
        adapter.mouseDown(x1, y1, button="left")
        try:
            for step in range(1, steps + 1):
                self._ensure_running()
                x = round(x1 + (x2 - x1) * step / steps)
                y = round(y1 + (y2 - y1) * step / steps)
                adapter.moveTo(x, y, duration=0)
                time.sleep(0.01)
        finally:
            adapter.mouseUp(button="left")

    @staticmethod
    def _validate_point(adapter: ControlAdapter, x: int, y: int) -> None:
        width, height = adapter.size()
        if x >= width or y >= height:
            raise ValueError(
                f"Coordinates must be within the primary display ({width}x{height})."
            )

    def _get_adapter(self) -> ControlAdapter:
        if self._adapter is None:
            self._adapter = self._adapter_factory()
            self._adapter.FAILSAFE = True
            self._adapter.PAUSE = 0.05
        return self._adapter

    @staticmethod
    def _load_adapter() -> ControlAdapter:
        try:
            return PyAutoGuiAdapter(importlib.import_module("pyautogui"))
        except ImportError as exc:
            raise RuntimeError(
                "PyAutoGUI is unavailable. Reinstall Alex's backend dependencies."
            ) from exc

    def _ensure_running(self) -> None:
        if self._timed_out.is_set():
            raise TimeoutError("Desktop-control operation exceeded its time limit.")
        if self._stop_requested.is_set():
            raise InterruptedError("Desktop-control operation stopped by the user.")

    def _expire_pending_requests(self, now: float) -> None:
        expired = [
            request_id
            for request_id, (created_at, _) in self._pending_requests.items()
            if now - created_at >= PENDING_REQUEST_TTL_SECONDS
        ]
        for request_id in expired:
            del self._pending_requests[request_id]

    def _timeout_operation(self, operation_token: object, operation: str) -> None:
        with self._state_lock:
            if (
                self._active_operation_token is not operation_token
                or self._stop_requested.is_set()
            ):
                return
            self._timed_out.set()
            self._stop_requested.set()
        logger.error("Desktop-control operation timed out: %s", operation)
        if self._adapter is not None:
            try:
                self._adapter.mouseUp()
            except Exception:
                logger.exception("Could not release the mouse after desktop-control timeout")

    @staticmethod
    def _hotkey_keys(name: HotkeyName) -> tuple[str, ...]:
        modifier = "command" if platform.system() == "Darwin" else "ctrl"
        keys: dict[HotkeyName, tuple[str, ...]] = {
            "copy": (modifier, "c"),
            "paste": (modifier, "v"),
            "select_all": (modifier, "a"),
            "undo": (modifier, "z"),
            "redo": (modifier, "shift", "z") if modifier == "command" else (modifier, "y"),
            "save": (modifier, "s"),
            "find": (modifier, "f"),
        }
        return keys[name]
