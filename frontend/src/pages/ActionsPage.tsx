import { useEffect, useState } from "react";

import { alexApi } from "../services/alexApi";
import type { ActionDescriptor, ActionExecution } from "../types/api";

interface ActionsPageProps {
  onError: (message: string) => void;
}

export function ActionsPage({ onError }: ActionsPageProps) {
  const [actions, setActions] = useState<ActionDescriptor[]>([]);
  const [history, setHistory] = useState<ActionExecution[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [parameters, setParameters] = useState("{}");
  const [confirmed, setConfirmed] = useState(false);
  const [lastResult, setLastResult] = useState<ActionExecution | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const [actionList, executions] = await Promise.all([
        alexApi.listActions(),
        alexApi.getActionHistory(),
      ]);
      setActions(actionList.actions);
      setHistory(executions.executions);
      setSelectedId((current) =>
        actionList.actions.some((action) => action.action_id === current)
          ? current
          : actionList.actions[0]?.action_id ?? "",
      );
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not load actions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const selected = actions.find((action) => action.action_id === selectedId) ?? null;

  async function toggle(action: ActionDescriptor) {
    setBusy(true);
    try {
      await alexApi.setActionEnabled(action.action_id, !action.enabled);
      await refresh();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not update action.");
    } finally {
      setBusy(false);
    }
  }

  async function execute() {
    if (!selected) return;
    setBusy(true);
    try {
      const parsed: unknown = JSON.parse(parameters);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new Error("Action parameters must be a JSON object.");
      }
      const result = await alexApi.executeAction(
        selected.action_id,
        parsed as Record<string, unknown>,
        confirmed,
      );
      setLastResult(result);
      await refresh();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not execute action.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-content actions-layout">
      <div className="section-heading">
        <div>
          <div className="eyebrow">REGISTERED BACKEND CAPABILITIES</div>
          <h3>Actions</h3>
          <p className="section-description">
            This list comes from the Python action registry. Local changes and external actions require explicit confirmation.
          </p>
        </div>
        <span className="count-badge">{actions.length} registered</span>
      </div>

      {loading ? (
        <div className="empty-state">Loading registered actions...</div>
      ) : actions.length === 0 ? (
        <div className="empty-state">No actions are registered.</div>
      ) : (
        <div className="actions-grid">
          <div className="actions-list" aria-label="Registered actions">
            {actions.map((action) => (
              <article
                className={`action-card ${selectedId === action.action_id ? "action-selected" : ""}`}
                key={action.action_id}
              >
                <button
                  className="action-select"
                  onClick={() => {
                    setSelectedId(action.action_id);
                    setParameters("{}");
                    setLastResult(null);
                    setConfirmed(false);
                  }}
                  type="button"
                >
                  <span className="action-category">{action.category}</span>
                  <strong>{action.name}</strong>
                  <small>{action.description}</small>
                  {!action.enabled && (
                    <em>{action.missing_dependencies.length ? "Dependency unavailable" : "Disabled"}</em>
                  )}
                </button>
                <button
                  aria-label={`${action.enabled ? "Disable" : "Enable"} ${action.name}`}
                  className="action-toggle"
                  disabled={busy || action.missing_dependencies.length > 0}
                  onClick={() => void toggle(action)}
                  type="button"
                >
                  {action.enabled ? "ON" : "OFF"}
                </button>
              </article>
            ))}
          </div>

          <div className="panel action-detail">
            {selected ? (
              <>
                <div className="panel-heading">
                  <div className="panel-icon">⚡</div>
                  <div>
                    <h4>{selected.name}</h4>
                    <p>{selected.action_id} · timeout {selected.timeout_seconds}s</p>
                  </div>
                </div>
                <p className="action-description">{selected.description}</p>
                <label className="field">
                  <span>Parameters · JSON object</span>
                  <textarea
                    aria-label="Action parameters JSON"
                    onChange={(event) => setParameters(event.target.value)}
                    rows={6}
                    value={parameters}
                  />
                </label>
                {selected.requires_confirmation && (
                  <label className="action-confirm">
                    <input
                      checked={confirmed}
                      onChange={(event) => setConfirmed(event.target.checked)}
                      type="checkbox"
                    />
                    I confirm this action may contact an external service or change local data.
                  </label>
                )}
                <div className="form-actions">
                  <button
                    className="button button-primary"
                    disabled={busy || !selected.enabled || (selected.requires_confirmation && !confirmed)}
                    onClick={() => void execute()}
                    type="button"
                  >
                    {busy ? "Executing..." : "Execute action"}
                  </button>
                </div>
                {lastResult && (
                  <div className={`action-result action-result-${lastResult.status}`}>
                    <strong>{lastResult.status.toUpperCase()} · {lastResult.execution_time}s</strong>
                    <p>{lastResult.message}</p>
                    {lastResult.error && <pre>{lastResult.error}</pre>}
                    {lastResult.data !== null && <pre>{JSON.stringify(lastResult.data, null, 2)}</pre>}
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state">Select an action to inspect or run it.</div>
            )}
          </div>
        </div>
      )}

      <section className="panel action-history">
        <div className="panel-heading">
          <div className="panel-icon">◷</div>
          <div><h4>Recent executions</h4><p>Latest execution results from this backend session.</p></div>
        </div>
        {history.length === 0 ? (
          <p className="section-description">No actions have run in this session.</p>
        ) : (
          <ol>
            {history.slice(0, 20).map((item, index) => (
              <li key={`${item.action_id}-${index}`}>
                <strong>{item.action_id}</strong>
                <span className={`execution-status execution-${item.status}`}>{item.status}</span>
                <span>{item.message}</span>
              </li>
            ))}
          </ol>
        )}
      </section>
    </section>
  );
}
