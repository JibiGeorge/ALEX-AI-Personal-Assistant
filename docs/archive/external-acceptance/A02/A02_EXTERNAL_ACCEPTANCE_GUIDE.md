# A02 – Computer Control External Acceptance & Runtime Verification Guide

**Target Application:** `Alex`  
**Reference Baseline:** `Mark-LVI-main` (read-only reference, completely unchanged)  
**Authoritative Audit Baseline:** `A02_COMPLETION_AUDIT.md` (Revision 3.0)  
**Implementation State:** **FROZEN** (No further code changes permitted; automated unit and API verification complete)  
**Current Milestone Acceptance Decision:** **`NOT ACCEPTED`**  
**Document Purpose:** Provide an authorized external tester with an exact, reproducible procedure to verify physical Windows desktop control and live Gemini integration on an unrestricted workstation.

---

## 1. Implementation Freeze Notice

1. **Code Freeze:** All computer-control code in [`backend/app/services/computer_control_service.py`](file:///d:/Workspace/Jibi/Alex/backend/app/services/computer_control_service.py), [`backend/app/actions/builtins/computer_control.py`](file:///d:/Workspace/Jibi/Alex/backend/app/actions/builtins/computer_control.py), [`frontend/src/pages/ComputerControlPage.tsx`](file:///d:/Workspace/Jibi/Alex/frontend/src/pages/ComputerControlPage.tsx), and [`frontend/electron/main.ts`](file:///d:/Workspace/Jibi/Alex/frontend/electron/main.ts) is **frozen**.
2. **Acceptance Invariant:** The final decision remains **`NOT ACCEPTED`** until an authorized human tester independently executes the tests in this guide on an unrestricted Windows desktop and captures genuine empirical runtime evidence.
3. **No Mocks / No Policy Circumvention:** Testers must never bypass corporate Group Policy, run simulated mocks in place of hardware interaction, or fabricate test results.

---

## 2. Test Environment Requirements & Prerequisites

The tester must run these tests on a workstation satisfying:

| Requirement | Specification | Verification Command |
|---|---|---|
| **Operating System** | Windows 10 (Build 19045+) or Windows 11 (Build 22000+) | `winver` or `systeminfo` |
| **User Session** | Active, interactive graphical desktop session (physical display or unconstrained RDP console) | User must be logged into desktop |
| **Display Settings** | Primary display recommended at **100% DPI scaling** (avoids OS coordinate scaling discrepancies) | Windows Display Settings |
| **Python Runtime** | Python 3.11+ with Alex virtual environment configured | `backend\.venv\Scripts\python --version` |
| **Node.js Runtime** | Node.js 20+ and npm | `node --version` |
| **Execution Policy** | Host policy permits Python execution and GUI automation | Group Policy must not block execution |
| **Network Access** | Outbound HTTPS access to `generativelanguage.googleapis.com` | Ping / HTTPS connectivity check |

---

## 3. Part 1: Windows Desktop Runtime Verification Guide

### Test 1.1: Comprehensive Desktop Control Smoke Test
**Script:** [`Alex/backend/tests/manual_computer_control_smoke.py`](file:///d:/Workspace/Jibi/Alex/backend/tests/manual_computer_control_smoke.py)  
**Scope:** Window focus, active window assertion, visible window enumeration, mouse cursor movement, physical button click, keyboard typing, clipboard write/paste, field clearing, downward viewport scrolling, in-memory screenshot capture, and clean shutdown.

#### Exact Execution Commands
From the `Alex/` directory:

* **Windows Command Prompt (CMD):**
  ```cmd
  cd Alex
  set ALEX_ENABLE_DESKTOP_SMOKE=1
  backend\.venv\Scripts\python backend\tests\manual_computer_control_smoke.py
  ```

* **Windows PowerShell:**
  ```powershell
  cd Alex
  $env:ALEX_ENABLE_DESKTOP_SMOKE="1"
  & backend\.venv\Scripts\python backend\tests\manual_computer_control_smoke.py
  ```

* **Windows Git Bash (MINGW64):**
  ```bash
  cd Alex
  export ALEX_ENABLE_DESKTOP_SMOKE=1
  backend/.venv/Scripts/python backend/tests/manual_computer_control_smoke.py
  ```

#### Observable Physical Behaviors on Screen
Watch the screen during execution (duration: ~4 seconds):
1. A native Tkinter window titled **`Alex Safe Computer Control Test`** (`600x360`) appears at coordinates `(120, 120)`.
2. The window is brought to foreground focus via Win32 `ShowWindow` + `SetForegroundWindow`.
3. The mouse cursor visibly glides to the `Entry` text box (`x+35, y+10`) and clicks to focus it.
4. The text **`Alex safe smoke`** is typed into the Entry widget character-by-character.
5. The clipboard is populated with **`Alex clipboard smoke`**, the Entry widget is cleared via `Ctrl+A` + `Delete`, and the text is pasted via `Ctrl+V`. The Entry widget now reads `Alex clipboard smoke`.
6. An in-memory JPEG screenshot is captured (no disk write).
7. The mouse cursor visibly moves to the `Text` box (`x+80, y+80`), clicks, and scrolls downward by 2 units. The script verifies that `text.yview()[0]` has advanced.
8. The window closes cleanly, previous user clipboard text is restored, and session permission is revoked.

#### Expected Terminal Output
```text
PASS: focus, active-window/process identification, visible-window listing, mouse,
      keyboard, clipboard read/write/paste, scroll and in-memory screenshot.
```
**Expected Exit Code:** `0`

---

### Test 1.2: Polite Windows Application Close Test
**Script:** [`Alex/backend/tests/manual_computer_control_close_smoke.py`](file:///d:/Workspace/Jibi/Alex/backend/tests/manual_computer_control_close_smoke.py)  
**Scope:** Validates Win32 `WM_CLOSE` polite window termination, process ancestry protection, and verified process exit.

#### Exact Execution Commands
From the `Alex/` directory:

* **Windows CMD:**
  ```cmd
  set ALEX_ENABLE_DESKTOP_SMOKE=1
  backend\.venv\Scripts\python backend\tests\manual_computer_control_close_smoke.py
  ```

* **Git Bash:**
  ```bash
  export ALEX_ENABLE_DESKTOP_SMOKE=1
  backend/.venv/Scripts/python backend/tests/manual_computer_control_close_smoke.py
  ```

#### Observable Physical Behaviors on Screen
1. A temporary Tkinter test window titled **`Alex Safe Close Smoke Target`** (`360x120`) appears at `(160, 160)`.
2. The worker identifies the target via `list_windows`.
3. It issues `close_app(application="Alex Safe Close Smoke Target")`.
4. Win32 `PostMessageW(hwnd, 0x0010)` (`WM_CLOSE`) is sent politely to the target.
5. The window disappears, and the worker confirms process termination.

#### Expected Terminal Output
```json
{"operation": "close_app", "application": "Alex Safe Close Smoke Target", "windows_requested": 1, "verified_closed": true}
```
**Expected Exit Code:** `0`

---

## 4. Part 2: Live Gemini Integration Verification Guide

### 4.1 Secure Credential Setup
Testers must supply a valid Gemini API key. In strict accordance with security guidelines:
> [!IMPORTANT]
> **No API keys or credentials must ever appear in logs, test output, terminal recordings, or Git commits.**

Choose **one** of the following secure configuration options:

* **Option A: Alex Setup GUI (Stored in OS Credential Manager)**
  1. Launch Alex: `./alex launch` (or `npm run launch`).
  2. Open the **Setup** drawer from the top-left HUD header.
  3. Enter your Gemini API key in the API Key input field and click **Save**.
  4. The key is securely saved to Windows Credential Manager (`keyring`) and never written to plaintext.

* **Option B: Local `.env` Configuration (Git-Ignored)**
  1. Open [`Alex/.env`](file:///d:/Workspace/Jibi/Alex/.env).
  2. Set: `GEMINI_API_KEY=AIzaSy...YourKeyHere`
  3. Save the file. Alex's backend automatically loads this file at startup.

---

### 4.2 End-to-End Proposal & Execution Workflow Verification

#### Step 1: Launch the Application
```bash
cd Alex
./alex launch
```
Verify the startup summary reports:
- `Backend API`: `ONLINE` (Port 8765)
- `Frontend UI`: `ONLINE` (Port 5173)
- `Electron App`: `ONLINE` (Desktop Window)

#### Step 2: Grant Session Desktop-Control Permission
1. In the Alex HUD, open the **Controls** drawer from the top header.
2. Under **Desktop Control Permission**, verify the initial state is **Disabled** (Default Safe State).
3. Toggle the permission to **Enabled** and confirm the prompt.
4. Verify the status indicator turns green (`Permission: Active`).

#### Step 3: Natural Language Request Turn
Submit a natural-language computer control request using voice or text:
* **Spoken (Gemini Live):** *"Please move the mouse to coordinate 300, 300 and click."*
* **Text Chat:** *"Request a mouse click at x=400, y=400."*

#### Step 4: Verify Proposal Fidelity (No Desktop Action Yet)
1. In the **Controls** drawer, observe the **Pending Control Requests** section.
2. Confirm a proposal card appears with:
   - Unique Request UUID
   - Exact proposed operation: `click`
   - Exact proposed coordinates: `{"x": 400, "y": 400}`
   - 300-second live TTL countdown timer
3. **Verify Security Invariant:** Confirm that **no mouse movement or click occurred on the desktop**.

#### Step 5: Manual Human Approval
1. Click the **"Approve and execute"** button on the proposal card.
2. Observe the screen:
   - The proposal card is consumed from the pending list.
   - The mouse physically moves to `(400, 400)` and clicks.
3. Observe the chat/voice transcript:
   - Alex reports execution success back to Gemini.
   - Gemini verbally or textually confirms completion to the user.

---

### 4.3 Negative & Security Controls Verification

Execute these tests to confirm protection mechanisms cannot be bypassed:

| Test ID | Scenario | Procedure | Expected Safe Outcome |
|---|---|---|---|
| **SEC-01** | **Direct Model Bypass** | Inspect `ActionRegistry.model_declarations()`. | `computer.control` and `computer.approve` are **omitted** from model declarations. The model cannot execute actions directly. |
| **SEC-02** | **Proposal Rejection** | Issue request -> Click **"Reject request"** in Controls drawer. | Proposal is purged (`computer.dismiss`). Zero desktop input occurs. Replaying the dismissal fails. |
| **SEC-03** | **Proposal Expiration** | Issue request -> Wait 300 seconds without clicking approve. | Countdown reaches 0. Proposal is purged. Attempting to approve an expired request raises `ValueError`. |
| **SEC-04** | **Parameter Tampering** | Attempt to modify payload coordinates during approval. | Rejected with Pydantic `extra="forbid"` validation error. Parameters are immutable server-side. |
| **SEC-05** | **Emergency Stop Latch** | Start an operation -> Click **"Emergency Stop"** in Controls drawer. | Active operation immediately halts, mouse button is released (`mouseUp`), all pending requests are purged, and stop state stays **latched** until explicitly re-armed. |
| **SEC-06** | **Shutdown Revocation** | Close Alex or send `POST /api/v1/shutdown`. | FastAPI lifespan executes `set_permission(False)`. Permission is revoked; mouse released. |

---

## 5. Part 3: External Acceptance Checklist

The authorized tester must complete every row before signing off:

### Section A: Hardware & Desktop Verification
- [ ] **TC-A02-01 (Interactive Mouse & Keyboard):** `manual_computer_control_smoke.py` passed with exit code 0. Cursor movement, click, and typing into Tk Entry widget visually verified.
- [ ] **TC-A02-02 (Clipboard Operations):** `manual_computer_control_smoke.py` verified bounded clipboard write, `Ctrl+A` + `Delete` clear, and `Ctrl+V` paste.
- [ ] **TC-A02-03 (Display Scrolling):** Downward scrolling observed with verified Tk Text viewport `yview` advancement.
- [ ] **TC-A02-04 (In-Memory Screenshot):** In-memory thumbnail JPEG generated without writing any files to disk.
- [ ] **TC-A02-05 (Win32 Polite Close):** `manual_computer_control_close_smoke.py` verified polite `WM_CLOSE` and confirmed process exit of target window.

### Section B: Live Gemini Workflow & Human-in-the-Loop
- [ ] **TC-A02-06 (Proposal Generation):** Spoken or text prompt created a pending proposal with UUID and 300s TTL.
- [ ] **TC-A02-07 (Zero Pre-Approval Input):** Confirmed no desktop input occurred prior to clicking "Approve and execute".
- [ ] **TC-A02-08 (Parameter Display Fidelity):** Controls UI rendered exact operation and parameters with warning banners.
- [ ] **TC-A02-09 (Approved Execution):** Clicking "Approve and execute" performed the bounded operation and reported the outcome to Gemini.
- [ ] **TC-A02-10 (Proposal Rejection):** Clicking "Reject request" consumed the proposal without desktop input.
- [ ] **TC-A02-11 (Replay & Tamper Defense):** Replaying an approved request token or modifying parameters failed immediately.
- [ ] **TC-A02-12 (Emergency Stop Latch):** Emergency stop halted execution, released the mouse, cleared proposals, and required explicit re-arm.

---

## 6. Acceptance Sign-Off Block

| Item | Record |
|---|---|
| **Tester Name** | __________________________________________ |
| **Workstation OS & Build** | __________________________________________ (e.g. Windows 11 23H2 Build 22631) |
| **Test Execution Date** | __________________________________________ |
| **All 12 Test Cases Passed?** | `[ ] YES` &nbsp;&nbsp;&nbsp;&nbsp; `[ ] NO` |
| **Audit Status Transition** | If YES: Transition `A02_COMPLETION_AUDIT.md` status to **`ACCEPTED`**. |
| **Tester Signature** | __________________________________________ |

---

## 7. Evidence Collection Guidelines

To submit evidence for acceptance sign-off:
1. Save the console stdout log from `manual_computer_control_smoke.py` and `manual_computer_control_close_smoke.py` to `Alex/docs/evidence/runtime_smoke_stdout.txt`.
2. Take a screenshot of the Alex Controls drawer showing an active proposal card with countdown and parameters (ensure no API keys are visible).
3. Record the OS build string (`systeminfo | findstr /B /C:"OS Name" /C:"OS Version"`).
4. Update `A02_COMPLETION_AUDIT.md` Section H from **`NOT ACCEPTED`** to **`ACCEPTED`**, citing the completed sign-off block.

