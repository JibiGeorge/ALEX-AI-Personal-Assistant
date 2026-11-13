# Alex – Security & Sender Validation Acceptance Protocols

**Document:** `SECURITY_ACCEPTANCE_TESTS.md`  
**Purpose:** Test procedures for origin-based navigation, canonical production file checks, IPC sender authorization, and credential protection (`TC-SEC-01` to `TC-SEC-10`).

---

## 1. Overview & Trust Boundaries

The Alex desktop security model enforces strict separation between the untrusted web renderer and native operating system capabilities:

```text
┌────────────────────────────────────────────────────────┐
│               Chromium Renderer Context                │
│  - contextIsolation: true                             │
│  - nodeIntegration: false                             │
│  - sandbox: true                                      │
│  - window.open: DENIED                                │
│  - will-navigate: LOCKED to approved origin or bundle │
└───────────────────────────┬────────────────────────────┘
                            │ typed IPC invoke (contextBridge)
┌───────────────────────────▼────────────────────────────┐
│                 Electron Main Process                  │
│  - assertTrustedSender: sender & mainFrame validated   │
│  - isAllowedDevOrigin: exact origin matching           │
│  - isAllowedProdFile: canonical file path matching     │
└───────────────────────────┬────────────────────────────┘
                            │ 127.0.0.1 loopback HTTP (Bearer Token)
┌───────────────────────────▼────────────────────────────┐
│                 Python FastAPI Sidecar                 │
│  - Endpoint authentication via per-run token           │
│  - Pydantic schema validation                          │
└────────────────────────────────────────────────────────┘
```

---

## 2. Automated Security Suite Execution

The tester can execute the automated security verification suite directly:

```cmd
npx --prefix frontend vitest run src/electron-security.test.ts > docs\external-acceptance\unified-startup\evidence\security\security_test_stdout.txt 2>&1
```

### Expected Automated Test Output
```text
 ✓ src/electron-security.test.ts (8 tests)
   ✓ Electron Security: Origin-based URL Validation
     ✓ permits exact loopback development origins
     ✓ rejects malicious string-prefix domain bypass attempts
     ✓ rejects unauthorized external protocols and ports
     ✓ handles malformed URLs gracefully without throwing uncaught exceptions
   ✓ Electron Security: Production Canonical File Path Validation
     ✓ permits exact canonical file URL matching the production bundle
     ✓ rejects non-file protocols in production mode
     ✓ rejects unauthorized local file URLs
     ✓ rejects path traversal escape attempts

 Test Files  1 passed (1)
      Tests  8 passed (8)
```

---

## 3. Detailed Security Verification Protocols

### TC-SEC-01 & TC-SEC-02: Dev Origin Validation & Subdomain Spoofing Defense
* **Objective:** Verify that development URL validation rejects string-prefix domain spoofing.
* **Mechanism:** [`isAllowedDevOrigin(testUrl, expectedUrl)`](file:///d:/Workspace/Jibi/Alex/frontend/electron/main.ts#L573-L581) evaluates `new URL(testUrl).origin === new URL(expectedUrl).origin`.
* **Validation Matrix:**
  * `http://127.0.0.1:5173/` -> **PERMITTED**
  * `http://127.0.0.1:5173/chat` -> **PERMITTED**
  * `http://127.0.0.1:5173.attacker.com/` -> **BLOCKED**
  * `http://127.0.0.1:51730/` -> **BLOCKED**
  * `http://127.0.0.1:5173-evil.com/` -> **BLOCKED**

---

### TC-SEC-03 to TC-SEC-05: Production Canonical File Path Security
* **Objective:** Ensure production IPC and navigation do not rely on `URL.origin` for `file://` protocols and reject local file traversal.
* **Mechanism:** [`isAllowedProdFile(testUrl)`](file:///d:/Workspace/Jibi/Alex/frontend/electron/main.ts#L583-L592) resolves `path.resolve(fileURLToPath(testUrl))` and compares against canonical `path.resolve(__dirname, "../../dist/index.html")`.
* **Validation Matrix:**
  * `file:///.../frontend/dist/index.html` -> **PERMITTED**
  * `file:///etc/passwd` -> **BLOCKED**
  * `file:///C:/Windows/System32/cmd.exe` -> **BLOCKED**
  * `file:///.../dist/index.html/../../secret.txt` -> **BLOCKED**
  * `http://127.0.0.1:5173/` in production -> **BLOCKED**

---

### TC-SEC-06: IPC Sender & Frame Isolation
* **Objective:** Verify that detached frames or child iframes cannot invoke IPC handlers.
* **Mechanism:** [`assertTrustedSender(event)`](file:///d:/Workspace/Jibi/Alex/frontend/electron/main.ts#L622-L639) inspects `event.sender` and `event.senderFrame`.
* **Validation Invariant:** If `event.senderFrame !== mainWindow.webContents.mainFrame`, the IPC call throws `"Untrusted IPC sender"`.

---

### TC-SEC-07 & TC-SEC-08: Window Creation & Navigation Lockdown
* **Objective:** Verify that renderer attempts to open external windows or navigate away are blocked.
* **Mechanism:**
  * `mainWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }))`
  * `mainWindow.webContents.on("will-navigate", (event, url) => { if (!isAllowed) event.preventDefault(); })`
* **Test Procedure:**
  1. In DevTools Console, attempt: `window.open("https://evil.com")`.
  2. Observe that the return value is `null` and no new window opens.
  3. In DevTools Console, attempt: `window.location.href = "https://evil.com"`.
  4. Observe that `will-navigate` blocks navigation and the page remains on Alex HUD.

---

### TC-SEC-09: Token Redaction in CLI & Logs
* **Objective:** Confirm that runtime bearer tokens never appear in terminal output or JSON status.
* **Procedure:**
  1. Launch Alex via `alex launch`.
  2. Inspect the terminal summary table: Confirm token is absent.
  3. Execute `alex status --json`.
  4. Inspect output: Confirm `backend.token` is masked as `****` or `xxxx...****`.
  5. Check log files in `%APPDATA%\Alex\logs\`: Confirm no plaintext bearer tokens or API keys exist.

---

## 4. Results Recording Sheet

| Test ID | Security Scenario | Date Tested | Actual Observed Result | Status |
|---|---|---|---|---|
| **TC-SEC-01** | Exact Dev Origin Validation | *(Date)* | `127.0.0.1:5173` permitted | `[  ] PASS  [  ] FAIL` |
| **TC-SEC-02** | Subdomain Prefix Spoofing Rejection | *(Date)* | `5173.attacker.com` blocked | `[  ] PASS  [  ] FAIL` |
| **TC-SEC-03** | Dev Protocol & External Port Isolation | *(Date)* | External sites blocked | `[  ] PASS  [  ] FAIL` |
| **TC-SEC-04** | Production Canonical File Path Match | *(Date)* | `dist/index.html` permitted | `[  ] PASS  [  ] FAIL` |
| **TC-SEC-05** | Production Local File Traversal Rejection | *(Date)* | Arbitrary file URLs blocked | `[  ] PASS  [  ] FAIL` |
| **TC-SEC-06** | Child Frame IPC Invocation Rejection | *(Date)* | Main frame only allowed | `[  ] PASS  [  ] FAIL` |
| **TC-SEC-07** | Renderer `window.open` Denial | *(Date)* | Window open request denied | `[  ] PASS  [  ] FAIL` |
| **TC-SEC-08** | Navigation Lockdown (`will-navigate`) | *(Date)* | Navigation blocked | `[  ] PASS  [  ] FAIL` |
| **TC-SEC-09** | Token Redaction in Terminal & Status JSON | *(Date)* | Bearer token masked as `****` | `[  ] PASS  [  ] FAIL` |
| **TC-SEC-10** | Audio-Only Media Permission Guard | *(Date)* | Video rejected; audio validated | `[  ] PASS  [  ] FAIL` |

