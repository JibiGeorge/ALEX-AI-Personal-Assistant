import { useEffect, useState } from "react";
import { jobHuntingApi } from "../../services/jobHuntingApi";
import type { CandidateProfile, JobListing, TailoredDocument } from "../../types/jobHunting";

interface ResumeStudioViewProps {
  job: JobListing | null;
  allJobs: JobListing[];
  candidateProfile: CandidateProfile | null;
  onSelectJob: (jobId: string) => void;
  onNavigateTab?: (tab: string) => void;
  onError: (msg: string) => void;
}

export function ResumeStudioView({
  job,
  allJobs,
  candidateProfile,
  onSelectJob,
  onError,
}: ResumeStudioViewProps) {
  const [documents, setDocuments] = useState<TailoredDocument[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<TailoredDocument | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [instructions, setInstructions] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showOriginalModal, setShowOriginalModal] = useState(false);

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
          // Select newest version by default
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
        setEditorContent(updated.resume_markdown);
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

  if (!job) {
    return (
      <div>
        <div className="jh-header">
          <div className="jh-header-titles">
            <h2><span>📝</span> ALEX RESUME STUDIO</h2>
            <p>Targeted ATS resume customization grounded strictly in verified candidate history.</p>
          </div>
        </div>

        <div className="jh-empty-state">
          <h3>No Target Job Selected</h3>
          <p>Select a job posting to prepare or review customized ATS resumes.</p>
          {allJobs.length > 0 && (
            <div style={{ marginTop: "1rem", maxWidth: "500px", margin: "1rem auto 0" }}>
              <select
                className="jh-input"
                onChange={(e) => {
                  if (e.target.value) onSelectJob(e.target.value);
                }}
                defaultValue=""
              >
                <option value="" disabled>-- Select a Job --</option>
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

  return (
    <div>
      {/* Header & Controls */}
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>📝</span> RESUME STUDIO: {job.title.toUpperCase()}</h2>
          <p>
            {job.company_name} • {job.modality.toUpperCase()} • Grounded ATS Resume Customization
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
            onClick={() => setShowOriginalModal(true)}
          >
            Original Master Resume 👁
          </button>
        </div>
      </div>

      {/* Top Metadata Bar: Version Selector & Downloads */}
      <div className="jh-card" style={{ marginBottom: "1rem", padding: "0.75rem 1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)" }}>Version:</span>
            {documents.length > 0 ? (
              <select
                className="jh-input"
                value={selectedDoc?.id || ""}
                onChange={(e) => handleSelectVersion(e.target.value)}
                style={{ width: "auto", padding: "0.25rem 0.5rem" }}
              >
                {documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    v{d.version_number} ({new Date(d.created_at).toLocaleDateString()} {new Date(d.created_at).toLocaleTimeString()})
                  </option>
                ))}
              </select>
            ) : (
              <span style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)" }}>
                No versions generated yet
              </span>
            )}

            {selectedDoc && (
              <span className="jh-tag" style={{ color: "var(--hud-success)" }}>
                ✓ Original Resume Preserved
              </span>
            )}
          </div>

          {selectedDoc && (
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <a
                href={jobHuntingApi.getDownloadUrl(selectedDoc.id, "docx", "resume")}
                download={`Resume_${job.company_name.replace(/\s+/g, "_")}_v${selectedDoc.version_number}.docx`}
                className="jh-btn jh-btn-secondary"
                style={{ textDecoration: "none", fontSize: "0.8rem" }}
              >
                Download DOCX
              </a>
              <a
                href={jobHuntingApi.getDownloadUrl(selectedDoc.id, "pdf", "resume")}
                download={`Resume_${job.company_name.replace(/\s+/g, "_")}_v${selectedDoc.version_number}.pdf`}
                className="jh-btn jh-btn-secondary"
                style={{ textDecoration: "none", fontSize: "0.8rem" }}
              >
                Download PDF
              </a>
              <button
                type="button"
                className="jh-btn jh-btn-secondary"
                disabled={saving}
                onClick={() => handleSave(false)}
              >
                Save
              </button>
              <button
                type="button"
                className="jh-btn jh-btn-primary"
                disabled={saving}
                onClick={() => handleSave(true)}
              >
                Save as v{(documents.length > 0 ? Math.max(...documents.map((d) => d.version_number)) : 0) + 1}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Relevant Skills and ATS Keywords Identified */}
      {selectedDoc && (
        <div className="jh-card" style={{ marginBottom: "1rem", padding: "0.75rem 1rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", marginBottom: "0.25rem" }}>
                Relevant Technical Skills Highlighted:
              </div>
              <div className="jh-job-tags">
                {selectedDoc.relevant_skills_identified?.slice(0, 8).map((sk) => (
                  <span key={sk} className="jh-tag" style={{ color: "var(--hud-cyan)" }}>
                    {sk}
                  </span>
                )) || <span style={{ fontSize: "0.8rem" }}>Standard skills alignment</span>}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", marginBottom: "0.25rem" }}>
                ATS Keywords Integrated:
              </div>
              <div className="jh-job-tags">
                {selectedDoc.ats_keywords_included?.slice(0, 8).map((kw) => (
                  <span key={kw} className="jh-tag" style={{ color: "var(--hud-teal)" }}>
                    {kw}
                  </span>
                )) || <span style={{ fontSize: "0.8rem" }}>Role keywords</span>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Studio View: Dual Pane (Editor & Live Preview) or Generation Prompt */}
      {loading ? (
        <div className="jh-empty-state">Loading tailored resume versions...</div>
      ) : documents.length === 0 ? (
        <div className="jh-card" style={{ padding: "2rem", textAlign: "center" }}>
          <h3 style={{ color: "var(--hud-cyan)", marginBottom: "0.5rem" }}>
            No Tailored Resume Generated for this Opportunity Yet
          </h3>
          <p style={{ color: "var(--hud-text-secondary)", maxWidth: "600px", margin: "0 auto 1.5rem" }}>
            ALEX will review your master profile against this job description, highlighting relevant project achievements,
            languages, and frameworks without fabricating any experience.
          </p>

          <div style={{ maxWidth: "550px", margin: "0 auto", textAlign: "left" }}>
            <label style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.35rem" }}>
              Custom Instructions (Optional):
            </label>
            <input
              type="text"
              className="jh-input"
              placeholder="e.g., Emphasize React 19 architecture and Next.js full-stack capabilities"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              style={{ marginBottom: "1rem" }}
            />
            <div style={{ textAlign: "center" }}>
              <button
                type="button"
                className="jh-btn jh-btn-primary"
                disabled={generating}
                onClick={handleGenerateNew}
                style={{ minWidth: "220px" }}
              >
                {generating ? "Generating Tailored Resume..." : "Generate Tailored Resume"}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="jh-dual-pane">
          {/* Left Pane: Markdown Source Editor */}
          <div className="jh-pane">
            <div className="jh-pane-header">
              <span>ATS MARKDOWN SOURCE (v{selectedDoc?.version_number})</span>
              <span style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)" }}>
                Editable text
              </span>
            </div>
            <textarea
              className="jh-editor-textarea"
              value={editorContent}
              onChange={(e) => setEditorContent(e.target.value)}
              placeholder="Resume markdown content..."
              spellCheck={false}
            />
          </div>

          {/* Right Pane: Live Document HUD Preview */}
          <div className="jh-pane">
            <div className="jh-pane-header">
              <span>LIVE HUD PREVIEW</span>
              <span style={{ fontSize: "0.75rem", color: "var(--hud-success)" }}>
                Formatted Display
              </span>
            </div>
            <div className="jh-preview-container">
              <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", margin: 0 }}>
                {editorContent}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Modal for viewing original unchanged resume */}
      {showOriginalModal && (
        <div className="jh-dialog-overlay" onClick={() => setShowOriginalModal(false)}>
          <div
            className="jh-dialog"
            style={{ maxWidth: "750px", width: "95%" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="jh-dialog-title" style={{ display: "flex", justifyContent: "space-between" }}>
              <span>MASTER RESUME (READ-ONLY REFERENCE)</span>
              <button
                type="button"
                className="jh-btn jh-btn-secondary"
                style={{ padding: "0.1rem 0.5rem" }}
                onClick={() => setShowOriginalModal(false)}
              >
                ✕
              </button>
            </div>

            <div style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)", marginBottom: "1rem" }}>
              This is your immutable master resume ground truth. Tailored versions are created independently without modifying this document.
            </div>

            <div
              style={{
                maxHeight: "450px",
                overflowY: "auto",
                background: "rgba(0, 0, 0, 0.4)",
                padding: "1rem",
                borderRadius: "4px",
                fontSize: "0.85rem",
                lineHeight: "1.6",
                whiteSpace: "pre-wrap",
                border: "1px solid var(--hud-border)",
              }}
            >
              {candidateProfile?.raw_resume_text || "No raw resume text stored in candidate profile."}
            </div>

            <div style={{ marginTop: "1rem", textAlign: "right" }}>
              <button
                type="button"
                className="jh-btn jh-btn-primary"
                onClick={() => setShowOriginalModal(false)}
              >
                Close Reference
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
