import { useState, type FormEvent } from "react";

import type { MemoryCategory, MemoryEntry } from "../types/api";

interface MemoryPageProps {
  entries: MemoryEntry[];
  busy: boolean;
  onSave: (category: MemoryCategory, key: string, value: string) => Promise<void>;
  onDelete: (category: MemoryCategory, key: string) => Promise<void>;
}

const categories: { id: MemoryCategory; label: string }[] = [
  { id: "identity", label: "Identity" },
  { id: "preferences", label: "Preferences" },
  { id: "projects", label: "Projects" },
  { id: "relationships", label: "Relationships" },
  { id: "wishes", label: "Wishes" },
  { id: "notes", label: "Notes" },
];

export function MemoryPage({ entries, busy, onSave, onDelete }: MemoryPageProps) {
  const [category, setCategory] = useState<MemoryCategory>("notes");
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      await onSave(category, key, value);
      setKey("");
      setValue("");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="page-content memory-layout">
      <div className="section-heading">
        <div>
          <div className="eyebrow">YOUR DATA</div>
          <h3>Personal memory</h3>
          <p className="section-description">
            Facts are saved locally and can be changed or removed at any time.
          </p>
        </div>
        <span className="count-badge">{entries.length} {entries.length === 1 ? "entry" : "entries"}</span>
      </div>

      <form className="panel memory-form" onSubmit={submit}>
        <div className="form-row">
          <label className="field">
            <span>Category</span>
            <select
              onChange={(event) => setCategory(event.target.value as MemoryCategory)}
              value={category}
            >
              {categories.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Memory key</span>
            <input
              maxLength={80}
              onChange={(event) => setKey(event.target.value)}
              placeholder="e.g. favorite_coffee"
              required
              value={key}
            />
          </label>
        </div>
        <label className="field">
          <span>Fact</span>
          <textarea
            maxLength={4000}
            onChange={(event) => setValue(event.target.value)}
            placeholder="Write a fact you want Alex to remember..."
            required
            rows={3}
            value={value}
          />
        </label>
        <div className="form-actions">
          <button className="button button-primary" disabled={saving || busy} type="submit">
            {saving ? "Saving..." : "Save memory"}
          </button>
        </div>
      </form>

      <div className="memory-list">
        {busy ? (
          <div className="empty-state">Loading your saved facts...</div>
        ) : entries.length === 0 ? (
          <div className="empty-state">
            <div className="empty-mark">✳</div>
            <strong>No memories saved yet</strong>
            <p>Add a fact above. It will remain on this device until you remove it.</p>
          </div>
        ) : (
          entries.map((entry) => (
            <article className="memory-item" key={`${entry.category}/${entry.key}`}>
              <div className="memory-item-main">
                <div className="memory-meta">
                  <span className="category-chip">{entry.category}</span>
                  <span>{entry.updated}</span>
                </div>
                <strong>{entry.key.replaceAll("_", " ")}</strong>
                <p>{entry.value}</p>
              </div>
              <button
                aria-label={`Delete ${entry.key}`}
                className="icon-button danger"
                disabled={busy}
                onClick={() => void onDelete(entry.category, entry.key)}
                type="button"
              >
                ×
              </button>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
