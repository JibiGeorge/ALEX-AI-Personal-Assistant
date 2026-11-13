import { useEffect, useMemo, useRef, useState } from "react";
import type { ActivityEntry, ActivityKind } from "./ActivityLog";

export interface ActivityDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activity: ActivityEntry[];
  loading?: boolean;
  onClear?: () => void;
}

export function ActivityDrawer({
  isOpen,
  onClose,
  activity,
  loading = false,
  onClear,
}: ActivityDrawerProps) {
  const [filter, setFilter] = useState<"ALL" | ActivityKind>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [isClosing, setIsClosing] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Smooth closing transition handler
  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      setIsClosing(false);
      onClose();
    }, 240);
  };

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        handleClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Filter and search activity entries
  const filteredActivity = useMemo(() => {
    return activity.filter((entry) => {
      if (filter !== "ALL" && entry.kind !== filter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          entry.text.toLowerCase().includes(q) ||
          entry.kind.toLowerCase().includes(q) ||
          entry.time.includes(q)
        );
      }
      return true;
    });
  }, [activity, filter, searchQuery]);

  // Counts by kind
  const counts = useMemo(() => {
    const res: Record<string, number> = { ALL: activity.length, SYS: 0, YOU: 0, ALEX: 0, ERR: 0 };
    for (const item of activity) {
      if (res[item.kind] !== undefined) {
        res[item.kind] += 1;
      }
    }
    return res;
  }, [activity]);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (isOpen && autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [isOpen, filteredActivity.length, autoScroll]);

  const isHidden = !isOpen && !isClosing;

  return (
    <div
      className={`activity-drawer-overlay ${isClosing ? "closing" : ""} ${isHidden ? "activity-drawer-hidden" : ""}`}
      style={isHidden ? { display: "none" } : undefined}
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Activity Logs Drawer"
      aria-hidden={isHidden}
    >
      <aside className={`activity-drawer ${isClosing ? "closing" : ""}`}>
        {/* Holographic Header */}
        <header className="activity-drawer-header">
          <div className="activity-drawer-title-group">
            <div className="activity-drawer-badge">
              <span className="activity-live-pulse-dot" />
              <strong>ALEX // ACTIVITY LOGS</strong>
            </div>
            <span className="activity-drawer-subtitle">
              Live System Telemetry &amp; Event Stream · {activity.length} Total Events
            </span>
          </div>

          <div className="activity-drawer-header-actions">
            {onClear && (
              <button
                type="button"
                className="activity-drawer-clear-btn"
                onClick={onClear}
                title="Clear activity log history"
              >
                CLEAR
              </button>
            )}
            <button
              type="button"
              className="activity-drawer-close-btn"
              onClick={handleClose}
              aria-label="Close activity log"
              title="Close [Esc]"
            >
              ✕
            </button>
          </div>
        </header>

        {/* Toolbar: Filters & Search */}
        <div className="activity-drawer-toolbar">
          <div className="activity-drawer-filter-tabs" role="tablist" aria-label="Filter events by kind">
            {(["ALL", "SYS", "YOU", "ALEX", "ERR"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={filter === tab}
                className={`activity-tab ${filter === tab ? "is-active" : ""}`}
                onClick={() => setFilter(tab)}
              >
                <span className="activity-tab-name">{tab}</span>
                <span className="activity-tab-count">{counts[tab] ?? 0}</span>
              </button>
            ))}
          </div>

          <div className="activity-drawer-search">
            <span className="activity-search-icon" aria-hidden="true">⌕</span>
            <input
              type="text"
              placeholder="Filter logs by keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="activity-search-input"
              aria-label="Filter logs"
            />
            {searchQuery && (
              <button
                type="button"
                className="activity-search-clear"
                onClick={() => setSearchQuery("")}
                aria-label="Clear filter"
              >
                ×
              </button>
            )}
          </div>
        </div>

        {/* Logs List Area */}
        <div
          className="activity-drawer-body"
          ref={logContainerRef}
          role="log"
          aria-live="polite"
        >
          {filteredActivity.length === 0 ? (
            <div className="activity-drawer-empty">
              <span className="activity-empty-radar" aria-hidden="true">◎</span>
              <p>
                {loading
                  ? "Connecting to local systems…"
                  : searchQuery
                  ? `No logs match "${searchQuery}"`
                  : "No events recorded in this category."}
              </p>
            </div>
          ) : (
            <div className="activity-drawer-stream">
              {filteredActivity.map((entry) => (
                <article
                  key={entry.id}
                  className={`activity-stream-item activity-${entry.kind.toLowerCase()}`}
                >
                  <div className="activity-stream-meta">
                    <span className="activity-stream-time">{entry.time}</span>
                    <span className="activity-stream-kind">{entry.kind}</span>
                  </div>
                  <p className="activity-stream-text">{entry.text}</p>
                </article>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="activity-drawer-footer">
          <div className="activity-drawer-footer-status">
            <span className="activity-footer-dot" />
            <span>AUTONOMOUS TELEMETRY STREAM ONLINE</span>
          </div>

          <label className="activity-autoscroll-toggle">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            <span>Auto-scroll</span>
          </label>
        </footer>
      </aside>
    </div>
  );
}
