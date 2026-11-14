import type { CSSProperties } from "react";
import { VisualizationManager } from "../avatar/VisualizationManager";
import { HUDWorkspace } from "../workspace/HUDWorkspace";
import type { AppSettings, HudStyle } from "../../types/api";
import type { WorkspaceActivity, WorkspaceActivityType } from "../../types/workspace";

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
  geminiModel,
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

      {/* Concentric Rotating Holographic Radar Rings */}
      <div className={`holo-concentric-rings ${isWorkspaceActive ? "in-workspace-mode" : ""}`} aria-hidden="true">
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

      {/* Futuristic Welcome Header & User Designation — hidden during startup diagnostics & workspace mode */}
      {!isStartupDiagnostics && !isWorkspaceActive && (
        <div className="hud-welcome-copy">
          <div className="hud-welcome-kicker">
            {booting ? "SYSTEM BOOT SEQUENCE" : "LOCAL COGNITIVE CORE • READY"}
          </div>
          <h1>
            {userName ? `WELCOME BACK, ${userName.toUpperCase()}` : "AT YOUR SERVICE"}
          </h1>
          <p>
            {chatBusy
              ? "Analyzing neural request and formulating synthesis…"
              : "Your assistant, your device, your control."}
          </p>

          {/* Dynamic Audio Spectral Waveform */}
          <div className="hud-waveform" aria-hidden="true">
            {Array.from({ length: 44 }, (_, index) => (
              <i key={index} style={{ "--wave-index": index } as CSSProperties} />
            ))}
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

          <span className="voice-pending">
            {voiceActive
              ? `GEMINI LIVE ACTIVE${geminiModel ? ` [${geminiModel.replace("models/", "")}]` : ""}`
              : geminiStatus === "POLICY 1008"
              ? "GEMINI: POLICY 1008 · REST MODE AVAILABLE"
              : apiKeyConfigured
              ? "VOICE & NEURAL MODEL READY"
              : "VOICE SETUP REQUIRED"}
          </span>
        </div>
      )}
    </main>
  );
}
