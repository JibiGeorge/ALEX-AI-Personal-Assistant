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
import { JobDetailsView } from "./JobDetailsView";
import { MatchAnalysisView } from "./MatchAnalysisView";
import { PendingApprovalsView } from "./PendingApprovalsView";
import { RecommendedView } from "./RecommendedView";
import { ResumeStudioView } from "./ResumeStudioView";
import { SettingsView } from "./SettingsView";

export type JobHuntingTab =
  | "dashboard"
  | "discover"
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

  const pendingApprovalsCount = approvals.filter((a) => a.approval_status === "pending").length;
  const activeApplicationsCount = applications.filter((a) =>
    ["tailored", "ready_to_apply", "applied", "interviewing"].includes(a.status),
  ).length;

  return (
    <div className="job-hunting-root">
      {/* Sub-Navigation Tabs */}
      <div className="jh-subnav job-nav-bar">
        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => setActiveTab("dashboard")}
        >
          <span>⚡</span> Dashboard
        </button>

        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "discover" ? "active" : ""}`}
          onClick={() => setActiveTab("discover")}
        >
          <span>🔍</span> Discover Jobs
        </button>

        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "recommended" ? "active" : ""}`}
          onClick={() => setActiveTab("recommended")}
        >
          <span>🎯</span> Recommended
        </button>

        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "details" ? "active" : ""}`}
          onClick={() => setActiveTab("details")}
        >
          <span>📋</span> Job Details
        </button>

        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "analysis" ? "active" : ""}`}
          onClick={() => setActiveTab("analysis")}
        >
          <span>⚖️</span> AI Match Analysis
        </button>

        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "resume" ? "active" : ""}`}
          onClick={() => setActiveTab("resume")}
        >
          <span>📝</span> Resume Studio
        </button>

        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "cover_letter" ? "active" : ""}`}
          onClick={() => setActiveTab("cover_letter")}
        >
          <span>✉️</span> Cover Letter
        </button>

        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "approvals" ? "active" : ""}`}
          onClick={() => setActiveTab("approvals")}
        >
          <span>🛡️</span> Approvals
          {pendingApprovalsCount > 0 && (
            <span
              style={{
                marginLeft: "0.35rem",
                background: "var(--hud-warning)",
                color: "#000",
                fontSize: "0.7rem",
                fontWeight: "bold",
                borderRadius: "8px",
                padding: "0.1rem 0.4rem",
              }}
            >
              {pendingApprovalsCount}
            </span>
          )}
        </button>

        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "applications" ? "active" : ""}`}
          onClick={() => setActiveTab("applications")}
        >
          <span>📊</span> Applications
          {activeApplicationsCount > 0 && (
            <span
              style={{
                marginLeft: "0.35rem",
                background: "rgba(0, 217, 255, 0.2)",
                color: "var(--hud-accent)",
                fontSize: "0.7rem",
                borderRadius: "8px",
                padding: "0.1rem 0.4rem",
              }}
            >
              {activeApplicationsCount}
            </span>
          )}
        </button>

        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "interview" ? "active" : ""}`}
          onClick={() => setActiveTab("interview")}
        >
          <span>🗓️</span> Interviews
        </button>

        <button
          type="button"
          className={`jh-subnav-btn ${activeTab === "settings" ? "active" : ""}`}
          onClick={() => setActiveTab("settings")}
        >
          <span>⚙️</span> Settings
        </button>
      </div>

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
                onNavigateTab={(t) => setActiveTab(t as JobHuntingTab)}
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
                  setActiveTab("details");
                }}
                onNavigateTab={(t) => setActiveTab(t as JobHuntingTab)}
                onIngestLinkedInUrl={handleIngestLinkedInUrl}
                onIngestLinkedInAlert={handleIngestLinkedInAlert}
                onIngestGreenhouse={handleIngestGreenhouse}
                onIngestLever={handleIngestLever}
                onIngestDirectUrl={handleIngestDirectUrl}
                onTriggerSearch={handleTriggerSearch}
              />
            )}

            {activeTab === "recommended" && (
              <RecommendedView
                jobs={jobs}
                scores={scores}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={(t) => setActiveTab(t as JobHuntingTab)}
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
                onNavigateTab={(t) => setActiveTab(t as JobHuntingTab)}
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
                onNavigateTab={(t) => setActiveTab(t as JobHuntingTab)}
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
                onNavigateTab={(t) => setActiveTab(t as JobHuntingTab)}
                onSelectJob={(id) => setSelectedJobId(id)}
              />
            )}

            {activeTab === "applications" && (
              <ApplicationTrackerView
                applications={applications}
                jobs={jobs}
                onUpdateStatus={handleUpdateStatus}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={(t) => setActiveTab(t as JobHuntingTab)}
              />
            )}

            {activeTab === "interview" && (
              <InterviewTrackerView
                applications={applications}
                jobs={jobs}
                onRecordInterview={handleRecordInterview}
                onSelectJob={(id) => setSelectedJobId(id)}
                onNavigateTab={(t) => setActiveTab(t as JobHuntingTab)}
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
