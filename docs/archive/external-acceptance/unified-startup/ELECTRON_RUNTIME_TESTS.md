# Alex – Electron Desktop Runtime Validation Protocols

**Document:** `ELECTRON_RUNTIME_TESTS.md`  
**Purpose:** Detailed runtime test procedures for Electron GUI, preload isolation, HUD rendering, and production packaging (`TC-ELC-01` to `TC-ELC-06`).

---

## 1. Overview & Verification Scope

The Electron desktop layer provides the secure native container for the Alex React HUD. The tester will validate:
1. **Development Mode:** Window loading from the active Vite dev server (`http://127.0.0.1:5173/`).
2. **Context Isolation:** Verifying `contextBridge` isolation and ensuring Node.js primitives are not exposed to the renderer.
3. **IPC Bridge Functionality:** Live bidirectional communication with the backend sidecar.
4. **Production Mode:** Compiling static React bundles and validating `file://` distribution loading.
5. **Backend Deduplication:** Confirming Electron attaches to the launcher-managed sidecar rather than spawning a duplicate process.

---

## 2. Test Execution Protocols

### TC-ELC-01: Development Window Loading & HUD Presentation
* **Objective:** Verify visual appearance, dimensions, and holographic HUD effects in development mode.
* **Procedure:**
  1. Execute `alex launch`.
  2. Observe the application window appearance.
* **Verification Checklist:**
  * [ ] Window dimensions open at approximately 1180x800.
  * [ ] Window title displays **"Alex"**.
  * [ ] Window background initializes with dark styling (`#00060a`).
  * [ ] Holographic boot animation / core face appears in cyan.
  * [ ] Top header displays **Setup** drawer button and **Controls** drawer button.
  * [ ] Clicking Setup opens the configuration drawer smoothly; clicking Controls opens the action drawer.
* **Evidence to Capture:**
  * Capture a full-window screenshot and save to [`evidence/electron/dev_window_hud.png`](./evidence/electron/).

---

### TC-ELC-02: Preload Security & Context Isolation
* **Objective:** Verify that Node.js primitives and raw `ipcRenderer` are completely inaccessible from the browser context.
* **Procedure:**
  1. With the Alex window active, open Chromium DevTools by pressing `Ctrl + Shift + I` (or `F12`).
  2. Navigate to the **Console** tab.
  3. Execute each of the following statements and observe output:
     ```javascript
     // 1. Check window.alex bridge
     typeof window.alex
     // Expected: "object"

     // 2. Check that raw electron / node primitives are undefined
     typeof window.ipcRenderer
     // Expected: "undefined"

     typeof require
     // Expected: "undefined"

     typeof process
     // Expected: "undefined"

     // 3. Test functional API call
     await window.alex.getStatus()
     // Expected: { status: "ready", name: "Alex" }
     ```
* **Evidence to Capture:**
  * Copy console output to [`evidence/electron/devtools_console.txt`](./evidence/electron/).
  * Take a screenshot of the DevTools Console showing the checks.

---

### TC-ELC-03: Real-Time Host Telemetry & Settings Persistence
* **Objective:** Confirm bidirectional IPC communication between the React renderer and the Python backend.
* **Procedure:**
  1. Observe the live system metrics pill in the HUD (CPU %, Memory %, Network MB/s).
  2. Open the **Setup** drawer.
  3. Update **Assistant Name** to a test string (e.g. `"Alex-Test"`) and click **Save**.
  4. Close and restart Alex using `alex restart`.
  5. Open Setup drawer and verify the updated name persisted.
* **Expected Result:**
  * Telemetry updates continuously without freezing.
  * Settings are persisted in `%APPDATA%\Alex\settings.json` and survive application restart.

---

### TC-ELC-04: Production Bundle Compilation & Execution
* **Objective:** Verify that production mode correctly loads `frontend/dist/index.html` via canonical `file://` path.
* **Procedure:**
  1. Build the production React frontend bundle (this compiles both renderer assets and Electron TypeScript):
     ```cmd
     npm --prefix frontend run build
     ```
     Verify `frontend/dist/index.html` and `frontend/dist-electron/electron/main.js` are generated.
  2. In a separate terminal, ensure backend is running or start it:
     ```cmd
     alex launch --no-electron
     ```
  3. Launch the compiled Electron application directly in production mode:
     ```cmd
     set NODE_ENV=production
     npx --prefix frontend electron frontend/dist-electron/electron/main.js
     ```
* **Expected Result:**
  * Electron launches without loading Vite dev server (`http://127.0.0.1:5173/`).
  * Electron loads canonical file: `file:///.../frontend/dist/index.html`.
  * The production UI renders cleanly with zero console errors.
  * No blank white or black window occurs.
* **Evidence to Capture:**
  * Save production window screenshot to [`evidence/electron/prod_window.png`](./evidence/electron/).

---

### TC-ELC-05: Stage-Specific Startup Error Diagnostics
* **Objective:** Verify that Electron's startup catch block reports the exact failing subsystem rather than a generic backend error.
* **Procedure:**
  1. Review the startup error handler in [`frontend/electron/main.ts`](file:///d:/Workspace/Jibi/Alex/frontend/electron/main.ts#L1125-L1142).
  2. Verify that `stepDescription` accurately isolates:
     * `configure microphone permissions`
     * `start or connect to the Python backend`
     * `register application IPC handlers`
     * `create the application window`
* **Expected Result:**
  * Any initialization defect identifies the exact stage: `Failed to [stage]. Detail: [message]`.
  * No IPC or window initialization issue is falsely blamed on the Python backend.

---

### TC-ELC-06: Backend Sidecar Deduplication
* **Objective:** Confirm that launching via `alex launch` does not spawn two backend instances.
* **Procedure:**
  1. Start Alex via `alex launch`.
  2. Open a terminal and check active Python processes:
     ```cmd
     tasklist | findstr /i "python"
     ```
* **Expected Result:**
  * Exactly ONE `python.exe` process is running (the launcher-managed backend).
  * Electron console logs confirm: `[electron] Connecting to launcher-managed backend on port 8765`.
  * Electron did NOT execute `spawn()` for a second backend instance.
* **Evidence to Capture:**
  * Save `tasklist` output to [`evidence/electron/single_backend_check.txt`](./evidence/electron/).

---

## 3. Results Recording Sheet

| Test ID | Description | Date Tested | Actual Observation | Status |
|---|---|---|---|---|
| **TC-ELC-01** | Dev Window HUD Presentation & Effects | *(Date)* | Window 1180x800, dark background, HUD renders | `[  ] PASS  [  ] FAIL` |
| **TC-ELC-02** | Preload Context Isolation & Bridge Verification | *(Date)* | `window.alex` active; `require`/`process`/`ipcRenderer` undefined | `[  ] PASS  [  ] FAIL` |
| **TC-ELC-03** | Host Telemetry & Settings Persistence | *(Date)* | Live CPU/RAM metrics; settings persist across restart | `[  ] PASS  [  ] FAIL` |
| **TC-ELC-04** | Production `dist/index.html` Bundle Execution | *(Date)* | `dist/index.html` loads via `file://`; UI renders cleanly | `[  ] PASS  [  ] FAIL` |
| **TC-ELC-05** | Stage-Specific Startup Diagnostics | *(Date)* | Specific subsystem reported on failure | `[  ] PASS  [  ] FAIL` |
| **TC-ELC-06** | Backend Sidecar Deduplication | *(Date)* | Exactly 1 backend process active; Electron connects | `[  ] PASS  [  ] FAIL` |

