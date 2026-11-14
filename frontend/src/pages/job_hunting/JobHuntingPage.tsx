import { useEffect, useState } from "react";
import { jobHuntingApi } from "../../services/jobHuntingApi";
import type {
  AdapterStatusReport,
  ApplicationApproval,
  ApplicationStatus,
  CandidatePreferences,
  CandidateProfile,
  CompatibilityScore,
  JobApplication,
  JobListing,
  ScheduleDiscoveryConfig,
} from "../../types/jobHunting";

import "./jobHunting.css";
import { ApplicationTrackerView } from "./ApplicationTrackerView";
import { ApprovalDialog } from "./ApprovalDialog";
import { CoverLetterStudioView } from "./CoverLetterStudioView";
import { DashboardView } from "./DashboardView";
import { DiscoverView } from "./DiscoverView";
import { InterviewTrackerView } from "./InterviewTrackerView";
import { JobComparisonView } from "./JobComparisonView";
import { JobDetailsView } from "./JobDetailsView";
import { JobLocationMapView } from "./JobLocationMapView";
import { MatchAnalysisView } from "./MatchAnalysisView";
import { PendingApprovalsView } from "./PendingApprovalsView";
import { RecommendedView } from "./RecommendedView";
import { ResumeStudioView } from "./ResumeStudioView";
import { SettingsView } from "./SettingsView";

export type JobHuntingTab =
  | "dashboard"
  | "discover"
  | "map"
  | "compare"
  | "recommended"
  | "details"
  | "analysis"
  | "resume"
  | "cover_letter"
  | "approvals"
  | "applications"
  | "interview"
  | "settings";

interface JobHuntingPageProps {
  onError?: (msg: string) => void;
  onOpenSettings?: () => void;
}

export function JobHuntingPage({ onError }: JobHuntingPageProps) {
  const [activeTab, setActiveTab] = useState<JobHuntingTab>("dashboard");
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [adapters, setAdapters] = useState<AdapterStatusReport[]>([]);
  const [scores, setScores] = useState<Record<string, CompatibilityScore>>({});
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [approvals, setApprovals] = useState<ApplicationApproval[]>([]);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [schedule, setSchedule] = useState<ScheduleDiscoveryConfig | null>(null);

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [activeApproval, setActiveApproval] = useState<ApplicationApproval | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  function showNotice(kind: "success" | "error", text: string) {
    setNotice({ kind, text });
    if (kind === "error" && onError) {
      onError(text);
    }
  }

  // Initial load
  useEffect(() => {
    let active = true;

    async function loadInitialData() {
      setLoading(true);
      try {
        const [jobsRes, adaptersRes, appsRes, apprRes, profRes, schedRes] = await Promise.all([
          jobHuntingApi.listJobs({ limit: 100 }),
          jobHuntingApi.listAdapters().catch(() => []),
          jobHuntingApi.listApplications(),
          jobHuntingApi.listPendingApprovals(),
          jobHuntingApi.getCandidateProfile().catch(() => null),
          jobHuntingApi.getDiscoverySchedule().catch(() => null),
        ]);

        if (!active) return;

        setJobs(jobsRes?.jobs || []);
        setAdapters(Array.isArray(adaptersRes) ? adaptersRes : []);
        setApplications(Array.isArray(appsRes) ? appsRes : []);
        setApprovals(Array.isArray(apprRes) ? apprRes : []);
        setProfile(profRes);
        setSchedule(schedRes);

        if (jobsRes.jobs && jobsRes.jobs.length > 0 && !selectedJobId) {
          setSelectedJobId(jobsRes.jobs[0].id);
        }

        // Fetch scores for known jobs
        const scoreEntries: Record<string, CompatibilityScore> = {};
        for (const j of jobsRes.jobs.slice(0, 20)) {
          try {
            const sc = await jobHuntingApi.getScore(j.id);
            scoreEntries[j.id] = sc;
          } catch {
            // No score yet
          }
        }
        if (active) {
          setScores(scoreEntries);
        }
      } catch (err: any) {
        if (active) showNotice("error", `Failed loading job hunting telemetry: ${err.message}`);
      } finally {
        if (active) setLoading(false);
      }
    }

    loadInitialData();

    return () => {
      active = false;
    };
  }, []);

  const selectedJob = jobs.find((j) => j.id === selectedJobId) || jobs[0] || null;
  const selectedScore = selectedJob ? scores[selectedJob.id] || null : null;

  // Handlers
  async function handleQuickIngestUrl(url: string) {
    try {
      let newJob: JobListing;
      if (url.includes("linkedin.com/jobs")) {
        newJob = await jobHuntingApi.ingestLinkedInUrl(url);
      } else {
        newJob = await jobHuntingApi.ingestDirectUrl(url);
      }
      setJobs((prev) => [newJob, ...prev]);
      setSelectedJobId(newJob.id);
      showNotice("success", `Ingested job: ${newJob.title} @ ${newJob.company_name}`);
    } catch (err: any) {
      showNotice("error", `Ingest failed: ${err.message}`);
      throw err;
    }
  }

  async function handleIngestLinkedInUrl(url: string, title?: string, company?: string, modality?: string) {
    try {
      const newJob = await jobHuntingApi.ingestLinkedInUrl(url, title, company, modality);
      setJobs((prev) => [newJob, ...prev]);
      setSelectedJobId(newJob.id);
      showNotice("success", `Ingested LinkedIn job: ${newJob.title} @ ${newJob.company_name}`);
    } catch (err: any) {
      showNotice("error", `LinkedIn URL ingestion failed: ${err.message}`);
      throw err;
    }
  }

  async function handleIngestLinkedInAlert(alertText: string) {
    try {
      const ingested = await jobHuntingApi.ingestLinkedInAlert(alertText);
      setJobs((prev) => [...ingested, ...prev]);
      if (ingested.length > 0) setSelectedJobId(ingested[0].id);
      showNotice("success", `Extracted and ingested ${ingested.length} jobs from LinkedIn alert.`);
    } catch (err: any) {
      showNotice("error", `Alert parsing failed: ${err.message}`);
      throw err;
    }
  }

  async function handleIngestGreenhouse(boardToken: string, filterRole?: string) {
    try {
      const ingested = await jobHuntingApi.ingestGreenhouse(boardToken, filterRole);
      setJobs((prev) => [...ingested, ...prev]);
      if (ingested.length > 0) setSelectedJobId(ingested[0].id);
      showNotice("success", `Ingested ${ingested.length} jobs from Greenhouse (${boardToken}).`);
    } catch (err: any) {
      showNotice("error", `Greenhouse ingestion failed: ${err.message}`);
      throw err;
    }
  }

  async function handleIngestLever(siteName: string, filterRole?: string) {
    try {
      const ingested = await jobHuntingApi.ingestLever(siteName, filterRole);
      setJobs((prev) => [...ingested, ...prev]);
      if (ingested.length > 0) setSelectedJobId(ingested[0].id);
      showNotice("success", `Ingested ${ingested.length} jobs from Lever (${siteName}).`);
    } catch (err: any) {
      showNotice("error", `Lever ingestion failed: ${err.message}`);
      throw err;
    }
  }

  async function handleIngestDirectUrl(url: string, title?: string, company?: string, rawText?: string, modality?: string) {
    try {
      const newJob = await jobHuntingApi.ingestDirectUrl(url, title, company, rawText, modality);
      setJobs((prev) => [newJob, ...prev]);
      setSelectedJobId(newJob.id);
      showNotice("success", `Ingested URL job: ${newJob.title} @ ${newJob.company_name}`);
    } catch (err: any) {
      showNotice("error", `URL ingestion failed: ${err.message}`);
      throw err;
    }
  }

  async function handleTriggerSearch(query: string, location: string, modalities: string[]) {
    try {
      const discovered = await jobHuntingApi.discoverJobs(query, location, modalities);
      setJobs((prev) => {
        const existingIds = new Set(prev.map((j) => j.id));
        const newOnes = discovered.filter((j) => !existingIds.has(j.id));
        return [...newOnes, ...prev];
      });
      if (discovered.length > 0) setSelectedJobId(discovered[0].id);
      showNotice("success", `Discovery completed: ${discovered.length} jobs retrieved.`);
    } catch (err: any) {
      showNotice("error", `Discovery failed: ${err.message}`);
      throw err;
    }
  }

  async function handleRunMatch(jobId: string) {
    try {
      const score = await jobHuntingApi.calculateMatch(jobId);
      setScores((prev) => ({ ...prev, [jobId]: score }));
      showNotice("success", `Match calculated: ${score.match_percentage}%`);
    } catch (err: any) {
      showNotice("error", `Match failed: ${err.message}`);
      throw err;
    }
  }

  async function handleTailorResume(jobId: string, instructions?: string) {
    try {
      const doc = await jobHuntingApi.tailorResume(jobId, instructions);
      // Refresh applications list
      const apps = await jobHuntingApi.listApplications();
      setApplications(apps);
      showNotice("success", `Resume & Cover letter prepared (v${doc.version_number})`);
    } catch (err: any) {
      showNotice("error", `Tailoring failed: ${err.message}`);
      throw err;
    }
  }

  async function handleUpdateStatus(applicationId: string, status: ApplicationStatus, notes?: string) {
    try {
      const updated = await jobHuntingApi.updateApplicationStatus(applicationId, status, notes);
      setApplications((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      showNotice("success", `Application status updated to ${status}`);
    } catch (err: any) {
      showNotice("error", `Update status failed: ${err.message}`);
      throw err;
    }
  }

  async function handleRecordInterview(
    applicationId: string,
    roundName: string,
    scheduledAt: string,
    interviewer?: string,
    feedback?: string,
  ) {
    try {
      const updated = await jobHuntingApi.recordInterview(
        applicationId,
        roundName,
        scheduledAt,
        interviewer,
        feedback,
      );
      setApplications((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      showNotice("success", `Interview round '${roundName}' scheduled`);
    } catch (err: any) {
      showNotice("error", `Interview record failed: ${err.message}`);
      throw err;
    }
  }

  async function handleDecideApproval(approvalId: string, approved: boolean, confirmationText?: string) {
    try {
      const decided = await jobHuntingApi.decideApproval(approvalId, approved, confirmationText);
      setApprovals((prev) => prev.map((a) => (a.id === decided.id ? decided : a)));
      // Refresh applications
      const apps = await jobHuntingApi.listApplications();
      setApplications(apps);
      setActiveApproval(null);
      showNotice("success", `Action ${approved ? "APPROVED" : "REJECTED"} successfully`);
    } catch (err: any) {
      showNotice("error", `Decision failed: ${err.message}`);
      throw err;
    }
  }

  async function handleUpdateProfile(payload: Partial<CandidateProfile>) {
    const updated = await jobHuntingApi.updateCandidateProfile(payload);
    setProfile(updated);
  }

  async function handleUpdatePreferences(prefs: Partial<CandidatePreferences>) {
    const updated = await jobHuntingApi.updateCandidatePreferences(prefs);
    setProfile(updated);
  }

  async function handleUploadResume(rawText: string) {
    const updated = await jobHuntingApi.uploadMasterResume({ raw_text: rawText });
    setProfile(updated);
  }

  async function handleUpdateSchedule(enabled: boolean, intervalHours: number) {
    const updated = await jobHuntingApi.updateDiscoverySchedule(enabled, intervalHours);
    setSchedule(updated);
  }

  function navigateTab(t: string) {
    let target = t;
    if (target === "resume_studio") target = "resume";
    if (target === "match") target = "analysis";
    if (target === "cover") target = "cover_letter";
    if (target === "approval") target = "approvals";
    if (target === "application") target = "applications";
    if (target === "interviews") target = "interview";
    if (target === "location_map" || target === "location") target = "map";
    if (target === "comparison") target = "compare";
    setActiveTab(target as JobHuntingTab);
  }

  const pendingApprovalsCount = approvals.filter((a) => a.approval_status === "pending").length;
  const activeApplicationsCount = applications.filter((a) =>
    ["tailored", "ready_to_apply", "applied", "interviewing"].includes(a.status),
  ).length;

  const currentCategory = ["dashboard", "discover", "map", "recommended"].includes(activeTab)
    ? "radar"
    : ["details", "analysis", "compare"].includes(activeTab)
    ? "eval"
    : ["resume", "cover_letter"].includes(activeTab)
    ? "studio"
    : ["approvals", "applications", "interview"].includes(activeTab)
    ? "pipeline"
    : "config";

  return (
    <div className="job-hunting-root jh-shell">
      {/* Category Quick-Navigation Ribbon */}
      <div className="jh-category-strip">
        <span className="jh-category-label">SECTIONS:</span>
        <button
          type="button"
          className={`jh-category-pill ${currentCategory === "radar" ? "active" : ""}`}
          onClick={() => navigateTab("dashboard")}
        >
          RADAR
        </button>
        <button
          type="button"
          className={`jh-category-pill ${currentCategory === "eval" ? "active" : ""}`}
          onClick={() => navigateTab("details")}
        >
          EVALUATION
        </button>
        <button
          type="button"
          className={`jh-category-pill ${currentCategory === "studio" ? "active" : ""}`}
          onClick={() => navigateTab("resume")}
        >
          STUDIO
        </button>
        <button
          type="button"
          className={`jh-category-pill ${currentCategory === "pipeline" ? "active" : ""}`}
          onClick={() => navigateTab(pendingApprovalsCount > 0 ? "approvals" : "applications")}
        >
          PIPELINE {pendingApprovalsCount > 0 ? `(${pendingApprovalsCount} Alert)` : ""}
        </button>
        <button
          type="button"
          className={`jh-category-pill ${currentCategory === "config" ? "active" : ""}`}
          onClick={() => navigateTab("settings")}
        >
          CONFIG
        </button>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="jh-subnav jh-nav-bar job-nav-bar" aria-label="Job hunting sub-navigation">
        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => navigateTab("dashboard")}
        >
          <span className="jh-tab-icon">⚡</span> Dashboard
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "discover" ? "active" : ""}`}
          onClick={() => navigateTab("discover")}
        >
          <span className="jh-tab-icon">🔍</span> Discover Jobs
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "map" ? "active" : ""}`}
          onClick={() => navigateTab("map")}
        >
          <span className="jh-tab-icon">🌐</span> Location Map
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "recommended" ? "active" : ""}`}
          onClick={() => navigateTab("recommended")}
        >
          <span className="jh-tab-icon">🎯</span> Recommended
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "details" ? "active" : ""}`}
          onClick={() => navigateTab("details")}
        >
          <span className="jh-tab-icon">📋</span> Job Details
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "analysis" ? "active" : ""}`}
          onClick={() => navigateTab("analysis")}
        >
          <span className="jh-tab-icon">⚖️</span> AI Match Analysis
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "compare" ? "active" : ""}`}
          onClick={() => navigateTab("compare")}
        >
          <span className="jh-tab-icon">⚖️</span> Compare Roles
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "resume" ? "active" : ""}`}
          onClick={() => navigateTab("resume")}
        >
          <span className="jh-tab-icon">📝</span> Resume Studio
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "cover_letter" ? "active" : ""}`}
          onClick={() => navigateTab("cover_letter")}
        >
          <span className="jh-tab-icon">✉️</span> Cover Letter
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "approvals" ? "active" : ""}`}
          onClick={() => navigateTab("approvals")}
        >
          <span className="jh-tab-icon">🛡️</span> Approvals
          {pendingApprovalsCount > 0 && (
            <span className="jh-badge-count jh-badge-alert">
              {pendingApprovalsCount}
            </span>
          )}
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "applications" ? "active" : ""}`}
          onClick={() => navigateTab("applications")}
        >
          <span className="jh-tab-icon">📊</span> Applications
          {activeApplicationsCount > 0 && (
            <span className="jh-badge-count">
              {activeApplicationsCount}
            </span>
          )}
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "interview" ? "active" : ""}`}
          onClick={() => navigateTab("interview")}
        >
          <span className="jh-tab-icon">🗓️</span> Interviews
        </button>

        <button
          type="button"
          className={`jh-subnav-btn jh-nav-item ${activeTab === "settings" ? "active" : ""}`}
          onClick={() => navigateTab("settings")}
        >
          <span className="jh-tab-icon">⚙️</span> Settings
        </button>
      </div>

      {/* Active Target Job Context Bar */}
      {selectedJob && (
        <div className="jh-target-context-bar" role="region" aria-label="Active Target Job">
          <div className="jh-target-info">
            <span className="jh-target-tag">ACTIVE TARGET</span>
            <span className="jh-target-title">Role: {selectedJob.title}</span>
            <span className="jh-target-company">@ {selectedJob.company_name}</span>
            <span className="jh-target-modality">{selectedJob.modality.toUpperCase()}</span>
            {selectedScore && (
              <span
                className={`jh-badge ${
                  selectedScore.match_percentage >= 80
                    ? "jh-badge-match-high"
                    : selectedScore.match_percentage >= 60
                    ? "jh-badge-match-med"
                    : "jh-badge-match-low"
                }`}
              >
                SCORE: {selectedScore.match_percentage}%
              </span>
            )}
          </div>
          <div className="jh-target-actions">
            <button
              type="button"
              className={`jh-context-btn ${activeTab === "details" ? "active" : ""}`}
              onClick={() => navigateTab("details")}
            >
              📋 Inspect Specs
            </button>
            <button
              type="button"
              className={`jh-context-btn ${activeTab === "analysis" ? "active" : ""}`}
              onClick={() => navigateTab("analysis")}
            >
              ⚖️ Compatibility
            </button>
            <button
              type="button"
              className={`jh-context-btn ${activeTab === "resume" ? "active" : ""}`}
              onClick={() => navigateTab("resume")}
            >
              📝 Tailor Document
            </button>
            <button
              type="button"
              className={`jh-context-btn ${activeTab === "cover_letter" ? "active" : ""}`}
              onClick={() => navigateTab("cover_letter")}
            >
              ✉️ Draft Letter
            </button>
            {jobs.length > 1 && (
              <select
                className="jh-context-select"
                value={selectedJob.id}
                onChange={(e) => setSelectedJobId(e.target.value)}
                aria-label="Switch Active Target Job"
              >
                {jobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    Switch: {j.title} @ {j.company_name}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>
      )}

      {/* Notice notification */}
      {notice && (
        <div
          style={{
            margin: "0.5rem 0",
            padding: "0.6rem 0.8rem",
            borderRadius: "4px",
            fontSize: "0.85rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background:
              notice.kind === "error"
                ? "rgba(239, 68, 68, 0.15)"
                : "rgba(16, 185, 129, 0.15)",
            border: `1px solid ${
              notice.kind === "error" ? "var(--hud-error)" : "var(--hud-success)"
            }`,
            color: notice.kind === "error" ? "var(--hud-error)" : "var(--hud-success)",
          }}
        >
          <span>
            {notice.kind === "error" ? "⚠ " : "✓ "} {notice.text}
          </span>
          <button
            type="button"
            onClick={() => setNotice(null)}
            style={{
              background: "transparent",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              fontSize: "0.9rem",
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <div className="jh-content">
        {loading && jobs.length === 0 ? (
          <div className="jh-empty-state">
            <h3>INITIALIZING CAREER RADAR...</h3>
            <p>Connecting to ALEX job hunting backend services.</p>
          </div>
        ) : (
          <>
            {activeTab === "dashboard" && (
              <DashboardView
                jobs={jobs}
                scores={scores}
                applications={applications}
                approvals={approvals}
                schedule={schedule}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={navigateTab}
                onQuickIngestUrl={handleQuickIngestUrl}
                onRunMatch={handleRunMatch}
                onTailorResume={handleTailorResume}
              />
            )}

            {activeTab === "discover" && (
              <DiscoverView
                jobs={jobs}
                adapters={adapters}
                onSelectJob={(id) => {
                  setSelectedJobId(id);
                  navigateTab("details");
                }}
                onNavigateTab={navigateTab}
                onIngestLinkedInUrl={handleIngestLinkedInUrl}
                onIngestLinkedInAlert={handleIngestLinkedInAlert}
                onIngestGreenhouse={handleIngestGreenhouse}
                onIngestLever={handleIngestLever}
                onIngestDirectUrl={handleIngestDirectUrl}
                onTriggerSearch={handleTriggerSearch}
              />
            )}

            {activeTab === "map" && (
              <JobLocationMapView
                jobs={jobs}
                scores={scores}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={navigateTab}
                onTailorResume={handleTailorResume}
              />
            )}

            {activeTab === "compare" && (
              <JobComparisonView
                jobs={jobs}
                scores={scores}
                selectedJobId={selectedJobId}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={navigateTab}
              />
            )}

            {activeTab === "recommended" && (
              <RecommendedView
                jobs={jobs}
                scores={scores}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={navigateTab}
                onRunMatch={handleRunMatch}
                onTailorResume={handleTailorResume}
              />
            )}

            {activeTab === "details" && (
              <JobDetailsView
                job={selectedJob}
                score={selectedScore}
                allJobs={jobs}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={navigateTab}
                onRunMatch={handleRunMatch}
                onTailorResume={handleTailorResume}
              />
            )}

            {activeTab === "analysis" && (
              <MatchAnalysisView
                job={selectedJob}
                score={selectedScore}
                allJobs={jobs}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={navigateTab}
                onRunMatch={handleRunMatch}
                onTailorResume={handleTailorResume}
              />
            )}

            {activeTab === "resume" && (
              <ResumeStudioView
                job={selectedJob}
                allJobs={jobs}
                candidateProfile={profile}
                onSelectJob={(id) => setSelectedJobId(id)}
                onError={(err) => showNotice("error", err)}
                onProfileUpdated={(p) => setProfile(p)}
              />
            )}

            {activeTab === "cover_letter" && (
              <CoverLetterStudioView
                job={selectedJob}
                allJobs={jobs}
                onSelectJob={(id) => setSelectedJobId(id)}
                onError={(err) => showNotice("error", err)}
              />
            )}

            {activeTab === "approvals" && (
              <PendingApprovalsView
                approvals={approvals}
                applications={applications}
                jobs={jobs}
                onOpenApprovalDialog={(appr) => setActiveApproval(appr)}
                onNavigateTab={navigateTab}
                onSelectJob={(id) => setSelectedJobId(id)}
              />
            )}

            {activeTab === "applications" && (
              <ApplicationTrackerView
                applications={applications}
                jobs={jobs}
                onUpdateStatus={handleUpdateStatus}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={navigateTab}
              />
            )}

            {activeTab === "interview" && (
              <InterviewTrackerView
                applications={applications}
                jobs={jobs}
                onRecordInterview={handleRecordInterview}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={navigateTab}
                onError={(err) => showNotice("error", err)}
              />
            )}

            {activeTab === "settings" && (
              <SettingsView
                profile={profile}
                schedule={schedule}
                onUpdateProfile={handleUpdateProfile}
                onUpdatePreferences={handleUpdatePreferences}
                onUploadResume={handleUploadResume}
                onUpdateSchedule={handleUpdateSchedule}
                onError={(err) => showNotice("error", err)}
                onSuccess={(msg) => showNotice("success", msg)}
              />
            )}
          </>
        )}
      </div>

      {/* Explicit Approval Dialog Modal */}
      {activeApproval && (
        <ApprovalDialog
          approval={activeApproval}
          onDecision={handleDecideApproval}
          onClose={() => setActiveApproval(null)}
        />
      )}
    </div>
  );
}
