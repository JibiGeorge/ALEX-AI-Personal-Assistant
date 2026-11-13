import type { ApiStatus, SystemMetrics } from "../../types/api";

export interface SystemMonitorProps {
  metrics: SystemMetrics | null;
  status: ApiStatus | null;
  voiceActive: boolean;
  apiKeyConfigured: boolean;
  osShort?: string;
  uptimeFormatted?: string;
  isRevealed?: boolean;
  geminiStatus?: string;
  geminiModel?: string;
  compact?: boolean;
}

export function SystemMonitor({
  metrics,
  status,
  voiceActive,
  apiKeyConfigured,
  osShort = "",
  uptimeFormatted = "--:--",
  isRevealed = true,
  geminiStatus,
  geminiModel,
}: SystemMonitorProps) {
  // 1. CPU & RAM utilization
  const cpuVal = metrics ? `${Math.round(metrics.cpu_percent)}%` : "--";
  const ramVal = metrics ? `${Math.round(metrics.memory_percent)}%` : "--";

  // 2. Network Status
  let networkState: "ONLINE" | "OFFLINE" | "CONNECTING" | "WARNING" | "UNAVAILABLE" = "ONLINE";
  let networkClass = "state-online";
  let networkTooltip = "Network interface online";

  if (!metrics) {
    networkState = "UNAVAILABLE";
    networkClass = "state-unavailable";
    networkTooltip = "Network telemetry unavailable";
  } else if (metrics.network_mb_per_sec !== null && metrics.network_mb_per_sec > 0) {
    networkState = "ONLINE";
    networkClass = "state-online";
    networkTooltip = `Network throughput: ${metrics.network_mb_per_sec.toFixed(1)} MB/s`;
  } else if (metrics.network_mb_per_sec === 0) {
    networkState = "ONLINE";
    networkClass = "state-online";
    networkTooltip = "Network link established (idle)";
  } else if (metrics.network_mb_per_sec === null) {
    networkState = "OFFLINE";
    networkClass = "state-offline";
    networkTooltip = "Network link offline";
  }

  // 3. Backend Connectivity
  let backendState: "CONNECTED" | "OFFLINE" | "CONNECTING" | "WARNING" | "UNAVAILABLE" = "CONNECTED";
  let backendClass = "state-online";

  if (!status) {
    backendState = "CONNECTING";
    backendClass = "state-connecting";
  } else if (status.status === "ready") {
    backendState = "CONNECTED";
    backendClass = "state-online";
  } else if (status.status === "booting" || status.status === "initializing") {
    backendState = "CONNECTING";
    backendClass = "state-connecting";
  } else {
    backendState = "OFFLINE";
    backendClass = "state-offline";
  }

  // 4. AI Engine Status
  let aiEngineState: "READY" | "ONLINE" | "OFFLINE" | "CONNECTING" | "WARNING" | "UNAVAILABLE" = "READY";
  let aiEngineClass = "state-online";
  let aiEngineTooltip = geminiModel ? `Gemini Engine: ${geminiModel}` : "AI engine operational";

  if (!apiKeyConfigured) {
    aiEngineState = "UNAVAILABLE";
    aiEngineClass = "state-unavailable";
    aiEngineTooltip = "Gemini API key required in Settings";
  } else if (geminiStatus) {
    const lower = geminiStatus.toLowerCase();
    if (lower.includes("1008") || lower.includes("policy")) {
      aiEngineState = "WARNING";
      aiEngineClass = "state-warning";
      aiEngineTooltip = "Gemini Live policy restriction (REST available)";
    } else if (lower.includes("error") || lower.includes("offline")) {
      aiEngineState = "OFFLINE";
      aiEngineClass = "state-offline";
      aiEngineTooltip = geminiStatus;
    } else if (lower.includes("connecting") || lower.includes("initializ")) {
      aiEngineState = "CONNECTING";
      aiEngineClass = "state-connecting";
      aiEngineTooltip = geminiStatus;
    } else {
      aiEngineState = "READY";
      aiEngineClass = "state-online";
    }
  }

  // 5. Microphone / Voice Status
  let voiceStateText: "ACTIVE" | "ONLINE" | "STANDBY" | "OFFLINE" | "WARNING" | "UNAVAILABLE" = "STANDBY";
  let voiceClass = "state-standby";
  let voiceTooltip = "Microphone channel ready on standby";

  if (voiceActive) {
    voiceStateText = "ACTIVE";
    voiceClass = "state-online";
    voiceTooltip = "Microphone active · listening & streaming";
  } else if (!apiKeyConfigured) {
    voiceStateText = "UNAVAILABLE";
    voiceClass = "state-unavailable";
    voiceTooltip = "Voice channel requires AI API key";
  } else {
    voiceStateText = "STANDBY";
    voiceClass = "state-standby";
  }

  return (
    <div
      className={`minimal-system-monitor reveal-component reveal-monitor ${
        isRevealed ? "is-revealed" : ""
      }`}
      role="region"
      aria-label="System Monitor"
    >
      {/* Category Heading */}
      <div className="mon-title-badge">
        <span className="mon-title-icon" aria-hidden="true">◆</span>
        <span className="mon-title-text">SYSTEM MONITOR</span>
      </div>

      <div className="mon-separator" aria-hidden="true" />

      {/* CPU & RAM utilization */}
      <div className="mon-utilization-group">
        <div className="mon-util-item" title="CPU Utilization">
          <span className="mon-util-label">CPU</span>
          <span className="mon-util-value">{cpuVal}</span>
        </div>
        <span className="mon-util-pipe" aria-hidden="true">|</span>
        <div className="mon-util-item" title="RAM Allocation">
          <span className="mon-util-label">RAM</span>
          <span className="mon-util-value">{ramVal}</span>
        </div>
      </div>

      <div className="mon-separator" aria-hidden="true" />

      {/* Real-time Status Chips */}
      <div className="mon-status-group">
        {/* NETWORK */}
        <div className="mon-status-chip" title={networkTooltip}>
          <span className="mon-status-label">NETWORK</span>
          <span className={`mon-status-dot ${networkClass}`} aria-hidden="true">●</span>
          <strong className={`mon-status-val ${networkClass}`}>{networkState}</strong>
        </div>

        {/* BACKEND (with Local Core tag) */}
        <div className="mon-status-chip" title="Local Python core and loopback server">
          <span className="mon-status-label">BACKEND</span>
          <span className="mon-sub-core" title="Local Core">LOCAL CORE</span>
          <span className={`mon-status-dot ${backendClass}`} aria-hidden="true">●</span>
          <strong className={`mon-status-val ${backendClass}`}>{backendState}</strong>
        </div>

        {/* AI ENGINE */}
        <div className="mon-status-chip" title={aiEngineTooltip}>
          <span className="mon-status-label">AI ENGINE</span>
          <span className={`mon-status-dot ${aiEngineClass}`} aria-hidden="true">●</span>
          <strong className={`mon-status-val ${aiEngineClass}`}>{aiEngineState}</strong>
        </div>

        {/* VOICE */}
        <div className="mon-status-chip" title={voiceTooltip}>
          <span className="mon-status-label">VOICE</span>
          <span className={`mon-status-dot ${voiceClass}`} aria-hidden="true">●</span>
          <strong className={`mon-status-val ${voiceClass}`}>{voiceStateText}</strong>
        </div>
      </div>

      {/* Subtle Uptime & OS Pill */}
      {uptimeFormatted && (
        <div className="mon-telemetry-meta" title={`Uptime: ${uptimeFormatted}${osShort ? ` · ${osShort}` : ""}`}>
          <span className="mon-meta-icon" aria-hidden="true">⏱</span>
          <span className="mon-meta-text">{uptimeFormatted}</span>
        </div>
      )}
    </div>
  );
}
