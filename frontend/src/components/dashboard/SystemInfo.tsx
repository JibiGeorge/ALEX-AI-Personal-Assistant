import type { ApiStatus, SystemMetrics } from "../../types/api";

export interface SystemInfoProps {
  metrics: SystemMetrics | null;
  status: ApiStatus | null;
  voiceActive: boolean;
  apiKeyConfigured: boolean;
  osShort: string;
  uptimeFormatted: string;
  geminiStatus?: string;
  geminiModel?: string;
}

export function SystemInfo({
  metrics,
  status,
  voiceActive,
  apiKeyConfigured,
  osShort,
  uptimeFormatted,
  geminiStatus,
  geminiModel,
}: SystemInfoProps) {
  let geminiClass = "status-good";
  let geminiLabel = "ONLINE";
  let geminiTitle = "Gemini AI neural services operational";

  if (!apiKeyConfigured) {
    geminiClass = "status-neutral";
    geminiLabel = "KEY REQUIRED";
    geminiTitle = "Configure a Gemini API key in Settings";
  } else if (geminiStatus) {
    const lower = geminiStatus.toLowerCase();
    if (lower.includes("1008") || lower.includes("policy")) {
      geminiClass = "status-bad";
      geminiLabel = "POLICY 1008";
      geminiTitle = "Gemini Live policy violation (1008) — key lacks Live WebSocket access; REST mode available";
    } else if (lower.includes("error") || lower.includes("offline")) {
      geminiClass = "status-bad";
      geminiLabel = "ERROR";
      geminiTitle = geminiStatus;
    } else if (lower.includes("live") || voiceActive) {
      geminiClass = "status-good";
      geminiLabel = geminiModel ? `LIVE (${geminiModel.replace("models/", "").replace("gemini-", "")})` : "LIVE ACTIVE";
      geminiTitle = `Gemini Live connected: ${geminiModel || "realtime"}`;
    } else {
      geminiClass = "status-good";
      geminiLabel = geminiStatus.toUpperCase();
    }
  } else if (voiceActive) {
    geminiClass = "status-good";
    geminiLabel = "LIVE ACTIVE";
    geminiTitle = "Gemini Live bidirectional voice session active";
  }

  const isDiskHealthy = Boolean(metrics);
  const diskLabel = isDiskHealthy ? "HEALTHY" : "--";
  const diskClass = isDiskHealthy ? "status-good" : "status-bad";

  const isLocalCoreOnline = status?.status === "ready";
  const localCoreLabel = isLocalCoreOnline ? "ONLINE" : "OFFLINE";
  const localCoreClass = isLocalCoreOnline ? "status-good" : "status-bad";

  const isVoiceLive = voiceActive;
  const voiceLabel = isVoiceLive ? "LIVE" : apiKeyConfigured ? "STANDBY" : "KEY REQUIRED";
  const voiceClass = isVoiceLive ? "status-good" : apiKeyConfigured ? "status-neutral" : "status-bad";

  return (
    <div className="hud-system-info-wrap" role="region" aria-label="System Information">
      <div className="hud-system-info-panel">
        {/* Upper Telemetry Metrics */}
        <div className="hud-info-row">
          <div className="hud-row-left">
            <span className="hud-row-icon" aria-hidden="true">⏱</span>
            <b>UP</b>
          </div>
          <span className="hud-row-val">{uptimeFormatted}</span>
        </div>

        <div className="hud-info-row">
          <div className="hud-row-left">
            <span className="hud-row-icon" aria-hidden="true">▤</span>
            <b>PROC</b>
          </div>
          <span className="hud-row-val">{metrics?.process_count ?? "--"}</span>
        </div>

        <div className="hud-info-row">
          <div className="hud-row-left">
            <span className="hud-row-icon" aria-hidden="true">💻</span>
            <b>OS</b>
          </div>
          <span className="hud-row-val">{osShort}</span>
        </div>

        <div className="hud-info-row">
          <div className="hud-row-left">
            <span className="hud-row-icon" aria-hidden="true">💾</span>
            <b>DISK</b>
          </div>
          <strong className={`hud-row-status ${diskClass}`}>{diskLabel}</strong>
        </div>

        {/* Thin Section Separator */}
        <div className="hud-system-divider" aria-hidden="true" />

        {/* Lower Service Status Rows */}
        <div className="hud-info-row">
          <div className="hud-row-left">
            <span className="hud-row-icon" aria-hidden="true">◈</span>
            <span>LOCAL CORE</span>
          </div>
          <strong className={`hud-row-status ${localCoreClass}`}>{localCoreLabel}</strong>
        </div>

        <div className="hud-info-row">
          <div className="hud-row-left">
            <span className="hud-row-icon" aria-hidden="true">🔒</span>
            <span>IPC LINK</span>
          </div>
          <strong className="hud-row-status status-good">SECURE</strong>
        </div>

        <div className="hud-info-row">
          <div className="hud-row-left">
            <span className="hud-row-icon" aria-hidden="true">✦</span>
            <span>GEMINI</span>
          </div>
          <strong className={`hud-row-status ${geminiClass}`} title={geminiTitle}>
            {geminiLabel}
          </strong>
        </div>

        <div className="hud-info-row">
          <div className="hud-row-left">
            <span className="hud-row-icon" aria-hidden="true">🎙</span>
            <span>VOICE</span>
          </div>
          <strong className={`hud-row-status ${voiceClass}`}>{voiceLabel}</strong>
        </div>
      </div>
    </div>
  );
}
