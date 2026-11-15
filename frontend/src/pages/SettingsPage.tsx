import { useEffect, useState, type FormEvent } from "react";

import { alexApi } from "../services/alexApi";
import type { AppSettings, SettingsView, WakeStatusResponse } from "../types/api";

interface SettingsPageProps {
  settings: SettingsView | null;
  onSave: (settings: Partial<AppSettings>) => Promise<void>;
  onSaveKey: (key: string) => Promise<void>;
  selectedModel?: string;
  onSelectModel?: (model: string) => void;
  wakeWordStatus?: WakeStatusResponse | null;
  onToggleWakeWord?: () => Promise<void>;
  onPurgeData?: () => void;
}

interface AudioInputDevice {
  deviceId: string;
  label: string;
}

const THEME_PRESETS = [
  { name: "Holographic Cyan", color: "#00d4ff" },
  { name: "Matrix Green", color: "#20d6a0" },
  { name: "Electric Indigo", color: "#7a5af8" },
  { name: "Tactical Amber", color: "#ffb547" },
];

const AVAILABLE_MODELS = [
  {
    id: "gemini-2.5-flash-native-audio-preview-12-2025",
    name: "Gemini 2.5 Flash Native Audio",
    tag: "LIVE VOICE · RECOMMENDED",
    description: "Lowest latency bidirectional streaming with native speech reasoning.",
  },
  {
    id: "gemini-3.1-flash-live-preview",
    name: "Gemini 3.1 Flash Live Preview",
    tag: "NEXT-GEN EXPERIMENTAL",
    description: "Next-generation multimodal model with enhanced instruction following.",
  },
  {
    id: "gemini-2.5-flash",
    name: "Gemini 2.5 Flash",
    tag: "BALANCED FAST",
    description: "High speed multimodal intelligence for chat, vision, and documents.",
  },
  {
    id: "gemini-2.5-pro",
    name: "Gemini 2.5 Pro",
    tag: "DEEP REASONING",
    description: "Maximum reasoning depth for complex code generation and analysis.",
  },
];

export function SettingsPage({
  settings,
  onSave,
  onSaveKey,
  selectedModel: externalSelectedModel,
  onSelectModel,
  wakeWordStatus,
  onToggleWakeWord,
  onPurgeData,
}: SettingsPageProps) {
  const [form, setForm] = useState<AppSettings>({
    assistant_name: "Alex",
    user_name: "",
    accent_color: "#00d4ff",
    operating_system: "Windows",
    voice_name: "Charon",
    hud_style: "face",
    audio_input_device_id: "",
    audio_output_device_id: "",
    push_to_talk_enabled: false,
  });
  const [key, setKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [keySource, setKeySource] = useState<string>("config/api_keys.json");
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<
    "voice" | "model" | "audio" | "wake" | "theme" | "performance" | "privacy"
  >("voice");

  // Audio input devices
  const [audioInputs, setAudioInputs] = useState<AudioInputDevice[]>([]);

  // Selected Gemini model
  const [selectedModel, setSelectedModel] = useState<string>(
    externalSelectedModel ||
      localStorage.getItem("alex_selected_model") ||
      "gemini-2.5-flash-native-audio-preview-12-2025",
  );

  // Performance mode state
  const [lowPowerMode, setLowPowerMode] = useState<boolean>(() => {
    return localStorage.getItem("alex_low_power_mode") === "true";
  });

  // Data retention policy state
  const [dataRetentionMode, setDataRetentionMode] = useState<"persistent" | "session">(() => {
    return (localStorage.getItem("alex_data_retention") as "persistent" | "session") || "persistent";
  });

  // Wake word threshold local state
  const [wakeThreshold, setWakeThreshold] = useState<number>(wakeWordStatus?.threshold ?? 0.5);
  const [wakeWordBusy, setWakeWordBusy] = useState(false);

  useEffect(() => {
    if (settings) {
      setForm((current) => ({ ...current, ...settings.settings }));
    }
  }, [settings]);

  useEffect(() => {
    let active = true;
    async function loadKey() {
      try {
        const details = await alexApi.getApiKey();
        if (active && details) {
          if (details.api_key) {
            setKey(details.api_key);
          }
          if (details.source) {
            setKeySource(details.source);
          }
        }
      } catch (err) {
        console.warn("Could not read API key:", err);
      }
    }
    void loadKey();
    return () => {
      active = false;
    };
  }, []);

  // Enumerate input devices
  useEffect(() => {
    async function enumerateMicrophones() {
      if (!navigator.mediaDevices?.enumerateDevices) return;
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const inputs = devices
          .filter((d) => d.kind === "audioinput" && d.deviceId)
          .map((d, index) => ({
            deviceId: d.deviceId,
            label: d.label || `Microphone ${index + 1}`,
          }));
        setAudioInputs(inputs);
      } catch (err) {
        console.warn("Could not enumerate audio input devices:", err);
      }
    }
    void enumerateMicrophones();
  }, []);

  async function submitSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      await onSave(form);
      if (onSelectModel) {
        onSelectModel(selectedModel);
      } else {
        localStorage.setItem("alex_selected_model", selectedModel);
      }
    } finally {
      setSaving(false);
    }
  }

  async function submitKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      await onSaveKey(key);
      const details = await alexApi.getApiKey();
      if (details?.api_key) {
        setKey(details.api_key);
      }
    } finally {
      setSaving(false);
    }
  }

  function handleModelChange(modelId: string) {
    setSelectedModel(modelId);
    localStorage.setItem("alex_selected_model", modelId);
    if (onSelectModel) {
      onSelectModel(modelId);
    }
  }

  function handleLowPowerToggle(enabled: boolean) {
    setLowPowerMode(enabled);
    localStorage.setItem("alex_low_power_mode", enabled ? "true" : "false");
    if (enabled) {
      document.documentElement.setAttribute("data-low-power", "true");
    } else {
      document.documentElement.removeAttribute("data-low-power");
    }
  }

  function handleRetentionChange(mode: "persistent" | "session") {
    setDataRetentionMode(mode);
    localStorage.setItem("alex_data_retention", mode);
  }

  async function handleToggleWake() {
    setWakeWordBusy(true);
    try {
      if (onToggleWakeWord) {
        await onToggleWakeWord();
      } else {
        const next = !wakeWordStatus?.enabled;
        await alexApi.toggleWakeWord(next, undefined, wakeThreshold);
      }
    } finally {
      setWakeWordBusy(false);
    }
  }

  async function handleUpdateWakeThreshold(threshold: number) {
    setWakeThreshold(threshold);
    if (wakeWordStatus?.enabled) {
      try {
        await alexApi.toggleWakeWord(true, undefined, threshold);
      } catch (err) {
        console.warn("Could not update wake word sensitivity:", err);
      }
    }
  }

  return (
    <section className="page-content settings-layout">
      <div className="section-heading">
        <div>
          <div className="eyebrow">SYSTEM & PREFERENCES</div>
          <h3>Make Alex yours</h3>
          <p className="section-description">
            Configure local voice persona, Gemini intelligence tier, microphone hardware, and privacy parameters.
          </p>
        </div>
      </div>

      <nav className="settings-tab-nav" aria-label="Settings categories">
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === "voice" ? "is-active" : ""}`}
          onClick={() => setActiveTab("voice")}
        >
          🎙 VOICE & PERSONA
        </button>
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === "model" ? "is-active" : ""}`}
          onClick={() => setActiveTab("model")}
        >
          ⚡ MODEL & COGNITION
        </button>
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === "audio" ? "is-active" : ""}`}
          onClick={() => setActiveTab("audio")}
        >
          🔊 MIC & HARDWARE
        </button>
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === "wake" ? "is-active" : ""}`}
          onClick={() => setActiveTab("wake")}
        >
          👁 WAKE WORD
        </button>
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === "theme" ? "is-active" : ""}`}
          onClick={() => setActiveTab("theme")}
        >
          🎨 THEME & DISPLAY
        </button>
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === "performance" ? "is-active" : ""}`}
          onClick={() => setActiveTab("performance")}
        >
          🚀 PERFORMANCE
        </button>
        <button
          type="button"
          className={`settings-tab-btn ${activeTab === "privacy" ? "is-active" : ""}`}
          onClick={() => setActiveTab("privacy")}
        >
          🔒 RETENTION & PRIVACY
        </button>
      </nav>

      {/* VOICE & PERSONA TAB */}
      {activeTab === "voice" && (
        <form className="panel settings-panel" onSubmit={submitSettings}>
          <div className="panel-heading">
            <div className="panel-icon">🎙</div>
            <div>
              <h4>Voice & Assistant Persona</h4>
              <p>Configure how Alex speaks, addresses you, and renders on the HUD.</p>
            </div>
          </div>
          <div className="form-row">
            <label className="field">
              <span>Assistant name</span>
              <input
                maxLength={50}
                onChange={(event) =>
                  setForm((current) => ({ ...current, assistant_name: event.target.value }))
                }
                required
                value={form.assistant_name}
              />
            </label>
            <label className="field">
              <span>Your name <small>OPTIONAL</small></span>
              <input
                maxLength={80}
                onChange={(event) =>
                  setForm((current) => ({ ...current, user_name: event.target.value }))
                }
                placeholder="How should Alex address you?"
                value={form.user_name}
              />
            </label>
          </div>

          <div className="form-row">
            <label className="field">
              <span>Assistant voice persona</span>
              <select
                onChange={(event) => {
                  const voiceName = event.target.value;
                  if (
                    voiceName === "Charon" ||
                    voiceName === "Puck" ||
                    voiceName === "Kore" ||
                    voiceName === "Fenrir" ||
                    voiceName === "Aoede"
                  ) {
                    setForm((current) => ({ ...current, voice_name: voiceName }));
                  }
                }}
                value={form.voice_name}
              >
                <option value="Charon">Charon (Deep, measured, calm)</option>
                <option value="Puck">Puck (Energetic, sharp, concise)</option>
                <option value="Kore">Kore (Smooth, articulate, warm)</option>
                <option value="Fenrir">Fenrir (Authoritative, robust)</option>
                <option value="Aoede">Aoede (Bright, melodic, clear)</option>
              </select>
              <small>Applies when the next Gemini Live voice session starts.</small>
            </label>

            <label className="field">
              <span>HUD centrepiece / Visualization</span>
              <select
                onChange={(event) => {
                  const style = event.target.value as any;
                  if (
                    style === "face" ||
                    style === "core" ||
                    style === "robot" ||
                    style === "realistic_humanoid"
                  ) {
                    setForm((current) => ({ ...current, hud_style: style }));
                  }
                }}
                value={form.hud_style}
              >
                <option value="face">Animated face</option>
                <option value="core">Reactor core</option>
                <option value="robot">Realistic humanoid robot</option>
              </select>
            </label>
          </div>

          <div className="form-row">
            <label className="field">
              <span>Operating system</span>
              <select
                onChange={(event) => {
                  const operatingSystem = event.target.value;
                  if (
                    operatingSystem === "Windows" ||
                    operatingSystem === "macOS" ||
                    operatingSystem === "Linux"
                  ) {
                    setForm((current) => ({ ...current, operating_system: operatingSystem }));
                  }
                }}
                value={form.operating_system}
              >
                <option value="Windows">Windows</option>
                <option value="macOS">macOS</option>
                <option value="Linux">Linux</option>
              </select>
            </label>

            <label className="field">
              <span>Push-to-talk mode</span>
              <select
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    push_to_talk_enabled: event.target.value === "true",
                  }))
                }
                value={form.push_to_talk_enabled ? "true" : "false"}
              >
                <option value="false">Open Mic / Continuous Voice Activation</option>
                <option value="true">Push-to-Talk (Hold Spacebar to speak)</option>
              </select>
            </label>
          </div>

          <div className="form-actions">
            <button className="button button-primary" disabled={saving} type="submit">
              {saving ? "Saving..." : "Save preferences"}
            </button>
          </div>
        </form>
      )}

      {/* MODEL & COGNITION TAB */}
      {activeTab === "model" && (
        <>
          <div className="panel settings-panel">
            <div className="panel-heading">
              <div className="panel-icon">⚡</div>
              <div>
                <h4>Gemini Cognition Model</h4>
                <p>Choose the model profile driving Alex's Live audio responses and reasoning.</p>
              </div>
            </div>

            <div className="model-selection-grid">
              {AVAILABLE_MODELS.map((model) => (
                <div
                  key={model.id}
                  className={`model-card ${selectedModel === model.id ? "is-selected" : ""}`}
                  onClick={() => handleModelChange(model.id)}
                >
                  <div className="model-card-header">
                    <span className="model-name">{model.name}</span>
                    <span className="model-tag">{model.tag}</span>
                  </div>
                  <p className="model-desc">{model.description}</p>
                  <div className="model-footer">
                    <code>{model.id}</code>
                    <button
                      type="button"
                      className={`button button-small ${selectedModel === model.id ? "button-primary" : "button-secondary"}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleModelChange(model.id);
                      }}
                    >
                      {selectedModel === model.id ? "✓ ACTIVE" : "SELECT"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <form className="panel settings-panel" onSubmit={submitKey}>
            <div className="panel-heading">
              <div className="panel-icon key-icon">⌑</div>
              <div>
                <h4>Model Credential</h4>
                <p>
                  {settings?.api_key_configured
                    ? "Credential configured and active from JSON configuration file."
                    : "A Gemini API key is required for live voice, conversation, and document analysis."}
                </p>
              </div>
            </div>
            <label className="field">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                <span>Gemini API Key</span>
                <button
                  type="button"
                  className="button button-small"
                  onClick={() => setShowKey(!showKey)}
                  style={{ fontSize: "10px", padding: "2px 8px" }}
                >
                  {showKey ? "Hide Key" : "Show Key"}
                </button>
              </div>
              <input
                autoComplete="new-password"
                maxLength={512}
                minLength={16}
                onChange={(event) => setKey(event.target.value)}
                placeholder="Paste Gemini API key (e.g. AIzaSy... or AQ...)"
                type={showKey ? "text" : "password"}
                value={key}
              />
            </label>
            <div className="secure-hint">
              <span aria-hidden="true">▣</span>
              Stored in <code>{keySource}</code> and read directly from this JSON configuration file.
            </div>
            <div className="form-actions">
              <button className="button button-secondary" disabled={saving || key.length < 16} type="submit">
                {saving ? "Saving..." : settings?.api_key_configured ? "Update in api_keys.json" : "Save to api_keys.json"}
              </button>
            </div>
          </form>
        </>
      )}

      {/* MIC & HARDWARE TAB */}
      {activeTab === "audio" && (
        <form className="panel settings-panel" onSubmit={submitSettings}>
          <div className="panel-heading">
            <div className="panel-icon">🔊</div>
            <div>
              <h4>Microphone & Audio Hardware</h4>
              <p>Select your dedicated input hardware for minimal ambient distortion.</p>
            </div>
          </div>

          <label className="field">
            <span>Primary microphone device</span>
            <select
              value={form.audio_input_device_id || ""}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  audio_input_device_id: event.target.value,
                }))
              }
            >
              <option value="">Default System Microphone</option>
              {audioInputs.map((device) => (
                <option key={device.deviceId} value={device.deviceId}>
                  {device.label}
                </option>
              ))}
            </select>
            <small>
              {audioInputs.length > 0
                ? `${audioInputs.length} microphone device(s) detected.`
                : "Using system default microphone stream."}
            </small>
          </label>

          <div className="hardware-specs-box">
            <div className="spec-row">
              <span className="spec-label">INPUT RATE:</span>
              <span className="spec-value">16,000 Hz (PCM16 Little-Endian mono)</span>
            </div>
            <div className="spec-row">
              <span className="spec-label">DSP PROCESSING:</span>
              <span className="spec-value">Echo Cancellation, Noise Suppression, Auto Gain</span>
            </div>
            <div className="spec-row">
              <span className="spec-label">OUTPUT RATE:</span>
              <span className="spec-value">24,000 Hz Web Audio Sink</span>
            </div>
          </div>

          <div className="form-actions">
            <button className="button button-primary" disabled={saving} type="submit">
              {saving ? "Saving..." : "Save audio settings"}
            </button>
          </div>
        </form>
      )}

      {/* WAKE WORD TAB */}
      {activeTab === "wake" && (
        <div className="panel settings-panel">
          <div className="panel-heading">
            <div className="panel-icon">👁</div>
            <div>
              <h4>Local Wake Word Detection</h4>
              <p>Listen hands-free for "Hey Alex" using on-device acoustic keyword spotting.</p>
            </div>
          </div>

          <div className="wake-status-card">
            <div className="wake-status-indicator">
              <span
                className={`status-dot ${wakeWordStatus?.enabled ? "is-live" : "is-idle"}`}
              />
              <span className="wake-status-text">
                {wakeWordStatus?.ready
                  ? wakeWordStatus.enabled
                    ? "WAKE WORD ACTIVE · LISTENING FOR 'HEY ALEX'"
                    : "WAKE WORD STANDBY (OFF)"
                  : "ACOUSTIC MODELS REQUIRED"}
              </span>
            </div>
            <button
              type="button"
              className={`button ${wakeWordStatus?.enabled ? "button-danger" : "button-primary"}`}
              onClick={() => void handleToggleWake()}
              disabled={wakeWordBusy}
            >
              {wakeWordBusy
                ? "PROCESSING…"
                : wakeWordStatus?.enabled
                ? "DISABLE WAKE WORD"
                : "ENABLE 'HEY ALEX'"}
            </button>
          </div>

          <label className="field" style={{ marginTop: 20 }}>
            <span>
              Detection Sensitivity (Threshold: {wakeThreshold.toFixed(2)})
            </span>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={wakeThreshold}
              onChange={(e) => void handleUpdateWakeThreshold(parseFloat(e.target.value))}
            />
            <small>Lower values trigger more easily; higher values prevent false positives.</small>
          </label>
        </div>
      )}

      {/* THEME & DISPLAY TAB */}
      {activeTab === "theme" && (
        <form className="panel settings-panel" onSubmit={submitSettings}>
          <div className="panel-heading">
            <div className="panel-icon">🎨</div>
            <div>
              <h4>HUD Theme & Semantic Palette</h4>
              <p>Customize the visual accent tokens and holographic styling.</p>
            </div>
          </div>

          <div className="theme-preset-grid">
            {THEME_PRESETS.map((preset) => (
              <button
                key={preset.name}
                type="button"
                className={`theme-chip ${form.accent_color.toLowerCase() === preset.color.toLowerCase() ? "is-selected" : ""}`}
                style={{ borderColor: preset.color }}
                onClick={() => setForm((c) => ({ ...c, accent_color: preset.color }))}
              >
                <span className="theme-color-preview" style={{ background: preset.color }} />
                <span className="theme-name">{preset.name}</span>
                <span className="theme-hex">{preset.color}</span>
              </button>
            ))}
          </div>

          <label className="field color-field" style={{ marginTop: 16 }}>
            <span>Custom Accent Color</span>
            <div className="color-control">
              <input
                aria-label="Accent color"
                onChange={(event) =>
                  setForm((current) => ({ ...current, accent_color: event.target.value }))
                }
                type="color"
                value={form.accent_color}
              />
              <code>{form.accent_color.toUpperCase()}</code>
            </div>
          </label>

          <div className="form-actions">
            <button className="button button-primary" disabled={saving} type="submit">
              {saving ? "Saving..." : "Apply theme"}
            </button>
          </div>
        </form>
      )}

      {/* PERFORMANCE TAB */}
      {activeTab === "performance" && (
        <div className="panel settings-panel">
          <div className="panel-heading">
            <div className="panel-icon">🚀</div>
            <div>
              <h4>Performance & Graphics Optimization</h4>
              <p>Tune frame rates, backdrop blur filters, and canvas animation rendering.</p>
            </div>
          </div>

          <div className="performance-toggle-card">
            <div>
              <strong>Low-Power Mode</strong>
              <p className="hint-text">
                Reduces HUD animation rate to 30 FPS, disables heavy backdrop blurs, and pauses canvas renders during background tabs.
              </p>
            </div>
            <button
              type="button"
              className={`button ${lowPowerMode ? "button-primary" : "button-secondary"}`}
              onClick={() => handleLowPowerToggle(!lowPowerMode)}
            >
              {lowPowerMode ? "LOW-POWER ACTIVE" : "STANDARD (60 FPS)"}
            </button>
          </div>

          <div className="hardware-specs-box" style={{ marginTop: 16 }}>
            <div className="spec-row">
              <span className="spec-label">TARGET FPS:</span>
              <span className="spec-value">{lowPowerMode ? "30 FPS" : "60 FPS"}</span>
            </div>
            <div className="spec-row">
              <span className="spec-label">CANVAS RENDERER:</span>
              <span className="spec-value">{lowPowerMode ? "Simplified (No Glow/Trails)" : "Full Holographic Shader"}</span>
            </div>
            <div className="spec-row">
              <span className="spec-label">BACKGROUND PAUSE:</span>
              <span className="spec-value">Enabled (Window visibility change detection)</span>
            </div>
          </div>
        </div>
      )}

      {/* RETENTION & PRIVACY TAB */}
      {activeTab === "privacy" && (
        <div className="panel settings-panel">
          <div className="panel-heading">
            <div className="panel-icon">🔒</div>
            <div>
              <h4>Data Retention & Local Privacy</h4>
              <p>Control what is retained on this workstation and wipe temporary caches.</p>
            </div>
          </div>

          <label className="field">
            <span>Storage policy</span>
            <select
              value={dataRetentionMode}
              onChange={(e) => handleRetentionChange(e.target.value as "persistent" | "session")}
            >
              <option value="persistent">Persistent Local Storage (Retain chat & memory locally)</option>
              <option value="session">Session Only (Clear state on app close / restart)</option>
            </select>
          </label>

          <div className="danger-zone-box" style={{ marginTop: 24 }}>
            <div>
              <strong style={{ color: "var(--hud-danger, #ff5364)" }}>Purge Local Conversation History</strong>
              <p className="hint-text">
                Permanently wipes cached chat turns, voice transcripts, and temporary workspace files from this machine.
              </p>
            </div>
            <button
              type="button"
              className="button button-danger"
              onClick={() => {
                if (window.confirm("Are you sure you want to purge all local cached conversation turns and ephemeral data?")) {
                  if (onPurgeData) onPurgeData();
                  else {
                    localStorage.removeItem("alex_chat_history");
                    window.location.reload();
                  }
                }
              }}
            >
              PURGE LOCAL CACHE
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
