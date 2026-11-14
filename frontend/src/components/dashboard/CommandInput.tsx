import type { FormEvent } from "react";
import type { SelectedFile } from "./FileUpload";

export interface CommandInputProps {
  command: string;
  onCommandChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  apiKeyConfigured: boolean;
  chatBusy: boolean;
  selectedFile: SelectedFile | null;
  voiceActive: boolean;
  voiceStarting: boolean;
  onVoiceToggle: () => void;
  onVoiceInterrupt: () => void;
  onOpenChat: () => void;
  isRevealed?: boolean;
  onVoiceStart?: () => void;
  onVoiceStop?: () => void;
  isSpeaking?: boolean;
  hasError?: boolean;
  errorMessage?: string | null;
}

export type VoiceHUDState = "LISTENING" | "THINKING" | "RESPONDING" | "IDLE" | "ERROR";

export function CommandInput({
  command,
  onCommandChange,
  onSubmit,
  apiKeyConfigured,
  chatBusy,
  selectedFile,
  voiceActive,
  voiceStarting,
  onVoiceToggle,
  onVoiceInterrupt,
  onOpenChat,
  isRevealed = true,
  onVoiceStart,
  onVoiceStop,
  isSpeaking = false,
  hasError = false,
  errorMessage = null,
}: CommandInputProps) {
  // Determine reactive voice state
  let voiceState: VoiceHUDState = "IDLE";
  if (hasError) {
    voiceState = "ERROR";
  } else if (isSpeaking) {
    voiceState = "RESPONDING";
  } else if (chatBusy) {
    voiceState = "THINKING";
  } else if (voiceActive) {
    voiceState = "LISTENING";
  } else {
    voiceState = "IDLE";
  }

  const handleStartMic = () => {
    if (onVoiceStart) {
      onVoiceStart();
    } else {
      onVoiceToggle();
    }
  };

  const handleStopMic = () => {
    if (onVoiceStop) {
      onVoiceStop();
    } else {
      onVoiceToggle();
    }
  };

  return (
    <footer
      className={`hud-bottom-command-bar reveal-component reveal-command ${
        isRevealed ? "is-revealed" : ""
      }`}
      role="region"
      aria-label="Command and Voice Controls"
    >
      <div className="hud-command-inner">
        {/* Dynamic Voice State & Audio Waveform Visualizer */}
        <div className={`hud-voice-waveform-bar state-${voiceState.toLowerCase()}`}>
          <div className="hud-waveform-status-wrap">
            <span className="hud-waveform-indicator-dot" aria-hidden="true" />
            <span className="hud-waveform-status-label">
              {voiceState === "LISTENING" && "VOICE CHANNEL LIVE • LISTENING"}
              {voiceState === "THINKING" && "COGNITIVE CORE PROCESSING…"}
              {voiceState === "RESPONDING" && "SYNTHESIS VOCALIZING"}
              {voiceState === "IDLE" && "AUDIO SENSORS STANDBY"}
              {voiceState === "ERROR" && (errorMessage ? `VOICE CHANNEL ALERT: ${errorMessage}` : "VOICE CHANNEL ERROR")}
            </span>
          </div>

          <div className="hud-waveform-bars" aria-hidden="true">
            {Array.from({ length: 32 }, (_, idx) => (
              <span
                key={idx}
                className="hud-waveform-bar"
                style={{ "--bar-index": idx } as React.CSSProperties}
              />
            ))}
          </div>
        </div>

        {/* Attachment Pill if a file or capture is primed */}
        {selectedFile && (
          <div className="hud-cmd-attached-badge">
            <span className="cmd-attached-icon">📎</span>
            <span>FILE PRIMED: {selectedFile.attachment.name}</span>
          </div>
        )}

        <div className="hud-command-controls-row">
          {/* 1. Text command input & 2. Send button */}
          <form className="hud-command-form" onSubmit={onSubmit}>
            <div className="hud-input-prefix">
              <span className="hud-prompt-glyph">❯</span>
            </div>
            <input
              aria-label="Command or question"
              className="hud-command-input"
              disabled={!apiKeyConfigured || chatBusy}
              maxLength={4000}
              onChange={(event) => onCommandChange(event.target.value)}
              placeholder={
                apiKeyConfigured
                  ? "Type a command or ask anything..."
                  : "Initialise Gemini access first…"
              }
              value={command}
            />
            <button
              aria-label="Send command"
              className="hud-send-btn"
              disabled={!apiKeyConfigured || chatBusy || (!command.trim() && !selectedFile)}
              type="submit"
              title="Send command"
            >
              {chatBusy ? "…" : "▶"}
            </button>
          </form>

          {/* Action Controls: 3. Mic Start/Active, 4. Interrupt, 5. Stop Mic, 6. Chat History */}
          <div className="hud-command-actions">
            {/* 3. Microphone Control */}
            <button
              type="button"
              aria-label={voiceActive ? "Microphone active" : "Start microphone"}
              className={`hud-cmd-btn hud-btn-mic ${
                voiceActive ? "hud-mic-active" : "hud-btn-standby"
              }`}
              disabled={!apiKeyConfigured || voiceStarting}
              onClick={voiceActive ? handleStopMic : handleStartMic}
              title={
                apiKeyConfigured
                  ? voiceActive
                    ? "Microphone is active (click to stop)"
                    : "Start microphone voice session"
                  : "Configure a Gemini API key in Settings"
              }
            >
              <span className="hud-btn-icon">🎙</span>
              <span className="hud-btn-label">
                {voiceStarting
                  ? "CONNECTING…"
                  : voiceActive
                  ? "MIC LIVE"
                  : "START MIC"}
              </span>
            </button>

            {/* 4. Interrupt Assistant Audio */}
            <button
              type="button"
              aria-label="Interrupt voice response"
              className={`hud-cmd-btn hud-btn-interrupt ${
                voiceActive || isSpeaking ? "hud-action-live" : "hud-action-disabled"
              }`}
              disabled={!voiceActive && !isSpeaking}
              onClick={onVoiceInterrupt}
              title={
                voiceActive || isSpeaking
                  ? "Stop the current response and continue listening"
                  : "Voice session offline"
              }
            >
              <span className="hud-btn-icon">✋</span>
              <span className="hud-btn-label">INTERRUPT</span>
            </button>

            {/* 5. Stop Microphone */}
            <button
              type="button"
              aria-label="Stop microphone"
              className={`hud-cmd-btn hud-btn-stop ${
                voiceActive ? "hud-action-stop" : "hud-action-disabled"
              }`}
              disabled={!voiceActive}
              onClick={handleStopMic}
              title={
                voiceActive ? "Stop microphone voice session" : "Microphone is offline"
              }
            >
              <span className="hud-btn-icon">⏹</span>
              <span className="hud-btn-label">STOP MIC</span>
            </button>

            {/* 6. Open Chat History */}
            <button
              type="button"
              aria-label="Open chat history"
              className="hud-cmd-btn hud-btn-chat text-chat-button"
              onClick={onOpenChat}
              title="Open full conversation history dialog"
            >
              <span className="hud-btn-icon">◈</span>
              <span className="hud-btn-label">CHAT HISTORY</span>
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
}
