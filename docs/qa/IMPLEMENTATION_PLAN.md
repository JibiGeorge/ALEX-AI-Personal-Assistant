# ALEX AI — QA, Testing & Modernization Implementation Plan

**Date:** 2026-11-14  
**Version:** 1.0.0  
**Lead:** Senior QA & Full-Stack Automation Engineer

---

## 1. Plan Purpose & Execution Rules

This document establishes the structured roadmap for auditing, testing, repairing, modernizing, and certifying the entire **ALEX AI Desktop Assistant**.

### Core Constraints & Invariants:
1. Preserve existing architecture (React 19 + Vite 6 + Electron 45 + FastAPI Python 3.14 + Action Registry + Model Ladder).
2. Never delete, weaken, or mock out passing tests to claim false green states.
3. Keep real backend integration separate from mocked UI unit tests.
4. Work in sequential, verifiable stages with automated validation at every step.

---

## 2. Phased Implementation Stages

### Stage 1: Repository Audit & Baseline Verification (Completed)
- [x] Run full backend Pytest suite (`pytest`): 583 passed, 1 skipped.
- [x] Run full frontend Vitest suite (`npm test`): 194 passed.
- [x] Run packaging and sidecar verification: 3 passed.
- [x] Establish total baseline count: **780 passing tests**.
- [x] Produce audit documents:
  - `docs/qa/INITIAL_AUDIT.md`
  - `docs/qa/FEATURE_TEST_MATRIX.md`
  - `docs/qa/UI_ISSUES.md`
  - `docs/qa/IMPLEMENTATION_PLAN.md`

### Stage 2: Playwright Testing Infrastructure Setup
- [ ] Configure `playwright.config.ts` in `frontend/` supporting:
  - Multi-browser web testing (Chromium, Firefox, WebKit).
  - Mobile viewport presets (iPhone 14 / Pixel 7).
  - Native Electron desktop application launching via Playwright's Electron API.
  - Video recording, failure traces, console log collection, and screenshots on failure.
- [ ] Implement robust fixtures in `frontend/e2e/fixtures/`:
  - `electronApp.fixture.ts` for launching the full Electron desktop app.
  - `mockBackend.fixture.ts` for hermetic web UI tests without external network dependencies.
  - `authApi.fixture.ts` for authenticated REST API communication with the backend.
- [ ] Implement helpers in `frontend/e2e/helpers/`:
  - `navigation.helper.ts` (drawer toggling, panel opening).
  - `workspace.helper.ts` (workspace launching, content verification).
  - `accessibility.helper.ts` (keyboard navigation, focus checking).

### Stage 3: HUD, Navigation, Avatar & Workspace E2E Tests
- [ ] Author `startup.spec.ts`: Verify cold launch, lifecycle stages, backend handshake.
- [ ] Author `navigation.spec.ts`: Verify Setup and Controls drawers, modal panels, Esc key dismissal.
- [ ] Author `hud.spec.ts`: Verify system monitor metrics, activity ticker, top HUD controls.
- [ ] Author `avatar.spec.ts`: Verify center idle positioning, bottom-right docking during workspace mode, return to center on close.
- [ ] Author `workspace.spec.ts`: Verify window open, close, minimize, restore, maximize, and window reuse.
- [ ] Author `media-player.spec.ts`: Verify video and music players with playback controls.
- [ ] Author `document-viewer.spec.ts`: Verify PDF, Markdown, and image viewers.
- [ ] Author `browser-workspace.spec.ts`: Verify sandboxed browser iframe, address bar, security badge.

### Stage 4: Backend, AI, Voice, Files & System Tests
- [ ] Author `voice.spec.ts`: Verify voice controls, push-to-talk, audio meter, transcription flows.
- [ ] Author `settings.spec.ts`: Verify API key storage, voice preferences, system configurations.
- [ ] Author `reminders.spec.ts`: Verify reminder creation, persistence, cancellation, and due delivery.
- [ ] Author `system-monitor.spec.ts`: Verify telemetry data binding, alerts, and offline degraded state.
- [ ] Author `security.spec.ts`: Verify Bearer token authorization, loopback binding, preload bridge isolation.
- [ ] Author `error-recovery.spec.ts`: Verify graceful recovery from network disconnection and sidecar restarts.

### Stage 5: Job Hunting & Mobile Companion Tests
- [ ] Author `job-hunting.spec.ts`:
  - Candidate profile management & resume upload.
  - Discovery adapters & duplicate detection.
  - Compatibility match scoring across all 6 weighted categories.
  - Resume Studio & Cover Letter generation.
  - Application tracker & approval confirmation dialog.
- [ ] Author `mobile-companion.spec.ts`:
  - QR code pairing handshake.
  - Authenticated command gateway.
  - Mobile action approvals & file uploads.

### Stage 6: Bug Fixing & Defect Remediation
- [ ] Fix identified UI alignment defects in `minimal-system-monitor` and `ApplicationHeader`.
- [ ] Fix viewport scaling and horizontal navigation overflow in `JobHuntingPage`.
- [ ] Implement accessible focus rings and keyboard focus management across all modal dialogs.
- [ ] Ensure 3D avatar respects `prefers-reduced-motion`.
- [ ] Harden error and empty states across all pages.

### Stage 7: UI Modernization & Responsive Verification
- [ ] Refine holographic cyan HUD theme with consistent glassmorphism and subtle elevation.
- [ ] Test and certify responsive viewports:
  - 1920 × 1080 (Full HD Desktop)
  - 1600 × 900 (Standard Laptop)
  - 1366 × 768 (Compact Laptop)
  - 1280 × 720 (HD Ready)
  - 1024 × 768 (Tablet Landscape)
  - 768 × 1024 (Tablet Portrait)
  - 390 × 844 (Mobile Companion)
- [ ] Capture verified visual screenshots of modernized views.

### Stage 8: Full Certification, Packaging & Final Reports
- [ ] Run full backend Pytest suite.
- [ ] Run full frontend Vitest suite.
- [ ] Run Playwright test suite.
- [ ] Run TypeScript type checks (`npx tsc --noEmit`).
- [ ] Run production Vite build (`npm run build`).
- [ ] Run Electron packaging verification (`npm run dist` / `verify:sidecar`).
- [ ] Generate comprehensive final documentation:
  - `docs/qa/FINAL_QA_REPORT.md`
  - `docs/qa/PLAYWRIGHT_RESULTS.md`
  - `docs/qa/BUG_FIX_LOG.md`
  - `docs/qa/UI_MODERNIZATION_REPORT.md`
  - `docs/qa/KNOWN_LIMITATIONS.md`

