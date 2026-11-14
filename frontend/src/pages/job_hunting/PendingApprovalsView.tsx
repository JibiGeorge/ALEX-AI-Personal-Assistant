import { useState } from "react";
import type { ApplicationApproval, JobApplication, JobListing } from "../../types/jobHunting";

interface PendingApprovalsViewProps {
  approvals: ApplicationApproval[];
  applications: JobApplication[];
  jobs: JobListing[];
  onOpenApprovalDialog: (approval: ApplicationApproval) => void;
  onNavigateTab: (tab: string) => void;
  onSelectJob: (jobId: string) => void;
}

export function PendingApprovalsView({
  approvals,
  applications,
  jobs,
  onOpenApprovalDialog,
  onNavigateTab,
  onSelectJob,
}: PendingApprovalsViewProps) {
  const [filter, setFilter] = useState<"pending" | "decided" | "all">("pending");

  const appMap = new Map<string, JobApplication>();
  applications.forEach((a) => appMap.set(a.id, a));

  const jobMap = new Map<string, JobListing>();
  jobs.forEach((j) => jobMap.set(j.id, j));

  const filteredApprovals = approvals.filter((appr) => {
    if (filter === "pending") return appr.approval_status === "pending";
    if (filter === "decided") return appr.approval_status !== "pending";
    return true;
  });

  return (
    <div>
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>🛡️</span> EXPLICIT HUMAN APPROVAL QUEUE</h2>
          <p>
            Zero autonomous submissions. Every application submission requires your direct, explicit confirmation.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            type="button"
            className={`jh-btn ${filter === "pending" ? "jh-btn-primary" : "jh-btn-secondary"}`}
            onClick={() => setFilter("pending")}
          >
            Pending ({approvals.filter((a) => a.approval_status === "pending").length})
          </button>
          <button
            type="button"
            className={`jh-btn ${filter === "decided" ? "jh-btn-primary" : "jh-btn-secondary"}`}
            onClick={() => setFilter("decided")}
          >
            History ({approvals.filter((a) => a.approval_status !== "pending").length})
          </button>
          <button
            type="button"
            className={`jh-btn ${filter === "all" ? "jh-btn-primary" : "jh-btn-secondary"}`}
            onClick={() => setFilter("all")}
          >
            All
          </button>
        </div>
      </div>

      {filteredApprovals.length === 0 ? (
        <div className="jh-empty-state">
          <h3>No {filter === "pending" ? "Pending" : ""} Approvals Found</h3>
          <p>
            {filter === "pending"
              ? "All actions have been approved or rejected. When ALEX prepares an application for submission, it will appear here for your explicit authorization."
              : "No approvals in the selected filter."}
          </p>
        </div>
      ) : (
        <div className="jh-jobs-list">
          {filteredApprovals.map((approval) => {
            const application = appMap.get(approval.application_id);
            const job = application ? jobMap.get(application.job_id) : undefined;

            const isPending = approval.approval_status === "pending";
            const isApproved = approval.approval_status === "approved";

            return (
              <div key={approval.id} className="jh-card" style={{ marginBottom: "1rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
                      <span
                        className={`jh-badge ${
                          isPending
                            ? "jh-badge-med"
                            : isApproved
                            ? "jh-badge-high"
                            : "jh-badge-low"
                        }`}
                      >
                        {isPending
                          ? "Requires your review"
                          : isApproved
                          ? approval.decided_at
                            ? `Submitted on ${new Date(approval.decided_at).toLocaleDateString()}`
                            : "Ready to submit"
                          : "Action aborted"}
                      </span>
                      <span className="jh-badge jh-badge-source">
                        {approval.requested_action === "submit_application"
                          ? "Ready to submit"
                          : approval.requested_action.replace(/_/g, " ").toUpperCase()}
                      </span>
                    </div>

                    <div style={{ fontSize: "1.05rem", fontWeight: "600", color: "var(--hud-text)" }}>
                      {job ? `${job.title} @ ${job.company_name}` : `Application ID: ${approval.application_id}`}
                    </div>

                    <div style={{ fontSize: "0.85rem", color: "var(--hud-text-secondary)", marginTop: "0.25rem" }}>
                      Requested: {new Date(approval.created_at).toLocaleString()} via{" "}
                      <span style={{ color: "var(--hud-accent)" }}>{approval.approval_channel}</span>
                      {approval.decided_at && (
                        <span> • Decided: {new Date(approval.decided_at).toLocaleString()}</span>
                      )}
                    </div>

                    {approval.user_confirmation_text && (
                      <div
                        style={{
                          marginTop: "0.5rem",
                          fontSize: "0.8rem",
                          color: "var(--hud-text)",
                          background: "rgba(0, 0, 0, 0.3)",
                          padding: "0.4rem 0.6rem",
                          borderRadius: "4px",
                          borderLeft: "2px solid var(--hud-success)",
                        }}
                      >
                        User Confirmation: "{approval.user_confirmation_text}"
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
                        Inspect Resume
                      </button>
                    )}

                    {isPending ? (
                      <button
                        type="button"
                        className="jh-btn jh-btn-primary"
                        onClick={() => onOpenApprovalDialog(approval)}
                      >
                        Review & Decide ⚡
                      </button>
                    ) : (
                      <span style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)" }}>
                        Completed
                      </span>
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

