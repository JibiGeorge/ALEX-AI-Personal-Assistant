import { useState } from "react";
import type { CompatibilityScore, JobListing } from "../../types/jobHunting";

interface RecommendedViewProps {
  jobs: JobListing[];
  scores: Record<string, CompatibilityScore>;
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
  onRunMatch: (jobId: string) => Promise<void>;
  onTailorResume: (jobId: string) => Promise<void>;
}

export function RecommendedView({
  jobs,
  scores,
  onSelectJob,
  onNavigateTab,
  onRunMatch,
  onTailorResume,
}: RecommendedViewProps) {
  const [minScoreFilter, setMinScoreFilter] = useState(80);
  const [matchingJobId, setMatchingJobId] = useState<string | null>(null);
  const [tailoringJobId, setTailoringJobId] = useState<string | null>(null);

  // Filter jobs that have a calculated score meeting the threshold
  const scoredJobs = jobs
    .map((job) => ({
      job,
      score: scores[job.id],
    }))
    .filter((item) => item.score && item.score.match_percentage >= minScoreFilter)
    .sort((a, b) => (b.score?.match_percentage || 0) - (a.score?.match_percentage || 0));

  async function handleAnalyze(jobId: string) {
    setMatchingJobId(jobId);
    try {
      await onRunMatch(jobId);
    } finally {
      setMatchingJobId(null);
    }
  }

  async function handleTailor(jobId: string) {
    setTailoringJobId(jobId);
    try {
      await onTailorResume(jobId);
      onSelectJob(jobId);
      onNavigateTab("resume");
    } finally {
      setTailoringJobId(null);
    }
  }

  return (
    <div>
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>🎯</span> RECOMMENDED OPPORTUNITIES (HIGH COMPATIBILITY)</h2>
          <p>
            AI-curated roles scoring ≥{minScoreFilter}% across technical skills, experience alignment, and seniority.
          </p>
        </div>
        <div className="jh-filter-group" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)" }}>Threshold:</label>
          <select
            value={minScoreFilter}
            onChange={(e) => setMinScoreFilter(Number(e.target.value))}
            className="jh-input"
            style={{ width: "auto", padding: "0.3rem 0.6rem" }}
          >
            <option value={90}>≥ 90% (Near Perfect)</option>
            <option value={80}>≥ 80% (High Match)</option>
            <option value={70}>≥ 70% (Moderate Match)</option>
            <option value={60}>≥ 60% (All Scored)</option>
          </select>
        </div>
      </div>

      {scoredJobs.length === 0 ? (
        <div className="jh-empty-state">
          <h3>No matching jobs at ≥{minScoreFilter}% threshold</h3>
          <p>
            {Object.keys(scores).length === 0
              ? "Run AI Match Analysis on discovered jobs or lower the filter threshold to see candidates."
              : "Try lowering the score threshold or discover new opportunities that match your verified profile."}
          </p>
          <div style={{ marginTop: "1rem", display: "flex", gap: "0.75rem", justifyContent: "center" }}>
            <button
              type="button"
              className="jh-btn jh-btn-secondary"
              onClick={() => setMinScoreFilter(60)}
            >
              Lower to 60%
            </button>
            <button
              type="button"
              className="jh-btn jh-btn-primary"
              onClick={() => onNavigateTab("discover")}
            >
              Discover New Jobs
            </button>
          </div>
        </div>
      ) : (
        <div className="jh-jobs-list">
          {scoredJobs.map(({ job, score }) => {
            const matchPct = score.match_percentage;
            const badgeClass =
              matchPct >= 90
                ? "jh-badge-high"
                : matchPct >= 75
                ? "jh-badge-med"
                : "jh-badge-low";

            return (
              <div key={job.id} className="jh-job-card">
                <div className="jh-job-header">
                  <div>
                    <div className="jh-job-title">{job.title}</div>
                    <div className="jh-job-company">
                      {job.company_name} • {job.location || "Remote"} •{" "}
                      <span style={{ textTransform: "uppercase" }}>{job.modality}</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span className={`jh-badge ${badgeClass}`}>
                      {matchPct}% MATCH
                    </span>
                    <span className="jh-badge jh-badge-source">
                      {job.source.replace("_", " ")}
                    </span>
                  </div>
                </div>

                {/* Score breakdown chips */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", margin: "0.75rem 0" }}>
                  <div className="jh-tag" style={{ borderLeft: "3px solid var(--hud-accent)" }}>
                    Tech Skills: {score.technical_skills_score}% (30% wt)
                  </div>
                  <div className="jh-tag" style={{ borderLeft: "3px solid var(--hud-teal)" }}>
                    Experience: {score.experience_score}% (20% wt)
                  </div>
                  <div className="jh-tag" style={{ borderLeft: "3px solid var(--hud-teal)" }}>
                    Responsibilities: {score.responsibilities_score}% (20% wt)
                  </div>
                  <div className="jh-tag" style={{ borderLeft: "3px solid var(--hud-accent)" }}>
                    Stack: {score.tech_stack_score}% (15% wt)
                  </div>
                </div>

                {/* Skills tags preview */}
                <div style={{ margin: "0.5rem 0" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", marginBottom: "0.25rem" }}>
                    Matched Skills ({score.skills_matched.length}):
                  </div>
                  <div className="jh-job-tags">
                    {score.skills_matched.slice(0, 8).map((sk) => (
                      <span key={sk} className="jh-tag" style={{ color: "var(--hud-success)", borderColor: "rgba(16, 185, 129, 0.4)" }}>
                        ✓ {sk}
                      </span>
                    ))}
                    {score.skills_missing.length > 0 && (
                      <span className="jh-tag" style={{ color: "var(--hud-warning)", borderColor: "rgba(245, 158, 11, 0.4)" }}>
                        Missing: {score.skills_missing.slice(0, 3).join(", ")}
                      </span>
                    )}
                  </div>
                </div>

                {/* AI Recommendation Summary */}
                {score.ai_recommendation && (
                  <div
                    style={{
                      background: "rgba(0, 217, 255, 0.05)",
                      border: "1px solid rgba(0, 217, 255, 0.2)",
                      borderRadius: "4px",
                      padding: "0.5rem 0.75rem",
                      fontSize: "0.8rem",
                      color: "var(--hud-cyan)",
                      margin: "0.5rem 0",
                    }}
                  >
                    <strong>AI Recommendation:</strong> {score.ai_recommendation}
                  </div>
                )}

                {/* Action buttons */}
                <div className="jh-job-actions">
                  <button
                    type="button"
                    className="jh-btn jh-btn-secondary"
                    onClick={() => {
                      onSelectJob(job.id);
                      onNavigateTab("details");
                    }}
                  >
                    Job Details
                  </button>

                  <button
                    type="button"
                    className="jh-btn jh-btn-secondary"
                    disabled={matchingJobId === job.id}
                    onClick={() => handleAnalyze(job.id)}
                  >
                    {matchingJobId === job.id ? "Analyzing..." : "Re-Calculate"}
                  </button>

                  <button
                    type="button"
                    className="jh-btn jh-btn-secondary"
                    onClick={() => {
                      onSelectJob(job.id);
                      onNavigateTab("analysis");
                    }}
                  >
                    Full Match Analysis
                  </button>

                  <button
                    type="button"
                    className="jh-btn jh-btn-primary"
                    disabled={tailoringJobId === job.id}
                    onClick={() => handleTailor(job.id)}
                  >
                    {tailoringJobId === job.id ? "Preparing Resume..." : "Tailor Resume & Letter"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
