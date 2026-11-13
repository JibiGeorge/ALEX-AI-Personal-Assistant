import json
import os
import platform
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path

if os.environ.get("ALEX_ENABLE_DESKTOP_SMOKE") != "1":
    raise SystemExit("Set ALEX_ENABLE_DESKTOP_SMOKE=1 to run this interactive desktop test.")
if platform.system() != "Windows":
    raise SystemExit("This application-close smoke test requires Windows.")

TARGET_TITLE = "Alex Safe Close Smoke Target"
SCRIPT_PATH = str(Path(__file__).resolve())


def run_target() -> None:
    root = tk.Tk()
    root.title(TARGET_TITLE)
    root.geometry("360x120+160+160")
    tk.Label(root, text="Temporary test window; safe to close.").pack(padx=20, pady=30)
    root.mainloop()


def run_worker() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.services.computer_control_service import ComputerControlService, ControlParameters

    service = ComputerControlService()
    service.set_permission(True)
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            windows = service.execute(ControlParameters(operation="list_windows"))["windows"]
            if any(window["title"] == TARGET_TITLE for window in windows):
                result = service.execute(ControlParameters(
                    operation="close_app",
                    application=TARGET_TITLE,
                ))
                print(json.dumps(result))
                if result["verified_closed"]:
                    return
                raise RuntimeError("The test window remained open after the close request.")
            time.sleep(0.1)
        raise TimeoutError("The temporary test window did not appear.")
    finally:
        service.set_permission(False)


def run_smoke() -> None:
    target = subprocess.Popen([sys.executable, SCRIPT_PATH, "--target"])
    worker = None
    try:
        worker = subprocess.Popen(
            [sys.executable, SCRIPT_PATH, "--worker"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = worker.communicate(timeout=15)
        if worker.returncode != 0:
            raise RuntimeError(
                f"Close worker failed with exit code {worker.returncode}: {stderr.strip()}"
            )
        result = json.loads(stdout.strip().splitlines()[-1])
        if result.get("verified_closed") is not True:
            raise RuntimeError(f"Close worker did not verify closure: {result!r}")
        target.wait(timeout=5)
        print("PASS: the uniquely titled temporary Tk window received WM_CLOSE and exited.")
    finally:
        if worker is not None and worker.poll() is None:
            worker.terminate()
            worker.wait(timeout=3)
        if target.poll() is None:
            target.terminate()
            target.wait(timeout=3)


if __name__ == "__main__":
    if sys.argv[1:] == ["--target"]:
        run_target()
    elif sys.argv[1:] == ["--worker"]:
        run_worker()
    elif not sys.argv[1:]:
        run_smoke()
    else:
        raise SystemExit("Unknown smoke-test mode.")
