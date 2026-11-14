import { useState } from "react";
import type { ApplicationStatus, JobApplication, JobListing } from "../../types/jobHunting";

interface ApplicationTrackerViewProps {
  applications: JobApplication[];
  jobs: JobListing[];
  onUpdateStatus: (applicationId: string, status: ApplicationStatus, notes?: string) => Promise<void>;
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
}

const PIPELINE_STATUSES: { key: ApplicationStatus; label: string; color: string }[] = [
  { key: "discovered", label: "Discovered", color: "var(--hud-text-secondary)" },
  { key: "analyzed", label: "Analyzed", color: "var(--hud-cyan)" },
  { key: "tailored", label: "Tailored", color: "var(--hud-teal)" },
  { key: "ready_to_apply", label: "Ready to Apply", color: "var(--hud-warning)" },
  { key: "applied", label: "Applied", color: "var(--hud-accent)" },
  { key: "interviewing", label: "Interviewing", color: "var(--hud-success)" },
  { key: "offered", label: "Offered", color: "#a855f7" },
  { key: "rejected", label: "Rejected", color: "var(--hud-error)" },
];

export function ApplicationTrackerView({
  applications,
  jobs,
  onUpdateStatus,
  onSelectJob,
  onNavigateTab,
}: ApplicationTrackerViewProps) {
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>("all");
  const [editingAppId, setEditingAppId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState<ApplicationStatus>("applied");
  const [editNotes, setEditNotes] = useState("");
  const [updating, setUpdating] = useState(false);

  const jobMap = new Map<string, JobListing>();
  jobs.forEach((j) => jobMap.set(j.id, j));

  const filtered = applications.filter((app) => {
    if (selectedStatusFilter === "all") return true;
    return app.status === selectedStatusFilter;
  });

  function startEdit(app: JobApplication) {
    setEditingAppId(app.id);
    setEditStatus(app.status);
    setEditNotes(app.notes || "");
  }

  async function handleSaveStatus(appId: string) {
    setUpdating(true);
    try {
      await onUpdateStatus(appId, editStatus, editNotes);
      setEditingAppId(null);
    } finally {
      setUpdating(false);
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>📊</span> APPLICATION LIFECYCLE TRACKER</h2>
          <p>End-to-end pipeline tracking from initial discovery to formal offer reception.</p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <select
            className="jh-input"
            value={selectedStatusFilter}
            onChange={(e) => setSelectedStatusFilter(e.target.value)}
            style={{ width: "auto", fontSize: "0.85rem", padding: "0.3rem 0.6rem" }}
          >
            <option value="all">All Statuses ({applications.length})</option>
            {PIPELINE_STATUSES.map((s) => (
              <option key={s.key} value={s.key}>
                {s.label} ({applications.filter((a) => a.status === s.key).length})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Pipeline Summary Bar */}
      <div className="jh-card" style={{ marginBottom: "1.25rem", padding: "0.75rem 1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem", overflowX: "auto" }}>
          {PIPELINE_STATUSES.map((stage) => {
            const count = applications.filter((a) => a.status === stage.key).length;
            const isSelected = selectedStatusFilter === stage.key;
            return (
              <div
                key={stage.key}
                onClick={() => setSelectedStatusFilter(isSelected ? "all" : stage.key)}
                style={{
                  flex: "1 1 0",
                  minWidth: "90px",
                  padding: "0.5rem",
                  background: isSelected ? "rgba(0, 217, 255, 0.1)" : "rgba(0, 0, 0, 0.2)",
                  border: `1px solid ${isSelected ? "var(--hud-accent)" : "rgba(255, 255, 255, 0.05)"}`,
                  borderRadius: "4px",
                  textAlign: "center",
                  cursor: "pointer",
                }}
              >
                <div style={{ fontSize: "1.1rem", fontWeight: "bold", color: stage.color }}>{count}</div>
                <div style={{ fontSize: "0.7rem", color: "var(--hud-text-secondary)", textTransform: "uppercase" }}>
                  {stage.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Applications List */}
      {filtered.length === 0 ? (
        <div className="jh-empty-state">
          <h3>No Applications Found</h3>
          <p>
            {selectedStatusFilter !== "all"
              ? `No applications currently in '${selectedStatusFilter}' state.`
              : "No applications have been tracked yet. Tailor a resume or apply to a job to begin tracking."}
          </p>
        </div>
      ) : (
        <div className="jh-jobs-list">
          {filtered.map((app) => {
            const job = jobMap.get(app.job_id);
            const isEditing = editingAppId === app.id;

            return (
              <div key={app.id} className="jh-card" style={{ marginBottom: "1rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
                      <span className={`jh-badge jh-badge-${app.status}`}>
                        {app.status.replace(/_/g, " ").toUpperCase()}
                      </span>
                      {job && (
                        <span className="jh-badge jh-badge-source">
                          {job.source.replace("_", " ")}
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: "1.1rem", fontWeight: "600", color: "var(--hud-text)" }}>
                      {job ? `${job.title} @ ${job.company_name}` : `Job ID: ${app.job_id}`}
                    </div>

                    <div style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)", marginTop: "0.25rem" }}>
                      Created: {new Date(app.created_at).toLocaleDateString()}
                      {app.applied_at && (
                        <span> • Applied: {new Date(app.applied_at).toLocaleDateString()}</span>
                      )}
                      {app.submission_method && (
                        <span> • Method: {app.submission_method}</span>
                      )}
                      {app.compensation_offered && (
                        <span style={{ color: "var(--hud-success)" }}>
                          {" "}• Offer: ${app.compensation_offered.toLocaleString()}
                        </span>
                      )}
                    </div>

                    {app.notes && !isEditing && (
                      <div
                        style={{
                          marginTop: "0.5rem",
                          fontSize: "0.8rem",
                          color: "var(--hud-text)",
                          background: "rgba(0, 0, 0, 0.25)",
                          padding: "0.4rem 0.6rem",
                          borderRadius: "4px",
                        }}
                      >
                        <strong>Notes:</strong> {app.notes}
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    {job && (
                      <button
                        type="button"
                        className="jh-btn jh-btn-secondary"
                        onClick={() => {
                          onSelectJob(job.id);
                          onNavigateTab("resume");
                        }}
                      >
                        Resume Studio
                      </button>
                    )}

                    {app.status === "interviewing" && (
                      <button
                        type="button"
                        className="jh-btn jh-btn-primary"
                        onClick={() => onNavigateTab("interview")}
                      >
                        Rounds ({app.interview_rounds.length})
                      </button>
                    )}

                    <button
                      type="button"
                      className="jh-btn jh-btn-secondary"
                      onClick={() => (isEditing ? setEditingAppId(null) : startEdit(app))}
                    >
                      {isEditing ? "Cancel" : "Update Status"}
                    </button>
                  </div>
                </div>

                {/* Edit inline drawer */}
                {isEditing && (
                  <div
                    style={{
                      marginTop: "1rem",
                      padding: "0.75rem",
                      background: "rgba(0, 0, 0, 0.35)",
                      borderRadius: "4px",
                      border: "1px solid var(--hud-border)",
                    }}
                  >
                    <div style={{ display: "grid", gridTemplateColumns: "200px 1fr auto", gap: "0.75rem", alignItems: "center" }}>
                      <div>
                        <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                          New Status:
                        </label>
                        <select
                          className="jh-input"
                          value={editStatus}
                          onChange={(e) => setEditStatus(e.target.value as ApplicationStatus)}
                        >
                          {PIPELINE_STATUSES.map((s) => (
                            <option key={s.key} value={s.key}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                          Notes / Feedback:
                        </label>
                        <input
                          type="text"
                          className="jh-input"
                          value={editNotes}
                          onChange={(e) => setEditNotes(e.target.value)}
                          placeholder="e.g., Completed screen with engineering director"
                        />
                      </div>

                      <div style={{ paddingTop: "1rem" }}>
                        <button
                          type="button"
                          className="jh-btn jh-btn-primary"
                          disabled={updating}
                          onClick={() => handleSaveStatus(app.id)}
                        >
                          {updating ? "Saving..." : "Save Status"}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

