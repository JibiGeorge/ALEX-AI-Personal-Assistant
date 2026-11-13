import { useEffect, useState, type FormEvent } from "react";

import { alexApi } from "../services/alexApi";
import type { Reminder } from "../types/api";

interface RemindersPageProps {
  onCreate: (message: string, dueAt: string) => Promise<void>;
  onCancel: (id: string) => Promise<void>;
  onError: (message: string) => void;
}

function localDateTimeValue(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export function RemindersPage({ onCreate, onCancel, onError }: RemindersPageProps) {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [message, setMessage] = useState("");
  const [dueAt, setDueAt] = useState(() => localDateTimeValue(new Date(Date.now() + 5 * 60_000)));
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const result = await alexApi.listReminders();
      setReminders(result.reminders);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not load reminders.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      await onCreate(message, new Date(dueAt).toISOString());
      setMessage("");
      await refresh();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not create reminder.");
    } finally {
      setBusy(false);
    }
  }

  async function cancel(id: string) {
    setBusy(true);
    try {
      await onCancel(id);
      await refresh();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not cancel reminder.");
    } finally {
      setBusy(false);
    }
  }

  const pending = reminders.filter((reminder) => reminder.status === "pending");
  const delivered = reminders.filter((reminder) => reminder.status === "delivered");

  return (
    <section className="page-content memory-layout">
      <div className="section-heading">
        <div>
          <div className="eyebrow">PERSONAL SCHEDULING</div>
          <h3>Reminders</h3>
          <p className="section-description">
            Alex checks reminders while the desktop app is running and shows a system notification.
          </p>
        </div>
        <span className="count-badge">{pending.length} pending</span>
      </div>

      <form className="panel memory-form" onSubmit={(event) => void submit(event)}>
        <label className="field">
          <span>Reminder</span>
          <input
            maxLength={200}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="What should Alex remind you about?"
            required
            value={message}
          />
        </label>
        <label className="field">
          <span>Date and time</span>
          <input
            min={localDateTimeValue(new Date())}
            onChange={(event) => setDueAt(event.target.value)}
            required
            type="datetime-local"
            value={dueAt}
          />
        </label>
        <div className="form-actions">
          <button className="button button-primary" disabled={busy || !message.trim()} type="submit">
            {busy ? "Saving..." : "Set reminder"}
          </button>
        </div>
      </form>

      {loading ? (
        <div className="empty-state">Loading reminders...</div>
      ) : reminders.length === 0 ? (
        <div className="empty-state">
          <div className="empty-mark">◷</div>
          <strong>No reminders yet</strong>
          <p>Set a reminder above. It will be stored locally on this device.</p>
        </div>
      ) : (
        <div className="memory-list">
          {[...pending, ...delivered].map((reminder) => (
            <article className="memory-item" key={reminder.id}>
              <div className="memory-item-main">
                <div className="memory-meta">
                  <span className="category-chip">
                    {reminder.status === "pending" ? "Scheduled" : "Delivered"}
                  </span>
                  <span>{new Date(reminder.due_at).toLocaleString()}</span>
                </div>
                <p>{reminder.message}</p>
              </div>
              {reminder.status === "pending" && (
                <button
                  aria-label={`Cancel reminder ${reminder.message}`}
                  className="icon-button danger"
                  disabled={busy}
                  onClick={() => void cancel(reminder.id)}
                  type="button"
                >
                  ×
                </button>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
