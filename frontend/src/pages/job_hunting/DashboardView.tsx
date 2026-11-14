import { useState } from "react";
import type {
  ApplicationApproval,
  CompatibilityScore,
  JobApplication,
  JobListing,
  ScheduleDiscoveryConfig,
} from "../../types/jobHunting";

interface DashboardViewProps {
  jobs: JobListing[];
  scores: Record<string, CompatibilityScore>;
  applications: JobApplication[];
  approvals: ApplicationApproval[];
  schedule: ScheduleDiscoveryConfig | null;
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
  onQuickIngestUrl: (url: string) => Promise<void>;
  onRunMatch: (jobId: string) => Promise<void>;
  onTailorResume: (jobId: string) => Promise<void>;
}

export function DashboardView({
  jobs,
  scores,
  applications,
  approvals,
  schedule,
  onSelectJob,
  onNavigateTab,
  onQuickIngestUrl,
  onRunMatch,
  onTailorResume,
}: DashboardViewProps) {
  const [quickUrl, setQuickUrl] = useState("");
  const [ingesting, setIngesting] = useState(false);

  const highMatchCount = Object.values(scores).filter((s) => s.match_percentage >= 80).length;
  const pendingApprovalsCount = approvals.filter((a) => a.approval_status === "pending").length;
  const activeApplicationsCount = applications.filter((a) =>
    ["tailored", "ready_to_apply", "applied", "interviewing"].includes(a.status),
  ).length;

  async function handleQuickIngest(e: React.FormEvent) {
    e.preventDefault();
    if (!quickUrl.trim() || ingesting) return;
    setIngesting(true);
    try {
      await onQuickIngestUrl(quickUrl.trim());
      setQuickUrl("");
    } finally {
      setIngesting(false);
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>⚡</span> ALEX CAREER INTELLIGENCE DASHBOARD</h2>
          <p>Autonomous discovery, 10-factor compatibility matching, and human-in-the-loop application operations.</p>
        </div>
        <div className="jh-telemetry-badge">
          <span className="jh-telemetry-dot" />
          {schedule?.enabled
            ? `SCHEDULER ACTIVE (EVERY ${schedule.interval_hours}H)`
            : "SCHEDULER STANDBY"}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="jh-stats-grid">
        <div className="jh-stat-card" onClick={() => onNavigateTab("discover")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">Total Jobs Discovered</div>
          <div className="jh-stat-value">{jobs.length}</div>
          <div className="jh-stat-hint">Across verified public sources & feeds</div>
        </div>

        <div className="jh-stat-card" onClick={() => onNavigateTab("recommended")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">High Match (≥80%)</div>
          <div className="jh-stat-value" style={{ color: "var(--hud-success)" }}>{highMatchCount}</div>
          <div className="jh-stat-hint">Roles matching verified skills & seniority</div>
        </div>

        <div className="jh-stat-card" onClick={() => onNavigateTab("applications")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">Active Applications</div>
          <div className="jh-stat-value" style={{ color: "var(--hud-accent)" }}>{activeApplicationsCount}</div>
          <div className="jh-stat-hint">{applications.length} total tracked in pipeline</div>
        </div>

        <div className="jh-stat-card" onClick={() => onNavigateTab("approvals")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">Pending Approvals</div>
          <div className="jh-stat-value" style={{ color: pendingApprovalsCount > 0 ? "var(--hud-warning)" : "var(--hud-text-secondary)" }}>
            {pendingApprovalsCount}
          </div>
          <div className="jh-stat-hint">Awaiting explicit user confirmation</div>
        </div>
      </div>

      {/* Quick Ingest Bar */}
      <div className="jh-card" style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
          <div style={{ fontFamily: "var(--hud-font-mono)", fontSize: "12px", color: "var(--hud-accent)" }}>
            ▸ RAPID OPPORTUNITY INGESTION
          </div>
          <span style={{ fontSize: "11px", color: "var(--hud-text-muted)" }}>
            Direct Job URL / Greenhouse / Lever / Company Page
          </span>
        </div>
        <form onSubmit={handleQuickIngest} className="jh-form-row" style={{ margin: 0 }}>
          <div style={{ flex: 1, minWidth: "260px" }}>
            <input
              type="url"
              className="jh-input"
              style={{ width: "100%", boxSizing: "border-box" }}
              placeholder="Paste job posting URL (e.g. https://jobs.lever.co/company/...)"
              value={quickUrl}
              onChange={(e) => setQuickUrl(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="jh-btn jh-btn-primary" disabled={ingesting}>
            {ingesting ? "Ingesting..." : "Ingest & Extract"}
          </button>
          <button
            type="button"
            className="jh-btn jh-btn-secondary"
            onClick={() => onNavigateTab("discover")}
          >
            Advanced Discovery
          </button>
        </form>
      </div>

      {/* Recent Discovered Jobs */}
      <div className="jh-card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
          <div style={{ fontFamily: "var(--hud-font-mono)", fontSize: "13px", fontWeight: 700 }}>
            RECENT DISCOVERED OPPORTUNITIES ({jobs.slice(0, 10).length} of {jobs.length})
          </div>
          <button type="button" className="jh-btn jh-btn-secondary" style={{ padding: "4px 10px", fontSize: "11px" }} onClick={() => onNavigateTab("discover")}>
            View All Jobs
          </button>
        </div>

        {jobs.length === 0 ? (
          <div style={{ padding: "30px 10px", textAlign: "center", color: "var(--hud-text-muted)" }}>
            No job opportunities discovered yet. Use Rapid Ingestion above or trigger an autonomous discovery run.
          </div>
        ) : (
          <div>
            {jobs.slice(0, 8).map((job) => {
              const score = scores[job.id];
              return (
                <div
                  key={job.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 12px",
                    borderBottom: "1px solid rgba(20, 53, 71, 0.4)",
                    gap: "12px",
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <strong
                        style={{ color: "var(--hud-text-primary)", cursor: "pointer", fontSize: "13px" }}
                        onClick={() => { onSelectJob(job.id); onNavigateTab("details"); }}
                      >
                        {job.title}
                      </strong>
                      <span className="jh-badge">{job.modality}</span>
                      <span className="jh-badge" style={{ color: "var(--hud-accent-secondary)" }}>
                        {job.source.replace("_", " ")}
                      </span>
                    </div>
                    <div style={{ fontSize: "11.5px", color: "var(--hud-text-secondary)", marginTop: "2px" }}>
                      <span style={{ color: "var(--hud-accent)" }}>{job.company_name}</span> · {job.location} · Req: {job.experience_required_min}-{job.experience_required_max} yrs
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    {score ? (
                      <span
                        className={`jh-badge ${
                          score.match_percentage >= 80
                            ? "jh-badge-match-high"
                            : score.match_percentage >= 60
                            ? "jh-badge-match-med"
                            : "jh-badge-match-low"
                        }`}
                        style={{ fontSize: "11px", padding: "3px 8px" }}
                      >
                        {score.match_percentage}% MATCH
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="jh-btn jh-btn-secondary"
                        style={{ padding: "3px 8px", fontSize: "10px" }}
                        onClick={() => void onRunMatch(job.id)}
                      >
                        Run Match
                      </button>
                    )}

                    <button
                      type="button"
                      className="jh-btn jh-btn-secondary"
                      style={{ padding: "4px 8px", fontSize: "11px" }}
                      onClick={() => { onSelectJob(job.id); onNavigateTab("details"); }}
                    >
                      Details
                    </button>

                    <button
                      type="button"
                      className="jh-btn jh-btn-primary"
                      style={{ padding: "4px 8px", fontSize: "11px" }}
                      onClick={() => { onSelectJob(job.id); void onTailorResume(job.id); onNavigateTab("resume_studio"); }}
                    >
                      Tailor
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

