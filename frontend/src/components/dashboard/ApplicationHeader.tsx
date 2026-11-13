export interface ApplicationHeaderProps {
  assistantName: string;
  setupMenuOpen: boolean;
  controlsMenuOpen: boolean;
  isSettingsActive: boolean;
  clock: Date;
  onOpenOverview: () => void;
  onToggleSetup: () => void;
  onToggleControls: () => void;
  isRevealed?: boolean;
  activityCount?: number;
  activityOpen?: boolean;
  onToggleActivity?: () => void;
  geminiStatus?: string;
  latestActivity?: {
    kind: string;
    text: string;
    time: string;
  } | null;
}

export function ApplicationHeader({
  assistantName,
  setupMenuOpen,
  controlsMenuOpen,
  isSettingsActive,
  clock,
  onOpenOverview,
  onToggleSetup,
  onToggleControls,
  isRevealed = true,
  activityCount,
  activityOpen = false,
  onToggleActivity,
  geminiStatus,
  latestActivity,
}: ApplicationHeaderProps) {
  return (
    <header
      className={`hud-header reveal-component reveal-header ${
        isRevealed ? "is-revealed" : ""
      }`}
    >
      {/* Brand & Drawer Control Area */}
      <div className="hud-brand-area">
        <button
          aria-label="Home"
          className="hud-brand"
          onClick={onOpenOverview}
          type="button"
        >
          <span className="brand-logo-mark">◈</span>
          <span className="brand-title">ALEX</span>
        </button>

        <button
          aria-label="Setup"
          aria-expanded={setupMenuOpen}
          className={`hud-icon-button ${setupMenuOpen || isSettingsActive ? "selected" : ""}`}
          onClick={onToggleSetup}
          type="button"
          title="Setup — things you set once"
        >
          ⚙
        </button>

        <button
          aria-label="Controls"
          aria-expanded={controlsMenuOpen}
          className={`hud-icon-button ${controlsMenuOpen ? "selected" : ""}`}
          onClick={onToggleControls}
          type="button"
          title="Controls — everyday switches"
        >
          <span className="app-grid-icon" aria-hidden="true">
            🎛
          </span>
        </button>

        {onToggleActivity && (
          <button
            aria-label="Activity Logs"
            aria-expanded={activityOpen}
            className={`hud-icon-button hud-activity-header-btn ${activityOpen ? "selected" : ""}`}
            onClick={onToggleActivity}
            type="button"
            title="Activity Logs — live telemetry & event stream [or say 'open activity log']"
          >
            <span className="app-grid-icon" aria-hidden="true">
              📜
            </span>
            {activityCount !== undefined && activityCount > 0 && (
              <span className="hud-badge-counter">{activityCount > 99 ? "99+" : activityCount}</span>
            )}
          </button>
        )}
      </div>

      {/* Center Operating Status Mode & Current Activity */}
      <div className="hud-title">
        <div className="hud-title-main">
          <strong>{assistantName.toUpperCase()}</strong>
          <span className="hud-title-sub">
            <i className="title-pulse-dot" /> LOCAL COGNITIVE CORE • {geminiStatus ? `GEMINI ${geminiStatus}` : "ALL SYSTEMS NOMINAL"}
          </span>
        </div>
        {latestActivity && (
          <button
            type="button"
            className="hud-activity-ticker-pill"
            onClick={onToggleActivity}
            title="Click to view full Activity Log"
          >
            <span className="ticker-dot" />
            <span className="ticker-kind">{latestActivity.kind}:</span>
            <span className="ticker-text">{latestActivity.text}</span>
          </button>
        )}
      </div>

      {/* Right Digital Clock & Date */}
      <div className="hud-clock" aria-label="Current time">
        <strong>
          {clock.toLocaleTimeString([], { hour12: false })}
        </strong>
        <span>
          {clock.toLocaleDateString("en-GB", {
            weekday: "short",
            day: "2-digit",
            month: "short",
            year: "numeric",
          })}
        </span>
      </div>
    </header>
  );
}

