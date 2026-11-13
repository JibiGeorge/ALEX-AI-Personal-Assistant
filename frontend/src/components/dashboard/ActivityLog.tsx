export type ActivityKind = "SYS" | "YOU" | "ALEX" | "ERR";

export interface ActivityEntry {
  id: string;
  kind: ActivityKind;
  text: string;
  time: string;
}

export interface ActivityLogProps {
  activity: ActivityEntry[];
  loading?: boolean;
  isRevealed?: boolean;
}

export function ActivityLog({
  activity,
  loading = false,
  isRevealed = true,
}: ActivityLogProps) {
  return (
    <div
      className={`activity-section reveal-component reveal-activity ${
        isRevealed ? "is-revealed" : ""
      }`}
    >
      <div className="hud-panel-head">
        <div className="hud-section-label">
          <i className="activity-live-dot" />▸ ACTIVITY LOG{" "}
          <span className="hud-count-tag">
            {activity.length.toString().padStart(2, "0")}
          </span>
        </div>
      </div>

      <div className="activity-log" role="log" aria-live="polite">
        {activity.length === 0 ? (
          <p className="activity-empty">
            {loading ? "Connecting to local systems…" : "No activity recorded."}
          </p>
        ) : (
          activity.map((entry) => (
            <article
              className={`activity-entry activity-${entry.kind.toLowerCase()}`}
              key={entry.id}
            >
              <span className="activity-time">{entry.time}</span>
              <span className="activity-kind">{entry.kind}:</span>
              <p>{entry.text}</p>
            </article>
          ))
        )}
      </div>
    </div>
  );
}

