import type { VoiceErrorInfo } from "../types/voice";

export interface VoiceErrorBannerProps {
  error: VoiceErrorInfo;
  onReconnect: () => void;
  onDismiss: () => void;
}

export function VoiceErrorBanner({
  error,
  onReconnect,
  onDismiss,
}: VoiceErrorBannerProps) {
  return (
    <aside
      className={`voice-error-banner error-type-${error.type}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="voice-error-icon" aria-hidden="true">
        {error.type === "permission_denied" && "🎙🚫"}
        {error.type === "quota_exceeded" && "⏳"}
        {error.type === "websocket_dropped" && "⚡"}
        {error.type === "model_unavailable" && "⚠"}
        {error.type === "general" && "⚠"}
      </div>

      <div className="voice-error-body">
        <strong className="voice-error-title">{error.title}</strong>
        <p className="voice-error-message">{error.message}</p>
      </div>

      <div className="voice-error-actions">
        {error.reconnectable && (
          <button
            type="button"
            className="voice-error-reconnect-btn"
            onClick={onReconnect}
            title="Retry voice connection"
          >
            ↻ RECONNECT
          </button>
        )}
        <button
          type="button"
          className="voice-error-dismiss-btn"
          onClick={onDismiss}
          title="Dismiss warning"
          aria-label="Dismiss warning"
        >
          ✕
        </button>
      </div>
    </aside>
  );
}
