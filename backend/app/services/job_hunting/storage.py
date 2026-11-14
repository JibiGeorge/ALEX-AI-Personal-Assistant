"""
Persistent SQLite Storage for ALEX Job Hunting Module.
Provides ACID transactions, schema creation, indexed queries, and local-first data isolation.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schemas.job_hunting import (
    ApplicationApproval,
    ApplicationStatus,
    ApprovalChannel,
    ApprovalStatus,
    CandidateProfile,
    CompatibilityScore,
    DiscoveryRunRecord,
    JobApplication,
    JobListing,
    JobSource,
    TailoredDocument,
    TimelineEvent,
    WorkModality,
)

logger = logging.getLogger(__name__)


class JobHuntingStorage:
    """Thread-safe persistent storage for Job Hunting entities via SQLite."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        self._ensure_initialized()
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            try:
                if str(self.db_path) != ":memory:":
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                import tempfile
                self.db_path = Path(tempfile.gettempdir()) / "alex_job_hunting.db"
                try:
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)
                except OSError:
                    self.db_path = Path(":memory:")

            try:
                conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            except sqlite3.OperationalError:
                self.db_path = Path(":memory:")
                conn = sqlite3.connect(str(self.db_path), check_same_thread=False)

            with conn:
                cursor = conn.cursor()
                cursor.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS candidate_profiles (
                        id TEXT PRIMARY KEY,
                        full_name TEXT NOT NULL,
                        data_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS job_listings (
                        id TEXT PRIMARY KEY,
                        source TEXT NOT NULL,
                        external_id TEXT,
                        source_url TEXT NOT NULL,
                        company_name TEXT NOT NULL,
                        title TEXT NOT NULL,
                        location TEXT NOT NULL,
                        modality TEXT NOT NULL,
                        salary_min REAL,
                        salary_max REAL,
                        salary_currency TEXT DEFAULT 'USD',
                        experience_required_min INTEGER DEFAULT 2,
                        experience_required_max INTEGER DEFAULT 5,
                        raw_description TEXT NOT NULL,
                        cleaned_description TEXT,
                        required_skills_json TEXT NOT NULL,
                        preferred_skills_json TEXT,
                        benefits_json TEXT,
                        posted_at TEXT,
                        discovered_at TEXT NOT NULL,
                        status TEXT NOT NULL,
                        is_expired INTEGER DEFAULT 0,
                        expiry_checked_at TEXT,
                        content_hash TEXT NOT NULL UNIQUE,
                        full_json TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_jobs_hash ON job_listings(content_hash);
                    CREATE INDEX IF NOT EXISTS idx_jobs_status ON job_listings(status);
                    CREATE INDEX IF NOT EXISTS idx_jobs_source ON job_listings(source);
                    CREATE INDEX IF NOT EXISTS idx_jobs_expired ON job_listings(is_expired);
                    CREATE INDEX IF NOT EXISTS idx_jobs_discovered ON job_listings(discovered_at DESC);

                    CREATE TABLE IF NOT EXISTS compatibility_scores (
                        id TEXT PRIMARY KEY,
                        job_id TEXT NOT NULL UNIQUE REFERENCES job_listings(id) ON DELETE CASCADE,
                        candidate_id TEXT NOT NULL,
                        overall_score INTEGER NOT NULL,
                        skills_score INTEGER NOT NULL,
                        experience_score INTEGER NOT NULL,
                        location_modality_score INTEGER NOT NULL,
                        data_json TEXT NOT NULL,
                        calculated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS tailored_documents (
                        id TEXT PRIMARY KEY,
                        job_id TEXT NOT NULL REFERENCES job_listings(id) ON DELETE CASCADE,
                        candidate_id TEXT NOT NULL,
                        version_number INTEGER DEFAULT 1,
                        resume_markdown TEXT NOT NULL,
                        cover_letter_markdown TEXT NOT NULL,
                        data_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_tailored_job ON tailored_documents(job_id, version_number);

                    CREATE TABLE IF NOT EXISTS applications (
                        id TEXT PRIMARY KEY,
                        job_id TEXT NOT NULL REFERENCES job_listings(id) ON DELETE CASCADE,
                        candidate_id TEXT NOT NULL,
                        tailored_document_id TEXT,
                        status TEXT NOT NULL,
                        applied_at TEXT,
                        submission_method TEXT,
                        notes TEXT,
                        interview_rounds_json TEXT,
                        compensation_offered REAL,
                        data_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
                    CREATE INDEX IF NOT EXISTS idx_apps_job ON applications(job_id);

                    CREATE TABLE IF NOT EXISTS application_approvals (
                        id TEXT PRIMARY KEY,
                        application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                        requested_action TEXT NOT NULL,
                        approval_status TEXT NOT NULL,
                        approval_channel TEXT NOT NULL,
                        user_confirmation_text TEXT,
                        decided_at TEXT,
                        data_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_approvals_app ON application_approvals(application_id);

                    CREATE TABLE IF NOT EXISTS application_timeline (
                        id TEXT PRIMARY KEY,
                        application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                        event_type TEXT NOT NULL,
                        description TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        occurred_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_timeline_app ON application_timeline(application_id);

                    CREATE TABLE IF NOT EXISTS discovery_runs (
                        id TEXT PRIMARY KEY,
                        source TEXT NOT NULL,
                        query TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        finished_at TEXT,
                        status TEXT NOT NULL,
                        jobs_found INTEGER DEFAULT 0,
                        new_jobs_stored INTEGER DEFAULT 0,
                        errors_json TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_discovery_runs_time ON discovery_runs(started_at DESC);
                    """
                )
                # Try migration in case job_listings was created without is_expired
                try:
                    cursor.execute("ALTER TABLE job_listings ADD COLUMN is_expired INTEGER DEFAULT 0;")
                except sqlite3.OperationalError:
                    pass
                try:
                    cursor.execute("ALTER TABLE job_listings ADD COLUMN expiry_checked_at TEXT;")
                except sqlite3.OperationalError:
                    pass

                # Ensure tailored_documents allows multiple versions per job (remove legacy UNIQUE(job_id) if present)
                try:
                    table_sql = cursor.execute(
                        "SELECT sql FROM sqlite_master WHERE type='table' AND name='tailored_documents'"
                    ).fetchone()
                    if table_sql and "job_id TEXT NOT NULL UNIQUE" in table_sql[0]:
                        cursor.execute("ALTER TABLE tailored_documents RENAME TO tailored_documents_old;")
                        cursor.execute("""
                            CREATE TABLE tailored_documents (
                                id TEXT PRIMARY KEY,
                                job_id TEXT NOT NULL REFERENCES job_listings(id) ON DELETE CASCADE,
                                candidate_id TEXT NOT NULL,
                                version_number INTEGER DEFAULT 1,
                                resume_markdown TEXT NOT NULL,
                                cover_letter_markdown TEXT NOT NULL,
                                data_json TEXT NOT NULL,
                                created_at TEXT NOT NULL
                            );
                        """)
                        cursor.execute("INSERT INTO tailored_documents SELECT * FROM tailored_documents_old;")
                        cursor.execute("DROP TABLE tailored_documents_old;")
                        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tailored_job ON tailored_documents(job_id, version_number);")
                except Exception as exc:
                    logger.debug("Tailored documents schema migration: %s", exc)

                conn.commit()
            conn.close()

            # Secure file permissions on Unix if real file
            if os.name != "nt" and str(self.db_path) != ":memory:" and self.db_path.exists():
                try:
                    os.chmod(self.db_path, 0o600)
                except OSError:
                    pass

            self._initialized = True

    # -----------------------------------------------------------------------
    # Candidate Profile CRUD
    # -----------------------------------------------------------------------

    def get_candidate_profile(self, profile_id: str = "default_candidate") -> Optional[CandidateProfile]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM candidate_profiles WHERE id = ?", (profile_id,)
            ).fetchone()
            if not row:
                return None
            data = json.loads(row["data_json"])
            return CandidateProfile.model_validate(data)

    def save_candidate_profile(self, profile: CandidateProfile) -> CandidateProfile:
        with self._lock, self._get_connection() as conn:
            profile_dict = profile.model_dump()
            data_json = json.dumps(profile_dict)
            conn.execute(
                """
                INSERT INTO candidate_profiles (id, full_name, data_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    full_name = excluded.full_name,
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at
                """,
                (profile.id, profile.full_name, data_json, profile.updated_at),
            )
            conn.commit()
            return profile

    # -----------------------------------------------------------------------
    # Job Listings CRUD & Deduplication
    # -----------------------------------------------------------------------

    def get_job_by_hash(self, content_hash: str) -> Optional[JobListing]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT full_json FROM job_listings WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            if not row:
                return None
            return JobListing.model_validate(json.loads(row["full_json"]))

    def get_job(self, job_id: str) -> Optional[JobListing]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT full_json FROM job_listings WHERE id = ?", (job_id,)
            ).fetchone()
            if not row:
                return None
            return JobListing.model_validate(json.loads(row["full_json"]))

    def save_job(self, job: JobListing) -> JobListing:
        with self._lock, self._get_connection() as conn:
            full_json = json.dumps(job.model_dump())
            required_skills_json = json.dumps(job.required_skills)
            preferred_skills_json = json.dumps(job.preferred_skills)
            benefits_json = json.dumps(job.benefits)
            conn.execute(
                """
                INSERT INTO job_listings (
                    id, source, external_id, source_url, company_name, title, location,
                    modality, salary_min, salary_max, salary_currency, experience_required_min,
                    experience_required_max, raw_description, cleaned_description,
                    required_skills_json, preferred_skills_json, benefits_json,
                    posted_at, discovered_at, status, is_expired, expiry_checked_at, content_hash, full_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                    status = excluded.status,
                    is_expired = excluded.is_expired,
                    expiry_checked_at = excluded.expiry_checked_at,
                    full_json = excluded.full_json
                """,
                (
                    job.id,
                    job.source.value,
                    job.external_id,
                    job.source_url,
                    job.company_name,
                    job.title,
                    job.location,
                    job.modality.value,
                    job.salary_min,
                    job.salary_max,
                    job.salary_currency,
                    job.experience_required_min,
                    job.experience_required_max,
                    job.raw_description,
                    job.cleaned_description,
                    required_skills_json,
                    preferred_skills_json,
                    benefits_json,
                    job.posted_at,
                    job.discovered_at,
                    job.status.value,
                    1 if job.is_expired else 0,
                    job.expiry_checked_at,
                    job.content_hash,
                    full_json,
                ),
            )
            conn.commit()
            return job

    def mark_job_expiry(
        self,
        job_id: str,
        is_expired: bool,
        checked_at: str,
    ) -> Optional[JobListing]:
        job = self.get_job(job_id)
        if not job:
            return None
        job.is_expired = is_expired
        job.expiry_checked_at = checked_at
        if is_expired and job.status == ApplicationStatus.DISCOVERED:
            job.status = ApplicationStatus.ARCHIVED
        return self.save_job(job)

    def list_jobs(
        self,
        status: Optional[ApplicationStatus] = None,
        modality: Optional[WorkModality] = None,
        source: Optional[JobSource] = None,
        min_salary: Optional[float] = None,
        experience_min: Optional[int] = None,
        experience_max: Optional[int] = None,
        is_expired: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[JobListing]:
        with self._lock, self._get_connection() as conn:
            clauses: List[str] = []
            params: List[Any] = []
            if status:
                clauses.append("status = ?")
                params.append(status.value)
            if modality:
                clauses.append("modality = ?")
                params.append(modality.value)
            if source:
                clauses.append("source = ?")
                params.append(source.value)
            if min_salary is not None:
                clauses.append("(salary_min >= ? OR salary_max >= ?)")
                params.extend([min_salary, min_salary])
            if experience_min is not None:
                clauses.append("experience_required_max >= ?")
                params.append(experience_min)
            if experience_max is not None:
                clauses.append("experience_required_min <= ?")
                params.append(experience_max)
            if is_expired is not None:
                clauses.append("is_expired = ?")
                params.append(1 if is_expired else 0)
            if search:
                clauses.append("(title LIKE ? OR company_name LIKE ? OR raw_description LIKE ?)")
                p = f"%{search}%"
                params.extend([p, p, p])

            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            sql = f"""
                SELECT full_json FROM job_listings
                {where_sql}
                ORDER BY discovered_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            rows = conn.execute(sql, params).fetchall()
            return [JobListing.model_validate(json.loads(r["full_json"])) for r in rows]

    def count_jobs(self) -> int:
        with self._lock, self._get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM job_listings").fetchone()
            return int(row["cnt"]) if row else 0

    # -----------------------------------------------------------------------
    # Discovery Runs (History) CRUD
    # -----------------------------------------------------------------------

    def save_discovery_run(self, run: DiscoveryRunRecord) -> DiscoveryRunRecord:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO discovery_runs (
                    id, source, query, started_at, finished_at, status,
                    jobs_found, new_jobs_stored, errors_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    finished_at = excluded.finished_at,
                    status = excluded.status,
                    jobs_found = excluded.jobs_found,
                    new_jobs_stored = excluded.new_jobs_stored,
                    errors_json = excluded.errors_json
                """,
                (
                    run.id,
                    run.source,
                    run.query,
                    run.started_at,
                    run.finished_at,
                    run.status,
                    run.jobs_found,
                    run.new_jobs_stored,
                    json.dumps(run.errors),
                ),
            )
            conn.commit()
            return run

    def list_discovery_runs(self, limit: int = 50) -> List[DiscoveryRunRecord]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, source, query, started_at, finished_at, status,
                       jobs_found, new_jobs_stored, errors_json
                FROM discovery_runs
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            runs: List[DiscoveryRunRecord] = []
            for r in rows:
                runs.append(
                    DiscoveryRunRecord(
                        id=r["id"],
                        source=r["source"],
                        query=r["query"],
                        started_at=r["started_at"],
                        finished_at=r["finished_at"],
                        status=r["status"],
                        jobs_found=r["jobs_found"],
                        new_jobs_stored=r["new_jobs_stored"],
                        errors=json.loads(r["errors_json"]),
                    )
                )
            return runs

    # -----------------------------------------------------------------------
    # Compatibility Scores CRUD
    # -----------------------------------------------------------------------

    def get_score_for_job(self, job_id: str) -> Optional[CompatibilityScore]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM compatibility_scores WHERE job_id = ?", (job_id,)
            ).fetchone()
            if not row:
                return None
            return CompatibilityScore.model_validate(json.loads(row["data_json"]))

    def save_score(self, score: CompatibilityScore) -> CompatibilityScore:
        with self._lock, self._get_connection() as conn:
            data_json = json.dumps(score.model_dump())
            conn.execute(
                """
                INSERT INTO compatibility_scores (
                    id, job_id, candidate_id, overall_score, skills_score,
                    experience_score, location_modality_score, data_json, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    overall_score = excluded.overall_score,
                    skills_score = excluded.skills_score,
                    experience_score = excluded.experience_score,
                    location_modality_score = excluded.location_modality_score,
                    data_json = excluded.data_json,
                    calculated_at = excluded.calculated_at
                """,
                (
                    score.id,
                    score.job_id,
                    score.candidate_id,
                    score.overall_score,
                    score.skills_score,
                    score.experience_score,
                    score.location_modality_score,
                    data_json,
                    score.calculated_at,
                ),
            )
            conn.commit()
            return score

    # -----------------------------------------------------------------------
    # Tailored Documents CRUD
    # -----------------------------------------------------------------------

    def get_tailored_document(self, doc_id: str) -> Optional[TailoredDocument]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM tailored_documents WHERE id = ?", (doc_id,)
            ).fetchone()
            if not row:
                return None
            return TailoredDocument.model_validate(json.loads(row["data_json"]))

    def get_tailored_document_for_job(self, job_id: str) -> Optional[TailoredDocument]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM tailored_documents WHERE job_id = ? ORDER BY version_number DESC LIMIT 1",
                (job_id,),
            ).fetchone()
            if not row:
                return None
            return TailoredDocument.model_validate(json.loads(row["data_json"]))

    def list_tailored_documents_for_job(self, job_id: str) -> List[TailoredDocument]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute(
                "SELECT data_json FROM tailored_documents WHERE job_id = ? ORDER BY version_number ASC",
                (job_id,),
            ).fetchall()
            return [TailoredDocument.model_validate(json.loads(r["data_json"])) for r in rows]

    def get_next_version_number_for_job(self, job_id: str) -> int:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT MAX(version_number) as max_v FROM tailored_documents WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row and row["max_v"] is not None:
                return int(row["max_v"]) + 1
            return 1

    def delete_tailored_document(self, doc_id: str) -> bool:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM tailored_documents WHERE id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0

    def save_tailored_document(self, doc: TailoredDocument) -> TailoredDocument:
        with self._lock, self._get_connection() as conn:
            data_json = json.dumps(doc.model_dump())
            conn.execute(
                """
                INSERT INTO tailored_documents (
                    id, job_id, candidate_id, version_number, resume_markdown,
                    cover_letter_markdown, data_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    resume_markdown = excluded.resume_markdown,
                    cover_letter_markdown = excluded.cover_letter_markdown,
                    data_json = excluded.data_json
                """,
                (
                    doc.id,
                    doc.job_id,
                    doc.candidate_id,
                    doc.version_number,
                    doc.resume_markdown,
                    doc.cover_letter_markdown,
                    data_json,
                    doc.created_at,
                ),
            )
            conn.commit()
            return doc

    # -----------------------------------------------------------------------
    # Applications CRUD
    # -----------------------------------------------------------------------

    def get_application(self, app_id: str) -> Optional[JobApplication]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM applications WHERE id = ?", (app_id,)
            ).fetchone()
            if not row:
                return None
            app_dict = json.loads(row["data_json"])
            # Load latest approval if any
            app = JobApplication.model_validate(app_dict)
            app.latest_approval = self.get_latest_approval(app_id)
            return app

    def get_application_by_job(self, job_id: str) -> Optional[JobApplication]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM applications WHERE job_id = ?", (job_id,)
            ).fetchone()
            if not row:
                return None
            app = JobApplication.model_validate(json.loads(row["data_json"]))
            app.latest_approval = self.get_latest_approval(app.id)
            return app

    def list_applications(self, status: Optional[ApplicationStatus] = None) -> List[JobApplication]:
        with self._lock, self._get_connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT data_json FROM applications WHERE status = ? ORDER BY updated_at DESC",
                    (status.value,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT data_json FROM applications ORDER BY updated_at DESC"
                ).fetchall()

            apps: List[JobApplication] = []
            for r in rows:
                app = JobApplication.model_validate(json.loads(r["data_json"]))
                app.latest_approval = self.get_latest_approval(app.id)
                apps.append(app)
            return apps

    def save_application(self, app: JobApplication) -> JobApplication:
        with self._lock, self._get_connection() as conn:
            data_json = json.dumps(app.model_dump())
            rounds_json = json.dumps([r.model_dump() if hasattr(r, "model_dump") else r for r in app.interview_rounds])
            conn.execute(
                """
                INSERT INTO applications (
                    id, job_id, candidate_id, tailored_document_id, status, applied_at,
                    submission_method, notes, interview_rounds_json, compensation_offered,
                    data_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    tailored_document_id = excluded.tailored_document_id,
                    status = excluded.status,
                    applied_at = excluded.applied_at,
                    submission_method = excluded.submission_method,
                    notes = excluded.notes,
                    interview_rounds_json = excluded.interview_rounds_json,
                    compensation_offered = excluded.compensation_offered,
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at
                """,
                (
                    app.id,
                    app.job_id,
                    app.candidate_id,
                    app.tailored_document_id,
                    app.status.value,
                    app.applied_at,
                    app.submission_method,
                    app.notes,
                    rounds_json,
                    app.compensation_offered,
                    data_json,
                    app.created_at,
                    app.updated_at,
                ),
            )
            conn.commit()
            return app

    # -----------------------------------------------------------------------
    # Approvals & Timeline
    # -----------------------------------------------------------------------

    def save_approval(self, approval: ApplicationApproval) -> ApplicationApproval:
        with self._lock, self._get_connection() as conn:
            data_json = json.dumps(approval.model_dump())
            conn.execute(
                """
                INSERT INTO application_approvals (
                    id, application_id, requested_action, approval_status,
                    approval_channel, user_confirmation_text, decided_at,
                    data_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    approval_status = excluded.approval_status,
                    decided_at = excluded.decided_at,
                    user_confirmation_text = excluded.user_confirmation_text,
                    data_json = excluded.data_json
                """,
                (
                    approval.id,
                    approval.application_id,
                    approval.requested_action,
                    approval.approval_status.value,
                    approval.approval_channel.value,
                    approval.user_confirmation_text,
                    approval.decided_at,
                    data_json,
                    approval.created_at,
                ),
            )
            conn.commit()
            return approval

    def get_latest_approval(self, application_id: str) -> Optional[ApplicationApproval]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT data_json FROM application_approvals
                WHERE application_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (application_id,),
            ).fetchone()
            if not row:
                return None
            return ApplicationApproval.model_validate(json.loads(row["data_json"]))

    def get_approval(self, approval_id: str) -> Optional[ApplicationApproval]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM application_approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
            if not row:
                return None
            return ApplicationApproval.model_validate(json.loads(row["data_json"]))

    def list_pending_approvals(self, limit: int = 50) -> List[ApplicationApproval]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT data_json FROM application_approvals
                WHERE LOWER(approval_status) = 'pending'
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [ApplicationApproval.model_validate(json.loads(r["data_json"])) for r in rows]

    def add_timeline_event(self, event: TimelineEvent) -> TimelineEvent:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO application_timeline (
                    id, application_id, event_type, description, metadata_json, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.application_id,
                    event.event_type,
                    event.description,
                    json.dumps(event.metadata),
                    event.occurred_at,
                ),
            )
            conn.commit()
            return event

    def list_timeline_events(self, application_id: str) -> List[TimelineEvent]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, application_id, event_type, description, metadata_json, occurred_at
                FROM application_timeline
                WHERE application_id = ?
                ORDER BY occurred_at ASC
                """,
                (application_id,),
            ).fetchall()
            events: List[TimelineEvent] = []
            for r in rows:
                events.append(
                    TimelineEvent(
                        id=r["id"],
                        application_id=r["application_id"],
                        event_type=r["event_type"],
                        description=r["description"],
                        metadata=json.loads(r["metadata_json"]),
                        occurred_at=r["occurred_at"],
                    )
                )
            return events
