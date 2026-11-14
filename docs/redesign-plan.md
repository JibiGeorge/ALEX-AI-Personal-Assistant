# ALEX Redesign & Architecture Modernization Plan

> **Version:** 1.0.0  
> **Target:** Voice-first Desktop AI Assistant & Job Hunting / Career Radar Suite  
> **Status:** Step 0 Complete — Awaiting Approval to Begin Phase 1  

---

## 1. Executive Summary & Step 0 Repo Audit

### 1.1 Architecture & Stack Summary
- **Frontend Framework:** React 19 (`react` 19.1.0, `react-dom` 19.1.0) with TypeScript 5.8.3, bundled via Vite 6.
- **Desktop Runtime:** Electron 45.1.0 with context isolation, strict IPC handlers (`ipcRenderer.invoke` / `ipcMain.handle`), preload security bridge (`preload.ts`), and secure token-authenticated local backend communication.
- **Styling System:** Tailwind CSS v4 (`@tailwindcss/vite`) combined with extensive modular HUD CSS (`src/index.css`, `HUDWorkspace.css`, `jobHunting.css`). Root design tokens use `--hud-*` variables.
- **State Management:** React hooks (`useState`, `useCallback`, `useMemo`, `useRef`, custom `useLiveVoice` hook) with top-level lifting in `App.tsx` and child component coordination. Dedicated typed REST clients (`alexApi.ts`, `jobHuntingApi.ts`) interface with Electron IPC and the FastAPI backend.
- **Voice & Gemini Live Layer:**
  - Frontend microphone acquisition via Web Audio API (`AudioContext`, `AudioWorklet`/ScriptProcessor) resampling to PCM16 16kHz via `useLiveVoice.ts`.
  - Electron main process opens an authenticated WebSocket (`ws://127.0.0.1:<port>/api/v1/conversation/live?token=...`).
  - Python backend sidecar (`backend/app/services/live_voice_service.py`) connects directly to Google's Gemini Live via `google.genai.Client` (`gemini-3.1-flash-live-preview` / `gemini-2.5-flash-native-audio-preview`), streaming bidirectional audio, performing real-time tool calling (`ActionExecutor`), and sending back PCM24 output audio and transcript events.
- **Job-Intelligence Services:**
  - **Ingest:** `backend/app/services/job_hunting/adapters.py` (Greenhouse, Lever, public API job boards), `discovery_service.py` (multi-platform ingestion and RSS/API fetchers).
  - **Extract:** `extraction.py` (job posting schema extraction from HTML/text) and `profile_service.py` (candidate profile extraction from resumes via `document_parser_service.py` and Gemini).
  - **Match:** `matching_service.py` (computes 0–100% compatibility across 10 weighted dimensions: technical skills 30%, experience 25%, responsibilities 15%, education 10%, industry 10%, location 10%, etc.).
  - **Tailor:** `tailoring_service.py` (tailors resume sections and generates custom cover letters with base profile diffing) and `document_exporter.py` (PDF and DOCX formatting).
  - **Approvals & Applications:** `approval_service.py` (human-in-the-loop gate) and `application_service.py` (kanban state tracker).
- **Data Storage:** SQLite database stored locally at `~/.alex/job_hunting.db` (or platform AppData / `$ALEX_DATA_DIR/job_hunting.db`), managed via `storage.py`.

---

## 2. Redesign Phase-by-Phase Plan & File Manifest

### Phase 1: Design System & Global Shell
**Objective:** Establish a clean, semantic design token system, fix visual contrast and typography hierarchy, declutter the top bar, and replace confusing wording.
- **Semantic Color Tokens:** Define strict semantic CSS variables:
  - Cyan (`#00D9FF` / `--hud-primary`): Primary action and holographic accents.
  - Green (`#20D6A0` / `--hud-success`): Live voice, connected status, success states.
  - Amber (`#FFB547` / `--hud-warning`): Needs attention, pending review, rate limits.
  - Red (`#FF5364` / `--hud-danger`): Errors, destructive actions, offline state.
- **Typography:** Enforce Inter / Geist sans-serif for body text, job titles, and descriptions. Monospace reserved strictly for telemetry, metrics, and timestamps. Minimum font size 12–13px; secondary text elevated to meet WCAG AA contrast (>= 4.5:1).
- **Header Reorganization:**
  - Left zone: Logo + navigation icons with tooltips and accessible ARIA labels. Remove/clarify unlabeled "6" badge.
  - Center zone: Single status indicator with honest, accurate wording: `"LOCAL APP · CLOUD VOICE"` instead of misleading contradictory claims.
  - Right zone: Live clock, tools, and a toggle button for the System Monitor.
- **System Monitor Popover:** Move the sprawling CPU/RAM/network/AI/voice bar into a clean collapsible popover/drawer.
- **Input Bar Improvements:** Move "Drop file here" and "Capture Screen" into subtle attachment icon buttons inside `CommandInput.tsx`.
- **Suggestion Chips:** Replace static tagline with actionable prompt chips ("Find jobs", "Tailor my resume", "Summarize my day").
- **Model Config:** Move raw model string (`gemini-2.5-flash-...`) out of the header and into Settings.

#### Files Touched in Phase 1:
- `frontend/src/index.css` (semantic design tokens, typography rules, WCAG contrast)
- `frontend/src/components/dashboard/ApplicationHeader.tsx` (3-zone header layout, honest status pill, icon tooltips)
- `frontend/src/components/dashboard/SystemMonitor.tsx` (collapsible popover / drawer container)
- `frontend/src/components/dashboard/CommandInput.tsx` (inline attachment buttons, suggestion chips)
- `frontend/src/components/dashboard/HolographicAssistant.tsx` (clean tagline & suggestion chip layout)
- `frontend/src/App.tsx` (header & input wiring)
- `frontend/src/components/dashboard/ApplicationHeader.test.tsx` (unit test updates)

---

### Phase 2: Voice State Machine & Error Handling
**Objective:** Consolidate fragmented voice states into ONE unified finite state machine and provide clear error recovery.
- **Voice State Machine:** Single canonical state: `idle` | `listening` | `thinking` | `speaking` | `error`.
- **Single Status Indicator:** All HUD indicators, avatar pulses, and top-bar status derive from this one state machine (no duplicated "Listening" labels).
- **Unified Mic Control:** Replace separate `MIC LIVE` + `STOP MIC` buttons with a single toggle button whose label and color follow state. Show `INTERRUPT` exclusively while ALEX is `speaking`.
- **Error Recovery Banners:** Floating actionable banners with a `Reconnect` button for:
  - Microphone permission denied.
  - WebSocket connection dropped / disconnected.
  - Gemini API quota or 429 rate limit reached.
  - Model unavailable or Policy 1008 rejection.
- **Settings Screen:** Comprehensive settings view for voice model, voice profile selection, mic input device, wake-word sensitivity, theme, and data retention.

#### Files Touched in Phase 2:
- `frontend/src/hooks/useLiveVoice.ts` (finite state machine implementation and event dispatch)
- `frontend/src/types/voice.ts` (new typed voice state machine definitions)
- `frontend/src/components/dashboard/CommandInput.tsx` (unified single-toggle mic button, conditional interrupt)
- `frontend/src/components/Notice.tsx` / `frontend/src/components/VoiceErrorBanner.tsx` (actionable reconnect banners)
- `frontend/src/pages/SettingsPage.tsx` (voice, model, device, and performance settings)
- `frontend/src/App.tsx` (state machine subscription and error banner handlers)
- `frontend/src/hooks/useLiveVoice.test.ts` (voice state machine transition tests)

---

### Phase 3: Avatar, Animation & Performance Optimization
**Objective:** Make the avatar react fluidly to the voice state machine, improve docking in workspace mode, and add low-power / accessibility modes.
- **State-Driven Avatar:**
  - `idle`: gentle breathing loop.
  - `listening`: dynamic ripples driven by live microphone input level.
  - `thinking`: faster planetary orbit.
  - `speaking`: pulse synced to output audio amplitude.
  - Retain `FACE` / `CORE` / `ROBOT` 3D visualizers.
- **Docked Corner Avatar:** When Job Panel or any workspace is open, smoothly transition the avatar into a compact fixed-corner status widget that is never clipped.
- **De-clutter HUD Background:** Fade perspective grid floor to a subtle depth texture; consolidate waveforms to a single clean visualizer.
- **Performance & Reduced Motion:**
  - Implement `@media (prefers-reduced-motion)` to disable orbits/spins for accessibility.
  - Low-power mode toggle: disables CSS backdrop-blur and particle effects, caps 3D canvas render rate at 30 FPS.
  - Visibility API listener: pauses Three.js animations when window is minimized or tab is hidden (`document.hidden`).
  - CPU/RAM profiling benchmark before and after.

#### Files Touched in Phase 3:
- `frontend/src/components/HudAvatar.tsx` (audio-reactive state animations)
- `frontend/src/components/avatar/VisualizationManager.tsx` (FPS throttling & visibility pausing)
- `frontend/src/components/avatar/FaceVisualization.tsx` / `CoreVisualization.tsx` / `RobotVisualization.tsx`
- `frontend/src/components/dashboard/HolographicAssistant.tsx` (background grid fade & docked corner positioning)
- `frontend/src/index.css` (reduced motion, low-power mode styles)
- `frontend/src/components/HudAvatar.test.tsx` (avatar state tests)

---

### Phase 4: Job Panel Layout Modernization
**Objective:** Replace the cramped floating modal with a professional, full-width docked workspace and a live activity feed.
- **Workspace Layout:** Clean full-height docked view with an optimal 70/30 split between the main Career Radar Workspace and the live Activity Log.
- **Remove Cut-Through Glow Lines:** Remove horizontal decorative lines that cut through text or input controls.
- **Real-Time Live Activity Stream:** Transform the right activity panel into an informative real-time transmission log ("Searching Greenhouse...", "Scoring 12 vacancies...", "Drafting cover letter..."), automatically collapsing when empty.

#### Files Touched in Phase 4:
- `frontend/src/pages/job_hunting/JobHuntingPage.tsx` (docked 70/30 layout)
- `frontend/src/pages/job_hunting/jobHunting.css` (layout styles, responsive grid, visual line fixes)
- `frontend/src/components/dashboard/AlexResponseStream.tsx` (activity stream integration)
- `frontend/src/components/workspace/HUDWorkspaceWindow.tsx` (workspace docking enhancements)

---

### Phase 5: Job Hunting Flow & Information Architecture
**Objective:** Streamline the entire career workflow into a coherent 5-stage pipeline, eliminating navigation clutter and redundant views.
- **Streamlined Workflow Navigation:** Replace stacked navigation bars and overflowing tabs with a single intuitive workflow bar:
  `Discover` ➔ `Review` ➔ `Tailor` ➔ `Apply` ➔ `Track` (+ `Settings`).
- **Contextual Job Inspector:**
  - `Job Details`, `AI Match Analysis`, and `Compare Roles` move from top-level tabs into nested drawer/inspector panels inside any selected job.
- **Unified Discovery Flow:**
  - Merge "Multi-platform discovery" and "Advanced discovery" into one unified search and filter flow.
  - Place the Interactive Geo Map behind a clean location filter/toggle instead of an intrusive full-screen blocker.
- **Actionable Career Dashboard:**
  - Replace generic stat cards with actionable metrics: `New Today`, `To Review`, `Applications in Progress`, `Interviews`, `Response Rate`.
  - Remove empty placeholder states and the redundant "Global" card; provide actionable "Upload Resume" / "Add Job" onboarding CTAs.
- **Two-Pane Jobs List:**
  - Left pane: Filterable job list with auto-calculated compatibility score badges (no manual "Run Match" button needed), company name, source badge, remote tag, and seniority.
  - Right pane: In-depth job breakdown, 10-factor radar/bar visualization, matched skills, missing skills, and recommended action (`Apply` / `Tailor First` / `Skip`).
- **Tailoring Studio & Base Profile Diff:**
  - One-click "Tailor resume + cover letter" with an interactive side-by-side diff against the base profile.
  - Explicit Human-in-the-Loop approval gate: tailored applications require user approval before moving to the pipeline.
- **Kanban Application Tracker:**
  - Columns: `Saved` ➔ `Tailored` ➔ `Applied` ➔ `Interview` ➔ `Offer` ➔ `Rejected`.
  - Automated follow-up reminders (default 7 days post-application) and recruiter contact fields.
- **Scheduler Popover:**
  - Make "Every 12h" badge clickable to inspect last execution, next scheduled run, newly discovered jobs, and desktop notification toggles.

#### Files Touched in Phase 5:
- `frontend/src/pages/job_hunting/JobHuntingPage.tsx` (streamlined single workflow bar)
- `frontend/src/pages/job_hunting/DashboardView.tsx` (actionable KPI cards, clean empty states)
- `frontend/src/pages/job_hunting/DiscoverView.tsx` (unified search, two-pane list & inspector)
- `frontend/src/pages/job_hunting/MatchAnalysisView.tsx` (10-factor radar/bar chart, skill gap summary)
- `frontend/src/pages/job_hunting/ResumeStudioView.tsx` / `CoverLetterStudioView.tsx` (diff view & approval gate)
- `frontend/src/pages/job_hunting/ApplicationTrackerView.tsx` (Kanban drag/transition, follow-up alerts)
- `frontend/src/pages/job_hunting/PendingApprovalsView.tsx` (review queue)
- `frontend/src/pages/job_hunting/JobLocationMapView.tsx` (embedded location toggle)
- `frontend/src/pages/job_hunting/JobHuntingPage.test.tsx` (flow and transition tests)

---

### Phase 6: Data Sources & LinkedIn Compliance
**Objective:** Maintain 100% compliance with LinkedIn terms of service while providing seamless multi-channel job discovery.
- **Compliance Rules:** Strictly zero automated bot scraping or authentication bypass of LinkedIn.
- **Supported Ingestion Channels:**
  - Direct URL ingestion for LinkedIn, Greenhouse, Lever, and public job postings (`/api/v1/jobs/ingest/url`).
  - Webhook endpoint for browser extensions or bookmarklets to ingest currently active job tabs (`/api/v1/jobs/ingest/webhook`).
  - Parsing for user-forwarded job alert notification emails (`/api/v1/jobs/ingest/email`).
  - Public job board API adapters (Greenhouse, Lever, public feeds).
- **Normalized Job Schema:** Enforce a single canonical `JobOpportunity` schema with verified `source` attribution (`LINKEDIN_URL`, `GREENHOUSE`, `LEVER`, `PUBLIC_API`, etc.).

#### Files Touched in Phase 6:
- `backend/app/services/job_hunting/adapters.py` (verified public API adapters)
- `backend/app/services/job_hunting/discovery_service.py` (webhook & email ingest handlers)
- `backend/app/api/routes.py` (webhook ingestion routes)
- `frontend/src/pages/job_hunting/DiscoverView.tsx` (multi-source badge indicators)
- `backend/tests/test_job_adapters.py` (compliance and ingestion tests)

---

### Phase 7: Onboarding, Privacy Transparency & Accessibility
**Objective:** Guide new users through setup, provide explicit local-vs-cloud data transparency, and achieve full WCAG AA accessibility.
- **First-Run Onboarding Wizard:**
  - Step 1: Base resume upload & instant skill extraction.
  - Step 2: Target roles, seniority, and preferred locations.
  - Step 3: Salary expectations and work authorization.
  - Displays dynamic profile completeness percentage on the dashboard.
- **Privacy & Data Governance Panel:**
  - Clear plain-language explanation of what data is stored strictly locally in SQLite (`job_hunting.db`) vs. what is transmitted to Google's Gemini API for processing.
  - One-click `Export All Data` (JSON/ZIP) and `Purge All Data` with safety confirmation.
- **Accessibility & Focus Management:**
  - Full keyboard navigation across all views with high-visibility focus rings.
  - ARIA live announcements for voice state changes (`aria-live="polite"` / `assertive`).
  - WCAG AA contrast compliance across dark HUD themes.

#### Files Touched in Phase 7:
- `frontend/src/components/onboarding/JobOnboardingWizard.tsx` (new onboarding wizard)
- `frontend/src/pages/PrivacyPage.tsx` or `frontend/src/pages/job_hunting/PrivacyView.tsx` (data governance & export)
- `frontend/src/pages/job_hunting/DashboardView.tsx` (profile completeness meter)
- `frontend/src/index.css` (accessible focus rings and contrast)
- `frontend/src/pages/job_hunting/JobHuntingPage.tsx` (onboarding trigger)

---

### Phase 8: Voice & Chat Control of Career Radar
**Objective:** Enable natural voice and text control of the job hunt directly from ALEX's conversational interface.
- **Natural Language Command Routing:**
  - "Show remote React jobs over 80%" ➔ Filters jobs list and switches to Discover view.
  - "Tailor my resume for the Bjak role" ➔ Initiates tailoring and opens side-by-side diff.
  - "Move Bjak to Applied" ➔ Transitions application state in the Kanban tracker.
  - "What jobs did you find today?" ➔ Queries SQLite and returns a spoken summary.

#### Files Touched in Phase 8:
- `frontend/src/utils/workspaceCommands.ts` (job command parsing)
- `backend/app/services/job_hunting/command_router.py` (NL intent extraction to job actions)
- `frontend/src/App.tsx` (dispatching voice command results to Job Hunting state)
- `frontend/src/VoiceControlledWorkspace.test.tsx` (job voice command tests)

---

## 3. Risk Mitigation & Verification Strategy
- **Working Business Logic Preserved:** Backend services (`adapters.py`, `matching_service.py`, `tailoring_service.py`, `storage.py`) remain untouched in their core mathematical scoring and storage integrity; only typed interfaces and presentation layers are refactored.
- **Test Gate per Phase:** Every phase requires:
  1. Zero TypeScript/Vite compilation errors (`npm run build`).
  2. All 29 frontend Vitest test suites passing (`npm test -- --run`).
  3. All 587 backend pytest tests passing (`pytest tests/`).
  4. Manual visual verification and screenshot capture before proceeding.
- **Small Commits:** Each phase will be implemented task-by-task with isolated, descriptive git commits.

