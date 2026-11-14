import { useState } from "react";
import type { ApplicationStatus, JobApplication, JobListing } from "../../types/jobHunting";

interface ApplicationTrackerViewProps {
  applications: JobApplication[];
  jobs: JobListing[];
  onUpdateStatus: (applicationId: string, status: ApplicationStatus, notes?: string) => Promise<void>;
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
}

type KanbanStageKey = "saved" | "applied" | "interview" | "offer" | "rejected";

interface KanbanStageConfig {
  key: KanbanStageKey;
  label: string;
  color: string;
  statuses: ApplicationStatus[];
  defaultStatus: ApplicationStatus;
}

const KANBAN_STAGES: KanbanStageConfig[] = [
  {
    key: "saved",
    label: "Saved",
    color: "var(--hud-cyan, #00d9ff)",
    statuses: ["discovered", "analyzed"],
    defaultStatus: "analyzed",
  },
  {
    key: "applied",
    label: "Applied",
    color: "var(--hud-teal, #00e5ff)",
    statuses: ["tailored", "ready_to_apply", "applied"],
    defaultStatus: "applied",
  },
  {
    key: "interview",
    label: "Interview",
    color: "var(--hud-success, #10b981)",
    statuses: ["interviewing"],
    defaultStatus: "interviewing",
  },
  {
    key: "offer",
    label: "Offer",
    color: "#c084fc",
    statuses: ["offered"],
    defaultStatus: "offered",
  },
  {
    key: "rejected",
    label: "Rejected",
    color: "var(--hud-error, #f87171)",
    statuses: ["rejected", "withdrawn", "archived"],
    defaultStatus: "rejected",
  },
];

function getStageForStatus(status: ApplicationStatus): KanbanStageKey {
  for (const stage of KANBAN_STAGES) {
    if (stage.statuses.includes(status)) return stage.key;
  }
  return "applied";
}

export function ApplicationTrackerView({
  applications,
  jobs,
  onUpdateStatus,
  onSelectJob,
  onNavigateTab,
}: ApplicationTrackerViewProps) {
  const [viewMode, setViewMode] = useState<"kanban" | "list">("kanban");
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>("all");
  const [updatingAppId, setUpdatingAppId] = useState<string | null>(null);

  const jobMap = new Map<string, JobListing>();
  jobs.forEach((j) => jobMap.set(j.id, j));

  async function handleQuickStageChange(appId: string, newStage: KanbanStageKey) {
    const config = KANBAN_STAGES.find((s) => s.key === newStage);
    if (!config) return;
    setUpdatingAppId(appId);
    try {
      await onUpdateStatus(appId, config.defaultStatus);
    } finally {
      setUpdatingAppId(null);
    }
  }

  const filtered = applications.filter((app) => {
    if (selectedStatusFilter === "all") return true;
    return app.status === selectedStatusFilter;
  });

  return (
    <div>
      {/* Header */}
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>📊</span> APPLICATION LIFECYCLE & KANBAN RADAR</h2>
          <p>Workflow stage progression: Saved → Applied → Interview → Offer → Rejected</p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          {viewMode === "list" && (
            <select
              className="jh-input"
              value={selectedStatusFilter}
              onChange={(e) => setSelectedStatusFilter(e.target.value)}
              style={{ width: "auto", fontSize: "0.8rem", padding: "0.25rem 0.5rem" }}
            >
              <option value="all">All Statuses ({applications.length})</option>
              {KANBAN_STAGES.map((s) => (
                <option key={s.key} value={s.defaultStatus}>
                  Stage: {s.label}
                </option>
              ))}
            </select>
          )}
          <div className="jh-view-mode-pill-group">
            <button
              type="button"
              className={`jh-btn ${viewMode === "kanban" ? "jh-btn-primary" : "jh-btn-secondary"}`}
              style={{ fontSize: "11.5px", padding: "4px 10px" }}
              onClick={() => setViewMode("kanban")}
            >
              📋 Kanban Board
            </button>
            <button
              type="button"
              className={`jh-btn ${viewMode === "list" ? "jh-btn-primary" : "jh-btn-secondary"}`}
              style={{ fontSize: "11.5px", padding: "4px 10px" }}
              onClick={() => setViewMode("list")}
            >
              📑 Unified List
            </button>
          </div>
        </div>
      </div>

      {/* Stage Summary Metrics Bar */}
      <div className="jh-card" style={{ marginBottom: "1.25rem", padding: "0.75rem 1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem", overflowX: "auto" }}>
          {KANBAN_STAGES.map((stage) => {
            const count = applications.filter((a) => stage.statuses.includes(a.status)).length;
            return (
              <div
                key={stage.key}
                style={{
                  flex: "1 1 0",
                  minWidth: "100px",
                  padding: "0.6rem 0.5rem",
                  background: "rgba(0, 0, 0, 0.25)",
                  border: `1px solid ${stage.color}40`,
                  borderRadius: "6px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "1.2rem", fontWeight: "bold", color: stage.color }}>{count}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  {stage.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* KANBAN BOARD VIEW */}
      {viewMode === "kanban" ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(5, minmax(210px, 1fr))",
            gap: "12px",
            overflowX: "auto",
            paddingBottom: "1rem",
          }}
        >
          {KANBAN_STAGES.map((stage) => {
            const stageApps = applications.filter((a) => stage.statuses.includes(a.status));
            return (
              <div
                key={stage.key}
                style={{
                  background: "rgba(3, 14, 22, 0.65)",
                  border: "1px solid rgba(20, 53, 71, 0.7)",
                  borderRadius: "6px",
                  display: "flex",
                  flexDirection: "column",
                  maxHeight: "680px",
                }}
              >
                <div
                  style={{
                    padding: "10px 12px",
                    borderBottom: "1px solid rgba(20, 53, 71, 0.7)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    background: "rgba(0,0,0,0.2)",
                  }}
                >
                  <span style={{ fontSize: "12px", fontWeight: 700, color: stage.color }}>
                    {stage.label.toUpperCase()} ({stageApps.length})
                  </span>
                  <span className="jh-badge" style={{ fontSize: "9px" }}>STAGE</span>
                </div>

                <div style={{ padding: "8px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px", flex: 1 }}>
                  {stageApps.length === 0 ? (
                    <div style={{ padding: "1.5rem 0.5rem", textAlign: "center", fontSize: "11px", color: "var(--hud-text-muted)" }}>
                      No applications in {stage.label}
                    </div>
                  ) : (
                    stageApps.map((app) => {
                      const job = jobMap.get(app.job_id);
                      const currentStage = getStageForStatus(app.status);
                      const isUpdating = updatingAppId === app.id;

                      return (
                        <div
                          key={app.id}
                          style={{
                            background: "rgba(4, 18, 28, 0.8)",
                            border: "1px solid rgba(20, 53, 71, 0.6)",
                            borderRadius: "6px",
                            padding: "10px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "6px",
                          }}
                        >
                          <div style={{ fontSize: "12.5px", fontWeight: 600, color: "var(--hud-text-primary)" }}>
                            {job ? job.title : `App #${app.id.slice(0, 6)}`}
                          </div>
                          <div style={{ fontSize: "11px", color: "var(--hud-accent)" }}>
                            {job ? job.company_name : "Company"} {job?.location ? `· ${job.location}` : ""}
                          </div>

                          {/* Stage Selector */}
                          <div style={{ marginTop: "4px" }}>
                            <label style={{ fontSize: "10px", color: "var(--hud-text-secondary)", display: "block", marginBottom: "2px" }}>
                              Stage Selector:
                            </label>
                            <select
                              className="jh-input"
                              disabled={isUpdating}
                              style={{ padding: "3px 6px", fontSize: "11px", width: "100%" }}
                              value={currentStage}
                              onChange={(e) => handleQuickStageChange(app.id, e.target.value as KanbanStageKey)}
                            >
                              {KANBAN_STAGES.map((s) => (
                                <option key={s.key} value={s.key}>
                                  Stage: {s.label}
                                </option>
                              ))}
                            </select>
                          </div>

                          {/* Action Links */}
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "6px", fontSize: "11px" }}>
                            {job && (
                              <button
                                type="button"
                                className="jh-btn jh-btn-secondary"
                                style={{ padding: "2px 6px", fontSize: "10px" }}
                                onClick={() => {
                                  onSelectJob(job.id);
                                  onNavigateTab("resume");
                                }}
                              >
                                Resume
                              </button>
                            )}
                            {app.interview_rounds && app.interview_rounds.length > 0 && (
                              <button
                                type="button"
                                className="jh-btn jh-btn-primary"
                                style={{ padding: "2px 6px", fontSize: "10px" }}
                                onClick={() => onNavigateTab("interview")}
                              >
                                {app.interview_rounds.length} Interview(s)
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* UNIFIED LIST VIEW */
        <div className="jh-jobs-list">
          {filtered.length === 0 ? (
            <div className="jh-empty-state">
              <h3>No Applications Tracked</h3>
              <p>Applications will appear here once tailored or submitted.</p>
            </div>
          ) : (
            filtered.map((app) => {
              const job = jobMap.get(app.job_id);
              const currentStage = getStageForStatus(app.status);
              const isUpdating = updatingAppId === app.id;

              return (
                <div key={app.id} className="jh-card" style={{ marginBottom: "1rem", padding: "12px 16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
                        <span className={`jh-badge jh-badge-${app.status}`}>
                          {app.status.replace(/_/g, " ").toUpperCase()}
                        </span>
                        {job && <span className="jh-badge jh-badge-source">{job.source.replace("_", " ")}</span>}
                      </div>

                      <div style={{ fontSize: "1.1rem", fontWeight: "600", color: "var(--hud-text)" }}>
                        {job ? `${job.title} @ ${job.company_name}` : `Job ID: ${app.job_id}`}
                      </div>

                      <div style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)", marginTop: "0.25rem" }}>
                        Created: {new Date(app.created_at).toLocaleDateString()}
                        {app.applied_at && <span> • Applied: {new Date(app.applied_at).toLocaleDateString()}</span>}
                        {app.submission_method && <span> • Method: {app.submission_method}</span>}
                      </div>

                      {app.notes && (
                        <div
                          style={{
                            marginTop: "0.5rem",
                            fontSize: "0.8rem",
                            color: "var(--hud-text)",
                            background: "rgba(0, 0, 0, 0.25)",
                            padding: "0.4rem 0.6rem",
                            borderRadius: "4px",
                          }}
                        >
                          <strong>Notes:</strong> {app.notes}
                        </div>
                      )}
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", minWidth: "160px" }}>
                      <label style={{ fontSize: "10.5px", color: "var(--hud-text-secondary)" }}>
                        Stage Selector:
                      </label>
                      <select
                        className="jh-input"
                        disabled={isUpdating}
                        style={{ padding: "4px 8px", fontSize: "11.5px" }}
                        value={currentStage}
                        onChange={(e) => handleQuickStageChange(app.id, e.target.value as KanbanStageKey)}
                      >
                        {KANBAN_STAGES.map((s) => (
                          <option key={s.key} value={s.key}>
                            Stage: {s.label}
                          </option>
                        ))}
                      </select>

                      <div style={{ display: "flex", gap: "6px", marginTop: "4px" }}>
                        {job && (
                          <button
                            type="button"
                            className="jh-btn jh-btn-secondary"
                            style={{ flex: 1, fontSize: "11px", padding: "3px 6px" }}
                            onClick={() => {
                              onSelectJob(job.id);
                              onNavigateTab("resume");
                            }}
                          >
                            Resume
                          </button>
                        )}
                        <button
                          type="button"
                          className="jh-btn jh-btn-primary"
                          style={{ flex: 1, fontSize: "11px", padding: "3px 6px" }}
                          onClick={() => onNavigateTab("interview")}
                        >
                          Interviews
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
