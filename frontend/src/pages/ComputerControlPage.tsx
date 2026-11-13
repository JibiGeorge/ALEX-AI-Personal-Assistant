import { useEffect, useState } from "react";

import { alexApi } from "../services/alexApi";
import type { ActionExecution } from "../types/api";

type DesktopOperation =
  | "move"
  | "click"
  | "click_current"
  | "double_click"
  | "right_click"
  | "drag"
  | "type"
  | "press"
  | "hotkey"
  | "scroll"
  | "screenshot"
  | "clipboard_read"
  | "clipboard_write"
  | "clipboard_paste"
  | "active_window"
  | "list_windows"
  | "focus_window"
  | "close_app"
  | "screen_find"
  | "clear_field"
  | "smart_type"
  | "wait"
  | "random_data"
  | "user_data";

interface ComputerStatus {
  permission_enabled: boolean;
  adapter_available: boolean;
  platform: string;
  active_operation: string | null;
  emergency_stop_requested: boolean;
}

interface PendingControlRequest {
  request_id: string;
  operation: DesktopOperation;
  parameters: Record<string, unknown>;
  expires_in_seconds: number;
}

interface ControlDecisionResult {
  status: string;
  data: unknown;
  message: string;
  error: string | null;
}

interface ComputerControlPageProps {
  onError: (message: string) => void;
  onDecision: (
    request: PendingControlRequest,
    approved: boolean,
    result: ControlDecisionResult,
  ) => Promise<void>;
}

const operationNames: Record<DesktopOperation, string> = {
  move: "Move pointer",
  click: "Left click",
  click_current: "Left click at current pointer",
  double_click: "Double click",
  right_click: "Right click",
  drag: "Drag pointer",
  type: "Type text",
  press: "Press key",
  hotkey: "Keyboard shortcut",
  scroll: "Scroll",
  screenshot: "Capture screenshot",
  clipboard_read: "Read clipboard",
  clipboard_write: "Write clipboard",
  clipboard_paste: "Paste text",
  active_window: "Inspect active window",
  list_windows: "List visible windows",
  focus_window: "Focus a window",
  close_app: "Request app close",
  screen_find: "Find a screen element",
  clear_field: "Clear focused field",
  smart_type: "Replace field text",
  wait: "Wait",
  random_data: "Generate fake form data",
  user_data: "Autofill profile/memory data",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asComputerStatus(value: unknown): ComputerStatus | null {
  if (
    !isRecord(value) ||
    typeof value.permission_enabled !== "boolean" ||
    typeof value.adapter_available !== "boolean" ||
    typeof value.platform !== "string" ||
    (value.active_operation !== null && typeof value.active_operation !== "string") ||
    typeof value.emergency_stop_requested !== "boolean"
  ) {
    return null;
  }
  return {
    permission_enabled: value.permission_enabled,
    adapter_available: value.adapter_available,
    platform: value.platform,
    active_operation: value.active_operation,
    emergency_stop_requested: value.emergency_stop_requested,
  };
}

function asPendingControlRequests(value: unknown): PendingControlRequest[] | null {
  if (!Array.isArray(value)) return null;
  const requests: PendingControlRequest[] = [];
  for (const item of value) {
    if (
      !isRecord(item) ||
      typeof item.request_id !== "string" ||
      typeof item.operation !== "string" ||
      !Object.hasOwn(operationNames, item.operation) ||
      !isRecord(item.parameters) ||
      typeof item.expires_in_seconds !== "number"
    ) {
      return null;
    }
    requests.push({
      request_id: item.request_id,
      operation: item.operation as DesktopOperation,
      parameters: item.parameters,
      expires_in_seconds: item.expires_in_seconds,
    });
  }
  return requests;
}

function resultError(result: ActionExecution): string {
  return result.error ?? result.message;
}

export function ComputerControlPage({ onError, onDecision }: ComputerControlPageProps) {
  const [status, setStatus] = useState<ComputerStatus | null>(null);
  const [pendingRequests, setPendingRequests] = useState<PendingControlRequest[]>([]);
  const [operation, setOperation] = useState<DesktopOperation>("click");
  const [values, setValues] = useState<Record<string, string>>({
    x: "100",
    y: "100",
    x2: "200",
    y2: "200",
    text: "",
    key: "enter",
    hotkey: "copy",
    direction: "down",
    amount: "3",
    title: "",
    application: "",
    description: "",
    clipboard_text: "",
    seconds: "1",
    data_type: "name",
    field: "name",
  });
  const [showPermissionDialog, setShowPermissionDialog] = useState(false);
  const [permissionConfirmed, setPermissionConfirmed] = useState(false);
  const [operationConfirmed, setOperationConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [activeOperation, setActiveOperation] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<ActionExecution | null>(null);
  const [stopMessage, setStopMessage] = useState("");

  async function refreshStatus() {
    try {
      const result = await alexApi.executeAction("computer.status", {}, false);
      if (result.status !== "success") throw new Error(resultError(result));
      const next = asComputerStatus(result.data);
      if (!next) throw new Error("Computer-control status response is invalid.");
      setStatus(next);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not read desktop-control status.");
    }
  }

  async function refreshPendingRequests() {
    try {
      const result = await alexApi.executeAction("computer.pending", {}, false);
      if (result.status !== "success") throw new Error(resultError(result));
      const requests = asPendingControlRequests(result.data);
      if (!requests) throw new Error("Pending computer-control response is invalid.");
      setPendingRequests(requests);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not check pending control requests.");
    }
  }

  useEffect(() => {
    void refreshStatus();
    void refreshPendingRequests();
    const interval = window.setInterval(() => void refreshPendingRequests(), 1_000);
    return () => window.clearInterval(interval);
  }, []);

  function setValue(name: string, value: string) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  function numericValue(name: string): number {
    const parsed = Number(values[name]);
    if (!Number.isInteger(parsed) || parsed < 0 || parsed > 100_000) {
      throw new Error(`${name} must be a whole number between 0 and 100000.`);
    }
    return parsed;
  }

  function buildParameters(): Record<string, unknown> {
    switch (operation) {
      case "move":
      case "click":
      case "double_click":
      case "right_click":
        return { operation, x: numericValue("x"), y: numericValue("y") };
      case "click_current":
        return { operation };
      case "drag":
        return {
          operation,
          x: numericValue("x"),
          y: numericValue("y"),
          x2: numericValue("x2"),
          y2: numericValue("y2"),
        };
      case "type":
        return { operation, text: values.text };
      case "press":
        return { operation, key: values.key };
      case "hotkey":
        return { operation, hotkey: values.hotkey };
      case "scroll":
        return {
          operation,
          direction: values.direction,
          amount: Number(values.amount),
        };
      case "screenshot":
        return { operation };
      case "clipboard_read":
      case "active_window":
      case "list_windows":
      case "clear_field":
        return { operation };
      case "clipboard_write":
      case "clipboard_paste":
        return { operation, clipboard_text: values.clipboard_text };
      case "focus_window":
        return { operation, title: values.title };
      case "close_app":
        return { operation, application: values.application };
      case "screen_find":
        return { operation, description: values.description };
      case "smart_type":
        return { operation, text: values.text, clear_first: true };
      case "wait":
        return { operation, seconds: Number(values.seconds) };
      case "random_data":
        return { operation, data_type: values.data_type || "name" };
      case "user_data":
        return { operation, field: values.field || "name" };
    }
  }

  async function grantPermission() {
    setBusy(true);
    try {
      const result = await alexApi.executeAction(
        "computer.permission",
        { enabled: true },
        true,
      );
      if (result.status !== "success") throw new Error(resultError(result));
      setStatus(asComputerStatus(result.data));
      setShowPermissionDialog(false);
      setPermissionConfirmed(false);
      setStopMessage("");
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not enable desktop control.");
    } finally {
      setBusy(false);
    }
  }

  async function revokePermission() {
    setBusy(true);
    try {
      const result = await alexApi.executeAction(
        "computer.permission",
        { enabled: false },
        true,
      );
      if (result.status !== "success") throw new Error(resultError(result));
      setStatus(asComputerStatus(result.data));
      setOperationConfirmed(false);
      setStopMessage("Desktop-control permission was revoked.");
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not revoke desktop control.");
    } finally {
      setBusy(false);
    }
  }

  async function executeControl() {
    if (!operationConfirmed) return;
    setBusy(true);
    setActiveOperation(operationNames[operation]);
    setLastResult(null);
    setStopMessage("");
    try {
      const result = await alexApi.executeAction(
        "computer.control",
        buildParameters(),
        true,
      );
      setLastResult(result);
      if (result.status !== "success") onError(resultError(result));
      await refreshStatus();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Desktop-control operation failed.");
    } finally {
      setBusy(false);
      setActiveOperation(null);
      setOperationConfirmed(false);
    }
  }

  async function emergencyStop() {
    try {
      const result = await alexApi.executeAction("computer.stop", {}, false);
      if (result.status !== "success") throw new Error(resultError(result));
      setStopMessage("Emergency stop sent. Any active operation will stop at its next safe checkpoint.");
      await refreshStatus();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Emergency stop failed.");
    }
  }

  async function handlePendingRequest(requestId: string, approve: boolean) {
    setBusy(true);
    const request = pendingRequests.find((item) => item.request_id === requestId);
    try {
      const result = await alexApi.executeAction(
        approve ? "computer.approve" : "computer.dismiss",
        { request_id: requestId },
        true,
      );
      if (result.status !== "success") onError(resultError(result));
      setLastResult(result);
      await Promise.all([refreshStatus(), refreshPendingRequests()]);
      if (request) await onDecision(request, approve, result);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not handle the assistant's request.");
    } finally {
      setBusy(false);
    }
  }

  const screenshot = lastResult?.status === "success" && isRecord(lastResult.data)
    ? lastResult.data
    : null;
  const canControl = status?.permission_enabled === true
    && !status.emergency_stop_requested;
  const requiresRearm = status?.emergency_stop_requested === true;

  return (
    <section className="page-content computer-control-layout">
      <div className="section-heading">
        <div>
          <div className="eyebrow">LOCAL DESKTOP PERMISSIONS</div>
          <h3>Computer Control</h3>
          <p className="section-description">
            Control runs only on this computer. Permission resets when the backend stops,
            and every operation needs separate confirmation.
          </p>
        </div>
        <span className={`count-badge ${status?.permission_enabled ? "control-permitted" : ""}`}>
          {status?.permission_enabled ? "PERMISSION ON" : "PERMISSION OFF"}
        </span>
      </div>

      <section className="panel computer-control-status" aria-live="polite">
        <div>
          <span>PLATFORM</span><strong>{status?.platform ?? "Checking…"}</strong>
        </div>
        <div>
          <span>CONTROLLER</span>
          <strong>{status?.adapter_available ? "AVAILABLE" : "UNAVAILABLE"}</strong>
        </div>
        <div>
          <span>EXECUTION</span>
          <strong>{activeOperation ?? status?.active_operation ?? "IDLE"}</strong>
        </div>
        <div>
          <span>PERMISSION</span>
          <strong>{status?.permission_enabled ? "SESSION ONLY" : "NOT GRANTED"}</strong>
        </div>
        {!status?.permission_enabled ? (
          <button
            className="button button-primary"
            disabled={busy || !status?.adapter_available}
            onClick={() => setShowPermissionDialog(true)}
            type="button"
          >
            Grant session permission
          </button>
        ) : requiresRearm ? (
          <button
            className="button button-primary"
            disabled={busy}
            onClick={() => setShowPermissionDialog(true)}
            type="button"
          >
            Re-arm session permission
          </button>
        ) : (
          <button
            className="button button-secondary"
            disabled={busy}
            onClick={() => void revokePermission()}
            type="button"
          >
            Revoke permission
          </button>
        )}
        <button
          className="button computer-stop-button"
          disabled={!status?.permission_enabled && !status?.active_operation && !activeOperation}
          onClick={() => void emergencyStop()}
          type="button"
        >
          Emergency stop
        </button>
      </section>

      <section className="panel computer-control-form">
        <div className="panel-heading">
          <div className="panel-icon">⌖</div>
          <div>
            <h4>One confirmed operation</h4>
            <p>Click targets are restricted to the primary display. No shell or unrestricted OS access.</p>
          </div>
        </div>
        <label className="field">
          <span>Operation</span>
          <select
            disabled={!canControl || busy}
            onChange={(event) => {
              setOperation(event.target.value as DesktopOperation);
              setOperationConfirmed(false);
              setLastResult(null);
            }}
            value={operation}
          >
            {Object.entries(operationNames).map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
        </label>

        {["move", "click", "double_click", "right_click", "drag"].includes(operation) && (
          <div className="computer-coordinate-grid">
            {(["x", "y"] as const).map((field) => (
              <label className="field" key={field}>
                <span>{field.toUpperCase()} coordinate</span>
                <input
                  disabled={!canControl || busy}
                  max="100000"
                  min="0"
                  onChange={(event) => setValue(field, event.target.value)}
                  type="number"
                  value={values[field]}
                />
              </label>
            ))}
            {operation === "drag" && (["x2", "y2"] as const).map((field) => (
              <label className="field" key={field}>
                <span>{field.toUpperCase()} destination</span>
                <input
                  disabled={!canControl || busy}
                  max="100000"
                  min="0"
                  onChange={(event) => setValue(field, event.target.value)}
                  type="number"
                  value={values[field]}
                />
              </label>
            ))}
          </div>
        )}
        {operation === "type" && (
          <label className="field">
            <span>Text · maximum 250 ASCII characters</span>
            <textarea
              disabled={!canControl || busy}
              maxLength={250}
              onChange={(event) => setValue("text", event.target.value)}
              rows={3}
              value={values.text}
            />
          </label>
        )}
        {operation === "press" && (
          <label className="field">
            <span>Key</span>
            <select
              disabled={!canControl || busy}
              onChange={(event) => setValue("key", event.target.value)}
              value={values.key}
            >
              {["enter", "tab", "esc", "backspace", "delete", "space", "up", "down", "left", "right", "home", "end", "pageup", "pagedown"].map((key) => (
                <option key={key} value={key}>{key}</option>
              ))}
            </select>
          </label>
        )}
        {operation === "hotkey" && (
          <label className="field">
            <span>Shortcut</span>
            <select
              disabled={!canControl || busy}
              onChange={(event) => setValue("hotkey", event.target.value)}
              value={values.hotkey}
            >
              {["copy", "paste", "select_all", "undo", "redo", "save", "find"].map((key) => (
                <option key={key} value={key}>{key.replace("_", " ")}</option>
              ))}
            </select>
          </label>
        )}
        {operation === "scroll" && (
          <div className="computer-coordinate-grid">
            <label className="field">
              <span>Direction</span>
              <select
                disabled={!canControl || busy}
                onChange={(event) => setValue("direction", event.target.value)}
                value={values.direction}
              >
                {["up", "down", "left", "right"].map((direction) => (
                  <option key={direction} value={direction}>{direction}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Amount · maximum 10</span>
              <input
                disabled={!canControl || busy}
                max="10"
                min="1"
                onChange={(event) => setValue("amount", event.target.value)}
                type="number"
                value={values.amount}
              />
            </label>
          </div>
        )}
        {operation === "clipboard_read" && (
          <p className="computer-control-warning">
            Reads text from the system clipboard. The value is visible in this panel and may be sent to Gemini when you approve an assistant proposal.
          </p>
        )}
        {(operation === "clipboard_write" || operation === "clipboard_paste") && (
          <>
            <label className="field">
              <span>Clipboard text · maximum 4000 characters</span>
              <textarea
                disabled={!canControl || busy}
                maxLength={4000}
                onChange={(event) => setValue("clipboard_text", event.target.value)}
                rows={3}
                value={values.clipboard_text}
              />
            </label>
            <p className="computer-control-warning">
              This replaces the system clipboard{operation === "clipboard_paste"
                ? " and pastes into the currently focused application"
                : ""}.
            </p>
          </>
        )}
        {operation === "focus_window" && (
          <label className="field">
            <span>Visible window title</span>
            <input
              disabled={!canControl || busy}
              maxLength={120}
              onChange={(event) => setValue("title", event.target.value)}
              value={values.title}
            />
          </label>
        )}
        {operation === "close_app" && (
          <label className="field">
            <span>Application name</span>
            <input
              disabled={!canControl || busy}
              maxLength={100}
              onChange={(event) => setValue("application", event.target.value)}
              value={values.application}
            />
          </label>
        )}
        {operation === "screen_find" && (
          <label className="field">
            <span>Describe the visible screen element</span>
            <input
              disabled={!canControl || busy}
              maxLength={160}
              onChange={(event) => setValue("description", event.target.value)}
              value={values.description}
            />
          </label>
        )}
        {operation === "smart_type" && (
          <>
            <label className="field">
              <span>Replacement text · maximum 250 characters</span>
              <textarea
                disabled={!canControl || busy}
                maxLength={250}
                onChange={(event) => setValue("text", event.target.value)}
                rows={3}
                value={values.text}
              />
            </label>
            <p className="computer-control-warning">
              Replaces the focused field using Select All and Delete, then writes and pastes the approved text through the system clipboard.
            </p>
          </>
        )}
        {operation === "wait" && (
          <label className="field">
            <span>Wait · up to 10 seconds</span>
            <input
              disabled={!canControl || busy}
              max="10"
              min="0.1"
              onChange={(event) => setValue("seconds", event.target.value)}
              step="0.1"
              type="number"
              value={values.seconds}
            />
          </label>
        )}
        {operation === "random_data" && (
          <label className="field">
            <span>Data type</span>
            <select
              disabled={!canControl || busy}
              onChange={(event) => setValue("data_type", event.target.value)}
              value={values.data_type}
            >
              {[
                "name",
                "first_name",
                "last_name",
                "email",
                "username",
                "password",
                "phone",
                "birthday",
                "address",
                "zip_code",
                "city",
              ].map((dt) => (
                <option key={dt} value={dt}>{dt.replace("_", " ")}</option>
              ))}
            </select>
          </label>
        )}
        {operation === "user_data" && (
          <>
            <label className="field">
              <span>Memory identity field</span>
              <input
                disabled={!canControl || busy}
                maxLength={50}
                onChange={(event) => setValue("field", event.target.value)}
                placeholder="e.g. name, email, city"
                value={values.field}
              />
            </label>
            <p className="computer-control-warning">
              Reads saved profile data from long-term memory (identity category). If not found in memory, synthetic fallback data is generated.
            </p>
          </>
        )}
        {false && (
          <label className="field">
            <input
            />
          </label>
        )}
        {["active_window", "list_windows", "clear_field", "click_current"].includes(operation) && (
          <p className="computer-control-warning">
            {operation === "clear_field"
              ? "Sends Select All and Delete to the currently focused field."
              : operation === "click_current"
                ? "Clicks at the pointer's present location."
                : "This reads desktop window metadata locally and returns the result only after approval."}
          </p>
        )}

        <label className="action-confirm">
          <input
            checked={operationConfirmed}
            disabled={!canControl || busy}
            onChange={(event) => setOperationConfirmed(event.target.checked)}
            type="checkbox"
          />
          I have reviewed these parameters and confirm one desktop operation.
        </label>
        <button
          className="button button-primary"
          disabled={!canControl || busy || !operationConfirmed}
          onClick={() => void executeControl()}
          type="button"
        >
          {busy ? "Operation running…" : "Run confirmed operation"}
        </button>
        {stopMessage && <p className="computer-stop-message" role="status">{stopMessage}</p>}
        {lastResult && (
          <div className={`action-result action-result-${lastResult.status}`} aria-live="polite">
            <strong>{lastResult.status.toUpperCase()}</strong>
            <p>{lastResult.message}</p>
            {lastResult.error && <pre>{lastResult.error}</pre>}
            {screenshot && typeof screenshot.data_base64 === "string" && (
              <img
                alt="Desktop-control screenshot"
                className="computer-screenshot-preview"
                src={`data:image/jpeg;base64,${screenshot.data_base64}`}
              />
            )}
            {lastResult.data !== null && !screenshot?.data_base64 && (
              <pre>{JSON.stringify(lastResult.data, null, 2)}</pre>
            )}
          </div>
        )}
      </section>

      {pendingRequests.length > 0 && (
        <section className="panel computer-pending-requests" aria-live="polite">
          <div className="panel-heading">
            <div className="panel-icon">!</div>
            <div>
              <h4>Assistant requests your approval</h4>
              <p>Nothing runs until you approve the exact operation below.</p>
            </div>
          </div>
          {pendingRequests.map((request) => (
            <article className="computer-pending-request" key={request.request_id}>
              <strong>{operationNames[request.operation]}</strong>
              <pre>{JSON.stringify(request.parameters, null, 2)}</pre>
              {request.operation === "clipboard_read" && (
                <p className="computer-control-warning">
                  Approval reads clipboard text and sends that content to Gemini for the pending conversation.
                </p>
              )}
              {request.operation === "close_app" && (
                <p className="computer-control-warning">
                  Approval sends a polite window-close request. Alex will not force-terminate the application.
                </p>
              )}
              {request.operation === "user_data" && (
                <p className="computer-control-warning">
                  Approval retrieves user profile data from long-term memory for form autofill.
                </p>
              )}
              <p>Expires in {request.expires_in_seconds} seconds.</p>
              <div className="form-actions">
                <button
                  className="button button-secondary"
                  disabled={busy}
                  onClick={() => void handlePendingRequest(request.request_id, false)}
                  type="button"
                >
                  Reject request
                </button>
                <button
                  className="button button-primary"
                  disabled={busy || !canControl}
                  onClick={() => void handlePendingRequest(request.request_id, true)}
                  type="button"
                >
                  Approve and execute
                </button>
              </div>
            </article>
          ))}
        </section>
      )}

      {showPermissionDialog && (
        <div className="hud-modal-backdrop computer-permission-backdrop">
          <section
            className="panel computer-permission-dialog"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="computer-permission-title"
            aria-describedby="computer-permission-detail"
          >
            <h4 id="computer-permission-title">
              {requiresRearm ? "Re-arm desktop control?" : "Grant desktop-control permission?"}
            </h4>
            <p id="computer-permission-detail">
              {requiresRearm
                ? "The emergency stop is latched. Re-arming restores session permission; every operation still needs separate confirmation."
                : "This lets Alex move the pointer and send bounded keyboard input to the currently focused desktop application until permission is revoked or Alex closes. Alex will not access a shell or control the computer in the background."}
            </p>
            <label className="action-confirm">
              <input
                checked={permissionConfirmed}
                onChange={(event) => setPermissionConfirmed(event.target.checked)}
                type="checkbox"
              />
              I understand and {requiresRearm ? "re-grant" : "grant"} permission for this session.
            </label>
            <div className="form-actions">
              <button
                className="button button-secondary"
                onClick={() => {
                  setShowPermissionDialog(false);
                  setPermissionConfirmed(false);
                }}
                type="button"
              >
                Cancel
              </button>
              <button
                className="button button-primary"
                disabled={!permissionConfirmed || busy}
                onClick={() => void grantPermission()}
                type="button"
              >
                {requiresRearm ? "Re-arm permission" : "Grant permission"}
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
