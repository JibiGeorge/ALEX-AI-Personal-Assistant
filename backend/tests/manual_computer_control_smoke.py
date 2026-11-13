import os
import sys
import time
import tkinter as tk
from pathlib import Path

import pyperclip

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.computer_control_service import ComputerControlService, ControlParameters


if os.environ.get("ALEX_ENABLE_DESKTOP_SMOKE") != "1":
    raise SystemExit("Set ALEX_ENABLE_DESKTOP_SMOKE=1 to run this interactive desktop test.")


root = tk.Tk()
root.title("Alex Safe Computer Control Test")
root.geometry("600x360+120+120")
root.resizable(False, False)

entry = tk.Entry(root, width=48)
entry.place(x=40, y=45)

text = tk.Text(root, width=65, height=10)
text.insert("1.0", "\n".join(f"Safe scroll line {index}" for index in range(30)))
text.place(x=40, y=90)

root.update()
root.lift()
root.focus_force()
root.update()

clipboard_before = pyperclip.paste()
service = ComputerControlService()
service.set_permission(True)

try:
    entry_x = entry.winfo_rootx() + 35
    entry_y = entry.winfo_rooty() + 10
    service.execute(ControlParameters(operation="focus_window", title=root.title()))
    assert root.title() in service.execute(
        ControlParameters(operation="active_window")
    )["window"]["title"]
    assert any(
        window["title"] == root.title()
        for window in service.execute(ControlParameters(operation="list_windows"))["windows"]
    )

    service.execute(ControlParameters(operation="move", x=entry_x, y=entry_y))
    service.execute(ControlParameters(operation="click", x=entry_x, y=entry_y))
    service.execute(ControlParameters(operation="type", text="Alex safe smoke"))
    root.update()
    assert entry.get() == "Alex safe smoke"

    service.execute(ControlParameters(
        operation="clipboard_write",
        clipboard_text="Alex clipboard smoke",
    ))
    assert pyperclip.paste() == "Alex clipboard smoke"
    service.execute(ControlParameters(operation="clear_field"))
    service.execute(ControlParameters(
        operation="clipboard_paste",
        clipboard_text="Alex clipboard smoke",
    ))
    root.update()
    assert entry.get() == "Alex clipboard smoke"

    capture = service.execute(ControlParameters(operation="screenshot"))
    assert capture["mime_type"] == "image/jpeg"
    assert capture["data_base64"]

    text_x = text.winfo_rootx() + 80
    text_y = text.winfo_rooty() + 80
    before_scroll = text.yview()
    service.execute(ControlParameters(operation="move", x=text_x, y=text_y))
    service.execute(ControlParameters(operation="click", x=text_x, y=text_y))
    service.execute(ControlParameters(operation="scroll", direction="down", amount=2))
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        root.update()
        if text.yview()[0] > before_scroll[0]:
            break
        time.sleep(0.01)
    after_scroll = text.yview()
    if after_scroll[0] <= before_scroll[0]:
        print(
            "Scroll diagnostic:",
            f"viewport_before={before_scroll!r}",
            f"viewport_after={after_scroll!r}",
        )
    assert after_scroll[0] > before_scroll[0]

    print("PASS: focus, active-window/process identification, visible-window listing, mouse,")
    print("      keyboard, clipboard read/write/paste, scroll and in-memory screenshot.")
finally:
    service.set_permission(False)
    pyperclip.copy(clipboard_before)
    root.destroy()
