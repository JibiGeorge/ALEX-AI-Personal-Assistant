import { useState } from "react";
import type { CompatibilityScore, JobListing } from "../../types/jobHunting";

interface JobDetailsViewProps {
  job: JobListing | null;
  score: CompatibilityScore | null;
  allJobs: JobListing[];
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
  onRunMatch: (jobId: string) => Promise<void>;
  onTailorResume: (jobId: string) => Promise<void>;
}

export function JobDetailsView({
  job,
  score,
  allJobs,
  onSelectJob,
  onNavigateTab,
  onRunMatch,
  onTailorResume,
}: JobDetailsViewProps) {
  const [matching, setMatching] = useState(false);
  const [tailoring, setTailoring] = useState(false);

  if (!job) {
    return (
      <div>
        <div className="jh-header">
          <div className="jh-header-titles">
            <h2><span>📋</span> JOB SPECIFICATION & ATTRIBUTION</h2>
            <p>Select an opportunity from discovery or recommendations to inspect full job parameters.</p>
          </div>
        </div>

        <div className="jh-empty-state">
          <h3>No Job Currently Selected</h3>
          <p>Please select a job from the list below or from the Discovery / Recommended tabs.</p>

          {allJobs.length > 0 && (
            <div style={{ marginTop: "1.5rem", maxWidth: "600px", margin: "1.5rem auto 0" }}>
              <select
                className="jh-input"
                onChange={(e) => {
                  if (e.target.value) onSelectJob(e.target.value);
                }}
                defaultValue=""
              >
                <option value="" disabled>
                  -- Select a Discovered Job ({allJobs.length} available) --
                </option>
                {allJobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title} @ {j.company_name} ({j.source})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>
    );
  }

  async function handleMatch() {
    if (!job) return;
    setMatching(true);
    try {
      await onRunMatch(job.id);
    } finally {
      setMatching(false);
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
      {/* Header with Switcher */}
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>📋</span> {job.title.toUpperCase()}</h2>
          <p>
            {job.company_name} • {job.location || "Remote"} • {job.modality.toUpperCase()}
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
        </div>
      </div>

      {/* Primary Overview Card */}
      <div className="jh-card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
              <span className="jh-badge jh-badge-source">{job.source.replace("_", " ")}</span>
              <span className={`jh-badge jh-badge-${job.status}`}>{job.status.replace("_", " ")}</span>
              {job.is_expired && (
                <span className="jh-badge jh-badge-low">EXPIRED LISTING</span>
              )}
              {score && (
                <span
                  className={`jh-badge ${
                    score.match_percentage >= 80 ? "jh-badge-high" : "jh-badge-med"
                  }`}
                >
                  {score.match_percentage}% MATCH
                </span>
              )}
            </div>

            <div style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)", lineHeight: "1.6" }}>
              <strong>Experience Required:</strong> {job.experience_required_min} - {job.experience_required_max} years
              <br />
              <strong>Compensation:</strong>{" "}
              {job.salary_min || job.salary_max
                ? `${job.salary_currency || "$"}${job.salary_min?.toLocaleString() || "N/A"} - ${job.salary_currency || "$"}${job.salary_max?.toLocaleString() || "N/A"}`
                : "Not disclosed in posting"}
              <br />
              <strong>Discovered At:</strong> {new Date(job.discovered_at).toLocaleString()}
              {job.posted_at && <span> • <strong>Posted:</strong> {new Date(job.posted_at).toLocaleDateString()}</span>}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", minWidth: "220px" }}>
            <a
              href={job.source_url}
              target="_blank"
              rel="noreferrer"
              className="jh-btn jh-btn-secondary"
              style={{ textAlign: "center", textDecoration: "none" }}
            >
              Open Original Posting ↗
            </a>
            <button
              type="button"
              className="jh-btn jh-btn-secondary"
              disabled={matching}
              onClick={handleMatch}
            >
              {matching ? "Analyzing..." : score ? "Re-Run Match Analysis" : "Run AI Match Analysis"}
            </button>
            <button
              type="button"
              className="jh-btn jh-btn-primary"
              disabled={tailoring}
              onClick={handleTailor}
            >
              {tailoring ? "Generating Package..." : "Tailor Resume & Letter"}
            </button>
          </div>
        </div>
      </div>

      {/* Grid: Requirements and Skills */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "1.5rem" }}>
        {/* Required Skills */}
        <div className="jh-card">
          <div className="jh-card-header">
            <h4>REQUIRED SKILLS & QUALIFICATIONS ({job.required_skills.length})</h4>
          </div>
          <div className="jh-job-tags">
            {job.required_skills.length > 0 ? (
              job.required_skills.map((skill) => (
                <span
                  key={skill}
                  className="jh-tag"
                  style={{
                    color: score?.skills_matched.includes(skill)
                      ? "var(--hud-success)"
                      : score?.skills_missing.includes(skill)
                      ? "var(--hud-warning)"
                      : "inherit",
                  }}
                >
                  {score?.skills_matched.includes(skill) ? "✓ " : ""}
                  {skill}
                </span>
              ))
            ) : (
              <span style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)" }}>
                No explicit required skills extracted.
              </span>
            )}
          </div>
        </div>

        {/* Preferred Skills & Benefits */}
        <div className="jh-card">
          <div className="jh-card-header">
            <h4>PREFERRED SKILLS & BENEFITS</h4>
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", marginBottom: "0.4rem" }}>
              Preferred Skills:
            </div>
            <div className="jh-job-tags">
              {job.preferred_skills.length > 0 ? (
                job.preferred_skills.map((skill) => (
                  <span key={skill} className="jh-tag">
                    {skill}
                  </span>
                ))
              ) : (
                <span style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)" }}>None listed</span>
              )}
            </div>
          </div>

          <div>
            <div style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", marginBottom: "0.4rem" }}>
              Perks & Benefits:
            </div>
            <div className="jh-job-tags">
              {job.benefits.length > 0 ? (
                job.benefits.map((b) => (
                  <span key={b} className="jh-tag" style={{ borderColor: "rgba(0, 217, 255, 0.2)" }}>
                    ★ {b}
                  </span>
                ))
              ) : (
                <span style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)" }}>Standard package</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Description Content */}
      <div className="jh-card">
        <div className="jh-card-header">
          <h4>VERIFIED JOB DESCRIPTION</h4>
          <span style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)" }}>
            Source: {job.source_url}
          </span>
        </div>
        <div
          style={{
            maxHeight: "380px",
            overflowY: "auto",
            fontSize: "0.85rem",
            lineHeight: "1.7",
            color: "var(--hud-text)",
            whiteSpace: "pre-wrap",
            padding: "0.75rem",
            background: "rgba(0, 0, 0, 0.3)",
            borderRadius: "4px",
            border: "1px solid var(--hud-border)",
            fontFamily: "var(--font-mono, monospace)",
          }}
        >
          {job.cleaned_description || job.raw_description || "No description text provided."}
        </div>
      </div>
    </div>
  );
}

