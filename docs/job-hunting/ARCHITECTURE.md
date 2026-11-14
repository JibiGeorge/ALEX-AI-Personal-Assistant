# Job Hunting Module — Architecture Specification

## 1. Executive Summary & Philosophy

The **Job Hunting Module** is an autonomous, privacy-centric, and user-supervised career accelerator natively integrated into **ALEX AI Desktop Assistant**.

It operates strictly within the existing ALEX architecture:
- **Desktop Shell**: Electron + Vite + React 19 + TypeScript
- **Backend Core**: FastAPI (Python 3.12+)
- **Cognitive Engine**: ALEX AI Model Ladder (`ModelLadderService` with Gemini Live, OpenAI, Anthropic, DeepSeek, Groq, Ollama)
- **Execution & Safety**: Action Registry with mandatory user consent gates (`ActionRegistry`, `ActionExecutor`)
- **System Integration**: Native OS Scheduler (`OSSchedulerAdapter`), Web Search (`WebSearchService`), Browser Control (`BrowserControlService`), and Document Parser (`DocumentParserService`).

The module avoids external SaaS lock-in, stores all resumes, candidate profiles, scraped listings, match analytics, and application histories locally, and strictly requires **explicit user approval** prior to submitting applications or performing external state-changing interactions.

---

## 2. System Architecture Diagram

```
+---------------------------------------------------------------------------------------+
|                                    ALEX UI LAYER                                      |
|                                                                                       |
|  +--------------------+  +----------------------+  +-------------------------------+  |
|  |   HUD Workspace    |  |  Navigation Drawer   |  |   Job Hunting Dashboard Page   |  |
|  |  (Job Preview/Card)|  | (Job Hunter Action)  |  |   (Kanban / Match / Profiles) |  |
|  +--------------------+  +----------------------+  +-------------------------------+  |
+-------------------------------------------|-------------------------------------------+
                                            | REST API & SSE / WebSocket
                                            v
+---------------------------------------------------------------------------------------+
|                                  FASTAPI BACKEND                                      |
|                                                                                       |
|  [ API Router: /api/jobs ]                                                            |
|    ├── GET /jobs/search          -> Query & filter discovered listings                |
|    ├── POST /jobs/match          -> Score candidate profile vs job description        |
|    ├── POST /resumes/tailor      -> Synthesize ATS-optimized tailored resume & letter |
|    ├── POST /applications/apply  -> Staged application with MANDATORY User Approval   |
|    └── GET /applications/kanban  -> Application lifecycle state tracking              |
|                                                                                       |
|  [ Job Hunting Engine Services ]                                                      |
|    ├── JobDiscoveryService       -> WebSearchService & BrowserControlService feeds    |
|    ├── JobMatchingService        -> LLM structured scoring & semantic embeddings      |
|    ├── ResumeTailoringService    -> DocumentParserService & ModelLadder synthesis     |
|    ├── ApplicationTrackerService -> Application state machine & timeline journal      |
|    └── JobSchedulerService       -> Native OS background discovery tasks (launchd/cron|
|                                                                                       |
|  [ Action Registry Integration ]                                                      |
|    └── builtins/job_hunting.py   -> Exposes `jobs.search`, `jobs.match`,              |
|                                     `resumes.tailor`, `applications.submit`           |
+-------------------------------------------|-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                                PERSISTENCE & STORAGE                                  |
|                                                                                       |
|  [ SQLite Database: ~/.alex/job_hunting.db ]                                          |
|    ├── candidate_profiles        -> User master resume, skills, target preferences    |
|    ├── job_listings              -> Discovered roles, raw JD, parsed requirements     |
|    ├── compatibility_scores      -> Multi-dimensional match metrics (skills, exp, ATS)|
|    ├── tailored_documents        -> Generated resume variants & cover letters (MD/PDF)|
|    ├── applications              -> Application lifecycle & user approval logs        |
|    └── discovery_runs            -> Audit log of scheduled/manual discovery passes    |
+---------------------------------------------------------------------------------------+
```

---

## 3. Core Component Subsystems

### 3.1. Job Discovery Service (`JobDiscoveryService`)
- **Query Synthesis**: Formulates targeted search queries combining target roles (*Software Developer*, *Full Stack Developer*, *React Developer*, *Next.js Developer*, *Node.js Developer*), experience filters (*2–5 years*), locations (*Worldwide, Remote, Hybrid, On-site*), and freshness parameters.
- **Provider Aggregation**: Leverages existing `WebSearchService` (DuckDuckGo, SearXNG, Google) and `BrowserControlService` to crawl and extract postings from platforms (LinkedIn, Indeed, Greenhouse, Lever, Workday, GitHub Jobs, RemoteOK, Wellfound).
- **Deduplication & Normalization**: Computes normalized hashing on `(company_name, job_title, cleaned_location)` to prevent duplicate listings.

### 3.2. Job Matching & Compatibility Engine (`JobMatchingService`)
- **Target Profiles**: Evaluates candidate against target preferences:
  - Experience: 2–5 years (Mid-level / Experienced Engineer)
  - Core Skills: React, Next.js, Node.js, TypeScript, Full Stack systems, REST/GraphQL APIs, State Management, Cloud/CI/CD
  - Modalities: Remote, Hybrid, On-site (Worldwide)
- **Scoring Dimensions**:
  - `skills_score` (0–100): Direct overlap of required vs. demonstrated technical proficiencies.
  - `experience_score` (0–100): Alignment with the 2–5 year window and architectural responsibilities.
  - `cultural_domain_score` (0–100): Alignment with industry domain, work style, and working hours/geography.
  - `overall_compatibility` (0–100): Weighted formula:
    $$\text{Overall} = 0.45 \times \text{Skills} + 0.35 \times \text{Experience} + 0.20 \times \text{Domain}$$
- **Model Ladder Integration**: Uses fast models (e.g. Groq / DeepSeek / Ollama) for initial triage and high-intelligence models (Gemini 2.5/Pro, GPT-4o, Claude 3.5) for deep skill gap analysis and reasoning.

### 3.3. Document Parsing & Resume Tailoring Engine (`ResumeTailoringService`)
- **Master Resume Ingestion**: Uses `DocumentParserService` to extract structured sections (Summary, Technical Proficiencies, Work Experience, Projects, Education, Certifications) from the user's base resume (PDF, DOCX, Markdown).
- **Tailoring Engine**:
  - Highlights relevant keywords and bullet points that directly map to the job's requirements.
  - Rewrites experience bullet points using the Google XYZ formula: *"Accomplished [X] as measured by [Y] by doing [Z]"*.
  - Never fabricates experience; strictly operates within the ground truth of the candidate profile.
- **Document Generation**: Generates clean Markdown, plaintext ATS-friendly versions, and exports structured PDFs using clean HTML-to-PDF templates.
- **Cover Letter Synthesizer**: Produces concise, company-specific cover letters addressing key pain points noted in the job description.

### 3.4. Application Tracking & State Machine (`ApplicationTrackerService`)
Tracks jobs through a formal state machine:
```
[Discovered] ──> [Analysed & Matched] ──> [Bookmarked]
                       │                        │
                       v                        v
             [Tailored & Prepared] ──> [PENDING USER APPROVAL]
                                                │
                          ┌─────────────────────┴─────────────────────┐
                          │                                           │
                    [User Approved]                             [User Rejected]
                          │                                           │
                          v                                           v
                  [Application Sent]                            [Archived]
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       v                  v                  v
 [Interviewing]     [Offer Extended]    [Rejected]
```

### 3.5. Native Scheduler Adapter (`JobSchedulerService`)
- Integrates with `OSSchedulerAdapter` and `ReminderService`.
- Dispatches periodic, non-intrusive discovery sweeps (e.g., daily at 09:00 or every 12 hours).
- Emits desktop notifications and briefings via `BriefingService` ("ALEX found 3 high-compatibility Full Stack React/Node roles matching your preferences today").

---

## 4. Reusability of Existing ALEX Core

| Existing Component | Integration Role in Job Hunting | Modification Required? |
|---|---|---|
| `app.services.ModelLadderService` | Executes structured extraction, compatibility scoring, and resume tailoring across configured LLM tiers | None (Used as client) |
| `app.services.WebSearchService` | Queries job boards, company listings, and hiring portals | None (Used as client) |
| `app.services.BrowserControlService` | Inspects live job posting pages, parses dynamic DOM content, fills drafts | None (Used as client) |
| `app.services.DocumentParserService` | Parses master resume files in PDF, DOCX, Markdown format | None (Used as client) |
| `app.services.OSSchedulerAdapter` | Manages scheduled background discovery jobs across macOS/Linux/Windows | None (Used as client) |
| `app.actions.action_registry` | Registers voice/chat callable job hunting actions (`jobs.search`, `jobs.match`, etc.) | None (Registers new action group) |
| `app.core.security` | Secures REST endpoints via API bearer token & rate limits | None (Attached to router) |
| `frontend/src/components/workspace` | Displays tailored resumes, job preview cards, and cover letters in floating HUD workspace | Minor (Adds `'job_hunting'` activity type) |

---

## 5. Non-Functional Requirements & Performance
- **Latency**: Job matching and scoring must return within < 4 seconds using Model Ladder streaming or tier-1 fast LLMs.
- **Resource Footprint**: Background discovery sweeps run with low OS process priority (nice/launchd) to prevent any impact on the live avatar or voice conversation.
- **Privacy**: No telemetry, API keys, resume text, or employer data ever leaves the local machine except directly to the user's explicitly configured LLM provider endpoints.
- **Auditability**: Every AI action, match rationale, and user approval is recorded with an immutable timestamp in SQLite.

