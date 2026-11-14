import { useEffect, useRef, useState } from "react";

export interface AlexResponseItem {
  id: string;
  time: string;
  text: string;
}

export interface AlexResponseStreamProps {
  responses: AlexResponseItem[];
  isWorkspaceActive?: boolean;
  isStreaming?: boolean;
}

export function AlexResponseStream({
  responses,
  isWorkspaceActive = false,
  isStreaming = false,
}: AlexResponseStreamProps) {
  const [autoScroll, setAutoScroll] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom whenever responses change or streaming state updates
  useEffect(() => {
    if (!autoScroll || isCollapsed) return;
    const container = scrollRef.current;
    if (!container) return;

    if (typeof container.scrollTo === "function") {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth",
      });
    } else {
      container.scrollTop = container.scrollHeight;
    }
    setIsAtBottom(true);
  }, [responses, autoScroll, isCollapsed, isStreaming]);

  // Monitor scroll position to detect if user scrolled up
  const handleScroll = () => {
    const container = scrollRef.current;
    if (!container) return;

    const threshold = 36;
    const atBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight <= threshold;

    setIsAtBottom(atBottom);
  };

  const scrollToBottom = () => {
    const container = scrollRef.current;
    if (!container) return;

    if (typeof container.scrollTo === "function") {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth",
      });
    } else {
      container.scrollTop = container.scrollHeight;
    }
    setIsAtBottom(true);
    setAutoScroll(true);
  };

  return (
    <aside
      className={`alex-response-stream-panel ${
        isWorkspaceActive ? "in-workspace-mode" : ""
      } ${isCollapsed ? "is-collapsed" : ""}`}
      aria-label="ALEX Live Responses"
    >
      {/* Header bar */}
      <div className="stream-panel-header">
        <div className="stream-header-left">
          <span className="stream-pulse-dot" aria-hidden="true" />
          <span>&gt;&gt; ACTIVITY</span>
          <span className="stream-count-badge">
            {responses.length.toString().padStart(2, "0")}
          </span>
        </div>

        <div className="stream-header-right">
          <button
            type="button"
            className={`stream-autoscroll-btn ${autoScroll ? "is-active" : ""}`}
            onClick={() => setAutoScroll((prev) => !prev)}
            title={autoScroll ? "Auto-scroll Enabled" : "Auto-scroll Paused"}
          >
            {autoScroll ? "AUTOSCROLL" : "PAUSED"}
          </button>
          <button
            type="button"
            className="stream-collapse-btn"
            onClick={() => setIsCollapsed((prev) => !prev)}
            title={isCollapsed ? "Expand Stream" : "Minimize Stream"}
            aria-label={isCollapsed ? "Expand Stream" : "Minimize Stream"}
          >
            {isCollapsed ? "+" : "—"}
          </button>
        </div>
      </div>

      {/* Scrolling response body */}
      {!isCollapsed && (
        <div
          ref={scrollRef}
          className="stream-scroll-container"
          onScroll={handleScroll}
          role="log"
          aria-live="polite"
        >
          {responses.length === 0 ? (
            <div className="stream-empty">
              <span>Awaiting incoming transmission from ALEX...</span>
              <span className="stream-cursor">_</span>
            </div>
          ) : (
            responses.map((entry) => (
              <div key={entry.id} className="stream-entry">
                <span className="stream-time">{entry.time}</span>
                <div className="stream-text">{entry.text}</div>
              </div>
            ))
          )}

          {isStreaming && (
            <div className="stream-streaming-bar">
              <span className="stream-pulse-dot" />
              <span>ALEX transmitting...</span>
            </div>
          )}

          <div ref={messagesEndRef} style={{ height: 1 }} />
        </div>
      )}

      {/* Jump to latest button when user scrolled up */}
      {!isCollapsed && !isAtBottom && autoScroll && (
        <button
          type="button"
          className="stream-jump-bottom-btn"
          onClick={scrollToBottom}
        >
          ↓ NEW RESPONSES
        </button>
      )}
    </aside>
  );
}
