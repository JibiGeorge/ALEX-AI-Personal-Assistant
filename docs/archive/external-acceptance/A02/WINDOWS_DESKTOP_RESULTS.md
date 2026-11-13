# A02 – Windows Desktop Runtime Verification Results

**Target Script 1:** [`Alex/backend/tests/manual_computer_control_smoke.py`](file:///d:/Workspace/Jibi/Alex/backend/tests/manual_computer_control_smoke.py)  
**Target Script 2:** [`Alex/backend/tests/manual_computer_control_close_smoke.py`](file:///d:/Workspace/Jibi/Alex/backend/tests/manual_computer_control_close_smoke.py)  
**Verification Mode:** Live physical GUI session on an authorized Windows workstation  
**Current Verification Status:** **`PENDING EXTERNAL EXECUTION`**

---

## 1. Test Execution Instructions for External Tester

Run the following commands from the `Alex/` directory in Windows CMD or PowerShell:

```cmd
cd Alex
set ALEX_ENABLE_DESKTOP_SMOKE=1
backend\.venv\Scripts\python backend\tests\manual_computer_control_smoke.py > docs\external-acceptance\A02\evidence\desktop\smoke_stdout.txt 2>&1
backend\.venv\Scripts\python backend\tests\manual_computer_control_close_smoke.py > docs\external-acceptance\A02\evidence\desktop\close_stdout.txt 2>&1
```

---

## 2. Desktop Test Case Results Table

| Test ID | Capability | Test Procedure & Assertion | Observable Screen Action | Exit Code | Evidence File | Result |
|---|---|---|---|---|---|---|
| **TC-A02-01** | **Window Focus & Active Detection** | Win32 `ShowWindow` + `SetForegroundWindow` on Tkinter window; asserts `GetForegroundWindow()` matches title. | Tkinter window (`600x360`) appears at `(120, 120)` and comes to front. | *[0]* | `evidence/desktop/smoke_stdout.txt` | *[PENDING]* |
| **TC-A02-02** | **Visible Window Enumeration** | Win32 `EnumWindows` + `psutil` extracts visible window titles and PIDs. | Test window title appears in enumerated window list. | *[0]* | `evidence/desktop/smoke_stdout.txt` | *[PENDING]* |
| **TC-A02-03** | **Mouse Movement & Click** | Moves pointer to `(entry_x, entry_y)` and performs left click into native Tk Entry widget. | Cursor visibly moves to text box and focuses input caret. | *[0]* | `evidence/desktop/smoke_stdout.txt` | *[PENDING]* |
| **TC-A02-04** | **Keyboard Text Typing** | Dispatches `type(text="Alex safe smoke")` character by character with safety pauses. | Text `"Alex safe smoke"` is visibly typed into Entry widget. | *[0]* | `evidence/desktop/smoke_stdout.txt` | *[PENDING]* |
| **TC-A02-05** | **Clipboard Operations** | `clipboard_write`, `clear_field` (`Ctrl+A` + `Delete`), `clipboard_paste` (`Ctrl+V`). | Text in Entry widget replaced by `"Alex clipboard smoke"`. | *[0]* | `evidence/desktop/smoke_stdout.txt` | *[PENDING]* |
| **TC-A02-06** | **In-Memory Screenshot** | Bounded thumbnail JPEG (1280x720) encoded in-memory as Base64. | No file written to disk; MIME type `image/jpeg` returned. | *[0]* | `evidence/desktop/smoke_stdout.txt` | *[PENDING]* |
| **TC-A02-07** | **Display Scrolling** | Moves to Text widget, clicks, sends `scroll(down, 2)`, asserts `yview` change. | Text lines visibly scroll up; viewport `yview()[0]` advances. | *[0]* | `evidence/desktop/smoke_stdout.txt` | *[PENDING]* |
| **TC-A02-08** | **Polite Window Close** | Win32 `PostMessageW(WM_CLOSE)` sent to test window; verified process exit. | Target window disappears; process exits within 3 seconds. | *[0]* | `evidence/desktop/close_stdout.txt` | *[PENDING]* |

---

## 3. Raw Execution Evidence Log

### Test 1 Output (`manual_computer_control_smoke.py`)
```text
[Paste terminal stdout from docs\external-acceptance\A02\evidence\desktop\smoke_stdout.txt below]
```

### Test 2 Output (`manual_computer_control_close_smoke.py`)
```text
[Paste terminal stdout from docs\external-acceptance\A02\evidence\desktop\close_stdout.txt below]
```

---

## 4. Current Host Baseline Record

- **Audit Date:** 2026-11-01  
- **Runner Host Status:** `BLOCKED_BY_ENVIRONMENT`  
  - Attempting to spawn powershell/subprocess returned:  
    `Command failed to run: This program is blocked by group policy.`
- **External Tester Sign-Off Status:** Awaiting execution by authorized tester on an unrestricted Windows workstation.

