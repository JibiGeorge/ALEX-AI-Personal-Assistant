import { useEffect, useState } from "react";
import { jobHuntingApi } from "../../services/jobHuntingApi";
import type { CandidateProfile, CareerRecommendations, JobListing, TailoredDocument } from "../../types/jobHunting";

interface ResumeStudioViewProps {
  job: JobListing | null;
  allJobs: JobListing[];
  candidateProfile: CandidateProfile | null;
  onSelectJob: (jobId: string) => void;
  onNavigateTab?: (tab: string) => void;
  onError: (msg: string) => void;
  onProfileUpdated?: (profile: CandidateProfile) => void;
}

export function ResumeStudioView({
  job,
  allJobs,
  candidateProfile,
  onSelectJob,
  onNavigateTab,
  onError,
  onProfileUpdated,
}: ResumeStudioViewProps) {
  const [studioMode, setStudioMode] = useState<"tailor" | "master_analysis">(job ? "tailor" : "master_analysis");

  // Tailored document states
  const [documents, setDocuments] = useState<TailoredDocument[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<TailoredDocument | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [instructions, setInstructions] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Master profile & analysis states
  const [linkedInInput, setLinkedInInput] = useState("");
  const [uploadingResume, setUploadingResume] = useState(false);
  const [careerRecs, setCareerRecs] = useState<CareerRecommendations | null>(null);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [showJobSpecSide, setShowJobSpecSide] = useState(true);

  // Load documents for current job
  useEffect(() => {
    if (!job) {
      setDocuments([]);
      setSelectedDoc(null);
      setEditorContent("");
      return;
    }

    let active = true;
    setLoading(true);

    jobHuntingApi
      .listTailoredDocuments(job.id)
      .then((res) => {
        if (!active) return;
        setDocuments(res.documents || []);
        if (res.documents && res.documents.length > 0) {
          const newest = res.documents[res.documents.length - 1];
          setSelectedDoc(newest);
          setEditorContent(newest.resume_markdown);
        } else {
          setSelectedDoc(null);
          setEditorContent("");
        }
      })
      .catch((err) => {
        if (active) onError(`Failed to fetch documents: ${err.message}`);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [job?.id]);

  // Fetch career recommendations on mount or when switching to master analysis
  useEffect(() => {
    if (studioMode === "master_analysis" && !careerRecs) {
      setLoadingRecs(true);
      jobHuntingApi
        .getCareerRecommendations()
        .then((recs) => setCareerRecs(recs))
        .catch(() => {})
        .finally(() => setLoadingRecs(false));
    }
  }, [studioMode, careerRecs]);

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingResume(true);
    try {
      const text = await file.text();
      const updated = await jobHuntingApi.uploadMasterResume({
        raw_text: text,
        file_name: file.name,
      });
      if (onProfileUpdated) onProfileUpdated(updated);
      const recs = await jobHuntingApi.getCareerRecommendations();
      setCareerRecs(recs);
    } catch (err: any) {
      onError(`Resume upload failed: ${err.message}`);
    } finally {
      setUploadingResume(false);
    }
  }

  async function handleLinkedInImport(e: React.FormEvent) {
    e.preventDefault();
    if (!linkedInInput.trim()) return;
    setUploadingResume(true);
    try {
      const updated = await jobHuntingApi.ingestLinkedInProfile(linkedInInput.trim());
      if (onProfileUpdated) onProfileUpdated(updated);
      setLinkedInInput("");
    } catch (err: any) {
      onError(`LinkedIn import failed: ${err.message}`);
    } finally {
      setUploadingResume(false);
    }
  }

  function handleSelectVersion(docId: string) {
    const doc = documents.find((d) => d.id === docId);
    if (doc) {
      setSelectedDoc(doc);
      setEditorContent(doc.resume_markdown);
    }
  }

  async function handleGenerateNew(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!job) return;
    setGenerating(true);
    try {
      const newDoc = await jobHuntingApi.tailorResume(job.id, instructions.trim() || undefined);
      setDocuments((prev) => [...prev, newDoc]);
      setSelectedDoc(newDoc);
      setEditorContent(newDoc.resume_markdown);
      setInstructions("");
    } catch (err: any) {
      onError(`Generation failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  }

  async function handleSave(asNewVersion: boolean) {
    if (!selectedDoc) return;
    setSaving(true);
    try {
      const updated = await jobHuntingApi.updateTailoredDocument(selectedDoc.id, {
        resume_markdown: editorContent,
        create_new_version: asNewVersion,
      });
      if (asNewVersion) {
        setDocuments((prev) => [...prev, updated]);
        setSelectedDoc(updated);
      } else {
        setDocuments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
        setSelectedDoc(updated);
      }
    } catch (err: any) {
      onError(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="jh-studio-container" data-testid="resume-studio-view">
      {/* Studio Mode Selector */}
      <div className="jh-header" style={{ marginBottom: "1rem" }}>
        <div className="jh-header-titles">
          <h2>
            <span>📝</span> RESUME STUDIO: {job ? job.title.toUpperCase() : "AI CAREER ANALYSIS & TAILORING"}
          </h2>
          <p>
            Extract verified credentials, analyze ATS keywords and career paths, and craft job-specific customized applications.
          </p>
        </div>

        <div className="jh-view-mode-pill-group">
          <button
            type="button"
            className={`jh-btn ${studioMode === "master_analysis" ? "jh-btn-primary" : "jh-btn-secondary"}`}
            style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem" }}
            onClick={() => setStudioMode("master_analysis")}
          >
            📋 Master Profile & Recommendations
          </button>
          <button
            type="button"
            className={`jh-btn ${studioMode === "tailor" ? "jh-btn-primary" : "jh-btn-secondary"}`}
            style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem" }}
            onClick={() => setStudioMode("tailor")}
          >
            🎯 Job Tailoring Studio
          </button>
          <button
            type="button"
            className="jh-btn jh-btn-secondary"
            style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem" }}
            onClick={() => onNavigateTab?.("recommended")}
          >
            Matches 🎯
          </button>
        </div>
      </div>

      {/* MODE 1: MASTER PROFILE & AI CAREER RECOMMENDATIONS */}
      {studioMode === "master_analysis" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.2rem" }}>
          {/* Upload & LinkedIn Importer Card */}
          <div
            className="jh-card"
            style={{
              padding: "1.2rem",
              background: "rgba(2, 11, 18, 0.9)",
              borderColor: "rgba(0, 229, 255, 0.35)",
            }}
          >
            <h3 style={{ margin: "0 0 0.5rem 0", color: "var(--hud-cyan-bright)", fontSize: "1rem" }}>
              📥 INGEST PROFILE & RESUME
            </h3>
            <p style={{ margin: "0 0 1rem 0", fontSize: "0.8rem", color: "var(--hud-text-secondary)" }}>
              Upload your resume (PDF, DOCX, DOC, TXT) or link your LinkedIn profile. The system strictly extracts verified facts without fabrication.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              {/* File Upload */}
              <div
                style={{
                  border: "2px dashed rgba(0, 229, 255, 0.35)",
                  borderRadius: "8px",
                  padding: "1.2rem",
                  textAlign: "center",
                  background: "rgba(0, 229, 255, 0.03)",
                }}
              >
                <div style={{ fontSize: "1.5rem", marginBottom: "0.4rem" }}>📄</div>
                <label
                  className="jh-btn jh-btn-primary"
                  style={{ cursor: "pointer", display: "inline-block", fontSize: "0.8rem", padding: "0.4rem 0.9rem" }}
                >
                  {uploadingResume ? "Ingesting Resume..." : "Upload Resume (PDF/DOCX/TXT)"}
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    onChange={handleFileUpload}
                    style={{ display: "none" }}
                    disabled={uploadingResume}
                  />
                </label>
                <div style={{ marginTop: "0.5rem", fontSize: "0.7rem", color: "var(--hud-text-secondary)" }}>
                  Auto-extracts tech stack, work history, and education
                </div>
              </div>

              {/* LinkedIn Importer */}
              <form
                onSubmit={handleLinkedInImport}
                style={{
                  border: "1px solid rgba(0, 229, 255, 0.25)",
                  borderRadius: "8px",
                  padding: "1.2rem",
                  background: "rgba(2, 15, 24, 0.6)",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                }}
              >
                <label style={{ fontSize: "0.75rem", color: "var(--hud-cyan-bright)", marginBottom: "0.4rem", fontWeight: "bold" }}>
                  🔗 LINKEDIN PROFILE URL
                </label>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    type="url"
                    placeholder="https://linkedin.com/in/username"
                    className="jh-input"
                    value={linkedInInput}
                    onChange={(e) => setLinkedInInput(e.target.value)}
                    style={{ fontSize: "0.8rem", padding: "0.4rem 0.6rem" }}
                  />
                  <button
                    type="submit"
                    className="jh-btn jh-btn-primary"
                    disabled={uploadingResume || !linkedInInput.trim()}
                    style={{ fontSize: "0.75rem", padding: "0.4rem 0.8rem" }}
                  >
                    Import
                  </button>
                </div>
                <div style={{ marginTop: "0.4rem", fontSize: "0.7rem", color: "var(--hud-text-secondary)" }}>
                  Attaches verified public profile handle for recruiter communications
                </div>
              </form>
            </div>
          </div>

          {/* Missing Information Alert Banner */}
          {candidateProfile?.missing_information && candidateProfile.missing_information.length > 0 && (
            <div
              className="jh-card"
              style={{
                borderColor: "rgba(251, 191, 36, 0.6)",
                background: "rgba(251, 191, 36, 0.08)",
                padding: "0.8rem 1rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#fbbf24", fontWeight: "bold", fontSize: "0.85rem" }}>
                <span>⚠️</span> INFORMATION RECOMMENDATION (NON-BLOCKING)
              </div>
              <ul style={{ margin: "4px 0 0 0", paddingLeft: "20px", fontSize: "0.75rem", color: "#fef3c7" }}>
                {candidateProfile.missing_information.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Verified Profile Credentials Overview */}
          {candidateProfile && (
            <div
              className="jh-card"
              style={{
                padding: "1rem",
                background: "rgba(2, 11, 18, 0.85)",
                borderColor: "rgba(0, 229, 255, 0.3)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.8rem" }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#e0f7fa" }}>{candidateProfile.full_name}</h3>
                  <div style={{ fontSize: "0.85rem", color: "var(--hud-cyan-bright)", marginTop: "2px" }}>
                    {candidateProfile.headline}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", marginTop: "2px" }}>
                    📍 {candidateProfile.location} · ⏱️ {candidateProfile.total_years_experience} Yrs Experience ({candidateProfile.seniority_level})
                  </div>
                </div>
                <span className="jh-badge jh-badge-source">
                  {candidateProfile.is_verified ? "✓ VERIFIED BY PARSER" : "SELF-REPORTED"}
                </span>
              </div>

              {/* Skills and Tech Stack Overview */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.8rem" }}>
                <div>
                  <div style={{ fontSize: "0.7rem", color: "var(--hud-text-secondary)", textTransform: "uppercase" }}>Languages</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "3px" }}>
                    {candidateProfile.programming_languages.map((l) => (
                      <span key={l} className="jh-tag" style={{ fontSize: "0.7rem" }}>{l}</span>
                    ))}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: "0.7rem", color: "var(--hud-text-secondary)", textTransform: "uppercase" }}>Frameworks & Libraries</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "3px" }}>
                    {candidateProfile.frameworks.map((f) => (
                      <span key={f} className="jh-tag" style={{ fontSize: "0.7rem" }}>{f}</span>
                    ))}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: "0.7rem", color: "var(--hud-text-secondary)", textTransform: "uppercase" }}>Databases & Cloud</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "3px" }}>
                    {candidateProfile.databases.map((d) => (
                      <span key={d} className="jh-tag" style={{ fontSize: "0.7rem" }}>{d}</span>
                    ))}
                  </div>
                </div>

                {candidateProfile.tools_and_platforms && candidateProfile.tools_and_platforms.length > 0 && (
                  <div>
                    <div style={{ fontSize: "0.7rem", color: "var(--hud-text-secondary)", textTransform: "uppercase" }}>Tools & Platforms</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "3px" }}>
                      {candidateProfile.tools_and_platforms.slice(0, 6).map((t) => (
                        <span key={t} className="jh-tag" style={{ fontSize: "0.7rem" }}>{t}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* AI Career Recommendations & Path Diagnostics */}
          <div
            className="jh-card"
            style={{
              padding: "1.2rem",
              background: "linear-gradient(135deg, rgba(0, 229, 255, 0.08) 0%, rgba(2, 11, 18, 0.95) 100%)",
              borderColor: "rgba(0, 229, 255, 0.45)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.8rem" }}>
              <span style={{ fontSize: "1.2rem" }}>🔮</span>
              <h3 style={{ margin: 0, fontSize: "1rem", color: "var(--hud-cyan-bright)" }}>
                AI CAREER INTELLIGENCE & PATH RECOMMENDATIONS
              </h3>
            </div>

            {loadingRecs && <div className="jh-empty-state">Synthesizing career path telemetry...</div>}

            {careerRecs && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.2rem" }}>
                {/* Strengths & Weaknesses */}
                <div>
                  <strong style={{ fontSize: "0.8rem", color: "#4ade80", textTransform: "uppercase" }}>
                    Verified Strengths
                  </strong>
                  <ul style={{ margin: "4px 0 0.8rem 0", paddingLeft: "18px", fontSize: "0.75rem", color: "#e0f7fa" }}>
                    {careerRecs.strengths.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>

                  <strong style={{ fontSize: "0.8rem", color: "#fbbf24", textTransform: "uppercase" }}>
                    Missing ATS Keywords To Target
                  </strong>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                    {careerRecs.missing_keywords.map((kw, idx) => (
                      <span key={idx} className="jh-tag" style={{ color: "#fbbf24", borderColor: "rgba(251, 191, 36, 0.4)" }}>
                        + {kw}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Recommended Certifications & Career Paths */}
                <div>
                  <strong style={{ fontSize: "0.8rem", color: "var(--hud-cyan-bright)", textTransform: "uppercase" }}>
                    Recommended Certifications
                  </strong>
                  <ul style={{ margin: "4px 0 0.8rem 0", paddingLeft: "18px", fontSize: "0.75rem", color: "#e0f7fa" }}>
                    {careerRecs.recommended_certifications.map((c, idx) => (
                      <li key={idx}>{c}</li>
                    ))}
                  </ul>

                  <strong style={{ fontSize: "0.8rem", color: "#c084fc", textTransform: "uppercase" }}>
                    Suggested Career Paths
                  </strong>
                  <ul style={{ margin: "4px 0 0 0", paddingLeft: "18px", fontSize: "0.75rem", color: "#e0f7fa" }}>
                    {careerRecs.recommended_career_paths.map((p, idx) => (
                      <li key={idx}>{p}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODE 2: JOB-SPECIFIC TAILORING STUDIO */}
      {studioMode === "tailor" && (
        <>
          {/* Target Opportunity Selector & Controls Bar */}
          <div className="jh-card" style={{ marginBottom: "1rem", padding: "0.75rem 1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <label style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)" }}>Target Opportunity:</label>
                <select
                  value={job?.id || ""}
                  onChange={(e) => onSelectJob(e.target.value)}
                  className="jh-input"
                  style={{ width: "auto", minWidth: "240px" }}
                >
                  {allJobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title} @ {j.company_name} ({j.location})
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  className="jh-btn jh-btn-secondary"
                  style={{ fontSize: "0.75rem", padding: "0.35rem 0.65rem" }}
                  onClick={() => setShowJobSpecSide(!showJobSpecSide)}
                  title="Toggle Target Job Requirements Side-Panel"
                >
                  {showJobSpecSide ? "Hide Job Specs" : "Show Job Specs"}
                </button>

                <button
                  type="button"
                  className={`jh-btn ${showDiff ? "jh-btn-primary" : "jh-btn-secondary"}`}
                  style={{ fontSize: "0.75rem", padding: "0.35rem 0.65rem" }}
                  onClick={() => setShowDiff(!showDiff)}
                  title="Toggle Unified Diff vs Base Resume"
                >
                  {showDiff ? "✓ Unified Diff Active" : "Diff vs Base Resume"}
                </button>

                <button
                  type="button"
                  className="jh-btn jh-btn-secondary"
                  style={{ fontSize: "0.75rem", padding: "0.35rem 0.65rem" }}
                  onClick={() => onNavigateTab?.("cover_letter")}
                  title="Draft targeted cover letter for this job"
                >
                  ✉️ Draft Cover Letter →
                </button>
              </div>

              {documents.length > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <label style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)" }}>Version:</label>
                  <select
                    value={selectedDoc?.id || ""}
                    onChange={(e) => handleSelectVersion(e.target.value)}
                    className="jh-input"
                    style={{ width: "auto" }}
                  >
                    {documents.map((d) => (
                      <option key={d.id} value={d.id}>
                        v{d.version_number} ({new Date(d.created_at).toLocaleDateString()})
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="jh-btn jh-btn-secondary"
                    onClick={() => handleSave(false)}
                    disabled={saving}
                  >
                    {saving ? "Saving..." : "Save Draft"}
                  </button>
                  <button
                    type="button"
                    className="jh-btn jh-btn-primary"
                    onClick={() => handleSave(true)}
                  >
                    Save as v{(documents.length > 0 ? Math.max(...documents.map((d) => d.version_number)) : 0) + 1}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Unified Diff View (if toggled) */}
          {showDiff && selectedDoc && (
            <div className="jh-card" style={{ marginBottom: "1rem", padding: "14px", border: "1px solid rgba(0, 229, 255, 0.4)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <strong style={{ fontSize: "12px", color: "var(--hud-accent)" }}>
                  UNIFIED DIFF: TAILORED v{selectedDoc.version_number} VS BASE MASTER RESUME
                </strong>
                <button
                  type="button"
                  className="jh-btn jh-btn-secondary"
                  style={{ fontSize: "10.5px", padding: "2px 8px" }}
                  onClick={() => setShowDiff(false)}
                >
                  Close Diff
                </button>
              </div>
              <div
                style={{
                  maxHeight: "220px",
                  overflowY: "auto",
                  fontFamily: "var(--hud-font-mono, monospace)",
                  fontSize: "11px",
                  lineHeight: "1.6",
                  background: "rgba(0,0,0,0.5)",
                  padding: "10px",
                  borderRadius: "4px",
                }}
              >
                {selectedDoc.customizations_summary && selectedDoc.customizations_summary.length > 0 && (
                  <div style={{ marginBottom: "8px", color: "var(--hud-teal)" }}>
                    {selectedDoc.customizations_summary.map((c, i) => (
                      <div key={i}>+ [TAILORED HIGHLIGHT] {c}</div>
                    ))}
                  </div>
                )}
                {editorContent.split("\n").slice(0, 30).map((line, idx) => {
                  const isKeyword = selectedDoc.ats_keywords_included?.some((kw) => line.includes(kw));
                  return (
                    <div
                      key={idx}
                      style={{
                        color: isKeyword ? "var(--hud-success)" : "var(--hud-text-secondary)",
                        background: isKeyword ? "rgba(16, 185, 129, 0.1)" : "transparent",
                      }}
                    >
                      {isKeyword ? `+ ${line}` : `  ${line}`}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Dual / Tri-Pane Editor */}
          {loading ? (
            <div className="jh-empty-state">Loading tailored resume versions...</div>
          ) : documents.length === 0 ? (
            <div className="jh-card" style={{ padding: "2rem", textAlign: "center" }}>
              <h3 style={{ color: "var(--hud-cyan-bright)", marginBottom: "0.5rem" }}>
                No Tailored Resume Generated for this Opportunity Yet
              </h3>
              <p style={{ color: "var(--hud-text-secondary)", maxWidth: "600px", margin: "0 auto 1.5rem" }}>
                ALEX will analyze your verified profile against '{job?.title || "Target Role"}', aligning keywords and highlights strictly without fabrication.
              </p>
              <button
                type="button"
                className="jh-btn jh-btn-primary"
                disabled={generating || !job}
                onClick={handleGenerateNew}
                style={{ minWidth: "220px" }}
              >
                {generating ? "Generating Tailored Resume..." : "Generate Tailored Resume"}
              </button>
            </div>
          ) : (
            <div
              className="jh-dual-pane"
              style={{
                display: "grid",
                gridTemplateColumns: showJobSpecSide ? "300px 1fr 1fr" : "1fr 1fr",
                gap: "12px",
              }}
            >
              {/* Left Column: Target Job Requirements (Side-by-Side Reference) */}
              {showJobSpecSide && job && (
                <div className="jh-pane" style={{ background: "rgba(3, 14, 22, 0.7)" }}>
                  <div className="jh-pane-header">
                    <span>TARGET JOB SPECS</span>
                    <span style={{ fontSize: "0.75rem", color: "var(--hud-accent)" }}>{job.company_name}</span>
                  </div>
                  <div style={{ padding: "12px", overflowY: "auto", maxHeight: "550px", fontSize: "11.5px" }}>
                    <div style={{ fontWeight: 700, color: "var(--hud-text-primary)", marginBottom: "4px" }}>
                      {job.title}
                    </div>
                    <div style={{ color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
                      {job.location || "Remote"} · {job.modality.toUpperCase()} · Req: {job.experience_required_min}-{job.experience_required_max} yrs
                    </div>

                    <strong style={{ display: "block", color: "var(--hud-accent)", marginBottom: "6px" }}>
                      Required Skills:
                    </strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginBottom: "12px" }}>
                      {job.required_skills?.map((sk) => (
                        <span key={sk} className="jh-tag" style={{ fontSize: "10px" }}>
                          {sk}
                        </span>
                      ))}
                    </div>

                    <strong style={{ display: "block", color: "var(--hud-accent)", marginBottom: "6px" }}>
                      Job Summary:
                    </strong>
                    <div
                      style={{
                        whiteSpace: "pre-wrap",
                        color: "var(--hud-text-secondary)",
                        lineHeight: "1.5",
                        fontSize: "11px",
                        background: "rgba(0,0,0,0.25)",
                        padding: "8px",
                        borderRadius: "4px",
                      }}
                    >
                      {(job.cleaned_description || job.raw_description || "").slice(0, 450)}...
                    </div>
                  </div>
                </div>
              )}

              {/* Center Column: ATS Markdown Source */}
              <div className="jh-pane">
                <div className="jh-pane-header">
                  <span>ATS MARKDOWN SOURCE (v{selectedDoc?.version_number})</span>
                  <span style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)" }}>Editable</span>
                </div>
                <textarea
                  className="jh-editor-textarea"
                  value={editorContent}
                  onChange={(e) => setEditorContent(e.target.value)}
                  placeholder="Resume markdown content..."
                  spellCheck={false}
                />
              </div>

              {/* Right Column: Live HUD Preview */}
              <div className="jh-pane">
                <div className="jh-pane-header">
                  <span>LIVE HUD PREVIEW</span>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    {selectedDoc && (
                      <>
                        <a
                          href={`/api/job-hunting/tailored/${selectedDoc.id}/export?type=resume&format=docx`}
                          className="jh-btn jh-btn-secondary"
                          style={{ fontSize: "0.7rem", padding: "0.2rem 0.5rem", textDecoration: "none" }}
                          download
                        >
                          Download DOCX
                        </a>
                        <a
                          href={`/api/job-hunting/tailored/${selectedDoc.id}/export?type=resume&format=pdf`}
                          className="jh-btn jh-btn-secondary"
                          style={{ fontSize: "0.7rem", padding: "0.2rem 0.5rem", textDecoration: "none" }}
                          download
                        >
                          Download PDF
                        </a>
                      </>
                    )}
                    <span style={{ fontSize: "0.75rem", color: "var(--hud-cyan-bright)" }}>Export Ready</span>
                  </div>
                </div>
                <div className="jh-preview-container">
                  <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: "0.82rem", color: "#e0f7fa" }}>
                    {editorContent}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
