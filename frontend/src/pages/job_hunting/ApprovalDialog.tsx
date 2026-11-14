import { useState } from "react";
import type { ApplicationApproval } from "../../types/jobHunting";

interface ApprovalDialogProps {
  approval: ApplicationApproval;
  onDecision: (approvalId: string, approved: boolean, confirmationText?: string) => Promise<void>;
  onClose: () => void;
}

export function ApprovalDialog({ approval, onDecision, onClose }: ApprovalDialogProps) {
  const [confirmationText, setConfirmationText] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleAction(approved: boolean) {
    setBusy(true);
    try {
      await onDecision(approval.id, approved, confirmationText.trim() || undefined);
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="jh-dialog-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="jh-dialog-box" role="dialog" aria-modal="true" aria-label="Explicit Approval Confirmation">
        <header className="jh-dialog-header">
          <span>▸ EXPLICIT USER APPROVAL REQUIRED</span>
          <button
            type="button"
            className="jh-btn jh-btn-secondary"
            style={{ padding: "2px 8px", fontSize: "14px" }}
            onClick={onClose}
          >
            ×
          </button>
        </header>
        <div className="jh-dialog-body">
          <p style={{ marginTop: 0 }}>
            ALEX requires your explicit consent before executing external application activity:
          </p>
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "10px", borderRadius: "4px", marginBottom: "12px", fontFamily: "var(--hud-font-mono)", fontSize: "12px" }}>
            <div>
              <strong>ACTION STATUS:</strong>{" "}
              <span style={{ color: "var(--hud-accent)" }}>
                {approval.requested_action === "submit_application"
                  ? "Ready to submit (Requires your review)"
                  : approval.requested_action.replace(/_/g, " ").toUpperCase()}
              </span>
            </div>
            <div style={{ marginTop: "4px", fontSize: "11px", color: "var(--hud-text-secondary)" }}>
              All documents have been tailored and verified against facts. No external submission occurs without your direct sign-off.
            </div>
            <div style={{ marginTop: "4px" }}><strong>APPLICATION ID:</strong> {approval.application_id}</div>
            <div style={{ marginTop: "4px" }}><strong>CHANNEL:</strong> {approval.approval_channel}</div>
          </div>
          <label style={{ display: "block", marginBottom: "6px", fontFamily: "var(--hud-font-mono)", fontSize: "11px", color: "var(--hud-text-secondary)" }}>
            CONFIRMATION NOTES (OPTIONAL):
          </label>
          <input
            type="text"
            className="jh-input"
            style={{ width: "100%", boxSizing: "border-box" }}
            placeholder="e.g. Approved by user after reviewing tailored PDF"
            value={confirmationText}
            onChange={(e) => setConfirmationText(e.target.value)}
          />
        </div>
        <footer className="jh-dialog-actions">
          <button
            type="button"
            className="jh-btn jh-btn-danger"
            disabled={busy}
            onClick={() => void handleAction(false)}
          >
            Reject / Abort
          </button>
          <button
            type="button"
            className="jh-btn jh-btn-primary"
            disabled={busy}
            onClick={() => void handleAction(true)}
          >
            {busy ? "Processing..." : "Explicitly Approve Action"}
          </button>
        </footer>
      </div>
    </div>
  );
}

