import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { QuizCard, type QuizCardProps, type QuizResultPayload } from "../components/QuizCard";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
}

interface ConversationPageProps {
  assistantName: string;
  apiKeyConfigured: boolean;
  liveSessionActive: boolean;
  messages: ChatMessage[];
  busy: boolean;
  onSend: (text: string) => Promise<{ text: string }>;
  onError: (error: unknown) => void;
  onOpenSettings: () => void;
  activeQuiz?: QuizCardProps | null;
  onQuizComplete?: (payload: QuizResultPayload) => void;
  onQuizDismiss?: () => void;
}

export function ConversationPage({
  assistantName,
  apiKeyConfigured,
  liveSessionActive,
  messages,
  busy,
  onSend,
  onError,
  onOpenSettings,
  activeQuiz,
  onQuizComplete,
  onQuizDismiss,
}: ConversationPageProps) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy || !apiKeyConfigured) return;
    try {
      await onSend(text);
      setDraft("");
    } catch (error) {
      onError(error);
    }
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <section className="conversation-layout">
      <div className="conversation-heading">
        <div>
          <div className="eyebrow">TEXT CONVERSATION</div>
          <h3>Talk with {assistantName}</h3>
        </div>
        <span className="session-label">
          <span className="session-dot" />
          {liveSessionActive ? "LIVE VOICE SESSION" : "TEXT SESSION"}
        </span>
      </div>

      <div className="conversation-scroll" aria-live="polite">
        {messages.length === 0 ? (
          <div className="conversation-empty">
            <div className="chat-emblem">A</div>
            <h2>What can I help with?</h2>
            <p>
              Ask a question or start a conversation. Start the microphone to send
              text and voice through one live session. Computer actions are still
              being migrated.
            </p>
            {!apiKeyConfigured && (
              <div className="key-needed">
                <span>Gemini API key required</span>
                <button className="button button-secondary" onClick={onOpenSettings} type="button">
                  Open Settings
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="message-list">
            {messages.map((message) => (
              <article
                className={`chat-message ${message.role === "user" ? "user-message" : "assistant-message"}`}
                key={message.id}
              >
                <div className="message-avatar" aria-hidden="true">
                  {message.role === "user" ? "YOU" : "A"}
                </div>
                <div className="message-body">
                  <div className="message-speaker">
                    {message.role === "user" ? "You" : assistantName}
                  </div>
                  <p>{message.text}</p>
                </div>
              </article>
            ))}
            {busy && (
              <div className="chat-message assistant-message" role="status">
                <div className="message-avatar" aria-hidden="true">A</div>
                <div className="message-body">
                  <div className="message-speaker">{assistantName}</div>
                  <p className="typing-indicator"><span /><span /><span /> Thinking</p>
                </div>
              </div>
            )}
            {activeQuiz && (
              <div className="active-quiz-container">
                <QuizCard
                  {...activeQuiz}
                  onComplete={(payload) => {
                    activeQuiz.onComplete?.(payload);
                    onQuizComplete?.(payload);
                  }}
                  onDismiss={() => {
                    activeQuiz.onDismiss?.();
                    onQuizDismiss?.();
                  }}
                />
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <div className="composer-wrap">
        <form className="composer" onSubmit={submit}>
          <textarea
            aria-label="Message"
            disabled={!apiKeyConfigured || busy}
            maxLength={4000}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onComposerKeyDown}
            placeholder={
              apiKeyConfigured
                ? "Message Alex... (Enter to send, Shift+Enter for a new line)"
                : "Configure a Gemini API key to start chatting"
            }
            rows={2}
            value={draft}
          />
          <div className="composer-footer">
            <span>
              {liveSessionActive
                ? "Text and microphone input share this live Gemini session."
                : "Text chat uses its own session; context clears when Alex closes."}
            </span>
            <button
              aria-label="Send message"
              className="send-button"
              disabled={!apiKeyConfigured || busy || !draft.trim()}
              type="submit"
            >
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <path d="M3 10 17 3l-4.5 14-2.2-5.3L3 10Z" />
                <path d="m10.3 11.7 3.2-3.2" />
              </svg>
              Send
            </button>
          </div>
        </form>
        <div className="conversation-disclaimer">
          Responses are generated by Gemini. Check important information.
        </div>
      </div>
    </section>
  );
}
