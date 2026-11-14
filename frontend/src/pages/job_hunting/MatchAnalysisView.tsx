import { useState } from "react";
import type { CompatibilityScore, JobListing } from "../../types/jobHunting";

interface MatchAnalysisViewProps {
  job: JobListing | null;
  score: CompatibilityScore | null;
  allJobs: JobListing[];
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
  onRunMatch: (jobId: string) => Promise<void>;
  onTailorResume: (jobId: string) => Promise<void>;
}

export function MatchAnalysisView({
  job,
  score,
  allJobs,
  onSelectJob,
  onNavigateTab,
  onRunMatch,
  onTailorResume,
}: MatchAnalysisViewProps) {
  const [analyzing, setAnalyzing] = useState(false);
  const [tailoring, setTailoring] = useState(false);

  if (!job) {
    return (
      <div>
        <div className="jh-header">
          <div className="jh-header-titles">
            <h2><span>⚖️</span> AI COMPATIBILITY & MATCH ANALYSIS</h2>
            <p>10-factor multi-dimensional scoring against your verified master profile.</p>
          </div>
        </div>

        <div className="jh-empty-state">
          <h3>No Job Selected for Analysis</h3>
          <p>Please select a discovered job to view its 10-factor compatibility report.</p>
          {allJobs.length > 0 && (
            <div style={{ marginTop: "1rem", maxWidth: "500px", margin: "1rem auto 0" }}>
              <select
                className="jh-input"
                onChange={(e) => {
                  if (e.target.value) onSelectJob(e.target.value);
                }}
                defaultValue=""
              >
                <option value="" disabled>-- Select a Job to Analyze --</option>
                {allJobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title} @ {j.company_name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>
    );
  }

  async function handleRunAnalysis() {
    if (!job) return;
    setAnalyzing(true);
    try {
      await onRunMatch(job.id);
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleTailor() {
    if (!job) return;
    setTailoring(true);
    try {
      await onTailorResume(job.id);
      onNavigateTab("resume");
    } finally {
      setTailoring(false);
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>⚖️</span> 10-FACTOR AI COMPATIBILITY REPORT</h2>
          <p>
            Role: <strong>{job.title}</strong> @ <strong>{job.company_name}</strong>
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <select
            className="jh-input"
            value={job.id}
            onChange={(e) => onSelectJob(e.target.value)}
            style={{ width: "auto", fontSize: "0.8rem", padding: "0.3rem 0.6rem" }}
          >
            {allJobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title} ({j.company_name})
              </option>
            ))}
          </select>
          <button
            type="button"
            className="jh-btn jh-btn-secondary"
            disabled={analyzing}
            onClick={handleRunAnalysis}
          >
            {analyzing ? "Computing Match..." : score ? "Recalculate" : "Run Analysis"}
          </button>
        </div>
      </div>

      {!score ? (
        <div className="jh-empty-state">
          <h3>No Analysis Computed Yet</h3>
          <p>Click "Run Analysis" to calculate the 10-factor weighted compatibility breakdown for this job.</p>
          <button
            type="button"
            className="jh-btn jh-btn-primary"
            style={{ marginTop: "1rem" }}
            disabled={analyzing}
            onClick={handleRunAnalysis}
          >
            {analyzing ? "Computing 10-Factor Match..." : "Compute Match Analysis Now"}
          </button>
        </div>
      ) : (
        <div>
          {/* Top Score Banner & Recommendation */}
          <div className="jh-card" style={{ marginBottom: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
                <div
                  style={{
                    width: "84px",
                    height: "84px",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexDirection: "column",
                    background: "rgba(0, 217, 255, 0.08)",
                    border: `3px solid ${
                      score.match_percentage >= 80
                        ? "var(--hud-success)"
                        : score.match_percentage >= 65
                        ? "var(--hud-accent)"
                        : "var(--hud-warning)"
                    }`,
                    boxShadow: "0 0 15px rgba(0, 217, 255, 0.2)",
                  }}
                >
                  <span style={{ fontSize: "1.5rem", fontWeight: "bold", color: "var(--hud-cyan)" }}>
                    {score.match_percentage}%
                  </span>
                  <span style={{ fontSize: "0.65rem", color: "var(--hud-text-secondary)" }}>
                    MATCH
                  </span>
                </div>

                <div>
                  <div style={{ fontSize: "1.1rem", fontWeight: "600", color: "var(--hud-text)" }}>
                    {score.ai_recommendation || "Compatibility Analysis Complete"}
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)", marginTop: "0.25rem" }}>
                    Action: <span style={{ color: "var(--hud-accent)" }}>{score.recommended_action || "Tailor application"}</span> •
                    Calculated: {new Date(score.calculated_at).toLocaleString()}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: "0.75rem" }}>
                <button
                  type="button"
                  className="jh-btn jh-btn-primary"
                  disabled={tailoring}
                  onClick={handleTailor}
                >
                  {tailoring ? "Tailoring..." : "Tailor Resume for this Role"}
                </button>
              </div>
            </div>

            {score.match_summary && (
              <div
                style={{
                  marginTop: "1rem",
                  padding: "0.75rem",
                  background: "rgba(0, 0, 0, 0.25)",
                  borderLeft: "3px solid var(--hud-accent)",
                  fontSize: "0.85rem",
                  lineHeight: "1.6",
                }}
              >
                {score.match_summary}
              </div>
            )}
          </div>

          {/* 6-Factor Weighted Breakdown Bars */}
          <div className="jh-card" style={{ marginBottom: "1.25rem" }}>
            <div className="jh-card-header">
              <h4>6-FACTOR WEIGHTED SCORING BREAKDOWN</h4>
              <span style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)" }}>
                Formula: Tech (30%) + Exp (20%) + Resp (20%) + Stack (15%) + Loc (10%) + Sen (5%)
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
              {[
                { label: "Technical Skills", score: score.technical_skills_score, weight: "30%" },
                { label: "Years of Experience", score: score.experience_score, weight: "20%" },
                { label: "Responsibilities Fit", score: score.responsibilities_score, weight: "20%" },
                { label: "Technology Stack", score: score.tech_stack_score, weight: "15%" },
                { label: "Location Compatibility", score: score.location_score, weight: "10%" },
                { label: "Seniority Match", score: score.seniority_score, weight: "5%" },
              ].map((factor) => (
                <div key={factor.label} style={{ background: "rgba(0, 0, 0, 0.2)", padding: "0.75rem", borderRadius: "4px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "0.35rem" }}>
                    <span>{factor.label} ({factor.weight})</span>
                    <strong style={{ color: "var(--hud-accent)" }}>{factor.score}%</strong>
                  </div>
                  <div style={{ height: "6px", background: "rgba(255, 255, 255, 0.1)", borderRadius: "3px", overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${Math.min(100, Math.max(0, factor.score))}%`,
                        height: "100%",
                        background:
                          factor.score >= 80
                            ? "var(--hud-success)"
                            : factor.score >= 60
                            ? "var(--hud-accent)"
                            : "var(--hud-warning)",
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Matched vs Missing Skills */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "1.25rem" }}>
            <div className="jh-card">
              <div className="jh-card-header">
                <h4 style={{ color: "var(--hud-success)" }}>
                  ✓ MATCHED SKILLS ({score.skills_matched.length})
                </h4>
              </div>
              <div className="jh-job-tags">
                {score.skills_matched.length > 0 ? (
                  score.skills_matched.map((sk) => (
                    <span
                      key={sk}
                      className="jh-tag"
                      style={{ color: "var(--hud-success)", borderColor: "rgba(16, 185, 129, 0.4)" }}
                    >
                      ✓ {sk}
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)" }}>
                    No exact technical matches identified.
                  </span>
                )}
              </div>
            </div>

            <div className="jh-card">
              <div className="jh-card-header">
                <h4 style={{ color: "var(--hud-warning)" }}>
                  ⚠ MISSING / ADJACENT SKILLS ({score.skills_missing.length})
                </h4>
              </div>
              <div className="jh-job-tags">
                {score.skills_missing.length > 0 ? (
                  score.skills_missing.map((sk) => (
                    <span
                      key={sk}
                      className="jh-tag"
                      style={{ color: "var(--hud-warning)", borderColor: "rgba(245, 158, 11, 0.4)" }}
                    >
                      ! {sk}
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: "0.8rem", color: "var(--hud-success)" }}>
                    All target skills accounted for!
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Strengths & Weaknesses / Gaps */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "1.25rem" }}>
            <div className="jh-card">
              <div className="jh-card-header">
                <h4>IDENTIFIED CANDIDATE STRENGTHS</h4>
              </div>
              <ul style={{ paddingLeft: "1.2rem", margin: 0, fontSize: "0.85rem", lineHeight: "1.6" }}>
                {score.strengths.length > 0 ? (
                  score.strengths.map((str, idx) => <li key={idx}>{str}</li>)
                ) : (
                  <li style={{ color: "var(--hud-text-secondary)" }}>General profile alignment</li>
                )}
              </ul>
            </div>

            <div className="jh-card">
              <div className="jh-card-header">
                <h4>AREAS FOR CAUTION & GAPS</h4>
              </div>
              {score.mandatory_requirements_not_met.length > 0 && (
                <div style={{ marginBottom: "0.5rem", color: "var(--hud-error)", fontSize: "0.85rem" }}>
                  <strong>Mandatory requirements not met:</strong>
                  <ul style={{ paddingLeft: "1.2rem", margin: "0.25rem 0" }}>
                    {score.mandatory_requirements_not_met.map((m, idx) => (
                      <li key={idx}>{m}</li>
                    ))}
                  </ul>
                </div>
              )}
              <ul style={{ paddingLeft: "1.2rem", margin: 0, fontSize: "0.85rem", lineHeight: "1.6" }}>
                {score.experience_gaps.length > 0 ? (
                  score.experience_gaps.map((gap, idx) => <li key={idx}>{gap}</li>)
                ) : score.weaknesses.length > 0 ? (
                  score.weaknesses.map((w, idx) => <li key={idx}>{w}</li>)
                ) : (
                  <li style={{ color: "var(--hud-text-secondary)" }}>No critical gaps detected.</li>
                )}
              </ul>
            </div>
          </div>

          {/* Ground truth policy badge */}
          <div
            style={{
              padding: "0.75rem",
              background: "rgba(0, 175, 200, 0.08)",
              border: "1px dashed var(--hud-teal)",
              borderRadius: "4px",
              fontSize: "0.8rem",
              color: "var(--hud-text-secondary)",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span>🛡️</span>
            <span>
              <strong>Zero-Fabrication Guarantee:</strong> ALEX strictly evaluates real candidate history from your verified master profile. Experience, dates, and technologies are never invented.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

