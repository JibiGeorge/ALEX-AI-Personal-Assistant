import { useState } from "react";
import type { JobApplication, JobListing } from "../../types/jobHunting";

interface InterviewTrackerViewProps {
  applications: JobApplication[];
  jobs: JobListing[];
  onRecordInterview: (
    applicationId: string,
    roundName: string,
    scheduledAt: string,
    interviewer?: string,
    feedback?: string,
  ) => Promise<void>;
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
  onError: (msg: string) => void;
}

export function InterviewTrackerView({
  applications,
  jobs,
  onRecordInterview,
  onSelectJob,
  onNavigateTab,
  onError,
}: InterviewTrackerViewProps) {
  const [selectedAppId, setSelectedAppId] = useState<string>("");
  const [roundName, setRoundName] = useState("Technical Screen");
  const [scheduledAt, setScheduledAt] = useState("");
  const [interviewer, setInterviewer] = useState("");
  const [feedback, setFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [prepChecklist, setPrepChecklist] = useState<Record<string, boolean>>({
    tech_stack: true,
    system_design: false,
    star_stories: false,
    interviewer_questions: false,
  });

  const jobMap = new Map<string, JobListing>();
  jobs.forEach((j) => jobMap.set(j.id, j));

  // Extract all interview rounds across all applications
  const allRounds: {
    round: {
      round_name: string;
      scheduled_at: string;
      interviewer?: string | null;
      feedback?: string | null;
      passed?: boolean | null;
    };
    application: JobApplication;
    job?: JobListing;
  }[] = [];

  applications.forEach((app) => {
    const job = jobMap.get(app.job_id);
    (app.interview_rounds || []).forEach((r) => {
      allRounds.push({ round: r, application: app, job });
    });
  });

  // Sort by scheduled_at desc
  allRounds.sort((a, b) => new Date(b.round.scheduled_at).getTime() - new Date(a.round.scheduled_at).getTime());

  function exportToIcs(title: string, company: string, scheduledAtStr: string, roundType: string, interviewerName?: string | null) {
    try {
      const startDate = new Date(scheduledAtStr);
      const endDate = new Date(startDate.getTime() + 60 * 60 * 1000);
      const formatDate = (d: Date) => d.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";

      const icsLines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ALEX AI//Job Hunting Radar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        `SUMMARY:Interview: ${title} @ ${company} (${roundType})`,
        `DESCRIPTION:Round: ${roundType}\\nCompany: ${company}\\nInterviewer: ${interviewerName || "Engineering Team"}\\nTracked via ALEX Career Radar`,
        `DTSTART:${formatDate(startDate)}`,
        `DTEND:${formatDate(endDate)}`,
        `STATUS:CONFIRMED`,
        "END:VEVENT",
        "END:VCALENDAR",
      ];

      const blob = new Blob([icsLines.join("\r\n")], { type: "text/calendar;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `interview_${company.replace(/\s+/g, "_")}.ics`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      onError(`Failed to export calendar invitation: ${err.message}`);
    }
  }

  async function handleAddRound(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedAppId) {
      onError("Please select a target application.");
      return;
    }
    if (!scheduledAt) {
      onError("Please provide scheduled date and time.");
      return;
    }

    setSubmitting(true);
    try {
      await onRecordInterview(
        selectedAppId,
        roundName,
        scheduledAt,
        interviewer.trim() || undefined,
        feedback.trim() || undefined,
      );
      setShowAddForm(false);
      setInterviewer("");
      setFeedback("");
      setScheduledAt("");
    } catch (err: any) {
      onError(`Failed to record interview round: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>🗓️</span> TECHNICAL & SYSTEM INTERVIEW TRACKER</h2>
          <p>
            Track technical screens, architecture rounds, and debrief feedback across all company pipelines.
          </p>
        </div>

        <div>
          <button
            type="button"
            className="jh-btn jh-btn-primary"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            {showAddForm ? "Cancel" : "+ Schedule Interview Round"}
          </button>
        </div>
      </div>

      {/* Interview Prep Checklist Banner */}
      <div className="jh-card" style={{ marginBottom: "1.25rem", padding: "14px 16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <strong style={{ fontSize: "12px", color: "var(--hud-accent)", letterSpacing: "0.5px" }}>
            📋 UPCOMING INTERVIEW PREP CHECKLIST
          </strong>
          <span style={{ fontSize: "11px", color: "var(--hud-text-secondary)" }}>
            Autonomous Preparation Assistance
          </span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "8px", fontSize: "11.5px" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", color: "var(--hud-text-primary)" }}>
            <input
              type="checkbox"
              checked={prepChecklist.tech_stack}
              onChange={(e) => setPrepChecklist((p) => ({ ...p, tech_stack: e.target.checked }))}
            />
            Review Target Tech Stack & Docs
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", color: "var(--hud-text-primary)" }}>
            <input
              type="checkbox"
              checked={prepChecklist.system_design}
              onChange={(e) => setPrepChecklist((p) => ({ ...p, system_design: e.target.checked }))}
            />
            Scalability & Architecture Trade-offs
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", color: "var(--hud-text-primary)" }}>
            <input
              type="checkbox"
              checked={prepChecklist.star_stories}
              onChange={(e) => setPrepChecklist((p) => ({ ...p, star_stories: e.target.checked }))}
            />
            Align 3 STAR Stories with Job Requirements
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", color: "var(--hud-text-primary)" }}>
            <input
              type="checkbox"
              checked={prepChecklist.interviewer_questions}
              onChange={(e) => setPrepChecklist((p) => ({ ...p, interviewer_questions: e.target.checked }))}
            />
            Prepare Questions for Hiring Manager
          </label>
        </div>
      </div>

      {/* Add Interview Form Drawer */}
      {showAddForm && (
        <div className="jh-card" style={{ marginBottom: "1.5rem" }}>
          <div className="jh-card-header">
            <h4>RECORD / SCHEDULE INTERVIEW ROUND</h4>
          </div>
          <form onSubmit={handleAddRound}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.3rem" }}>
                  Target Company / Role *
                </label>
                <select
                  className="jh-input"
                  required
                  value={selectedAppId}
                  onChange={(e) => setSelectedAppId(e.target.value)}
                >
                  <option value="" disabled>-- Select Active Application --</option>
                  {applications.map((app) => {
                    const job = jobMap.get(app.job_id);
                    return (
                      <option key={app.id} value={app.id}>
                        {job ? `${job.company_name} - ${job.title}` : `App: ${app.id}`} ({app.status})
                      </option>
                    );
                  })}
                </select>
              </div>

              <div>
                <label style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.3rem" }}>
                  Round Type *
                </label>
                <select
                  className="jh-input"
                  value={roundName}
                  onChange={(e) => setRoundName(e.target.value)}
                >
                  <option value="Recruiter Screen">Recruiter Screen</option>
                  <option value="Technical Phone Screen">Technical Phone Screen</option>
                  <option value="Live Coding (React / TypeScript)">Live Coding (React / TypeScript)</option>
                  <option value="System Design & Architecture">System Design & Architecture</option>
                  <option value="Hiring Manager & Leadership">Hiring Manager & Leadership</option>
                  <option value="Final Debrief">Final Debrief</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.3rem" }}>
                  Date & Time *
                </label>
                <input
                  type="datetime-local"
                  className="jh-input"
                  required
                  value={scheduledAt}
                  onChange={(e) => setScheduledAt(e.target.value)}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.3rem" }}>
                  Interviewer(s) (Optional)
                </label>
                <input
                  type="text"
                  className="jh-input"
                  placeholder="e.g., Staff Frontend Engineer"
                  value={interviewer}
                  onChange={(e) => setInterviewer(e.target.value)}
                />
              </div>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.3rem" }}>
                Focus Topics & Preparation Notes
              </label>
              <textarea
                className="jh-input"
                rows={2}
                placeholder="e.g., Review concurrent React 19 hooks, state machine design, and offline storage"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <button
                type="button"
                className="jh-btn jh-btn-secondary"
                onClick={() => setShowAddForm(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="jh-btn jh-btn-primary"
                disabled={submitting}
              >
                {submitting ? "Saving Round..." : "Save Interview Round"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Rounds list */}
      {allRounds.length === 0 ? (
        <div className="jh-empty-state">
          <h3>No Interview Rounds Scheduled</h3>
          <p>
            When you receive interview invitations, record rounds here to log dates, interviewers, and debrief notes.
          </p>
        </div>
      ) : (
        <div className="jh-jobs-list">
          {allRounds.map(({ round, application, job }, idx) => {
            const scheduledDate = new Date(round.scheduled_at);
            const isUpcoming = scheduledDate.getTime() > Date.now();

            return (
              <div key={idx} className="jh-card" style={{ marginBottom: "1rem", padding: "14px 16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
                      <span
                        className={`jh-badge ${
                          isUpcoming
                            ? "jh-badge-high"
                            : round.passed === true
                            ? "jh-badge-high"
                            : round.passed === false
                            ? "jh-badge-low"
                            : "jh-badge-med"
                        }`}
                      >
                        {isUpcoming ? "UPCOMING" : round.passed === true ? "PASSED" : round.passed === false ? "NOT PASSED" : "COMPLETED"}
                      </span>
                      <span className="jh-badge jh-badge-source">
                        {round.round_name}
                      </span>
                    </div>

                    <div style={{ fontSize: "1.1rem", fontWeight: "600", color: "var(--hud-text)" }}>
                      {job ? `${job.company_name} — ${job.title}` : `App ID: ${application.id}`}
                    </div>

                    <div style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)", marginTop: "0.25rem" }}>
                      📅 <strong>{scheduledDate.toLocaleString()}</strong>
                      {round.interviewer && <span> • Interviewer: {round.interviewer}</span>}
                    </div>

                    {round.feedback && (
                      <div
                        style={{
                          marginTop: "0.5rem",
                          fontSize: "0.8rem",
                          background: "rgba(0, 0, 0, 0.3)",
                          padding: "0.5rem 0.75rem",
                          borderRadius: "4px",
                          borderLeft: "2px solid var(--hud-teal)",
                        }}
                      >
                        <strong>Debrief / Notes:</strong> {round.feedback}
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <button
                      type="button"
                      className="jh-btn jh-btn-primary"
                      style={{ fontSize: "11px", padding: "4px 10px" }}
                      onClick={() =>
                        exportToIcs(
                          job?.title || "Role",
                          job?.company_name || "Company",
                          round.scheduled_at,
                          round.round_name,
                          round.interviewer,
                        )
                      }
                      title="Export interview event as .ics calendar invitation"
                    >
                      📅 Add to Calendar (.ics)
                    </button>

                    {job && (
                      <button
                        type="button"
                        className="jh-btn jh-btn-secondary"
                        style={{ fontSize: "11px", padding: "4px 10px" }}
                        onClick={() => {
                          onSelectJob(job.id);
                          onNavigateTab("resume");
                        }}
                      >
                        View Resume
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
