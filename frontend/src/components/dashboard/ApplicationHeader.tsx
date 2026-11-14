import type { VoiceState } from "../../types/voice";

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
  voiceActive?: boolean;
  voiceState?: VoiceState;
  systemMonitorOpen?: boolean;
  onToggleSystemMonitor?: () => void;
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
  voiceActive = false,
  voiceState,
  systemMonitorOpen = false,
  onToggleSystemMonitor,
  latestActivity,
}: ApplicationHeaderProps) {
  let voiceStatusText = "READY";
  if (voiceState === "listening" || voiceActive) {
    voiceStatusText = "LIVE";
  } else if (voiceState === "thinking") {
    voiceStatusText = "PROCESSING";
  } else if (voiceState === "speaking") {
    voiceStatusText = "SPEAKING";
  } else if (voiceState === "error") {
    voiceStatusText = "ALERT";
  } else if (geminiStatus && geminiStatus !== "ONLINE") {
    voiceStatusText = geminiStatus;
  }
  return (
    <header
      className={`hud-header reveal-component reveal-header ${
        isRevealed ? "is-revealed" : ""
      }`}
      role="banner"
    >
      {/* Zone 1: Left — Brand Logo & Drawer Navigation */}
      <div className="hud-brand-area hud-header-left-zone">
        <button
          aria-label="Home"
          className="hud-brand"
          onClick={onOpenOverview}
          type="button"
          title="Return to home overview"
        >
          <span className="brand-logo-mark" aria-hidden="true">◈</span>
          <span className="brand-title">ALEX</span>
        </button>

        <button
          aria-label="Setup"
          aria-expanded={setupMenuOpen}
          className={`hud-icon-button ${setupMenuOpen || isSettingsActive ? "selected" : ""}`}
          onClick={onToggleSetup}
          type="button"
          title="Setup — Audio devices, shortcuts, reminders & system configuration"
        >
          <span aria-hidden="true">⚙</span>
        </button>

        <button
          aria-label="Controls"
          aria-expanded={controlsMenuOpen}
          className={`hud-icon-button ${controlsMenuOpen ? "selected" : ""}`}
          onClick={onToggleControls}
          type="button"
          title="Controls — Quick everyday switches, wake word, and display modes"
        >
          <span className="app-grid-icon" aria-hidden="true">
            🎛
          </span>
        </button>

        {onToggleActivity && (
          <button
            aria-label={`Activity Stream: ${activityCount ?? 0} events`}
            aria-expanded={activityOpen}
            className={`hud-icon-button hud-activity-header-btn ${activityOpen ? "selected" : ""}`}
            onClick={onToggleActivity}
            type="button"
            title={`Activity Stream — ${activityCount ?? 0} live events recorded (click to toggle log)`}
          >
            <span className="app-grid-icon" aria-hidden="true">
              📜
            </span>
            {activityCount !== undefined && activityCount > 0 && (
              <span
                className="hud-badge-counter"
                title={`${activityCount} activity events recorded`}
                aria-label={`${activityCount} activity updates`}
              >
                {activityCount > 99 ? "99+" : activityCount}
              </span>
            )}
          </button>
        )}
      </div>

      {/* Zone 2: Center — Single Honest Status Indicator */}
      <div className="hud-title hud-header-center-zone">
        <div className="hud-title-main">
          <strong>{assistantName.toUpperCase()}</strong>
          <span
            className="hud-title-sub"
            title="Architecture: Local application runtime connected to Cloud Voice AI"
          >
            <i className={`title-pulse-dot state-${voiceState || (voiceActive ? "listening" : "idle")}`} aria-hidden="true" /> LOCAL APP · CLOUD VOICE {voiceStatusText}
          </span>
        </div>
        {latestActivity && (
          <button
            type="button"
            className="hud-activity-ticker-pill"
            onClick={onToggleActivity}
            title="Click to view full Activity Log"
            aria-label={`Latest activity: ${latestActivity.kind}: ${latestActivity.text}`}
          >
            <span className="ticker-dot" aria-hidden="true" />
            <span className="ticker-kind">{latestActivity.kind}:</span>
            <span className="ticker-text">{latestActivity.text}</span>
          </button>
        )}
      </div>

      {/* Zone 3: Right — Tools & Digital Clock */}
      <div className="hud-header-right-zone">
        {onToggleSystemMonitor && (
          <button
            type="button"
            aria-label="Toggle System Monitor telemetry"
            aria-expanded={systemMonitorOpen}
            className={`hud-tool-btn ${systemMonitorOpen ? "active" : ""}`}
            onClick={onToggleSystemMonitor}
            title="Toggle System Monitor — CPU, RAM, Network & Engine Telemetry"
          >
            <span className="hud-tool-icon" aria-hidden="true">⚡</span>
            <span className="hud-tool-btn-label">MONITOR</span>
          </button>
        )}

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
      </div>
    </header>
  );
}

