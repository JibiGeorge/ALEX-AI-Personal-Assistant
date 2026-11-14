# ALEX AI Desktop Assistant — Bug Fix Log

**Date**: November 14, 2026  
**Auditor**: Senior QA Automation Engineer & UI/UX Specialist

---

## Issue Log & Resolutions

### 1. BUG-QA-01: Voice & Natural Language Command Collision with YouTube Playback
- **Severity**: High (Functional Regression / Incorrect Intent Routing)
- **Subsystem**: Action Executor / Command Parsing (`workspaceCommands.ts`, `activityCommands.ts`)
- **Reported Issue**: When issuing `"Alex, open job hunting on hud"`, the system matched the generic phrase `open <query> on hud` and launched YouTube video playback for `"How I Landed 10 Interviews in 1 Week (My Exact Job Search Strategy)"` inside the central video workspace, which subsequently produced a YouTube embedding restriction error.
- **Resolution**:
  1. Updated `activityCommands.ts` with a reserved list of `systemKeywords` (`job hunting`, `career radar`, `jobs`, `settings`, `memory`, `reminders`, `actions`, `computer`, `camera`, `logs`) that are explicitly rejected by media and YouTube video matching rules.
  2. Enhanced `workspaceCommands.ts` with dedicated panel route matching for `job_hunting`, `settings`, `memory`, `reminders`, `actions`, and `computer`.
  3. Integrated `wsCmd.panel === "job_hunting"` in `App.tsx` to automatically trigger `openPanel("job_hunting")` and surface `"Opened Job Hunting & Career Radar on the HUD."`.
- **Verified In**: `e2e/job-hunting.spec.ts` (Test 2: `opens Job Hunting via natural command 'open job hunting on hud'`).

---

### 2. BUG-QA-02: Modal Close Button Interception by Toast Notifications
- **Severity**: Medium (UI / Interaction Bug)
- **Subsystem**: CSS Layer Hierarchy (`frontend/src/index.css`)
- **Reported Issue**: When an error or notice toast was active, clicking modal backdrop close buttons (`×`) failed due to pointer event interception by `.notice` elements.
- **Resolution**:
  - Elevated `.hud-modal-backdrop` and `.setup-backdrop` from `z-index: 30` to `z-index: 1000`.
  - Maintained modal content containers (`.hud-modal-container`, `.setup-modal`) at `z-index: 1001`.
  - Guaranteed modal dialogs always maintain focus and pointer supremacy over background telemetry.
- **Verified In**: `e2e/navigation.spec.ts` (Test 3: `opens modal panel from drawer and closes via close button and Escape key`).

---

### 3. BUG-QA-03: Missing Semantic Class on Avatar Docking Transition
- **Severity**: Low (CSS / DOM Class Semantics)
- **Subsystem**: Holographic Avatar (`HolographicAssistant.tsx`)
- **Reported Issue**: Opening a central workspace stage docked the avatar smoothly via CSS, but only applied `.in-workspace-mode` without the semantic `.is-docked` class expected by automated docking verification tools.
- **Resolution**:
  - Modified line 138 of `HolographicAssistant.tsx` to apply:
    ```tsx
    className={`hud-avatar-stage ${
      isWorkspaceActive ? "in-workspace-mode is-docked" : ""
    } diag-phase-${diagnosticPhase}`}
    ```
- **Verified In**: `e2e/avatar.spec.ts` (Test 2: `avatar docks smoothly to bottom-right when workspace opens and restores on close`).

---

### 4. BUG-QA-04: Vitest Execution of Playwright Spec Files
- **Severity**: Medium (Build & Test Configuration)
- **Subsystem**: Vitest Configuration (`frontend/vite.config.ts`)
- **Reported Issue**: Running `npm test` triggered Vitest to discover `frontend/e2e/*.spec.ts`, throwing Playwright runtime errors (`Playwright Test did not expect test.describe() to be called here`).
- **Resolution**:
  - Updated `frontend/vite.config.ts` to strictly configure `test.include: ["src/**/*.{test,spec}.{ts,tsx}"]` and `test.exclude: ["e2e/**", "node_modules/**", "dist/**"]`.
  - Separated unit tests (`npm test` -> 190 tests passing) from Playwright E2E tests (`npm run test:e2e` -> 34 tests passing).
- **Verified In**: Clean execution of `npm test -- --run`.

---

### 5. BUG-QA-05: Non-Array Telemetry Ingestion Crash in DiscoverView
- **Severity**: Medium (Data Handling & React Error Boundary)
- **Subsystem**: Job Hunting UI (`DiscoverView.tsx`, `JobHuntingPage.tsx`)
- **Reported Issue**: If the adapter status endpoint returned an empty or malformed non-array payload in edge cases, calling `.map()` threw a runtime `TypeError: adapters.map is not a function`.
- **Resolution**:
  - Added defensive guards: `Array.isArray(adaptersRes) ? adaptersRes : []` in `JobHuntingPage.tsx`.
  - Added defensive rendering in `DiscoverView.tsx`: `(Array.isArray(adapters) ? adapters : []).map(...)`.
- **Verified In**: `e2e/job-hunting.spec.ts` (Test 3: `navigates to Discover tab and displays search filters and jobs list`).

---

### 6. BUG-QA-06: Mobile Header Responsiveness & Missing Activity Ticker
- **Severity**: Medium (Responsive Layout / Mobile Companion)
- **Subsystem**: CSS Breakpoints (`frontend/src/index.css`)
- **Reported Issue**: On viewports under 760px, `.hud-title` was set to `display: none;`, completely removing the assistant's cognitive status badge, title, and live activity ticker.
- **Resolution**:
  - Replaced `display: none;` with a responsive flex column layout (`order: 3; width: 100%; margin-top: 4px; font-size: 13px;`).
  - Added text truncation and `max-width: 90vw;` to `.hud-activity-ticker-pill` to eliminate overflow on mobile screens.
- **Verified In**: `e2e/startup.spec.ts` & `e2e/hud.spec.ts` on `mobile-companion` project (Pixel 7 viewport).

---

### 7. BUG-QA-07: Electron Camera Access Denial & Optical Sensor Block
- **Severity**: High (Hardware Video Block / Unreachable Camera)
- **Subsystem**: Electron Main Process (`frontend/electron/main.ts`, `frontend/electron/preload.ts`, `frontend/src/components/workspace/HUDWorkspaceWindow.tsx`)
- **Reported Issue**: Opening the optical sensor feed in the HUD window immediately produced `OPTICAL SENSOR OFFLINE: Camera access denied. Please allow camera permissions in System Settings > Privacy & Security > Camera.`.
- **Root Cause**:
  1. In `main.ts`, `session.defaultSession.setPermissionRequestHandler` explicitly rejected camera video requests with `callback(audioRequested && !videoRequested);` where `videoRequested === true` evaluated to `callback(false)`.
  2. `session.defaultSession.setPermissionCheckHandler` also returned `false` for any media request where `mediaType === "video"`.
  3. `systemPreferences.askForMediaAccess("camera")` was never called for macOS TCC permissions (only `"microphone"` was requested).
  4. `frontend/package.json` was missing `NSCameraUsageDescription` in electron-builder's macOS `extendInfo`.
- **Resolution**:
  1. Updated `setPermissionRequestHandler` and `setPermissionCheckHandler` in `main.ts` to allow `"camera"` and video `"media"` permissions for trusted application windows.
  2. Expanded `configureMicrophonePermission()` to `configureMediaPermissions()` to proactively query and request both `"microphone"` and `"camera"` access on macOS.
  3. Registered `alex:camera:ensure-access` IPC handler and exposed `ensureCameraAccess()` via `preload.ts` and `alexApi.ts`.
  4. Added `NSCameraUsageDescription` to `mac.extendInfo` in `package.json`.
  5. Updated `cleanInput()` in `workspaceCommands.ts` to strip chat transcript prefixes (`me:`, `user:`) and conversational prefixes.
- **Verified In**: Vitest unit test suite (190/190 passing) and Electron build compilation.

