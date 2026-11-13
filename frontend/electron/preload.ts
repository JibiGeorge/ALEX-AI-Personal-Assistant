import { contextBridge, ipcRenderer, type IpcRendererEvent } from "electron";

import type {
  AlexApi,
  AppSettings,
  ConversationTurn,
  FileAttachment,
  MemoryCategory,
  MemoryEntry,
  MemoryWrite,
  LiveVoiceEvent,
  LoginItemStatus,
  SettingsView,
  Reminder,
  WebSearchRequest,
  SystemAlert,
  ActionDescriptor,
  ActionExecution,
} from "../src/types/api";

const api: AlexApi = {
  toggleFullscreen: () => ipcRenderer.invoke("alex:window:toggle-fullscreen"),
  getStatus: () => ipcRenderer.invoke("alex:status"),
  getSystemMetrics: () => ipcRenderer.invoke("alex:system:metrics"),
  getSystemVerification: () =>
    ipcRenderer.invoke("alex:system:verification") as Promise<any>,
  getSystemAlerts: () =>
    ipcRenderer.invoke("alex:system:alerts") as Promise<{ alerts: SystemAlert[] }>,
  getSystemBriefing: () =>
    ipcRenderer.invoke("alex:system:briefing") as Promise<any>,
  listActions: () =>
    ipcRenderer.invoke("alex:actions:list") as Promise<{ actions: ActionDescriptor[] }>,
  setActionEnabled: (actionId: string, enabled: boolean) =>
    ipcRenderer.invoke("alex:actions:enable", actionId, enabled) as Promise<ActionDescriptor>,
  executeAction: (actionId: string, parameters: Record<string, unknown>, confirmed: boolean) =>
    ipcRenderer.invoke("alex:actions:execute", actionId, parameters, confirmed) as Promise<ActionExecution>,
  getActionHistory: () =>
    ipcRenderer.invoke("alex:actions:history") as Promise<{ executions: ActionExecution[] }>,
  getSettings: () => ipcRenderer.invoke("alex:settings:get"),
  updateSettings: (settings: Partial<AppSettings>) =>
    ipcRenderer.invoke("alex:settings:update", settings),
  saveApiKey: (key: string) => ipcRenderer.invoke("alex:settings:key", key),
  listMemory: () => ipcRenderer.invoke("alex:memory:list"),
  upsertMemory: (category: MemoryCategory, key: string, value: MemoryWrite) =>
    ipcRenderer.invoke("alex:memory:upsert", category, key, value),
  deleteMemory: (category: MemoryCategory, key: string) =>
    ipcRenderer.invoke("alex:memory:delete", category, key),
  listReminders: () => ipcRenderer.invoke("alex:reminders:list") as Promise<{ reminders: Reminder[] }>,
  createReminder: (message: string, dueAt: string) =>
    ipcRenderer.invoke("alex:reminders:create", message, dueAt) as Promise<Reminder>,
  cancelReminder: (id: string) => ipcRenderer.invoke("alex:reminders:cancel", id),
  listDueReminders: () =>
    ipcRenderer.invoke("alex:reminders:due") as Promise<{ reminders: Reminder[] }>,
  markReminderDelivered: (id: string) =>
    ipcRenderer.invoke("alex:reminders:delivered", id) as Promise<Reminder>,
  notifyReminder: (message: string) =>
    ipcRenderer.invoke("alex:reminders:notify", message),
  notifySystemAlert: (message: string) =>
    ipcRenderer.invoke("alex:system:alert:notify", message),
  sendMessage: (
    text: string,
    conversationId: string | null,
    attachment?: FileAttachment,
  ) => ipcRenderer.invoke("alex:conversation:turn", text, conversationId, attachment),
  captureScreen: () =>
    ipcRenderer.invoke("alex:screen:capture") as Promise<FileAttachment | null>,
  searchWeb: (request: WebSearchRequest) => ipcRenderer.invoke("alex:web:search", request),
  openExternal: (url: string) => ipcRenderer.invoke("alex:open-external", url),
  openWeatherSearch: (city: string, when?: string) =>
    ipcRenderer.invoke("alex:weather:search", city, when),
  getLoginItemStatus: () =>
    ipcRenderer.invoke("alex:app:autostart:get") as Promise<LoginItemStatus>,
  setLoginItemEnabled: (enabled: boolean) =>
    ipcRenderer.invoke("alex:app:autostart:set", enabled) as Promise<LoginItemStatus>,
  createDesktopShortcut: () => ipcRenderer.invoke("alex:app:shortcut:create"),
  startVoice: () => ipcRenderer.invoke("alex:voice:start"),
  sendVoiceAudio: (pcm: ArrayBuffer) => ipcRenderer.send("alex:voice:audio", pcm),
  sendVoiceText: (text: string) => ipcRenderer.invoke("alex:voice:text", text),
  interruptVoice: () => ipcRenderer.invoke("alex:voice:interrupt"),
  stopVoice: () => ipcRenderer.invoke("alex:voice:stop"),
  onVoiceEvent: (listener: (event: LiveVoiceEvent) => void) => {
    const handler = (_event: IpcRendererEvent, payload: LiveVoiceEvent) => listener(payload);
    ipcRenderer.on("alex:voice:event", handler);
    return () => ipcRenderer.removeListener("alex:voice:event", handler);
  },
  getWakeStatus: () => ipcRenderer.invoke("alex:wake-word:status"),
  toggleWakeWord: (enabled: boolean, model?: string, threshold?: number) =>
    ipcRenderer.invoke("alex:wake-word:toggle", enabled, model, threshold),
  installWakeModels: () => ipcRenderer.invoke("alex:wake-word:install"),
  wakeAssistant: () => ipcRenderer.invoke("alex:voice:wake"),
  sleepAssistant: () => ipcRenderer.invoke("alex:voice:sleep"),
  ensureMicrophoneAccess: () => ipcRenderer.invoke("alex:microphone:ensure-access"),
  getMediaStatus: () => ipcRenderer.invoke("alex:media:status"),
  resolveMedia: (source: string) => ipcRenderer.invoke("alex:media:resolve", source),
  controlMedia: (action: string, source?: string, title?: string, muted?: boolean) =>
    ipcRenderer.invoke("alex:media:control", action, source, title, muted),
};

contextBridge.exposeInMainWorld("alex", api);

export type { AlexApi, AppSettings, ConversationTurn, MemoryEntry, SettingsView };
