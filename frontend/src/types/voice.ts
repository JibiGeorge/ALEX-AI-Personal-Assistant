export type VoiceState = "idle" | "listening" | "thinking" | "speaking" | "error";

export type VoiceErrorType =
  | "permission_denied"
  | "websocket_dropped"
  | "quota_exceeded"
  | "model_unavailable"
  | "general";

export interface VoiceErrorInfo {
  type: VoiceErrorType;
  title: string;
  message: string;
  reconnectable: boolean;
}

export function classifyVoiceError(errorMessage: string): VoiceErrorInfo {
  const lower = errorMessage.toLowerCase();

  if (
    lower.includes("permission") ||
    lower.includes("notallowederror") ||
    lower.includes("denied") ||
    lower.includes("microphone access")
  ) {
    return {
      type: "permission_denied",
      title: "Microphone Access Blocked",
      message: "Microphone access was denied. Please allow microphone permissions in system settings.",
      reconnectable: true,
    };
  }

  if (
    lower.includes("quota") ||
    lower.includes("rate limit") ||
    lower.includes("429") ||
    lower.includes("resource_exhausted")
  ) {
    return {
      type: "quota_exceeded",
      title: "Gemini Quota Exceeded",
      message: "Cloud voice model quota or rate limit reached. Wait a moment or switch to text chat.",
      reconnectable: true,
    };
  }

  if (
    lower.includes("1008") ||
    lower.includes("policy") ||
    lower.includes("unavailable") ||
    lower.includes("model")
  ) {
    return {
      type: "model_unavailable",
      title: "Voice Model Unavailable",
      message: "Gemini Live voice model is currently unavailable or policy restricted.",
      reconnectable: true,
    };
  }

  if (
    lower.includes("websocket") ||
    lower.includes("connection") ||
    lower.includes("closed") ||
    lower.includes("dropped") ||
    lower.includes("timeout") ||
    lower.includes("timed out")
  ) {
    return {
      type: "websocket_dropped",
      title: "Voice Connection Lost",
      message: "The voice streaming socket disconnected. Click Reconnect to resume.",
      reconnectable: true,
    };
  }

  return {
    type: "general",
    title: "Voice Channel Error",
    message: errorMessage || "An unexpected error occurred in the voice pipeline.",
    reconnectable: true,
  };
}
