export type MemoryCategory =
  | "identity"
  | "preferences"
  | "projects"
  | "relationships"
  | "wishes"
  | "notes";

export type OperatingSystem = "Windows" | "macOS" | "Linux";
export type AssistantVoice = "Charon" | "Puck" | "Kore" | "Fenrir" | "Aoede";
export type HudStyle =
  | "face"
  | "core"
  | "robot"
  | "realistic_humanoid"
  | "existing_face"
  | "reactor_core";

export interface FileAttachment {
  name: string;
  mime_type: string;
  data_base64: string;
}

export interface ApiStatus {
  status: "ready";
  name: "Alex";
}

export interface AppSettings {
  assistant_name: string;
  user_name: string;
  accent_color: string;
  operating_system: OperatingSystem;
  voice_name: AssistantVoice;
  hud_style: HudStyle;
  audio_input_device_id: string;
  audio_output_device_id: string;
  push_to_talk_enabled: boolean;
}

export interface SettingsView {
  settings: AppSettings;
  api_key_configured: boolean;
}

export interface MemoryEntry {
  category: MemoryCategory;
  key: string;
  value: string;
  updated: string;
}

export interface MemoryWrite {
  value: string;
}

export interface ConversationTurn {
  conversation_id: string;
  text: string;
}

export type WebSearchMode = "search" | "news" | "research" | "price" | "compare";

export interface WebSearchRequest {
  query: string;
  mode: WebSearchMode;
  items?: string[];
  aspect?: string;
}

export interface WebSearchSource {
  title: string;
  url: string;
}

export interface WebSearchResponse {
  query: string;
  mode: WebSearchMode;
  answer: string;
  sources: WebSearchSource[];
}

export interface LoginItemStatus {
  supported: boolean;
  enabled: boolean;
  shortcutSupported: boolean;
}

export interface Reminder {
  id: string;
  message: string;
  due_at: string;
  status: "pending" | "delivered";
}

export type LiveVoiceEvent =
  | { type: "connected"; model: string }
  | { type: "audio"; pcm: Uint8Array }
  | {
      type: "turn_complete";
      input_text: string;
      output_text: string;
      interrupted: boolean;
    }
  | { type: "interrupted" }
  | { type: "model_fallback"; from_model: string; to_model: string; reason: string }
  | { type: "error"; message: string };

export interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  network_mb_per_sec: number | null;
  operating_system: string;
  uptime_seconds: number;
  process_count: number;
  gpu_percent: number | null;
  temperature_c: number | null;
}

export interface SystemAlert {
  metric: "cpu" | "memory" | "gpu" | "temperature";
  value: number;
  message: string;
}

export interface BriefingSystemSummary {
  cpu_percent: number;
  ram_percent: number;
  active_alerts_count: number;
  system_status: string;
}

export interface BriefingReminderSummary {
  total_pending: number;
  due_now: number;
  upcoming_messages: string[];
}

export interface BriefingResponse {
  greeting: string;
  assistant_name: string;
  user_name: string;
  timestamp_iso: string;
  system: BriefingSystemSummary;
  reminders: BriefingReminderSummary;
  known_identity_facts: string[];
}

export interface ActionDescriptor {
  action_id: string;
  name: string;
  description: string;
  category: string;
  parameters: Record<string, unknown>;
  enabled: boolean;
  missing_dependencies: string[];
  timeout_seconds: number;
  requires_confirmation: boolean;
}

export interface ActionExecution {
  action_id: string;
  status: "success" | "failed" | "rejected";
  data: unknown;
  message: string;
  error: string | null;
  execution_time: number;
}

export interface WakeStatusResponse {
  enabled: boolean;
  running: boolean;
  ready: boolean;
  model: string;
  threshold: number;
  last_detected_at?: number | null;
}

export interface HardwareVerification {
  os_name: string;
  os_version: string;
  architecture: string;
  cpu_model: string;
  cpu_physical_cores: number;
  cpu_logical_cores: number;
  cpu_percent: number;
  ram_total_gb: number;
  ram_available_gb: number;
  ram_percent: number;
  gpu_available: boolean;
  gpu_model?: string | null;
  gpu_percent?: number | null;
  gpu_temperature_c?: number | null;
  disk_total_gb: number;
  disk_free_gb: number;
  disk_percent: number;
  network_interfaces_count: number;
  internet_connected: boolean;
  uptime_seconds: number;
  process_count: number;
}

export interface ApplicationVerification {
  app_name: string;
  app_version: string;
  execution_environment: string;
  python_version: string;
  python_executable: string;
  fastapi_version: string;
  dependencies_installed: string[];
  missing_dependencies: string[];
  workspace_path: string;
  workspace_readable: boolean;
  workspace_writable: boolean;
  config_files_valid: boolean;
  secrets_sanitized: boolean;
}

export interface BackendDatabaseVerification {
  backend_online: boolean;
  loopback_endpoint: string;
  database_type: string;
  memory_store_accessible: boolean;
  memory_entries_count: number;
  reminder_store_accessible: boolean;
  active_reminders_count: number;
  scheduler_active: boolean;
  background_workers_active: boolean;
}

export interface AiEngineVerification {
  ollama_installed: boolean;
  ollama_running: boolean;
  ollama_version?: string | null;
  ollama_models: string[];
  ollama_default_model?: string | null;
  lmstudio_running: boolean;
  lmstudio_models: string[];
  cloud_provider: string;
  cloud_credentials_configured: boolean;
  cloud_connectivity_verified: boolean;
  cloud_models_available: string[];
  grounded_search_available: boolean;
}

export interface MediaStatus {
  active: boolean;
  source: string;
  title: string;
  url: string;
  audio_url?: string;
  is_playing: boolean;
  is_muted: boolean;
  source_type: string;
  error?: string | null;
}

export interface MediaResolveResponse {
  url: string;
  audio_url?: string;
  title: string;
  source_type: string;
  error?: string | null;
}

export interface FullSystemVerificationReport {
  timestamp: string;
  status: string;
  overall_score: number;
  hardware: HardwareVerification;
  application: ApplicationVerification;
  backend_database: BackendDatabaseVerification;
  ai_engines: AiEngineVerification;
}

export interface AlexApi {
  toggleFullscreen: () => Promise<boolean>;
  getStatus: () => Promise<ApiStatus>;
  getSystemMetrics: () => Promise<SystemMetrics>;
  getSystemVerification?: () => Promise<FullSystemVerificationReport>;
  getSystemAlerts: () => Promise<{ alerts: SystemAlert[] }>;
  getSystemBriefing?: () => Promise<BriefingResponse>;
  listActions: () => Promise<{ actions: ActionDescriptor[] }>;
  setActionEnabled: (actionId: string, enabled: boolean) => Promise<ActionDescriptor>;
  executeAction: (
    actionId: string,
    parameters: Record<string, unknown>,
    confirmed: boolean,
  ) => Promise<ActionExecution>;
  getActionHistory: () => Promise<{ executions: ActionExecution[] }>;
  getSettings: () => Promise<SettingsView>;
  updateSettings: (settings: Partial<AppSettings>) => Promise<SettingsView>;
  saveApiKey: (key: string) => Promise<{ configured: boolean }>;
  listMemory: () => Promise<{ entries: MemoryEntry[] }>;
  upsertMemory: (
    category: MemoryCategory,
    key: string,
    value: MemoryWrite,
  ) => Promise<MemoryEntry>;
  deleteMemory: (category: MemoryCategory, key: string) => Promise<boolean>;
  listReminders: () => Promise<{ reminders: Reminder[] }>;
  createReminder: (message: string, dueAt: string) => Promise<Reminder>;
  cancelReminder: (id: string) => Promise<void>;
  listDueReminders: () => Promise<{ reminders: Reminder[] }>;
  markReminderDelivered: (id: string) => Promise<Reminder>;
  notifyReminder: (message: string) => Promise<void>;
  notifySystemAlert: (message: string) => Promise<void>;
  sendMessage: (
    text: string,
    conversationId: string | null,
    attachment?: FileAttachment,
  ) => Promise<ConversationTurn>;
  captureScreen: () => Promise<FileAttachment | null>;
  searchWeb: (request: WebSearchRequest) => Promise<WebSearchResponse>;
  openExternal: (url: string) => Promise<void>;
  openWeatherSearch: (city: string, when?: string) => Promise<void>;
  getLoginItemStatus: () => Promise<LoginItemStatus>;
  setLoginItemEnabled: (enabled: boolean) => Promise<LoginItemStatus>;
  createDesktopShortcut: () => Promise<void>;
  startVoice: () => Promise<void>;
  sendVoiceAudio: (pcm: ArrayBuffer) => void;
  sendVoiceText: (text: string) => Promise<void>;
  interruptVoice: () => Promise<void>;
  stopVoice: () => Promise<void>;
  onVoiceEvent: (listener: (event: LiveVoiceEvent) => void) => () => void;
  getWakeStatus?: () => Promise<WakeStatusResponse>;
  toggleWakeWord?: (enabled: boolean, model?: string, threshold?: number) => Promise<WakeStatusResponse>;
  installWakeModels?: () => Promise<{ ok: boolean; message: string; ready: boolean }>;
  wakeAssistant?: () => Promise<{ status: string; state: string }>;
  sleepAssistant?: () => Promise<{ status: string; state: string }>;
  ensureMicrophoneAccess?: () => Promise<{ granted: boolean; status: string }>;
  getMediaStatus?: () => Promise<MediaStatus>;
  resolveMedia?: (source: string) => Promise<MediaResolveResponse>;
  controlMedia?: (action: string, source?: string, title?: string, muted?: boolean) => Promise<MediaStatus>;
}

declare global {
  interface Window {
    alex: AlexApi;
  }
}
