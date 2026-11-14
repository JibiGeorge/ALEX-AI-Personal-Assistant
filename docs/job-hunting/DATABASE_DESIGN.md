# Job Hunting Module — Database Design & Schema Specification

## 1. Overview & Storage Engine

The Job Hunting Module uses an embedded **SQLite 3** relational database located in the user's secure application data directory:
- **macOS**: `~/Library/Application Support/Alex/job_hunting.db`
- **Linux**: `~/.local/share/Alex/job_hunting.db`
- **Windows**: `%APPDATA%\Alex\job_hunting.db`
- **Configurable Override**: `$ALEX_DATA_DIR/job_hunting.db`

### Why SQLite?
1. **Zero External Dependencies**: Natively supported by Python's standard library `sqlite3` and bundled runtime without needing external database servers (Postgres/MySQL).
2. **ACID Transactions**: Guarantees atomic application state transitions and audit logging.
3. **Structured Foreign Keys & Indexes**: Enforces relational integrity across jobs, candidate profiles, match scores, tailored documents, and application timelines.
4. **Local File Permissions**: Enforces `0o600` permissions (read/write by owner only) on Unix-like operating systems.
5. **JSON Export & Backup**: Automated, periodic atomic snapshots to JSON for effortless migration or inspection.

---

## 2. Entity-Relationship Diagram (ERD)

```
 +------------------------+             1:N              +--------------------------+
 |   candidate_profiles   |----------------------------->| candidate_work_history   |
 +------------------------+                              +--------------------------+
             |                                                         |
             | 1:N                                                     | 1:N
             v                                                         v
 +------------------------+             1:N              +--------------------------+
 |  candidate_preferences |                              |    candidate_skills      |
 +------------------------+                              +--------------------------+
             |
             +-------------------------+
                                       |
                                       v
 +------------------------+   1:N   +------------------------+   1:1   +------------------------+
 |      job_listings      |-------->| compatibility_scores   |-------->|   tailored_documents   |
 +------------------------+         +------------------------+         +------------------------+
             |                                                                      |
             | 1:N                                                                  | 1:1
             v                                                                      v
 +------------------------+                                            +------------------------+
 |      applications      |<-------------------------------------------|  application_approvals |
 +------------------------+                                            +------------------------+
             |
             | 1:N
             v
 +------------------------+
 |  application_timeline  |
 +------------------------+
```

---

## 3. Detailed Table Schemas (DDL)

```sql
PRAGMA foreign_keys = ON;

-- 1. Candidate Master Profiles
CREATE TABLE IF NOT EXISTS candidate_profiles (
    id TEXT PRIMARY KEY,                       -- UUID v4
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    location TEXT NOT NULL,                    -- e.g. "San Francisco, CA / Remote"
    linkedin_url TEXT,
    github_url TEXT,
    portfolio_url TEXT,
    headline TEXT,                             -- e.g. "Full Stack Developer (React / Next.js / Node.js)"
    summary TEXT NOT NULL,                     -- Executive bio / professional summary
    total_years_experience REAL NOT NULL,     -- e.g. 3.5
    raw_resume_text TEXT,                      -- Extracted text from master resume file
    master_resume_path TEXT,                   -- Absolute local path to uploaded master resume
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Candidate Job Preferences
CREATE TABLE IF NOT EXISTS candidate_preferences (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    target_roles TEXT NOT NULL,                -- JSON Array: ["Software Developer", "Full Stack Developer", "React Developer", "Next.js Developer", "Node.js Developer"]
    min_years_experience INTEGER DEFAULT 2,
    max_years_experience INTEGER DEFAULT 5,
    modalities TEXT NOT NULL,                  -- JSON Array: ["remote", "hybrid", "onsite"]
    target_locations TEXT NOT NULL,            -- JSON Array: ["Worldwide", "US", "Europe", "Remote"]
    min_base_salary REAL,
    preferred_currency TEXT DEFAULT 'USD',
    keywords TEXT NOT NULL,                    -- JSON Array: ["React 19", "Next.js", "Node.js", "TypeScript", "Tailwind", "PostgreSQL", "FastAPI"]
    excluded_keywords TEXT,                    -- JSON Array: ["Java", "C#", ".NET", "PHP"]
    auto_discovery_enabled INTEGER DEFAULT 1,  -- Boolean: 1 = Active, 0 = Paused
    discovery_interval_hours INTEGER DEFAULT 12,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Candidate Work Experience Items
CREATE TABLE IF NOT EXISTS candidate_work_history (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    role_title TEXT NOT NULL,
    location TEXT,
    is_remote INTEGER DEFAULT 0,
    start_date TEXT NOT NULL,                  -- "YYYY-MM"
    end_date TEXT,                             -- "YYYY-MM" or NULL (current role)
    is_current INTEGER DEFAULT 0,
    highlights TEXT NOT NULL,                  -- JSON Array of impact bullets
    tech_stack TEXT NOT NULL,                  -- JSON Array of skills utilized
    order_index INTEGER DEFAULT 0
);

-- 4. Candidate Skills Inventory
CREATE TABLE IF NOT EXISTS candidate_skills (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    category TEXT NOT NULL,                    -- "Frontend", "Backend", "Language", "Database", "DevOps"
    skill_name TEXT NOT NULL,                  -- e.g. "React", "Next.js", "Node.js", "TypeScript"
    proficiency_level TEXT NOT NULL,           -- "Expert", "Proficient", "Familiar"
    years_experience REAL NOT NULL,
    is_core_highlight INTEGER DEFAULT 1
);

-- 5. Discovered Job Listings
CREATE TABLE IF NOT EXISTS job_listings (
    id TEXT PRIMARY KEY,                       -- UUID v4
    source TEXT NOT NULL,                      -- "LinkedIn", "Indeed", "Greenhouse", "Lever", "Wellfound", "Direct"
    external_id TEXT,                          -- Unique ID on the originating job board
    source_url TEXT NOT NULL,
    company_name TEXT NOT NULL,
    company_website TEXT,
    title TEXT NOT NULL,                       -- e.g. "Full Stack Engineer (React/Node)"
    location TEXT NOT NULL,
    modality TEXT NOT NULL,                    -- "remote", "hybrid", "onsite"
    country TEXT,
    salary_min REAL,
    salary_max REAL,
    salary_currency TEXT DEFAULT 'USD',
    experience_required_min INTEGER DEFAULT 2,
    experience_required_max INTEGER DEFAULT 5,
    raw_description TEXT NOT NULL,             -- Full scraped job description
    cleaned_description TEXT NOT NULL,
    required_skills TEXT NOT NULL,             -- JSON Array: ["React", "Node.js", "TypeScript"]
    preferred_skills TEXT,                    -- JSON Array: ["Next.js", "Docker", "GraphQL"]
    benefits TEXT,                             -- JSON Array
    posted_at TIMESTAMP,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'discovered',          -- "discovered", "analyzed", "bookmarked", "tailored", "applied", "archived", "rejected"
    content_hash TEXT NOT NULL UNIQUE          -- SHA256(company + title + location) for deduplication
);

-- 6. Job Compatibility & Match Scores
CREATE TABLE IF NOT EXISTS compatibility_scores (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL UNIQUE REFERENCES job_listings(id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    overall_score INTEGER NOT NULL,            -- 0 to 100
    skills_score INTEGER NOT NULL,             -- 0 to 100
    experience_score INTEGER NOT NULL,         -- 0 to 100
    location_modality_score INTEGER NOT NULL,  -- 0 to 100
    matching_skills TEXT NOT NULL,             -- JSON Array of matched skills
    missing_skills TEXT NOT NULL,              -- JSON Array of missing skills
    experience_gap_analysis TEXT NOT NULL,     -- Narrative evaluation by Model Ladder
    match_summary TEXT NOT NULL,               -- Concise summary for user HUD card
    recommended_action TEXT NOT NULL,          -- "HIGH_MATCH_APPLY", "CONSIDER_TAILORING", "LOW_MATCH_SKIP"
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Tailored Resumes & Cover Letters
CREATE TABLE IF NOT EXISTS tailored_documents (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES job_listings(id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    version_number INTEGER DEFAULT 1,
    resume_markdown TEXT NOT NULL,             -- Tailored markdown resume
    resume_pdf_path TEXT,                      -- Local filepath to rendered PDF
    cover_letter_markdown TEXT NOT NULL,       -- Tailored cover letter
    cover_letter_pdf_path TEXT,
    ats_keywords_included TEXT NOT NULL,       -- JSON Array of targeted ATS keywords
    customizations_summary TEXT NOT NULL,      -- Bullet points of what was highlighted/altered
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Applications Lifecycle State
CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES job_listings(id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    tailored_document_id TEXT REFERENCES tailored_documents(id),
    status TEXT NOT NULL DEFAULT 'draft',      -- "draft", "ready_for_review", "approved", "submitted", "interviewing", "offer", "rejected", "withdrawn"
    applied_at TIMESTAMP,
    submission_method TEXT,                    -- "manual_web", "email", "portal_auto_fill"
    notes TEXT,
    interview_rounds TEXT,                     -- JSON Array of interview objects
    compensation_offered REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Explicit User Approvals Audit Trail (MANDATORY GATE)
CREATE TABLE IF NOT EXISTS application_approvals (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    requested_action TEXT NOT NULL,            -- "SUBMIT_APPLICATION", "SEND_EMAIL_OUTREACH", "FILL_PORTAL"
    approval_status TEXT NOT NULL,             -- "PENDING", "APPROVED", "REJECTED"
    approval_channel TEXT NOT NULL,            -- "HUD_UI_CLICK", "VOICE_CONFIRMATION", "DESKTOP_POPUP"
    user_confirmation_text TEXT,               -- Exact prompt/voice utterance user agreed to
    decided_at TIMESTAMP,
    ip_or_session TEXT DEFAULT 'local_loopback',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Application Timeline Journal & Events
CREATE TABLE IF NOT EXISTS application_timeline (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,                  -- "DISCOVERED", "MATCHED", "TAILORED", "APPROVAL_REQUESTED", "APPROVED", "SUBMITTED", "INTERVIEW_SCHEDULED", "OFFER_RECEIVED"
    description TEXT NOT NULL,
    metadata_json TEXT,                        -- Contextual event data
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Discovery Runs (Scheduler History)
CREATE TABLE IF NOT EXISTS discovery_runs (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status TEXT NOT NULL,                      -- "running", "completed", "failed"
    queries_executed TEXT NOT NULL,            -- JSON Array of search strings
    jobs_found INTEGER DEFAULT 0,
    new_jobs_stored INTEGER DEFAULT 0,
    error_message TEXT
);
```

---

## 4. Key Indexes for High Performance
```sql
CREATE INDEX IF NOT EXISTS idx_jobs_status ON job_listings(status);
CREATE INDEX IF NOT EXISTS idx_jobs_hash ON job_listings(content_hash);
CREATE INDEX IF NOT EXISTS idx_jobs_modality ON job_listings(modality);
CREATE INDEX IF NOT EXISTS idx_jobs_discovered ON job_listings(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_scores_overall ON compatibility_scores(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON application_approvals(approval_status);
```

---

## 5. Migration Strategy & Compatibility
- **Backward Compatibility**: Completely isolated in its own file `job_hunting.db` alongside ALEX's other local databases, ensuring 0% impact on existing configuration or conversations.
- **Initial Seeding**: The service will inspect user settings and populate the default preferences (Software Developer, Full Stack Developer, React Developer, Next.js Developer, Node.js Developer; 2–5 years; Worldwide/Remote/Hybrid/Onsite).
- **Graceful Failover**: If SQLite write encounters lock contention, the service implements retry backoff with exponential jitter and falls back to atomic memory queues.

