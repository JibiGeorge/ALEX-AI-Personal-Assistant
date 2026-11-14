import { VisualizationManager } from "../avatar/VisualizationManager";
import { HUDWorkspace } from "../workspace/HUDWorkspace";
import "../workspace/HUDWorkspace.css";
import { AlexResponseStream, type AlexResponseItem } from "./AlexResponseStream";
import type { AppSettings, HudStyle } from "../../types/api";
import type { WorkspaceActivity, WorkspaceActivityType } from "../../types/workspace";
import type { VoiceState } from "../../types/voice";

export interface HolographicAssistantProps {
  assistantName: string;
  userName: string;
  mode: "booting" | "idle" | "listening" | "thinking" | "speaking";
  hudStyle: AppSettings["hud_style"];
  booting: boolean;
  chatBusy: boolean;
  voiceActive: boolean;
  apiKeyConfigured: boolean;
  activeMedia?: {
    active: boolean;
    source: string;
    title: string;
    url: string;
    audio_url?: string;
    is_playing: boolean;
    is_muted: boolean;
  } | null;
  onCloseMedia?: () => void;
  onMuteMediaChange?: (muted: boolean) => void;
  onPlayStateMediaChange?: (playing: boolean) => void;
  activeWorkspace?: WorkspaceActivity | null;
  onCloseWorkspace?: () => void;
  onOpenExternal?: (urlOrPath: string) => void;
  onOpenSampleActivity?: (type: WorkspaceActivityType) => void;
  isRevealed?: boolean;
  speaking?: boolean;
  amplitude?: number;
  spokenText?: string;
  analyserNode?: AnalyserNode | null;
  onToggleHudStyle?: (style?: HudStyle) => void;
  geminiStatus?: string;
  geminiModel?: string;
  isStartupDiagnostics?: boolean;
  diagnosticPhase?: string;
  isPanelActive?: boolean;
  alexResponses?: AlexResponseItem[];
  onSelectSuggestion?: (suggestion: string) => void;
  voiceState?: VoiceState;
}

export function HolographicAssistant({
  assistantName,
  userName,
  mode,
  hudStyle,
  booting,
  chatBusy,
  voiceActive,
  apiKeyConfigured,
  activeMedia,
  onCloseMedia,
  onMuteMediaChange,
  onPlayStateMediaChange,
  activeWorkspace,
  onCloseWorkspace,
  onOpenExternal,
  onOpenSampleActivity,
  isRevealed = true,
  isStartupDiagnostics = false,
  diagnosticPhase = "idle",
  isPanelActive = false,
  speaking = false,
  amplitude = 0.0,
  spokenText = "",
  analyserNode = null,
  onToggleHudStyle,
  geminiStatus,
  geminiModel: _geminiModel,
  alexResponses = [],
  onSelectSuggestion,
  voiceState,
}: HolographicAssistantProps) {
  // Determine dynamic assistant status (Section 4)
  let assistantStatusText = "STANDING BY";
  if (booting) {
    assistantStatusText = "INITIALIZING";
  } else if (speaking || mode === "speaking") {
    assistantStatusText = "RESPONDING";
  } else if (chatBusy || mode === "thinking") {
    assistantStatusText = "PROCESSING";
  } else if (voiceActive || mode === "listening") {
    assistantStatusText = "LISTENING";
  }

  // Effective workspace activity (from activeWorkspace or bridged activeMedia)
  const effectiveWorkspace: WorkspaceActivity | null =
    activeWorkspace ??
    (activeMedia?.active && activeMedia.url
      ? {
          id: "active-media-video",
          type: "video",
          title: activeMedia.title || activeMedia.source,
          url: activeMedia.url,
          audioUrl: activeMedia.audio_url,
          isPlaying: activeMedia.is_playing,
          isMuted: activeMedia.is_muted,
        }
      : null);

  const isWorkspaceActive = Boolean(effectiveWorkspace) || Boolean(isPanelActive);
  const handleClose = onCloseWorkspace || onCloseMedia || (() => {});

  return (
    <main
      className={`hud-center reveal-component reveal-center ${
        isRevealed ? "is-revealed" : ""
      } ${isStartupDiagnostics ? "in-diagnostics" : ""} ${
        isWorkspaceActive ? "has-active-workspace" : ""
      } diag-phase-${diagnosticPhase}`}
      data-diag-phase={diagnosticPhase}
    >
      {/* Background Graphic & Laser Scanning Ambient Layer */}
      <div className="hud-starfield" aria-hidden="true" />
      <div className="hud-laser-scanline" aria-hidden="true" />

      {/* Dynamic Central HUD Workspace (active during media/file/document/image/tool activities) */}
      {isWorkspaceActive && effectiveWorkspace && (
        <HUDWorkspace
          activity={effectiveWorkspace}
          analyserNode={analyserNode}
          onClose={handleClose}
          onMuteToggle={onMuteMediaChange}
          onPlayPauseToggle={onPlayStateMediaChange}
          onOpenExternal={onOpenExternal}
          onOpenSampleActivity={onOpenSampleActivity}
        />
      )}

      {/* Concentric Rotating Holographic Radar Rings & Targeting Vectors */}
      <div className={`holo-concentric-rings ${isWorkspaceActive ? "in-workspace-mode" : ""}`} aria-hidden="true">
        <svg
          className="holo-radar-vector"
          viewBox="-500 -500 1000 1000"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <filter id="holoVectorGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <radialGradient id="holoVectorCoreGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#00e5ff" stopOpacity="0.25" />
              <stop offset="45%" stopColor="#087bff" stopOpacity="0.08" />
              <stop offset="100%" stopColor="#020a12" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Central Glow Aura */}
          <circle r="460" fill="url(#holoVectorCoreGlow)" />

          {/* Rotating Vector Arc Group */}
          <g className="holo-vector-spin">
            <circle r="440" fill="none" stroke="#00e5ff" strokeWidth="1.2" strokeDasharray="8 16" opacity="0.35" />
            <circle r="380" fill="none" stroke="#087bff" strokeWidth="1.8" strokeDasharray="24 12 6 12" opacity="0.45" />
            <circle r="320" fill="none" stroke="#00e5ff" strokeWidth="1.2" strokeDasharray="4 8" opacity="0.3" />
            <circle r="260" fill="none" stroke="#00a8cc" strokeWidth="1.4" strokeOpacity="0.4" />
            <circle r="200" fill="none" stroke="#00e5ff" strokeWidth="2.2" strokeDasharray="160 30" opacity="0.45" filter="url(#holoVectorGlow)" />
            <circle r="140" fill="none" stroke="#087bff" strokeWidth="1.2" strokeDasharray="40 10 10 10" opacity="0.35" />
            <circle r="90" fill="none" stroke="#00e5ff" strokeWidth="1.2" strokeOpacity="0.35" />

            {/* Circular Radar Angle Ticks */}
            <path d="M -300,-120 L -315,-126" stroke="#00e5ff" strokeWidth="1.8" opacity="0.55" />
            <path d="M 300,-120 L 315,-126" stroke="#00e5ff" strokeWidth="1.8" opacity="0.55" />
            <path d="M -300,120 L -315,126" stroke="#00e5ff" strokeWidth="1.8" opacity="0.55" />
            <path d="M 300,120 L 315,126" stroke="#00e5ff" strokeWidth="1.8" opacity="0.55" />
          </g>

          {/* Axis Crosshairs & Coordinates */}
          <g className="holo-vector-crosshairs">
            <line x1="-480" y1="0" x2="-280" y2="0" stroke="#00e5ff" strokeWidth="1.2" opacity="0.4" />
            <line x1="280" y1="0" x2="480" y2="0" stroke="#00e5ff" strokeWidth="1.2" opacity="0.4" />
            <line x1="0" y1="-440" x2="0" y2="-280" stroke="#00e5ff" strokeWidth="1.2" opacity="0.4" />
            <line x1="0" y1="280" x2="0" y2="440" stroke="#00e5ff" strokeWidth="1.2" opacity="0.4" />

            {/* Coordinate Target Reticle Ticks */}
            <line x1="-16" y1="0" x2="16" y2="0" stroke="#00e5ff" strokeWidth="1.5" opacity="0.5" />
            <line x1="0" y1="-16" x2="0" y2="16" stroke="#00e5ff" strokeWidth="1.5" opacity="0.5" />
          </g>
        </svg>

        {/* Existing CSS animated rings preserved for backwards compatibility */}
        <div className="holo-ring holo-ring-outer" />
        <div className="holo-ring holo-ring-mid" />
        <div className="holo-ring holo-ring-inner" />
      </div>

      {/* Main Center Entity: Intelligent Dynamic Assistant Avatar (Normal: Center / Workspace: Bottom-Right) */}
      <div
        className={`hud-avatar-stage ${
          isWorkspaceActive ? "in-workspace-mode is-docked" : ""
        } diag-phase-${diagnosticPhase}`}
        data-diag-phase={diagnosticPhase}
      >
        <div className="hud-avatar-wrapper">
          <VisualizationManager
            assistantName={assistantName}
            mode={speaking ? "speaking" : mode}
            visualization={hudStyle ?? "face"}
            speaking={speaking}
            amplitude={amplitude}
            spokenText={spokenText}
            analyserNode={analyserNode}
            diagnosticPhase={diagnosticPhase}
          />
        </div>
        {/* Compact Assistant Status Indicator when in Workspace Mode */}
        {isWorkspaceActive && (
          <div className="compact-avatar-status-pill">
            <span className="ws-badge-dot" style={{ display: "inline-block", marginRight: 4 }} />
            {assistantStatusText}
          </div>
        )}
      </div>

      {/* Futuristic Welcome Header & Contextual Suggestion Chips — hidden during startup diagnostics & workspace mode */}
      {!isStartupDiagnostics && !isWorkspaceActive && (
        <div className="hud-welcome-copy">
          <div className="hud-welcome-kicker">
            {booting ? "SYSTEM BOOT SEQUENCE" : "ALEX INTELLIGENCE SYSTEM • READY"}
          </div>
          <h1>
            {userName ? `WELCOME BACK, ${userName.toUpperCase()}` : "AT YOUR SERVICE"}
          </h1>

          {/* Contextual Suggestion Chips */}
          <div className="hud-suggestion-chips" role="group" aria-label="Suggested Commands">
            <button
              type="button"
              className="hud-chip"
              onClick={() => onSelectSuggestion?.("Find jobs")}
              title="Discover matching career vacancies"
            >
              <span className="hud-chip-icon" aria-hidden="true">💼</span>
              <span>Find jobs</span>
            </button>
            <button
              type="button"
              className="hud-chip"
              onClick={() => onSelectSuggestion?.("Tailor my resume")}
              title="Tailor resume and optimize skills"
            >
              <span className="hud-chip-icon" aria-hidden="true">✍</span>
              <span>Tailor my resume</span>
            </button>
            <button
              type="button"
              className="hud-chip"
              onClick={() => onSelectSuggestion?.("Summarize my day")}
              title="Get an executive briefing and schedule summary"
            >
              <span className="hud-chip-icon" aria-hidden="true">📋</span>
              <span>Summarize my day</span>
            </button>
            <button
              type="button"
              className="hud-chip"
              onClick={() => onSelectSuggestion?.("System status")}
              title="Inspect system telemetry and resources"
            >
              <span className="hud-chip-icon" aria-hidden="true">⚡</span>
              <span>System status</span>
            </button>
          </div>
        </div>
      )}

      {/* Hologram Assistant Dynamic Status Bar — hidden during startup diagnostics & workspace mode */}
      {!isStartupDiagnostics && !isWorkspaceActive && (
        <div className="hud-center-foot">
          <span
            className={`hud-status-pill status-${assistantStatusText.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <i className="signal-dot" />
            <strong>{assistantStatusText}</strong>
          </span>

          {onToggleHudStyle && (
            <div className="hud-mode-switcher" role="group" aria-label="HUD Visualization Modes">
              <button
                type="button"
                className={`hud-mode-pill ${hudStyle === "face" ? "active" : ""}`}
                onClick={() => onToggleHudStyle("face")}
                title="Switch to Animated Face"
              >
                👤 FACE
              </button>
              <button
                type="button"
                className={`hud-mode-pill ${hudStyle === "core" ? "active" : ""}`}
                onClick={() => onToggleHudStyle("core")}
                title="Switch to Reactor Core"
              >
                ⚡ CORE
              </button>
              <button
                type="button"
                className={`hud-mode-pill ${hudStyle === "robot" || hudStyle === "realistic_humanoid" ? "active" : ""}`}
                onClick={() => onToggleHudStyle("robot")}
                title="Switch to Realistic Humanoid Robot"
              >
                🤖 ROBOT
              </button>
            </div>
          )}

          <span className="voice-pending" title="Voice connection status">
            {voiceState === "speaking"
              ? "CLOUD VOICE SPEAKING"
              : voiceState === "thinking"
              ? "CLOUD VOICE THINKING"
              : voiceActive || voiceState === "listening"
              ? "CLOUD VOICE LIVE"
              : voiceState === "error"
              ? "VOICE CHANNEL ALERT"
              : geminiStatus === "POLICY 1008"
              ? "GEMINI: POLICY 1008 · REST MODE AVAILABLE"
              : apiKeyConfigured
              ? "VOICE & NEURAL MODEL READY"
              : "VOICE SETUP REQUIRED"}
          </span>
        </div>
      )}

      {/* Right Side: ALEX Live Response Stream (Autoscrolling HUD Stream) */}
      {!isStartupDiagnostics && (
        <AlexResponseStream
          responses={alexResponses}
          isWorkspaceActive={isWorkspaceActive}
          isStreaming={speaking || chatBusy}
        />
      )}
    </main>
  );
}
