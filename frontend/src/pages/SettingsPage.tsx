import { useEffect, useState, type FormEvent } from "react";

import type { AppSettings, SettingsView } from "../types/api";

interface SettingsPageProps {
  settings: SettingsView | null;
  onSave: (settings: Partial<AppSettings>) => Promise<void>;
  onSaveKey: (key: string) => Promise<void>;
}

export function SettingsPage({ settings, onSave, onSaveKey }: SettingsPageProps) {
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
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) {
      setForm((current) => ({ ...current, ...settings.settings }));
    }
  }, [settings]);

  async function submitSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  }

  async function submitKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      await onSaveKey(key);
      setKey("");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="page-content settings-layout">
      <div className="section-heading">
        <div>
          <div className="eyebrow">PREFERENCES</div>
          <h3>Make Alex yours</h3>
        </div>
      </div>
      <form className="panel settings-panel" onSubmit={submitSettings}>
        <div className="panel-heading">
          <div className="panel-icon">✳</div>
          <div>
            <h4>Assistant profile</h4>
            <p>These preferences are saved locally for this account.</p>
          </div>
        </div>
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
          <span>Assistant voice</span>
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
            <option value="Charon">Charon</option>
            <option value="Puck">Puck</option>
            <option value="Kore">Kore</option>
            <option value="Fenrir">Fenrir</option>
            <option value="Aoede">Aoede</option>
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
        <label className="field color-field">
          <span>Accent color</span>
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
            {saving ? "Saving..." : "Save preferences"}
          </button>
        </div>
      </form>

      <form className="panel settings-panel" onSubmit={submitKey}>
        <div className="panel-heading">
          <div className="panel-icon key-icon">⌑</div>
          <div>
            <h4>Model credential</h4>
            <p>
              {settings?.api_key_configured
                ? "A credential is saved in your operating system's secure store."
                : "A Gemini API key is required for text conversation and attached-file analysis."}
            </p>
          </div>
        </div>
        <label className="field">
          <span>Gemini API key</span>
          <input
            autoComplete="new-password"
            maxLength={512}
            minLength={16}
            onChange={(event) => setKey(event.target.value)}
            placeholder={settings?.api_key_configured ? "Enter a new key to replace" : "Paste API key"}
            type="password"
            value={key}
          />
        </label>
        <div className="secure-hint">
          <span aria-hidden="true">▣</span>
          Alex stores this value using the operating system credential manager.
          It is never returned to the interface.
        </div>
        <div className="form-actions">
          <button className="button button-secondary" disabled={saving || key.length < 16} type="submit">
            {saving ? "Saving..." : "Save secure credential"}
          </button>
        </div>
      </form>
    </section>
  );
}
