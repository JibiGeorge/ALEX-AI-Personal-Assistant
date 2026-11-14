import { useEffect, useState } from "react";
import { jobHuntingApi } from "../../services/jobHuntingApi";
import type { CompatibilityScore, JobComparisonResponse, JobListing } from "../../types/jobHunting";

interface JobComparisonViewProps {
  jobs: JobListing[];
  scores: Record<string, CompatibilityScore>;
  selectedJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
}

export function JobComparisonView({
  jobs,
  scores,
  selectedJobId,
  onSelectJob,
  onNavigateTab,
}: JobComparisonViewProps) {
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>(() => {
    if (selectedJobId && jobs.some((j) => j.id === selectedJobId)) {
      const other = jobs.find((j) => j.id !== selectedJobId);
      return other ? [selectedJobId, other.id] : [selectedJobId];
    }
    return jobs.slice(0, 2).map((j) => j.id);
  });

  const [comparisonData, setComparisonData] = useState<JobComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Trigger comparison when selectedJobIds change
  useEffect(() => {
    let active = true;

    async function runComparison() {
      if (selectedJobIds.length === 0) {
        setComparisonData(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const res = await jobHuntingApi.compareJobs(selectedJobIds);
        if (active) {
          setComparisonData(res);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message || "Failed to compare selected opportunities.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    runComparison();

    return () => {
      active = false;
    };
  }, [selectedJobIds]);

  function toggleJobSelection(jobId: string) {
    if (selectedJobIds.includes(jobId)) {
      if (selectedJobIds.length <= 1) return;
      setSelectedJobIds(selectedJobIds.filter((id) => id !== jobId));
    } else {
      if (selectedJobIds.length >= 4) {
        // limit to 4 jobs max for readable side-by-side
        setSelectedJobIds([...selectedJobIds.slice(1), jobId]);
      } else {
        setSelectedJobIds([...selectedJobIds, jobId]);
      }
    }
  }

  if (jobs.length === 0) {
    return (
      <div className="jh-compare-container" data-testid="job-comparison-view">
        <div className="jh-empty-state">
          <h3>No opportunities available to compare</h3>
          <p>Discover or ingest job opportunities to run side-by-side career comparison.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="jh-compare-container" data-testid="job-comparison-view">
      {/* Header */}
      <div className="jh-header" style={{ marginBottom: "1rem" }}>
        <div className="jh-header-titles">
          <h2><span>⚖️</span> MULTI-OPPORTUNITY COMPARISON MATRIX</h2>
          <p>
            Side-by-side architectural comparison of responsibilities, technical stacks, compensation, and career growth potential.
          </p>
        </div>
        <div className="jh-telemetry-badge">
          <span>{selectedJobIds.length} OF 4 SELECTED</span>
        </div>
      </div>

      {/* Job Selection Ribbon */}
      <div
        className="jh-card"
        style={{
          marginBottom: "1.2rem",
          padding: "0.8rem 1rem",
          background: "rgba(2, 11, 18, 0.8)",
          borderColor: "rgba(0, 229, 255, 0.3)",
        }}
      >
        <div style={{ fontSize: "0.8rem", color: "var(--hud-cyan-bright)", marginBottom: "0.6rem", fontWeight: "bold" }}>
          SELECT OPPORTUNITIES TO COMPARE (CHOOSE 2–4):
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {jobs.map((job) => {
            const isSelected = selectedJobIds.includes(job.id);
            const score = scores[job.id]?.match_percentage;
            return (
              <button
                key={job.id}
                type="button"
                className={`jh-btn ${isSelected ? "jh-btn-primary" : "jh-btn-secondary"}`}
                style={{
                  fontSize: "0.75rem",
                  padding: "0.35rem 0.75rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
                onClick={() => toggleJobSelection(job.id)}
              >
                <span>{isSelected ? "✓" : "+"}</span>
                <span>{job.title} ({job.company_name})</span>
                {score !== undefined && (
                  <span
                    style={{
                      background: "rgba(0, 0, 0, 0.4)",
                      padding: "1px 5px",
                      borderRadius: "4px",
                      fontSize: "0.7rem",
                    }}
                  >
                    {score}%
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {loading && (
        <div className="jh-empty-state">
          <h3>Comparing opportunities across 6 dimensions...</h3>
          <p>Generating resume compatibility analysis and AI career recommendation.</p>
        </div>
      )}

      {error && (
        <div className="jh-card" style={{ borderColor: "rgba(255, 82, 82, 0.6)", color: "#ff8a80" }}>
          ⚠️ {error}
        </div>
      )}

      {/* AI Recommendation Banner */}
      {comparisonData && !loading && (
        <div
          className="jh-card"
          style={{
            marginBottom: "1.5rem",
            borderColor: "rgba(0, 229, 255, 0.6)",
            background: "linear-gradient(135deg, rgba(0, 229, 255, 0.12) 0%, rgba(2, 11, 18, 0.95) 100%)",
            boxShadow: "0 0 30px rgba(0, 229, 255, 0.1)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.4rem" }}>
            <span style={{ fontSize: "1.2rem" }}>🎯</span>
            <strong style={{ fontSize: "0.95rem", color: "var(--hud-cyan-bright)", letterSpacing: "0.05em" }}>
              AI CAREER RECOMMENDATION: LEADING FIT — {(comparisonData.best_fit_job_title || "SELECTED ROLE").toUpperCase()} @ {(comparisonData.best_fit_company || "COMPANY").toUpperCase()}
            </strong>
          </div>
          <p style={{ margin: 0, fontSize: "0.85rem", color: "#e0f7fa", lineHeight: 1.5 }}>
            {comparisonData.ai_recommendation_reason}
          </p>
        </div>
      )}

      {/* Side-by-Side Comparison Matrix */}
      {comparisonData && comparisonData.compared_jobs && !loading && (
        <div
          className="jh-compare-matrix"
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${comparisonData.compared_jobs.length}, 1fr)`,
            gap: "1rem",
            alignItems: "stretch",
          }}
        >
          {comparisonData.compared_jobs.map((item) => {
            const isBestFit = item.job_id === comparisonData.best_fit_job_id;
            const originalJob = jobs.find((j) => j.id === item.job_id);

            return (
              <div
                key={item.job_id}
                className="jh-card"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  position: "relative",
                  borderColor: isBestFit ? "var(--hud-cyan-bright)" : "rgba(0, 229, 255, 0.25)",
                  boxShadow: isBestFit ? "0 0 25px rgba(0, 229, 255, 0.2)" : "none",
                  background: isBestFit ? "rgba(3, 20, 32, 0.9)" : "rgba(2, 11, 18, 0.8)",
                }}
              >
                {isBestFit && (
                  <div
                    style={{
                      position: "absolute",
                      top: "-10px",
                      right: "12px",
                      background: "var(--hud-cyan-bright)",
                      color: "#020B10",
                      fontSize: "0.65rem",
                      fontWeight: "bold",
                      padding: "2px 8px",
                      borderRadius: "10px",
                      letterSpacing: "0.08em",
                    }}
                  >
                    ★ TOP FIT
                  </div>
                )}

                {/* Header */}
                <div style={{ borderBottom: "1px solid rgba(0, 229, 255, 0.2)", paddingBottom: "0.75rem", marginBottom: "0.75rem" }}>
                  <h3 style={{ margin: 0, fontSize: "1rem", color: "#e0f7fa" }}>{item.title}</h3>
                  <div style={{ fontSize: "0.8rem", color: "var(--hud-cyan-bright)", marginTop: "2px" }}>
                    {item.company_name}
                  </div>
                  <div style={{ marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span className={`jh-badge ${item.match_percentage >= 80 ? "jh-badge-high" : "jh-badge-med"}`}>
                      {item.match_percentage}% MATCH
                    </span>
                    <span className="jh-badge jh-badge-source" style={{ textTransform: "capitalize" }}>
                      {item.modality}
                    </span>
                  </div>
                </div>

                {/* Core Attributes */}
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", flex: 1 }}>
                  {/* Location & Salary */}
                  <div>
                    <div style={{ fontSize: "0.7rem", color: "var(--hud-text-secondary)", textTransform: "uppercase" }}>Location & Comp</div>
                    <div style={{ fontSize: "0.8rem", color: "#e0f7fa", marginTop: "2px" }}>📍 {item.location}</div>
                    <div style={{ fontSize: "0.8rem", color: "#a7f3d0", marginTop: "2px" }}>💰 {item.salary}</div>
                  </div>

                  {/* Experience */}
                  <div>
                    <div style={{ fontSize: "0.7rem", color: "var(--hud-text-secondary)", textTransform: "uppercase" }}>Experience Request</div>
                    <div style={{ fontSize: "0.8rem", color: "#e0f7fa", marginTop: "2px" }}>⏱️ {item.experience_required}</div>
                  </div>

                  {/* Matching Skills */}
                  <div>
                    <div style={{ fontSize: "0.7rem", color: "#4ade80", textTransform: "uppercase", fontWeight: "bold" }}>
                      Matching Skills ({item.matching_skills.length})
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                      {item.matching_skills.slice(0, 5).map((s) => (
                        <span key={s} className="jh-tag" style={{ fontSize: "0.65rem", padding: "1px 6px", color: "#4ade80", borderColor: "rgba(74, 222, 128, 0.4)" }}>
                          ✓ {s}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Missing Skills */}
                  {item.missing_skills.length > 0 && (
                    <div>
                      <div style={{ fontSize: "0.7rem", color: "#f87171", textTransform: "uppercase", fontWeight: "bold" }}>
                        Skill Gaps ({item.missing_skills.length})
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                        {item.missing_skills.slice(0, 4).map((s) => (
                          <span key={s} className="jh-tag" style={{ fontSize: "0.65rem", padding: "1px 6px", color: "#f87171", borderColor: "rgba(248, 113, 113, 0.4)" }}>
                            ✗ {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Responsibilities */}
                  <div>
                    <div style={{ fontSize: "0.7rem", color: "var(--hud-text-secondary)", textTransform: "uppercase" }}>Key Responsibilities</div>
                    <ul style={{ margin: "4px 0 0 0", paddingLeft: "16px", fontSize: "0.75rem", color: "#cfd8dc", lineHeight: 1.4 }}>
                      {item.responsibilities.slice(0, 3).map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Career Growth */}
                  <div>
                    <div style={{ fontSize: "0.7rem", color: "var(--hud-text-secondary)", textTransform: "uppercase" }}>Growth Potential</div>
                    <p style={{ margin: "3px 0 0 0", fontSize: "0.75rem", color: "#e0f7fa", fontStyle: "italic" }}>
                      {item.growth_potential}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid rgba(0, 229, 255, 0.2)", display: "flex", gap: "0.5rem" }}>
                  <button
                    type="button"
                    className="jh-btn jh-btn-secondary"
                    style={{ flex: 1, fontSize: "0.75rem", padding: "0.35rem 0.5rem" }}
                    onClick={() => {
                      onSelectJob(item.job_id);
                      onNavigateTab("resume");
                    }}
                  >
                    Tailor 📝
                  </button>
                  {originalJob?.source_url && (
                    <a
                      href={originalJob.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="jh-btn jh-btn-primary"
                      style={{ flex: 1, fontSize: "0.75rem", padding: "0.35rem 0.5rem", textDecoration: "none", textAlign: "center" }}
                    >
                      Apply ↗
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
