import type { AlexApi } from "../types/api";

function api(): AlexApi {
  if (!window.alex) {
    throw new Error("Alex desktop bridge is unavailable");
  }
  return window.alex;
}

export const alexApi = {
  toggleFullscreen: () => api().toggleFullscreen(),
  getStatus: () => api().getStatus(),
  getSystemMetrics: () => api().getSystemMetrics(),
  getSystemVerification: () =>
    api().getSystemVerification
      ? api().getSystemVerification!()
      : Promise.resolve(null),
  getSystemAlerts: () => api().getSystemAlerts(),
  getSystemBriefing: () => (api().getSystemBriefing ? api().getSystemBriefing!() : Promise.resolve(null)),
  listActions: () => api().listActions(),
  setActionEnabled: (actionId: string, enabled: boolean) =>
    api().setActionEnabled(actionId, enabled),
  executeAction: (
    actionId: string,
    parameters: Record<string, unknown>,
    confirmed: boolean,
  ) => api().executeAction(actionId, parameters, confirmed),
  getActionHistory: () => api().getActionHistory(),
  getSettings: () => api().getSettings(),
  updateSettings: (settings: Parameters<AlexApi["updateSettings"]>[0]) =>
    api().updateSettings(settings),
  saveApiKey: (key: string) => api().saveApiKey(key),
  listMemory: () => api().listMemory(),
  upsertMemory: (
    category: Parameters<AlexApi["upsertMemory"]>[0],
    key: string,
    value: Parameters<AlexApi["upsertMemory"]>[2],
  ) => api().upsertMemory(category, key, value),
  deleteMemory: (
    category: Parameters<AlexApi["deleteMemory"]>[0],
    key: string,
  ) => api().deleteMemory(category, key),
  listReminders: () => api().listReminders(),
  createReminder: (message: string, dueAt: string) =>
    api().createReminder(message, dueAt),
  cancelReminder: (id: string) => api().cancelReminder(id),
  listDueReminders: () => api().listDueReminders(),
  markReminderDelivered: (id: string) => api().markReminderDelivered(id),
  notifyReminder: (message: string) => api().notifyReminder(message),
  notifySystemAlert: (message: string) => api().notifySystemAlert(message),
  sendMessage: (
    text: string,
    conversationId: string | null,
    attachment?: Parameters<AlexApi["sendMessage"]>[2],
  ) => attachment
    ? api().sendMessage(text, conversationId, attachment)
    : api().sendMessage(text, conversationId),
  captureScreen: () => api().captureScreen(),
  searchWeb: (request: Parameters<AlexApi["searchWeb"]>[0]) => api().searchWeb(request),
  openExternal: (url: string) => api().openExternal(url),
  openWeatherSearch: (city: string, when?: string) =>
    api().openWeatherSearch(city, when),
  getLoginItemStatus: () => api().getLoginItemStatus(),
  setLoginItemEnabled: (enabled: boolean) => api().setLoginItemEnabled(enabled),
  createDesktopShortcut: () => api().createDesktopShortcut(),
  startVoice: () => api().startVoice(),
  sendVoiceAudio: (pcm: ArrayBuffer) => api().sendVoiceAudio(pcm),
  sendVoiceText: (text: string) => api().sendVoiceText(text),
  interruptVoice: () => api().interruptVoice(),
  stopVoice: () => api().stopVoice(),
  onVoiceEvent: (listener: Parameters<AlexApi["onVoiceEvent"]>[0]) =>
    api().onVoiceEvent(listener),
  getWakeStatus: () =>
    api().getWakeStatus
      ? api().getWakeStatus!()
      : Promise.resolve({ enabled: false, running: false, ready: false, model: "hey_jarvis", threshold: 0.5 }),
  toggleWakeWord: (enabled: boolean, model?: string, threshold?: number) =>
    api().toggleWakeWord
      ? (model !== undefined || threshold !== undefined
          ? api().toggleWakeWord!(enabled, model, threshold)
          : api().toggleWakeWord!(enabled))
      : Promise.resolve({ enabled, running: enabled, ready: true, model: model || "hey_jarvis", threshold: threshold || 0.5 }),
  installWakeModels: () =>
    api().installWakeModels
      ? api().installWakeModels!()
      : Promise.resolve({ ok: true, message: "Wake word ready", ready: true }),
  wakeAssistant: () =>
    api().wakeAssistant
      ? api().wakeAssistant!()
      : Promise.resolve({ status: "ok", state: "LISTENING" }),
  sleepAssistant: () =>
    api().sleepAssistant
      ? api().sleepAssistant!()
      : Promise.resolve({ status: "ok", state: "SLEEPING" }),
  ensureMicrophoneAccess: () =>
    api().ensureMicrophoneAccess
      ? api().ensureMicrophoneAccess!()
      : Promise.resolve({ granted: true, status: "granted" }),
  getMediaStatus: () =>
    api().getMediaStatus
      ? api().getMediaStatus!()
      : Promise.resolve({
          active: false,
          source: "",
          title: "",
          url: "",
          audio_url: "",
          is_playing: false,
          is_muted: true,
          source_type: "none",
          error: null,
        }),
  resolveMedia: (source: string) =>
    api().resolveMedia
      ? api().resolveMedia!(source)
      : Promise.resolve({
          url: source.toLowerCase().includes("youtube")
            ? "https://www.youtube.com/embed?listType=search&list=trending&autoplay=1"
            : source,
          audio_url: "",
          title: source.toLowerCase().includes("youtube") ? "YouTube" : "Media",
          source_type: source.toLowerCase().includes("youtube") ? "youtube" : "direct",
          error: null,
        }),
  controlMedia: (action: string, source?: string, title?: string, muted?: boolean) =>
    api().controlMedia
      ? api().controlMedia!(action, source, title, muted)
      : Promise.resolve({
          active: action === "play",
          source: source || "",
          title: title || "",
          url: source || "",
          audio_url: "",
          is_playing: action === "play",
          is_muted: muted ?? true,
          source_type: "direct",
          error: null,
        }),
};
