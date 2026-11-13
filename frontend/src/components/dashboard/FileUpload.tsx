import type { DragEvent } from "react";
import type { FileAttachment } from "../../types/api";

export interface SelectedFile {
  attachment: FileAttachment;
  size: number;
  previewUrl?: string;
}

export interface FileUploadProps {
  selectedFile: SelectedFile | null;
  fileBusy: boolean;
  screenBusy: boolean;
  apiKeyConfigured: boolean;
  metricsUnavailable: boolean;
  metricsError: string | null;
  onFileDrop: (event: DragEvent<HTMLLabelElement>) => void;
  onFileSelect: (file: File) => void;
  onCaptureScreen: () => void;
  onRemoveFile: () => void;
  onOpenFileInWorkspace?: (file: SelectedFile) => void;
  formatBytes: (bytes: number) => string;
  isRevealed?: boolean;
  compact?: boolean;
}

export function FileUpload({
  selectedFile,
  fileBusy,
  screenBusy,
  apiKeyConfigured,
  metricsUnavailable,
  metricsError,
  onFileDrop,
  onFileSelect,
  onCaptureScreen,
  onRemoveFile,
  onOpenFileInWorkspace,
  formatBytes,
  isRevealed = true,
  compact = false,
}: FileUploadProps) {
  if (compact) {
    return (
      <div
        className={`file-section file-section-compact reveal-component ${
          isRevealed ? "is-revealed" : ""
        }`}
      >
        <label
          className={`file-drop file-drop-compact ${fileBusy ? "file-reading" : ""}`}
          htmlFor="hud-file-input"
          onDragOver={(event) => event.preventDefault()}
          onDrop={onFileDrop}
          title="Drop file here or Click to Browse"
        >
          <input
            accept=".aac,.csv,.flac,.gif,.jpeg,.jpg,.js,.jsx,.json,.m4a,.md,.mp3,.mp4,.mov,.ogg,.pdf,.png,.py,.ts,.tsx,.txt,.wav,.webm,.webp,.xml"
            id="hud-file-input"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onFileSelect(file);
              event.currentTarget.value = "";
            }}
            type="file"
          />
          <span className="file-upload-icon" aria-hidden="true">
            {fileBusy ? "◌" : "↥"}
          </span>
          <span className="file-drop-text-compact">
            <strong>
              {fileBusy ? "READING FILE…" : "Drop file here or Click to Browse"}
            </strong>
          </span>
        </label>

        <button
          className="button button-secondary screen-capture-button screen-capture-compact"
          disabled={!apiKeyConfigured || fileBusy || screenBusy}
          onClick={onCaptureScreen}
          title="Choose one display, preview the capture, then send it with your message"
          type="button"
        >
          {screenBusy ? "CAPTURING SCREEN…" : "CAPTURE SCREEN"}
        </button>

        {selectedFile && (
          <div className="file-preview-card file-preview-compact">
            <div className="file-selected">
              <span>
                ATTACHED: {selectedFile.attachment.name} · {formatBytes(selectedFile.size)}
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {onOpenFileInWorkspace && (
                  <button
                    className="file-preview-open-btn"
                    onClick={() => onOpenFileInWorkspace(selectedFile)}
                    title="Open in central holographic workspace"
                    type="button"
                    style={{
                      background: "rgba(0, 217, 255, 0.15)",
                      border: "1px solid rgba(0, 217, 255, 0.4)",
                      color: "#00dfff",
                      fontSize: "9px",
                      fontWeight: 700,
                      padding: "2px 6px",
                      borderRadius: "4px",
                      cursor: "pointer",
                      letterSpacing: "0.06em",
                    }}
                  >
                    WORKSPACE ❯
                  </button>
                )}
                <button
                  aria-label="Remove attachment"
                  onClick={onRemoveFile}
                  type="button"
                >
                  ×
                </button>
              </div>
            </div>
            {selectedFile.previewUrl && (
              <img
                alt="Screen capture preview"
                className="screen-capture-preview"
                src={selectedFile.previewUrl}
              />
            )}
          </div>
        )}
      </div>
    );
  }
  return (
    <div
      className={`file-section reveal-component ${
        isRevealed ? "is-revealed" : ""
      }`}
    >
      <div className="hud-panel-head">
        <div className="hud-section-label">
          ◆ FILE UPLOAD <span className="hud-count-tag">MAX 8 MB</span>
        </div>
      </div>

      <label
        className={`file-drop ${fileBusy ? "file-reading" : ""}`}
        htmlFor="hud-file-input"
        onDragOver={(event) => event.preventDefault()}
        onDrop={onFileDrop}
      >
        <input
          accept=".aac,.csv,.flac,.gif,.jpeg,.jpg,.js,.jsx,.json,.m4a,.md,.mp3,.mp4,.mov,.ogg,.pdf,.png,.py,.ts,.tsx,.txt,.wav,.webm,.webp,.xml"
          id="hud-file-input"
          onChange={(event) => {
            const file = event.currentTarget.files?.[0];
            if (file) onFileSelect(file);
            event.currentTarget.value = "";
          }}
          type="file"
        />
        <span className="file-upload-icon" aria-hidden="true">
          {fileBusy ? "◌" : "↥"}
        </span>
        <div className="file-drop-text">
          <strong>
            {fileBusy ? "READING FILE…" : "Drop file here or Click to Browse"}
          </strong>
          <small>Images · Video · Audio · PDF · Text · Code · Data</small>
        </div>
      </label>

      <button
        className="button button-secondary screen-capture-button"
        disabled={!apiKeyConfigured || fileBusy || screenBusy}
        onClick={onCaptureScreen}
        title="Choose one display, preview the capture, then send it with your message"
        type="button"
      >
        {screenBusy ? "CAPTURING SCREEN…" : "CAPTURE SCREEN"}
      </button>

      {selectedFile ? (
        <div className="file-preview-card">
          <div className="file-selected">
            <span>
              ATTACHED: {selectedFile.attachment.name} · {formatBytes(selectedFile.size)}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              {onOpenFileInWorkspace && (
                <button
                  className="file-preview-open-btn"
                  onClick={() => onOpenFileInWorkspace(selectedFile)}
                  title="Open in central holographic workspace"
                  type="button"
                  style={{
                    background: "rgba(0, 217, 255, 0.15)",
                    border: "1px solid rgba(0, 217, 255, 0.4)",
                    color: "#00dfff",
                    fontSize: "9px",
                    fontWeight: 700,
                    padding: "2px 6px",
                    borderRadius: "4px",
                    cursor: "pointer",
                    letterSpacing: "0.06em",
                  }}
                >
                  WORKSPACE ❯
                </button>
              )}
              <button
                aria-label="Remove attachment"
                onClick={onRemoveFile}
                type="button"
              >
                ×
              </button>
            </div>
          </div>
          {selectedFile.previewUrl && (
            <img
              alt="Screen capture preview"
              className="screen-capture-preview"
              src={selectedFile.previewUrl}
            />
          )}
        </div>
      ) : (
        <div className="file-hint" title={metricsError ?? undefined}>
          {metricsUnavailable
            ? `System telemetry unavailable${metricsError ? `: ${metricsError}` : "."}`
            : apiKeyConfigured
            ? "Files are sent securely alongside your text query."
            : "Initialise Gemini access before attaching files."}
        </div>
      )}
    </div>
  );
}

