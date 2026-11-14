import { useEffect, useState } from "react";
import { jobHuntingApi } from "../../services/jobHuntingApi";
import type { JobListing, TailoredDocument } from "../../types/jobHunting";

interface CoverLetterStudioViewProps {
  job: JobListing | null;
  allJobs: JobListing[];
  onSelectJob: (jobId: string) => void;
  onNavigateTab?: (tab: string) => void;
  onError: (msg: string) => void;
}

export function CoverLetterStudioView({
  job,
  allJobs,
  onSelectJob,
  onError,
}: CoverLetterStudioViewProps) {
  const [documents, setDocuments] = useState<TailoredDocument[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<TailoredDocument | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [instructions, setInstructions] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);

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
          setEditorContent(newest.cover_letter_markdown || "");
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
      setEditorContent(doc.cover_letter_markdown || "");
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
      setEditorContent(newDoc.cover_letter_markdown || "");
      setInstructions("");
    } catch (err: any) {
      onError(`Cover letter generation failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  }

  async function handleSave(asNewVersion: boolean) {
    if (!selectedDoc) return;
    setSaving(true);
    try {
      const updated = await jobHuntingApi.updateTailoredDocument(selectedDoc.id, {
        cover_letter_markdown: editorContent,
        create_new_version: asNewVersion,
      });

      if (asNewVersion) {
        setDocuments((prev) => [...prev, updated]);
        setSelectedDoc(updated);
        setEditorContent(updated.cover_letter_markdown || "");
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
            <h2><span>✉️</span> ALEX COVER LETTER STUDIO</h2>
            <p>Personalized, authentic cover letters targeted to company mission and specific engineering roles.</p>
          </div>
        </div>

        <div className="jh-empty-state">
          <h3>No Target Job Selected</h3>
          <p>Select a job posting to prepare or review personalized cover letters.</p>
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
      {/* Header */}
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>✉️</span> COVER LETTER STUDIO: {job.company_name.toUpperCase()}</h2>
          <p>
            Role: <strong>{job.title}</strong> • Addressed to Hiring Team • Zero Fabrication
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

      {/* Top Controls Bar */}
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
                    v{d.version_number} ({new Date(d.created_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
            ) : (
              <span style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)" }}>
                No cover letter version created
              </span>
            )}
          </div>

          {selectedDoc && (
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <a
                href={jobHuntingApi.getDownloadUrl(selectedDoc.id, "docx", "cover_letter")}
                download={`CoverLetter_${job.company_name.replace(/\s+/g, "_")}_v${selectedDoc.version_number}.docx`}
                className="jh-btn jh-btn-secondary"
                style={{ textDecoration: "none", fontSize: "0.8rem" }}
              >
                Download DOCX
              </a>
              <a
                href={jobHuntingApi.getDownloadUrl(selectedDoc.id, "pdf", "cover_letter")}
                download={`CoverLetter_${job.company_name.replace(/\s+/g, "_")}_v${selectedDoc.version_number}.pdf`}
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

      {loading ? (
        <div className="jh-empty-state">Loading cover letter documents...</div>
      ) : documents.length === 0 ? (
        <div className="jh-card" style={{ padding: "2rem", textAlign: "center" }}>
          <h3 style={{ color: "var(--hud-cyan)", marginBottom: "0.5rem" }}>
            No Cover Letter Generated Yet
          </h3>
          <p style={{ color: "var(--hud-text-secondary)", maxWidth: "550px", margin: "0 auto 1.5rem" }}>
            ALEX will craft a personalized cover letter highlighting your engineering strengths, enthusiasm for the
            company mission, and relevant technical capabilities.
          </p>

          <div style={{ maxWidth: "550px", margin: "0 auto", textAlign: "left" }}>
            <label style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.35rem" }}>
              Specific Tone / Highlights (Optional):
            </label>
            <input
              type="text"
              className="jh-input"
              placeholder="e.g., Emphasize passion for distributed systems and clean React code"
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
                {generating ? "Crafting Cover Letter..." : "Generate Cover Letter"}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="jh-dual-pane">
          {/* Left Pane: Markdown Source Editor */}
          <div className="jh-pane">
            <div className="jh-pane-header">
              <span>COVER LETTER MARKDOWN (v{selectedDoc?.version_number})</span>
              <span style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)" }}>
                Editable text
              </span>
            </div>
            <textarea
              className="jh-editor-textarea"
              value={editorContent}
              onChange={(e) => setEditorContent(e.target.value)}
              placeholder="Cover letter markdown content..."
              spellCheck={false}
            />
          </div>

          {/* Right Pane: Live Document Preview */}
          <div className="jh-pane">
            <div className="jh-pane-header">
              <span>PREVIEW</span>
              <span style={{ fontSize: "0.75rem", color: "var(--hud-success)" }}>
                Formatted Document
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
    </div>
  );
}
