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
  const [listSearch, setListSearch] = useState("");

  const highMatchCount = Object.values(scores).filter((s) => s.match_percentage >= 80).length;
  const excellentMatchCount = Object.values(scores).filter((s) => s.match_percentage >= 85).length;
  const goodMatchCount = Object.values(scores).filter((s) => s.match_percentage >= 70 && s.match_percentage < 85).length;
  const remoteJobsCount = jobs.filter((j) => j.modality === "remote").length;
  const pendingApprovalsCount = approvals.filter((a) => a.approval_status === "pending").length;
  const activeApplicationsCount = applications.filter((a) =>
    !["rejected", "withdrawn", "archived"].includes(a.status)
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

  async function handlePasteClipboard() {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.startsWith("http")) {
          setQuickUrl(text.trim());
        }
      }
    } catch {
      // Clipboard access denied or unavailable
    }
  }

  const displayedJobs = jobs.filter((j) => {
    if (!listSearch.trim()) return true;
    const q = listSearch.toLowerCase();
    return (
      j.title.toLowerCase().includes(q) ||
      j.company_name.toLowerCase().includes(q) ||
      j.location.toLowerCase().includes(q) ||
      j.required_skills.some((s) => s.toLowerCase().includes(q))
    );
  });

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
          <div className="jh-stat-label">
            <span>Total Jobs Discovered</span>
            <span style={{ fontSize: "14px" }}>🌐</span>
          </div>
          <div className="jh-stat-value">{jobs.length}</div>
          <div className="jh-stat-hint">{remoteJobsCount} remote · Explore →</div>
        </div>

        <div className="jh-stat-card jh-stat-card-success" onClick={() => onNavigateTab("recommended")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">
            <span>High Match (≥80%)</span>
            <span style={{ fontSize: "14px" }}>🎯</span>
          </div>
          <div className="jh-stat-value" style={{ color: "var(--hud-success)" }}>{highMatchCount}</div>
          <div className="jh-stat-hint">{excellentMatchCount} excellent (≥85%), {goodMatchCount} good · View →</div>
        </div>

        <div className="jh-stat-card jh-stat-card-purple" onClick={() => onNavigateTab("map")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">
            <span>Geographic Hubs</span>
            <span style={{ fontSize: "14px" }}>🗺️</span>
          </div>
          <div className="jh-stat-value" style={{ color: "var(--hud-accent)" }}>
            {new Set(jobs.filter((j) => j.city).map((j) => j.city)).size || "Global"}
          </div>
          <div className="jh-stat-hint">Interactive Location Radar · Map →</div>
        </div>

        <div className="jh-stat-card jh-stat-card-warning" onClick={() => onNavigateTab("approvals")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">
            <span>Pending Approvals</span>
            <span style={{ fontSize: "14px" }}>🛡️</span>
          </div>
          <div className="jh-stat-value" style={{ color: pendingApprovalsCount > 0 ? "var(--hud-warning)" : "var(--hud-text-secondary)" }}>
            {pendingApprovalsCount}
          </div>
          <div className="jh-stat-hint">{activeApplicationsCount} in tracker · {pendingApprovalsCount} await review →</div>
        </div>
      </div>

      {/* Cybernetic Quick Radar Action Buttons */}
      <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", marginBottom: "1.2rem" }}>
        <button
          type="button"
          className="jh-btn jh-btn-primary"
          style={{ fontSize: "0.8rem", padding: "0.45rem 0.9rem" }}
          onClick={() => onNavigateTab("map")}
        >
          🗺️ Open Interactive Geo Map
        </button>
        <button
          type="button"
          className="jh-btn jh-btn-secondary"
          style={{ fontSize: "0.8rem", padding: "0.45rem 0.9rem" }}
          onClick={() => onNavigateTab("compare")}
        >
          ⚖️ Compare Multiple Roles
        </button>
        <button
          type="button"
          className="jh-btn jh-btn-secondary"
          style={{ fontSize: "0.8rem", padding: "0.45rem 0.9rem" }}
          onClick={() => onNavigateTab("resume")}
        >
          📄 Profile & Resume Analysis
        </button>
        <button
          type="button"
          className="jh-btn jh-btn-secondary"
          style={{ fontSize: "0.8rem", padding: "0.45rem 0.9rem" }}
          onClick={() => onNavigateTab("discover")}
        >
          🔍 Multi-Platform Discovery
        </button>
      </div>

      {/* Quick Ingest Bar */}
      <div className="jh-card" style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px", flexWrap: "wrap", gap: "6px" }}>
          <div style={{ fontFamily: "var(--hud-font-mono)", fontSize: "12px", color: "var(--hud-accent)", fontWeight: 700 }}>
            ▸ RAPID OPPORTUNITY INGESTION
          </div>
          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
            <span className="jh-badge" style={{ fontSize: "9.5px" }}>GREENHOUSE</span>
            <span className="jh-badge" style={{ fontSize: "9.5px" }}>LEVER</span>
            <span className="jh-badge" style={{ fontSize: "9.5px" }}>LINKEDIN LINK</span>
            <span className="jh-badge" style={{ fontSize: "9.5px" }}>DIRECT URL</span>
          </div>
        </div>
        <form onSubmit={handleQuickIngest} className="jh-form-row" style={{ margin: 0, alignItems: "center" }}>
          <div style={{ flex: 1, minWidth: "260px", display: "flex", gap: "6px" }}>
            <input
              type="url"
              className="jh-input"
              style={{ width: "100%", boxSizing: "border-box" }}
              placeholder="Paste job posting URL (e.g. https://jobs.lever.co/company/... or greenhouse.io/...)"
              value={quickUrl}
              onChange={(e) => setQuickUrl(e.target.value)}
              required
            />
            <button
              type="button"
              className="jh-btn jh-btn-secondary"
              style={{ padding: "6px 10px", fontSize: "11px", whiteSpace: "nowrap" }}
              onClick={handlePasteClipboard}
              title="Paste URL from clipboard"
            >
              📋 Paste
            </button>
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
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ fontFamily: "var(--hud-font-mono)", fontSize: "13px", fontWeight: 700 }}>
              RECENT DISCOVERED OPPORTUNITIES ({displayedJobs.slice(0, 10).length} of {jobs.length})
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <input
              type="text"
              className="jh-input"
              style={{ padding: "4px 8px", fontSize: "11px", width: "180px" }}
              placeholder="Filter by title / company..."
              value={listSearch}
              onChange={(e) => setListSearch(e.target.value)}
            />
            <button type="button" className="jh-btn jh-btn-secondary" style={{ padding: "4px 10px", fontSize: "11px" }} onClick={() => onNavigateTab("discover")}>
              View All Jobs
            </button>
          </div>
        </div>

        {jobs.length === 0 ? (
          <div style={{ padding: "30px 10px", textAlign: "center", color: "var(--hud-text-muted)" }}>
            No job opportunities discovered yet. Use Rapid Ingestion above or trigger an autonomous discovery run.
          </div>
        ) : displayedJobs.length === 0 ? (
          <div style={{ padding: "20px 10px", textAlign: "center", color: "var(--hud-text-muted)" }}>
            No opportunities matched &quot;{listSearch}&quot;.
          </div>
        ) : (
          <div>
            {displayedJobs.slice(0, 8).map((job) => {
              const score = scores[job.id];
              const initials = (job.company_name || "JB").slice(0, 2).toUpperCase();
              return (
                <div
                  key={job.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    borderBottom: "1px solid rgba(20, 53, 71, 0.4)",
                    gap: "12px",
                    borderRadius: "4px",
                    transition: "background 0.15s ease",
                  }}
                  className="jh-job-row"
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        width: "34px",
                        height: "34px",
                        borderRadius: "6px",
                        background: "rgba(0, 217, 255, 0.1)",
                        border: "1px solid rgba(0, 217, 255, 0.3)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: "var(--hud-font-mono)",
                        fontSize: "12px",
                        fontWeight: 700,
                        color: "var(--hud-accent)",
                        flexShrink: 0,
                      }}
                    >
                      {initials}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        <strong
                          style={{ color: "var(--hud-text-primary)", cursor: "pointer", fontSize: "13.5px" }}
                          onClick={() => { onSelectJob(job.id); onNavigateTab("details"); }}
                        >
                          {job.title}
                        </strong>
                        <span className="jh-badge" style={{ textTransform: "uppercase" }}>{job.modality}</span>
                        <span className="jh-badge" style={{ color: "var(--hud-accent-secondary)" }}>
                          {job.source.replace("_", " ")}
                        </span>
                      </div>
                      <div style={{ fontSize: "11.5px", color: "var(--hud-text-secondary)", marginTop: "2px" }}>
                        <span style={{ color: "var(--hud-accent)" }}>{job.company_name}</span> · {job.location || "Remote"} · Req: {job.experience_required_min}-{job.experience_required_max} yrs
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
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
                        style={{ padding: "4px 8px", fontSize: "10px" }}
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
                      style={{ padding: "4px 10px", fontSize: "11px" }}
                      onClick={() => { onSelectJob(job.id); void onTailorResume(job.id); onNavigateTab("resume"); }}
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

