# Job Hunting Module — Step-by-Step Integration Plan

## 1. Integration Strategy & Phased Roadmap

To uphold the core directive — **preserving all existing ALEX functionality without disruption** — the integration follows a strict, non-destructive 6-phase plan. Each phase concludes with automated verification (Vitest + Pytest) before proceeding.

```
 Phase 1: Database & Schemas (Backend Core)
    │  - SQLite storage layer in app/core/storage/
    │  - Pydantic models in app/schemas/job_hunting.py
    ▼
 Phase 2: Engine Services (Backend Services)
    │  - JobDiscoveryService (WebSearch + Browser integration)
    │  - JobMatchingService (ModelLadder semantic match)
    │  - ResumeTailoringService (DocumentParser + LLM synthesis)
    │  - ApplicationTrackerService & Scheduler
    ▼
 Phase 3: Action Registry & FastAPI API Endpoints
    │  - Built-in actions in app/actions/builtins/job_hunting.py
    │  - FastAPI REST Router in app/api/endpoints/job_hunting.py
    │  - Approval gate enforcement in ActionExecutor
    ▼
 Phase 4: Frontend Service & Types (Client Core)
    │  - TypeScript API client in frontend/src/services/jobHuntingService.ts
    │  - Types in frontend/src/types/jobHunting.ts
    ▼
 Phase 5: UI & HUD Workspace Integration
    │  - Job Hunting Page in frontend/src/pages/JobHuntingPage.tsx
    │  - Activity cards in frontend/src/components/workspace/HUDWorkspaceWindow.tsx
    │  - Voice/chat commands in frontend/src/utils/workspaceCommands.ts
    ▼
 Phase 6: End-to-End Regression & Verification
       - Pytest coverage for all backend services & actions
       - Vitest coverage for frontend components & state
       - Build validation (Vite build + Electron packaging check)
```

---

## 2. Phase Breakdown & Deliverables

### Phase 1: Persistence Layer & Schemas
- **Goals**: Establish local SQLite database (`job_hunting.db`), migration runner, and robust Pydantic v2 schemas for all payloads.
- **Key Files**:
  - `backend/app/schemas/job_hunting.py`
  - `backend/app/services/job_database_service.py`
- **Verification**: Dedicated Pytest tests verifying table creation, ACID constraints, CRUD operations, and deduplication logic.

### Phase 2: Cognitive Engine Services
- **Goals**: Implement business logic leveraging existing ALEX services:
  - `JobDiscoveryService`: Discovers jobs via `WebSearchService` and `BrowserControlService` based on user preferences (*Software Developer, Full Stack Developer, React Developer, Next.js Developer, Node.js Developer*; *2–5 years*; *Remote/Hybrid/Onsite Worldwide*).
  - `JobMatchingService`: Implements compatibility scoring (0–100%) against candidate resume.
  - `ResumeTailoringService`: Integrates with `DocumentParserService` and `ModelLadderService` to generate targeted resumes and cover letters without hallucinations.
  - `ApplicationTrackerService`: Manages application state machine and logs all timeline events.
- **Verification**: Unit tests mocking LLM completions and web search responses, verifying deterministic scoring calculations.

### Phase 3: Action Registry & REST Endpoints
- **Goals**: Wire services into ALEX's existing Action Registry and FastAPI routing.
  - Expose actions: `jobs.discover`, `jobs.match`, `resumes.tailor`, `applications.submit` (with `requires_confirmation = True`).
  - Attach API router to `backend/app/api/` and mount it cleanly in `backend/app/main.py`.
- **Verification**: Test action invocation through `ActionExecutor` ensuring unapproved submission raises safety exception.

### Phase 4: Frontend Data Client & State Management
- **Goals**: Provide type-safe React 19 hooks and service clients for frontend views.
  - Define `JobListing`, `CompatibilityScore`, `TailoredDocument`, `JobApplication`, and `CandidateProfile` interfaces in `frontend/src/types/jobHunting.ts`.
  - Implement `jobHuntingService.ts` calling `/api/jobs/*` endpoints with API token authentication.
- **Verification**: Vitest tests verifying mock network responses, optimistic updates, and error handling.

### Phase 5: UI & HUD Workspace Integration
- **Goals**: Present the user with a seamless, sci-fi cyberpunk HUD experience matching ALEX's aesthetic.
  - **Job Hunting Dashboard Page**: `frontend/src/pages/JobHuntingPage.tsx` with a Kanban board (Discovered, Matched, Tailored, Applied, Interviewing, Offer), filter bar, and profile manager.
  - **HUD Workspace Cards**: Extend `HUDWorkspaceWindow.tsx` to render tailored resume side-by-side with job descriptions and match breakdown.
  - **Approval Modal**: Visual confirmation modal requiring single-click or voice confirmation to proceed with application submission.
  - **Voice Commands**: Add patterns in `workspaceCommands.ts`:
    - *"ALEX, find React developer jobs"*
    - *"ALEX, match this job with my resume"*
    - *"ALEX, tailor resume for Stripe application"*
    - *"ALEX, open job hunting dashboard"*
- **Verification**: Vitest component testing for `JobHuntingPage.test.tsx` and workspace command parser tests.

### Phase 6: Regression Testing & Final Polish
- **Goals**: Guarantee zero regressions across existing ALEX features.
  - Run full Vitest suite (186 existing tests + new job hunting tests).
  - Run full Pytest suite (520 existing tests + new job hunting tests).
  - Validate production bundle compilation via `npm run build`.

---

## 3. Rollback & Fail-Safe Strategy
- All Job Hunting code resides in discrete, isolated files and directories.
- If the module is disabled or encounters an error, ALEX continues running without disruption.
- The database is completely independent (`job_hunting.db`), ensuring zero chance of schema collision with core memory or configuration files.

