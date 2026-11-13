import { useEffect, useRef, useState } from "react";

export interface FloatingClipboardPanelProps {
  onAction: (command: string) => void;
  /** Optional override for direct testing or manual display */
  initialText?: string;
  /** Duration before panel auto-dismisses in milliseconds (default: 8000ms matching Mark-LVI) */
  autoDismissMs?: number;
}

const MIN_CLIP_LENGTH = 10;
const MAX_PREVIEW_LENGTH = 58;
const MAX_CMD_CLIP_LENGTH = 800;

export function FloatingClipboardPanel({
  onAction,
  initialText,
  autoDismissMs = 8000,
}: FloatingClipboardPanelProps) {
  const isValidInitial = Boolean(initialText && initialText.trim().length >= MIN_CLIP_LENGTH);
  const [clipText, setClipText] = useState<string | null>(isValidInitial ? initialText!.trim() : null);
  const [visible, setVisible] = useState<boolean>(isValidInitial);
  const lastSeenRef = useRef<string>(isValidInitial ? initialText!.trim() : "");
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const showText = (text: string) => {
    const trimmed = text.trim();
    if (trimmed.length >= MIN_CLIP_LENGTH && trimmed !== lastSeenRef.current) {
      lastSeenRef.current = trimmed;
      setClipText(trimmed);
      setVisible(true);
    }
  };

  useEffect(() => {
    if (initialText && initialText.trim().length >= MIN_CLIP_LENGTH) {
      setClipText(initialText.trim());
      lastSeenRef.current = initialText.trim();
      setVisible(true);
    } else if (initialText && initialText.trim().length < MIN_CLIP_LENGTH) {
      setVisible(false);
    }
  }, [initialText]);

  useEffect(() => {
    if (visible) {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      timerRef.current = setTimeout(() => {
        setVisible(false);
      }, autoDismissMs);
    }
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [visible, autoDismissMs]);

  useEffect(() => {
    const handleCopy = () => {
      // Delay slightly so clipboard has flushed
      setTimeout(() => {
        try {
          if (navigator.clipboard && typeof navigator.clipboard.readText === "function") {
            navigator.clipboard.readText().then((text) => {
              if (text) showText(text);
            }).catch(() => {
              // Permission denied or clipboard empty
            });
          }
        } catch {
          // Unsupported or disabled
        }
      }, 50);
    };

    const handleFocus = () => {
      try {
        if (navigator.clipboard && typeof navigator.clipboard.readText === "function") {
          navigator.clipboard.readText().then((text) => {
            if (text) showText(text);
          }).catch(() => {
            // Silently ignore permission denials on focus
          });
        }
      } catch {
        // Unsupported
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && visible) {
        setVisible(false);
      }
    };

    document.addEventListener("copy", handleCopy);
    window.addEventListener("focus", handleFocus);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("copy", handleCopy);
      window.removeEventListener("focus", handleFocus);
      window.removeEventListener("keydown", handleKeyDown);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [visible, autoDismissMs]);

  if (!visible || !clipText) {
    return null;
  }

  const preview =
    clipText.length > MAX_PREVIEW_LENGTH
      ? `${clipText.slice(0, MAX_PREVIEW_LENGTH).replace(/\n/g, " ")}…`
      : clipText.replace(/\n/g, " ");

  const handleTrigger = (cmdFormat: string) => {
    const snippet = clipText.slice(0, MAX_CMD_CLIP_LENGTH);
    const command = cmdFormat.replace("{text}", snippet);
    onAction(command);
    setVisible(false);
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const handleDismiss = () => {
    setVisible(false);
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  return (
    <div
      aria-label="Clipboard Intelligence Action Widget"
      className="clipboard-floating-panel"
      data-testid="clipboard-floating-panel"
      role="region"
    >
      <div className="clipboard-floating-header">
        <span className="clipboard-floating-icon">◈ CLIPBOARD DETECTED</span>
        <button
          aria-label="Dismiss clipboard panel"
          className="clipboard-floating-close"
          onClick={handleDismiss}
          type="button"
        >
          ✕
        </button>
      </div>

      <div className="clipboard-floating-preview" title={clipText}>
        "{preview}"
      </div>

      <div className="clipboard-floating-actions">
        <button
          className="clipboard-action-btn"
          onClick={() => handleTrigger("Translate this text to English: {text}")}
          type="button"
        >
          TRANSLATE
        </button>
        <button
          className="clipboard-action-btn"
          onClick={() => handleTrigger("Summarise this: {text}")}
          type="button"
        >
          SUMMARISE
        </button>
        <button
          className="clipboard-action-btn"
          onClick={() => handleTrigger("Explain this: {text}")}
          type="button"
        >
          EXPLAIN
        </button>
        <button
          className="clipboard-action-btn"
          onClick={() => handleTrigger("Fix grammar and spelling: {text}")}
          type="button"
        >
          FIX
        </button>
      </div>
    </div>
  );
}
