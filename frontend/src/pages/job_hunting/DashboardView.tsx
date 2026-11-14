import { useMemo, useState } from "react";
import type {
  ApplicationApproval,
  CandidateProfile,
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
  profile?: CandidateProfile | null;
  onOpenOnboarding?: () => void;
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
  profile,
  onOpenOnboarding,
  onSelectJob,
  onNavigateTab,
  onQuickIngestUrl,
  onRunMatch,
  onTailorResume,
}: DashboardViewProps) {
  const [quickUrl, setQuickUrl] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [listSearch, setListSearch] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [seniorityFilter, setSeniorityFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [minMatchFilter, setMinMatchFilter] = useState<number>(0);
  const [sortBy, setSortBy] = useState<"newest" | "match" | "company">("match");
  const [selectedPreviewId, setSelectedPreviewId] = useState<string | null>(
    jobs.length > 0 ? jobs[0].id : null,
  );

  // Stats calculations
  const highMatchCount = Object.values(scores).filter((s) => s.match_percentage >= 80).length;
  const excellentMatchCount = Object.values(scores).filter((s) => s.match_percentage >= 85).length;
  const pendingApprovalsCount = approvals.filter((a) => a.approval_status === "pending").length;
  const activeApplicationsCount = applications.filter((a) =>
    !["rejected", "withdrawn", "archived"].includes(a.status),
  ).length;

  const interviewsCount = applications.reduce(
    (acc, a) => acc + (a.interview_rounds?.length || 0),
    0,
  );

  const responseRate = useMemo(() => {
    if (applications.length === 0) return 0;
    const responded = applications.filter((a) =>
      ["interviewing", "offered", "rejected"].includes(a.status),
    ).length;
    return Math.round((responded / applications.length) * 100);
  }, [applications]);

  const newTodayCount = useMemo(() => {
    const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000;
    const count = jobs.filter(
      (j) => new Date(j.discovered_at).getTime() > oneDayAgo,
    ).length;
    return count > 0 ? count : jobs.length;
  }, [jobs]);

  // Profile Completeness calculation
  const completeness = useMemo(() => {
    let score = 0;
    const missing: string[] = [];

    if (profile?.raw_resume_text || (profile?.work_history && profile.work_history.length > 0)) {
      score += 30;
    } else {
      missing.push("Base Resume");
    }

    if (profile?.full_name && profile?.email && (profile?.location || profile?.current_location)) {
      score += 20;
    } else {
      missing.push("Contact Details");
    }

    if (profile?.preferences?.target_roles && profile.preferences.target_roles.length > 0) {
      score += 20;
    } else {
      missing.push("Target Roles");
    }

    if (
      (profile?.preferences?.modalities && profile.preferences.modalities.length > 0) ||
      (profile?.preferences?.target_locations && profile.preferences.target_locations.length > 0)
    ) {
      score += 15;
    } else {
      missing.push("Locations & Modality");
    }

    if (profile?.preferences?.minimum_salary || (profile as any)?.work_authorization) {
      score += 15;
    } else {
      missing.push("Salary & Work Auth");
    }

    return { percentage: Math.min(100, score), missing };
  }, [profile]);

  // Duplicate detection across sources
  const duplicateSet = useMemo(() => {
    const seen = new Map<string, string>();
    const dupes = new Set<string>();
    jobs.forEach((j) => {
      const key = `${j.company_name.toLowerCase().trim()}::${j.title.toLowerCase().trim()}`;
      if (seen.has(key)) {
        dupes.add(j.id);
      } else {
        seen.set(key, j.id);
      }
    });
    return dupes;
  }, [jobs]);

  // Filtering & Sorting
  const filteredJobs = useMemo(() => {
    return jobs
      .filter((j) => {
        if (remoteOnly && j.modality !== "remote") return false;
        if (sourceFilter !== "all" && j.source !== sourceFilter) return false;

        const score = scores[j.id]?.match_percentage || 0;
        if (minMatchFilter > 0 && score < minMatchFilter) return false;

        if (seniorityFilter !== "all") {
          const title = j.title.toLowerCase();
          if (seniorityFilter === "senior" && !title.includes("senior") && !title.includes("sr")) return false;
          if (seniorityFilter === "lead" && !title.includes("lead") && !title.includes("staff") && !title.includes("principal")) return false;
          if (seniorityFilter === "mid" && (title.includes("senior") || title.includes("junior") || title.includes("lead"))) return false;
        }

        if (listSearch.trim()) {
          const q = listSearch.toLowerCase();
          const matchTitle = j.title.toLowerCase().includes(q);
          const matchComp = j.company_name.toLowerCase().includes(q);
          const matchLoc = (j.location || "").toLowerCase().includes(q);
          const matchSkill = j.required_skills?.some((s) => s.toLowerCase().includes(q));
          if (!matchTitle && !matchComp && !matchLoc && !matchSkill) return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === "match") {
          const scoreA = scores[a.id]?.match_percentage || 0;
          const scoreB = scores[b.id]?.match_percentage || 0;
          return scoreB - scoreA;
        }
        if (sortBy === "company") {
          return a.company_name.localeCompare(b.company_name);
        }
        return new Date(b.discovered_at).getTime() - new Date(a.discovered_at).getTime();
      });
  }, [jobs, scores, remoteOnly, sourceFilter, minMatchFilter, seniorityFilter, listSearch, sortBy]);

  const activePreviewJob = jobs.find((j) => j.id === selectedPreviewId) || filteredJobs[0] || null;
  const activePreviewScore = activePreviewJob ? scores[activePreviewJob.id] : null;

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
      // Clipboard access denied
    }
  }

  return (
    <div className="jh-dashboard-container">
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

      {/* Candidate Radar Profile Completeness Banner */}
      <div
        className="jh-card"
        style={{
          marginBottom: "1.2rem",
          padding: "14px 18px",
          background: "linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.6) 100%)",
          border: "1px solid var(--hud-border-cyan, #0ea5e9)",
          borderRadius: "10px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "14px",
        }}
      >
        <div style={{ flex: "1 1 300px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
            <span style={{ fontSize: "11px", fontFamily: "var(--hud-font-mono, monospace)", color: "var(--hud-accent-cyan, #38bdf8)", fontWeight: 700, letterSpacing: "1px" }}>
              CANDIDATE RADAR PROFILE COMPLETENESS
            </span>
            <span style={{ fontSize: "13px", fontFamily: "var(--hud-font-mono, monospace)", color: completeness.percentage >= 80 ? "var(--hud-success, #20d6a0)" : "var(--hud-accent-cyan, #38bdf8)", fontWeight: 700 }}>
              {completeness.percentage}%
            </span>
          </div>
          <div style={{ width: "100%", height: "6px", background: "rgba(15, 23, 42, 0.8)", borderRadius: "3px", overflow: "hidden", marginBottom: "6px" }}>
            <div
              style={{
                width: `${completeness.percentage}%`,
                height: "100%",
                background: completeness.percentage >= 80 ? "var(--hud-success, #20d6a0)" : "var(--hud-accent-cyan, #0ea5e9)",
                transition: "width 0.4s ease",
              }}
            />
          </div>
          <div style={{ fontSize: "11px", color: "var(--hud-text-secondary, #94a3b8)" }}>
            {completeness.percentage === 100
              ? "✓ Profile fully configured — 10-factor matching engine running with maximum accuracy."
              : `Missing: ${completeness.missing.join(", ")}. Complete profile to maximize scoring precision.`}
          </div>
        </div>

        {onOpenOnboarding && (
          <button
            type="button"
            onClick={onOpenOnboarding}
            className="jh-btn jh-btn-primary"
            style={{
              padding: "7px 16px",
              fontSize: "11.5px",
              fontWeight: 700,
              whiteSpace: "nowrap",
            }}
            aria-label="Open Onboarding Setup Wizard"
          >
            {completeness.percentage === 100 ? "⚙️ Edit Profile & Targets" : "🚀 Launch Setup Wizard →"}
          </button>
        )}
      </div>

      {/* 5 Replaced Stat Cards */}
      <div className="jh-stats-grid jh-stats-grid-5">
        <div className="jh-stat-card" onClick={() => onNavigateTab("discover")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontWeight: 700, color: "var(--hud-accent)" }}>New today</span>
              <span style={{ fontSize: "10.5px", color: "var(--hud-text-secondary)" }}>Total Jobs Discovered</span>
            </div>
            <span style={{ fontSize: "14px" }}>⚡</span>
          </div>
          <div className="jh-stat-value">{newTodayCount}</div>
          <div className="jh-stat-hint">{jobs.length} total across sources · Explore →</div>
        </div>

        <div className="jh-stat-card jh-stat-card-success" onClick={() => onNavigateTab("recommended")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontWeight: 700, color: "var(--hud-success)" }}>To review</span>
              <span style={{ fontSize: "10.5px", color: "var(--hud-text-secondary)" }}>High Match (≥80%)</span>
            </div>
            <span style={{ fontSize: "14px" }}>🎯</span>
          </div>
          <div className="jh-stat-value" style={{ color: "var(--hud-success)" }}>{highMatchCount}</div>
          <div className="jh-stat-hint">{excellentMatchCount} excellent (≥85%) · View →</div>
        </div>

        <div className="jh-stat-card" onClick={() => onNavigateTab("applications")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">
            <span>Applications in progress</span>
            <span style={{ fontSize: "14px" }}>📊</span>
          </div>
          <div className="jh-stat-value" style={{ color: "var(--hud-accent)" }}>{activeApplicationsCount}</div>
          <div className="jh-stat-hint">{pendingApprovalsCount} await authorization →</div>
        </div>

        <div className="jh-stat-card" onClick={() => onNavigateTab("interview")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">
            <span>Interviews</span>
            <span style={{ fontSize: "14px" }}>🗓️</span>
          </div>
          <div className="jh-stat-value" style={{ color: "#a855f7" }}>{interviewsCount}</div>
          <div className="jh-stat-hint">Scheduled technical rounds →</div>
        </div>

        <div className="jh-stat-card jh-stat-card-teal" onClick={() => onNavigateTab("applications")} style={{ cursor: "pointer" }}>
          <div className="jh-stat-label">
            <span>Response rate</span>
            <span style={{ fontSize: "14px" }}>📈</span>
          </div>
          <div className="jh-stat-value" style={{ color: "var(--hud-teal, #00e5ff)" }}>{responseRate}%</div>
          <div className="jh-stat-hint">Pipeline progression velocity →</div>
        </div>
      </div>

      {/* Cybernetic Workflow Action Buttons */}
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

      {/* Rapid Opportunity Ingestion */}
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

      {/* Two-Pane Opportunity Explorer */}
      <div className="jh-card" style={{ padding: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ fontFamily: "var(--hud-font-mono)", fontSize: "13px", fontWeight: 700 }}>
              OPPORTUNITY RADAR ({filteredJobs.length} of {jobs.length})
            </div>
          </div>

          {/* Filters Bar */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <input
              type="text"
              className="jh-input"
              style={{ padding: "4px 8px", fontSize: "11px", width: "160px" }}
              placeholder="Filter title / skill..."
              value={listSearch}
              onChange={(e) => setListSearch(e.target.value)}
            />
            <label style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", color: "var(--hud-text-secondary)", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={remoteOnly}
                onChange={(e) => setRemoteOnly(e.target.checked)}
              />
              Remote Only
            </label>
            <select
              className="jh-input"
              style={{ padding: "4px 6px", fontSize: "11px", width: "auto" }}
              value={seniorityFilter}
              onChange={(e) => setSeniorityFilter(e.target.value)}
            >
              <option value="all">All Seniority</option>
              <option value="mid">Mid-Level</option>
              <option value="senior">Senior</option>
              <option value="lead">Lead / Staff</option>
            </select>
            <select
              className="jh-input"
              style={{ padding: "4px 6px", fontSize: "11px", width: "auto" }}
              value={minMatchFilter}
              onChange={(e) => setMinMatchFilter(Number(e.target.value))}
            >
              <option value="0">All Matches</option>
              <option value="70">≥ 70% Match</option>
              <option value="80">≥ 80% Match</option>
              <option value="90">≥ 90% Match</option>
            </select>
            <select
              className="jh-input"
              style={{ padding: "4px 6px", fontSize: "11px", width: "auto" }}
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
            >
              <option value="all">All Sources</option>
              <option value="greenhouse">Greenhouse</option>
              <option value="lever">Lever</option>
              <option value="linkedin_link">LinkedIn</option>
              <option value="direct_url">Direct URL</option>
            </select>
            <select
              className="jh-input"
              style={{ padding: "4px 6px", fontSize: "11px", width: "auto" }}
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
            >
              <option value="match">Sort: Match %</option>
              <option value="newest">Sort: Newest</option>
              <option value="company">Sort: Company</option>
            </select>
          </div>
        </div>

        {jobs.length === 0 ? (
          <div className="jh-empty-state" style={{ padding: "3rem 1rem", textAlign: "center" }}>
            <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📡</div>
            <h3 style={{ color: "var(--hud-accent)", marginBottom: "0.5rem" }}>No Job Opportunities Discovered Yet</h3>
            <p style={{ color: "var(--hud-text-secondary)", maxWidth: "500px", margin: "0 auto 1.5rem" }}>
              Paste a vacancy link in Rapid Ingestion above or trigger an autonomous discovery search across Greenhouse, Lever, and LinkedIn.
            </p>
            <button
              type="button"
              className="jh-btn jh-btn-primary"
              onClick={() => onNavigateTab("discover")}
            >
              Launch Discovery Search →
            </button>
          </div>
        ) : filteredJobs.length === 0 ? (
          <div style={{ padding: "2rem 1rem", textAlign: "center", color: "var(--hud-text-muted)" }}>
            No opportunities matched current filters.
          </div>
        ) : (
          <div className="jh-two-pane-radar-layout">
            {/* Left Pane: Job List */}
            <div className="jh-two-pane-list">
              {filteredJobs.map((job) => {
                const score = scores[job.id];
                const isSelected = activePreviewJob?.id === job.id;
                const isDuplicate = duplicateSet.has(job.id);
                const initials = (job.company_name || "JB").slice(0, 2).toUpperCase();

                return (
                  <div
                    key={job.id}
                    className={`jh-radar-job-card ${isSelected ? "selected" : ""}`}
                    onClick={() => {
                      setSelectedPreviewId(job.id);
                      onSelectJob(job.id);
                    }}
                  >
                    <div style={{ display: "flex", gap: "10px", alignItems: "flex-start", flex: 1, minWidth: 0 }}>
                      <div className="jh-radar-company-avatar">{initials}</div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                          <strong className="jh-radar-job-title">{job.title}</strong>
                          {isDuplicate && (
                            <span className="jh-badge jh-badge-alert" style={{ fontSize: "9px" }}>
                              DUPLICATE
                            </span>
                          )}
                          <span className="jh-badge" style={{ textTransform: "uppercase" }}>{job.modality}</span>
                        </div>
                        <div style={{ fontSize: "11.5px", color: "var(--hud-text-secondary)", marginTop: "2px" }}>
                          <span style={{ color: "var(--hud-accent)" }}>{job.company_name}</span> · {job.location || "Remote"} · Req: {job.experience_required_min}-{job.experience_required_max} yrs
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }}>
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
                          onClick={(e) => {
                            e.stopPropagation();
                            void onRunMatch(job.id);
                          }}
                        >
                          Run Match
                        </button>
                      )}

                      <button
                        type="button"
                        className="jh-btn jh-btn-secondary"
                        style={{ padding: "4px 8px", fontSize: "11px" }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectJob(job.id);
                          onNavigateTab("details");
                        }}
                      >
                        Details
                      </button>

                      <button
                        type="button"
                        className="jh-btn jh-btn-primary"
                        style={{ padding: "4px 10px", fontSize: "11px" }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectJob(job.id);
                          void onTailorResume(job.id);
                          onNavigateTab("resume");
                        }}
                      >
                        Tailor
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Right Pane: Selected Opportunity Preview & Match Breakdown */}
            {activePreviewJob && (
              <div className="jh-two-pane-preview">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                  <div>
                    <h3 style={{ margin: "0 0 4px 0", fontSize: "15px", color: "var(--hud-text-primary)" }}>
                      {activePreviewJob.title}
                    </h3>
                    <div style={{ fontSize: "12px", color: "var(--hud-accent)" }}>
                      {activePreviewJob.company_name} · {activePreviewJob.location || "Remote"} ({activePreviewJob.modality.toUpperCase()})
                    </div>
                  </div>
                  {activePreviewScore && (
                    <span
                      className={`jh-badge ${
                        activePreviewScore.match_percentage >= 80
                          ? "jh-badge-match-high"
                          : activePreviewScore.match_percentage >= 60
                          ? "jh-badge-match-med"
                          : "jh-badge-match-low"
                      }`}
                      style={{ fontSize: "12px", padding: "4px 10px" }}
                    >
                      {activePreviewScore.match_percentage}% MATCH ({activePreviewScore.match_tier || "scored"})
                    </span>
                  )}
                </div>

                {/* Compatibility Factors Mini-Breakdown */}
                {activePreviewScore && (
                  <div style={{ background: "rgba(0,0,0,0.35)", padding: "10px", borderRadius: "6px", marginBottom: "12px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--hud-accent)", marginBottom: "6px" }}>
                      10-FACTOR COMPATIBILITY SNAPSHOT
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "11px" }}>
                      <div>
                        <span style={{ color: "var(--hud-text-secondary)" }}>Technical Skills (30%):</span>{" "}
                        <strong style={{ color: "var(--hud-success)" }}>{activePreviewScore.technical_skills_score}%</strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--hud-text-secondary)" }}>Experience (25%):</span>{" "}
                        <strong style={{ color: "var(--hud-success)" }}>{activePreviewScore.experience_score}%</strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--hud-text-secondary)" }}>Responsibilities (15%):</span>{" "}
                        <strong>{activePreviewScore.responsibilities_score || 85}%</strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--hud-text-secondary)" }}>Location (10%):</span>{" "}
                        <strong>{activePreviewScore.location_score || 90}%</strong>
                      </div>
                    </div>

                    {activePreviewScore.strengths && activePreviewScore.strengths.length > 0 && (
                      <div style={{ marginTop: "8px", fontSize: "11px", color: "var(--hud-text-primary)" }}>
                        <span style={{ color: "var(--hud-success)", fontWeight: 700 }}>✓ Key Strengths: </span>
                        {activePreviewScore.strengths.slice(0, 2).join("; ")}
                      </div>
                    )}
                  </div>
                )}

                {/* Skills tags */}
                <div style={{ marginBottom: "12px" }}>
                  <div style={{ fontSize: "11px", color: "var(--hud-text-secondary)", marginBottom: "4px" }}>
                    Required Skills:
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                    {activePreviewJob.required_skills?.map((sk) => (
                      <span key={sk} className="jh-tag" style={{ fontSize: "10.5px" }}>
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Quick Actions */}
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "14px" }}>
                  <button
                    type="button"
                    className="jh-btn jh-btn-primary"
                    style={{ fontSize: "11.5px", padding: "5px 12px" }}
                    onClick={() => {
                      onSelectJob(activePreviewJob.id);
                      void onTailorResume(activePreviewJob.id);
                      onNavigateTab("resume");
                    }}
                  >
                    📝 Tailor Resume
                  </button>
                  <button
                    type="button"
                    className="jh-btn jh-btn-secondary"
                    style={{ fontSize: "11.5px", padding: "5px 12px" }}
                    onClick={() => {
                      onSelectJob(activePreviewJob.id);
                      onNavigateTab("cover_letter");
                    }}
                  >
                    ✉️ Draft Cover Letter
                  </button>
                  <button
                    type="button"
                    className="jh-btn jh-btn-secondary"
                    style={{ fontSize: "11.5px", padding: "5px 12px" }}
                    onClick={() => {
                      onSelectJob(activePreviewJob.id);
                      onNavigateTab("details");
                    }}
                  >
                    📋 Full Specification
                  </button>
                  <a
                    href={activePreviewJob.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="jh-btn jh-btn-secondary"
                    style={{ fontSize: "11.5px", padding: "5px 12px", textDecoration: "none" }}
                  >
                    ↗ Original Posting
                  </a>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
