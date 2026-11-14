import { useState } from "react";
import { jobHuntingApi } from "../../services/jobHuntingApi";

interface PrivacyViewProps {
  onNotifySuccess: (msg: string) => void;
  onNotifyError: (msg: string) => void;
  onDataPurged?: () => void;
}

export function PrivacyView({ onNotifySuccess, onNotifyError, onDataPurged }: PrivacyViewProps) {
  const [exporting, setExporting] = useState(false);
  const [purging, setPurging] = useState(false);
  const [showConfirmPurge, setShowConfirmPurge] = useState(false);

  const handleExportData = async () => {
    setExporting(true);
    try {
      const data = await jobHuntingApi.exportCareerData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `alex-career-radar-backup-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      onNotifySuccess("Full career archive exported successfully.");
    } catch (err: any) {
      onNotifyError(`Export failed: ${err.message || "Unknown error"}`);
    } finally {
      setExporting(false);
    }
  };

  const handlePurgeData = async () => {
    setPurging(true);
    try {
      await jobHuntingApi.purgeCareerData();
      setShowConfirmPurge(false);
      onNotifySuccess("All local career records have been purged from SQLite.");
      if (onDataPurged) {
        onDataPurged();
      }
    } catch (err: any) {
      onNotifyError(`Purge failed: ${err.message || "Unknown error"}`);
    } finally {
      setPurging(false);
    }
  };

  return (
    <div className="privacy-view hud-panel-page" style={{ padding: "24px", maxWidth: "1000px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "28px" }}>
        <div
          style={{
            fontSize: "11px",
            fontFamily: "var(--hud-font-mono, monospace)",
            color: "var(--hud-accent-cyan, #00f0ff)",
            letterSpacing: "1px",
            textTransform: "uppercase",
          }}
        >
          PRIVACY & LOCAL-FIRST GOVERNANCE PROTOCOL
        </div>
        <h1
          style={{
            fontSize: "24px",
            fontWeight: 700,
            color: "var(--hud-text-primary, #ffffff)",
            margin: "6px 0 10px",
          }}
        >
          Data Storage, Security & AI Transparency
        </h1>
        <p
          style={{
            fontSize: "13px",
            color: "var(--hud-text-secondary, #94a3b8)",
            lineHeight: 1.6,
            maxWidth: "760px",
            margin: 0,
          }}
        >
          ALEX operates on an uncompromising <strong>Local App · Cloud Voice</strong> architecture. You retain 100%
          ownership of your resume, job history, and personal credentials.
        </p>
      </div>

      {/* Local vs Cloud Comparison Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "20px",
          marginBottom: "32px",
        }}
      >
        {/* Local Storage Card */}
        <div
          style={{
            background: "rgba(15, 23, 42, 0.6)",
            border: "1px solid rgba(14, 165, 233, 0.3)",
            borderRadius: "10px",
            padding: "20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
            <span style={{ fontSize: "20px" }}>💻</span>
            <div>
              <h3 style={{ margin: 0, fontSize: "15px", color: "var(--hud-accent-cyan, #38bdf8)" }}>
                Stored Strictly Locally
              </h3>
              <span style={{ fontSize: "11px", color: "#64748b" }}>Your machine only (SQLite & local disk)</span>
            </div>
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: "18px",
              fontSize: "12px",
              color: "var(--hud-text-secondary, #cbd5e1)",
              lineHeight: 1.7,
            }}
          >
            <li>
              <strong>Candidate Profile:</strong> Full name, verified skills, work history, and contact details stored
              in SQLite database.
            </li>
            <li>
              <strong>Resume Documents:</strong> Master resume files and generated tailored cover letters/diffs remain
              on your local filesystem.
            </li>
            <li>
              <strong>Job Pipeline:</strong> All discovered opportunities, match scores, application tracker states, and
              interview notes.
            </li>
            <li>
              <strong>Zero Telemetry:</strong> No tracking cookies, no background recruitment data sales, and no cloud
              syncing without consent.
            </li>
          </ul>
        </div>

        {/* Cloud AI Card */}
        <div
          style={{
            background: "rgba(15, 23, 42, 0.6)",
            border: "1px solid rgba(168, 85, 247, 0.3)",
            borderRadius: "10px",
            padding: "20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
            <span style={{ fontSize: "20px" }}>☁️</span>
            <div>
              <h3 style={{ margin: 0, fontSize: "15px", color: "#c084fc" }}>Cloud Voice & Model Execution</h3>
              <span style={{ fontSize: "11px", color: "#64748b" }}>Google Gemini Live API</span>
            </div>
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: "18px",
              fontSize: "12px",
              color: "var(--hud-text-secondary, #cbd5e1)",
              lineHeight: 1.7,
            }}
          >
            <li>
              <strong>Bidirectional Audio:</strong> Real-time microphone audio is streamed securely via WebSocket to
              Gemini Live only when the mic is active.
            </li>
            <li>
              <strong>On-Demand Tailoring:</strong> Job descriptions and profile snippets are sent to Gemini when you
              explicitly request tailoring or match breakdown.
            </li>
            <li>
              <strong>Zero Model Training:</strong> Under Google Cloud API enterprise terms, customer inputs and audio
              are not used to train Gemini base models.
            </li>
            <li>
              <strong>Instant Interrupt:</strong> ALEX terminates audio capture immediately when the mic is toggled off
              or the session is ended.
            </li>
          </ul>
        </div>
      </div>

      {/* Data Governance & Actions */}
      <div
        style={{
          background: "rgba(15, 23, 42, 0.8)",
          border: "1px solid var(--hud-border-cyan, #334155)",
          borderRadius: "10px",
          padding: "22px",
          marginBottom: "28px",
        }}
      >
        <div
          style={{
            fontSize: "12px",
            fontFamily: "var(--hud-font-mono, monospace)",
            color: "var(--hud-text-primary, #ffffff)",
            fontWeight: 700,
            marginBottom: "12px",
          }}
        >
          DATA PORTABILITY & RIGHT TO ERASURE
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", alignItems: "start" }}>
          <div>
            <h4 style={{ margin: "0 0 6px", fontSize: "13px", color: "var(--hud-text-primary, #f8fafc)" }}>
              Export All Career Records
            </h4>
            <p style={{ margin: "0 0 12px", fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
              Download a complete JSON snapshot of your entire database: candidate profile, discovered jobs, 10-factor
              scores, and application pipeline.
            </p>
            <button
              type="button"
              onClick={handleExportData}
              disabled={exporting}
              aria-label="Download Full JSON Archive"
              style={{
                background: "rgba(14, 165, 233, 0.2)",
                border: "1px solid var(--hud-border-cyan, #0ea5e9)",
                color: "var(--hud-accent-cyan, #38bdf8)",
                borderRadius: "6px",
                padding: "8px 18px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: exporting ? "not-allowed" : "pointer",
              }}
            >
              {exporting ? "Generating Archive..." : "Download Full JSON Archive 📥"}
            </button>
          </div>

          <div>
            <h4 style={{ margin: "0 0 6px", fontSize: "13px", color: "var(--hud-destructive, #ef4444)" }}>
              Purge Local Database (Delete All Data)
            </h4>
            <p style={{ margin: "0 0 12px", fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
              Irreversibly delete all discovered opportunities, match analyses, application history, and reset your
              candidate profile.
            </p>
            <button
              type="button"
              onClick={() => setShowConfirmPurge(true)}
              aria-label="Purge all career data"
              style={{
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid #ef4444",
                color: "#fca5a5",
                borderRadius: "6px",
                padding: "8px 18px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Purge All Career Records 🗑️
            </button>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmPurge && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="purge-dialog-title"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(3, 7, 18, 0.85)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10000,
            padding: "16px",
          }}
        >
          <div
            style={{
              maxWidth: "480px",
              width: "100%",
              background: "#0f172a",
              border: "1px solid #ef4444",
              borderRadius: "10px",
              padding: "24px",
              boxShadow: "0 20px 40px rgba(239, 68, 68, 0.2)",
            }}
          >
            <div style={{ fontSize: "28px", marginBottom: "12px" }}>⚠️</div>
            <h3 id="purge-dialog-title" style={{ margin: "0 0 8px", fontSize: "16px", color: "#f8fafc" }}>
              Confirm Complete Data Erasure
            </h3>
            <p style={{ margin: "0 0 20px", fontSize: "13px", color: "#cbd5e1", lineHeight: 1.5 }}>
              This action cannot be undone. All saved jobs, 10-factor compatibility calculations, interview schedules,
              and application tracking records will be permanently erased from your local SQLite database.
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button
                type="button"
                onClick={() => setShowConfirmPurge(false)}
                disabled={purging}
                style={{
                  background: "transparent",
                  border: "1px solid #334155",
                  color: "#94a3b8",
                  borderRadius: "6px",
                  padding: "8px 16px",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePurgeData}
                disabled={purging}
                style={{
                  background: "#ef4444",
                  border: "none",
                  color: "#ffffff",
                  borderRadius: "6px",
                  padding: "8px 18px",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: purging ? "not-allowed" : "pointer",
                }}
              >
                {purging ? "Purging Records..." : "Yes, Permanently Purge All Data"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
