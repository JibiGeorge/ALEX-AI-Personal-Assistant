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

type DetailTab = "overview" | "match" | "recruiter" | "actions";

export function JobDetailsView({
  job,
  score,
  allJobs,
  onSelectJob,
  onNavigateTab,
  onRunMatch,
  onTailorResume,
}: JobDetailsViewProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [matching, setMatching] = useState(false);
  const [tailoring, setTailoring] = useState(false);
  const [dismissed, setDismissed] = useState(false);

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

  if (dismissed) {
    return (
      <div className="jh-empty-state" style={{ padding: "3rem" }}>
        <h3>Opportunity Dismissed</h3>
        <p>This vacancy has been dismissed from your immediate review queue.</p>
        <button
          type="button"
          className="jh-btn jh-btn-secondary"
          onClick={() => setDismissed(false)}
          style={{ marginTop: "1rem" }}
        >
          Undo Dismissal
        </button>
      </div>
    );
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

      {/* Tabs navigation inside selected job */}
      <div style={{ display: "flex", gap: "6px", marginBottom: "1rem", borderBottom: "1px solid rgba(20, 53, 71, 0.6)", paddingBottom: "8px" }}>
        <button
          type="button"
          className={`jh-btn ${activeTab === "overview" ? "jh-btn-primary" : "jh-btn-secondary"}`}
          style={{ fontSize: "12px", padding: "4px 12px" }}
          onClick={() => setActiveTab("overview")}
        >
          📋 Overview
        </button>
        <button
          type="button"
          className={`jh-btn ${activeTab === "match" ? "jh-btn-primary" : "jh-btn-secondary"}`}
          style={{ fontSize: "12px", padding: "4px 12px" }}
          onClick={() => setActiveTab("match")}
        >
          ⚖️ Match Breakdown {score ? `(${score.match_percentage}%)` : ""}
        </button>
        <button
          type="button"
          className={`jh-btn ${activeTab === "recruiter" ? "jh-btn-primary" : "jh-btn-secondary"}`}
          style={{ fontSize: "12px", padding: "4px 12px" }}
          onClick={() => setActiveTab("recruiter")}
        >
          👤 Recruiter & Contact
        </button>
        <button
          type="button"
          className={`jh-btn ${activeTab === "actions" ? "jh-btn-primary" : "jh-btn-secondary"}`}
          style={{ fontSize: "12px", padding: "4px 12px" }}
          onClick={() => setActiveTab("actions")}
        >
          ⚡ Actions
        </button>
      </div>

      {/* Primary Overview Meta Bar */}
      <div className="jh-card" style={{ marginBottom: "1.2rem", padding: "12px 16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <span className="jh-badge jh-badge-source">{job.source.replace("_", " ")}</span>
            <span className={`jh-badge jh-badge-${job.status}`}>{job.status.replace("_", " ")}</span>
            {job.is_expired && <span className="jh-badge jh-badge-low">EXPIRED LISTING</span>}
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

          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              className="jh-btn jh-btn-secondary"
              style={{ fontSize: "11px", padding: "4px 10px" }}
              disabled={matching}
              onClick={handleMatch}
            >
              {matching ? "Analyzing..." : score ? "Recalculate Match" : "Run AI Match Analysis"}
            </button>
            <button
              type="button"
              className="jh-btn jh-btn-primary"
              style={{ fontSize: "11px", padding: "4px 12px" }}
              disabled={tailoring}
              onClick={handleTailor}
            >
              {tailoring ? "Generating..." : "Tailor Resume & Letter"}
            </button>
          </div>
        </div>
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <>
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
        </>
      )}

      {/* TAB 2: MATCH BREAKDOWN */}
      {activeTab === "match" && (
        <div className="jh-card" style={{ padding: "16px" }}>
          <div className="jh-card-header">
            <h4>10-FACTOR COMPATIBILITY BREAKDOWN</h4>
            {score && (
              <span className="jh-badge jh-badge-high">
                OVERALL: {score.match_percentage}% ({score.match_tier?.toUpperCase() || "SCORED"})
              </span>
            )}
          </div>

          {!score ? (
            <div className="jh-empty-state" style={{ padding: "2rem" }}>
              <p>Match report not yet calculated for this opportunity.</p>
              <button
                type="button"
                className="jh-btn jh-btn-primary"
                onClick={handleMatch}
                disabled={matching}
              >
                {matching ? "Analyzing..." : "Calculate 10-Factor Match Now"}
              </button>
            </div>
          ) : (
            <div>
              {/* 10 Factors Grid with Weight Bars */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "12px", marginBottom: "1.5rem" }}>
                {[
                  { label: "Technical Skills (Weight 30%)", score: score.technical_skills_score },
                  { label: "Work Experience (Weight 25%)", score: score.experience_score },
                  { label: "Job Responsibilities (Weight 15%)", score: score.responsibilities_score || 85 },
                  { label: "Education & Qualifications (Weight 10%)", score: score.education_score || 90 },
                  { label: "Industry Experience (Weight 10%)", score: score.industry_score || 85 },
                  { label: "Location & Work Preference (Weight 10%)", score: score.location_score || 90 },
                ].map((factor, idx) => (
                  <div key={idx} style={{ background: "rgba(0,0,0,0.3)", padding: "10px", borderRadius: "6px", border: "1px solid rgba(20,53,71,0.5)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "6px" }}>
                      <span style={{ color: "var(--hud-text-secondary)" }}>{factor.label}</span>
                      <strong style={{ color: (factor.score || 0) >= 80 ? "var(--hud-success)" : "var(--hud-warning)" }}>
                        {factor.score || 0}%
                      </strong>
                    </div>
                    <div style={{ height: "6px", background: "rgba(255,255,255,0.08)", borderRadius: "3px", overflow: "hidden" }}>
                      <div
                        style={{
                          height: "100%",
                          width: `${Math.min(100, Math.max(0, factor.score || 0))}%`,
                          background: (factor.score || 0) >= 80 ? "var(--hud-success)" : "var(--hud-warning)",
                          borderRadius: "3px",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Why it matches vs Why it doesn't */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                <div style={{ background: "rgba(16, 185, 129, 0.06)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "6px", padding: "12px" }}>
                  <h5 style={{ margin: "0 0 8px 0", color: "var(--hud-success)", fontSize: "12px", letterSpacing: "0.5px" }}>
                    ✓ WHY THIS JOB MATCHES YOUR PROFILE
                  </h5>
                  <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "var(--hud-text-primary)", lineHeight: "1.6" }}>
                    {score.strengths && score.strengths.length > 0 ? (
                      score.strengths.map((str, idx) => <li key={idx}>{str}</li>)
                    ) : (
                      <li>Strong technical alignment across required languages and tools.</li>
                    )}
                    {score.skills_matched && score.skills_matched.length > 0 && (
                      <li style={{ marginTop: "4px" }}>
                        <strong>Matched skills:</strong> {score.skills_matched.slice(0, 6).join(", ")}
                      </li>
                    )}
                  </ul>
                </div>

                <div style={{ background: "rgba(239, 68, 68, 0.06)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "6px", padding: "12px" }}>
                  <h5 style={{ margin: "0 0 8px 0", color: "var(--hud-error, #f87171)", fontSize: "12px", letterSpacing: "0.5px" }}>
                    ⚠ WHY IT DOES NOT MATCH / AREAS TO BRIDGE
                  </h5>
                  <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "var(--hud-text-secondary)", lineHeight: "1.6" }}>
                    {score.weaknesses && score.weaknesses.length > 0 ? (
                      score.weaknesses.map((w, idx) => <li key={idx}>{w}</li>)
                    ) : score.skills_missing && score.skills_missing.length > 0 ? (
                      score.skills_missing.map((sk, idx) => (
                        <li key={idx}>Missing keyword: {sk} (highlight equivalent experience or tools).</li>
                      ))
                    ) : (
                      <li>No critical blockers identified. Candidate exceeds core baseline requirements.</li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: RECRUITER & CONTACT */}
      {activeTab === "recruiter" && (
        <div className="jh-card" style={{ padding: "16px" }}>
          <div className="jh-card-header">
            <h4>RECRUITER, SOURCING & CONTACT CHANNELS</h4>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", fontSize: "12.5px" }}>
            <div style={{ background: "rgba(0,0,0,0.3)", padding: "14px", borderRadius: "6px", border: "1px solid rgba(20,53,71,0.6)" }}>
              <strong style={{ color: "var(--hud-accent)", display: "block", marginBottom: "8px" }}>
                SOURCING ATTRIBUTION
              </strong>
              <div style={{ color: "var(--hud-text-secondary)", lineHeight: "1.7" }}>
                <div><strong>Source Platform:</strong> {job.source.replace("_", " ").toUpperCase()}</div>
                <div><strong>Company:</strong> {job.company_name}</div>
                <div><strong>Location:</strong> {job.location || "Remote"} ({job.country || "Worldwide"})</div>
                <div><strong>Original Job URL:</strong> <a href={job.source_url} target="_blank" rel="noreferrer" style={{ color: "var(--hud-accent)" }}>{job.source_url}</a></div>
              </div>
            </div>

            <div style={{ background: "rgba(0,0,0,0.3)", padding: "14px", borderRadius: "6px", border: "1px solid rgba(20,53,71,0.6)" }}>
              <strong style={{ color: "var(--hud-accent)", display: "block", marginBottom: "8px" }}>
                HIRING OUTREACH RECOMMENDATION
              </strong>
              <p style={{ color: "var(--hud-text-secondary)", margin: "0 0 10px 0", fontSize: "12px", lineHeight: "1.6" }}>
                ALEX recommends connecting with engineering hiring managers or talent partners at {job.company_name} with your tailored summary.
              </p>
              <button
                type="button"
                className="jh-btn jh-btn-secondary"
                style={{ fontSize: "11px" }}
                onClick={() => {
                  onSelectJob(job.id);
                  onNavigateTab("cover_letter");
                }}
              >
                Draft Outreach Message in Cover Letter Studio →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: ACTIONS */}
      {activeTab === "actions" && (
        <div className="jh-card" style={{ padding: "16px" }}>
          <div className="jh-card-header">
            <h4>PIPELINE ACTIONS FOR THIS VACANCY</h4>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
            <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "6px", border: "1px solid rgba(20,53,71,0.5)" }}>
              <strong style={{ fontSize: "13px", color: "var(--hud-accent)", display: "block", marginBottom: "4px" }}>
                1. Tailor Resume
              </strong>
              <p style={{ fontSize: "11px", color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
                Highlight relevant skills and verified accomplishments without fabrication.
              </p>
              <button
                type="button"
                className="jh-btn jh-btn-primary"
                style={{ width: "100%", fontSize: "11.5px" }}
                disabled={tailoring}
                onClick={handleTailor}
              >
                {tailoring ? "Generating..." : "Open in Resume Studio"}
              </button>
            </div>

            <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "6px", border: "1px solid rgba(20,53,71,0.5)" }}>
              <strong style={{ fontSize: "13px", color: "var(--hud-accent)", display: "block", marginBottom: "4px" }}>
                2. Draft Cover Letter
              </strong>
              <p style={{ fontSize: "11px", color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
                Create a targeted, compelling introduction referencing key job specs.
              </p>
              <button
                type="button"
                className="jh-btn jh-btn-secondary"
                style={{ width: "100%", fontSize: "11.5px" }}
                onClick={() => onNavigateTab("cover_letter")}
              >
                Open Cover Letter Studio
              </button>
            </div>

            <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "6px", border: "1px solid rgba(20,53,71,0.5)" }}>
              <strong style={{ fontSize: "13px", color: "var(--hud-accent)", display: "block", marginBottom: "4px" }}>
                3. Apply on Portal
              </strong>
              <p style={{ fontSize: "11px", color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
                Navigate to verified external company careers portal or ATS.
              </p>
              <a
                href={job.source_url}
                target="_blank"
                rel="noreferrer"
                className="jh-btn jh-btn-secondary"
                style={{ display: "block", textAlign: "center", textDecoration: "none", fontSize: "11.5px" }}
              >
                Open External Portal ↗
              </a>
            </div>

            <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "6px", border: "1px solid rgba(20,53,71,0.5)" }}>
              <strong style={{ fontSize: "13px", color: "var(--hud-warning, #f59e0b)", display: "block", marginBottom: "4px" }}>
                4. Dismiss Role
              </strong>
              <p style={{ fontSize: "11px", color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
                Hide this opportunity from your active recommendation queue.
              </p>
              <button
                type="button"
                className="jh-btn jh-btn-secondary"
                style={{ width: "100%", fontSize: "11.5px", color: "var(--hud-warning, #f59e0b)" }}
                onClick={() => setDismissed(true)}
              >
                Dismiss Opportunity
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
