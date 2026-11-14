import { useEffect, useRef, useState } from "react";

export interface NoticeProps {
  kind: "error" | "success";
  children: string;
  onDismiss: () => void;
  /**
   * Auto-close duration in milliseconds.
   * Defaults to 4000ms for success, 6000ms for error.
   * Set to `false` or `0` to disable auto-closing.
   */
  autoCloseMs?: number | false;
}

export function Notice({ kind, children, onDismiss, autoCloseMs }: NoticeProps) {
  const [isPaused, setIsPaused] = useState(false);

  // Default duration: 4000ms for success, 6000ms for error
  const duration =
    autoCloseMs === false ? 0 : (autoCloseMs ?? (kind === "error" ? 6000 : 4000));

  const remainingTimeRef = useRef(duration);
  const startTimeRef = useRef(Date.now());
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onDismissRef = useRef(onDismiss);

  useEffect(() => {
    onDismissRef.current = onDismiss;
  }, [onDismiss]);

  // Reset remaining time when children, kind, or duration changes
  useEffect(() => {
    remainingTimeRef.current = duration;
    setIsPaused(false);
  }, [children, kind, duration]);

  // Handle scheduling / pausing
  useEffect(() => {
    if (duration <= 0 || isPaused) return;

    startTimeRef.current = Date.now();
    timerRef.current = setTimeout(() => {
      onDismissRef.current();
    }, remainingTimeRef.current);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [children, kind, duration, isPaused]);

  function handleMouseEnter() {
    if (duration <= 0) return;
    const elapsed = Date.now() - startTimeRef.current;
    remainingTimeRef.current = Math.max(remainingTimeRef.current - elapsed, 500);
    setIsPaused(true);
  }

  function handleMouseLeave() {
    if (duration <= 0) return;
    setIsPaused(false);
  }

  return (
    <div
      className={`notice notice-${kind}`}
      role={kind === "error" ? "alert" : "status"}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <span className="notice-icon" aria-hidden="true">
        {kind === "error" ? "⚠" : "✓"}
      </span>
      <span className="notice-text">{children}</span>
      <button
        aria-label="Dismiss notification"
        className="notice-dismiss-btn"
        onClick={() => onDismissRef.current()}
        type="button"
      >
        ×
      </button>
      {duration > 0 && (
        <div
          className={`notice-progress-bar ${isPaused ? "is-paused" : ""}`}
          style={{ animationDuration: `${duration}ms` }}
        />
      )}
    </div>
  );
}
