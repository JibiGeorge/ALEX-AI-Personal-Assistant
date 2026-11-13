import { useState, type FormEvent } from "react";

export interface QuizQuestion {
  question: string;
  options?: string[];
  answer: string;
  type?: string;
  note?: string;
}

export interface QuizResultItem {
  question: string;
  type?: string;
  given: string;
  answer: string;
  correct: boolean | null;
}

export interface QuizResultPayload {
  topic: string;
  total: number;
  correct: number;
  results: QuizResultItem[];
}

export interface QuizCardProps {
  topic: string;
  questions: QuizQuestion[];
  onComplete?: (payload: QuizResultPayload) => void;
  onDismiss?: () => void;
  grader?: (question: QuizQuestion, given: string) => boolean | null;
}

export function defaultGrader(question: QuizQuestion, given: string): boolean | null {
  const normGiven = given.trim().toLowerCase();
  const normAns = question.answer.trim().toLowerCase();
  if (!normGiven) return false;
  if (normGiven === normAns) return true;
  if (!question.options || question.options.length === 0) {
    if (normGiven.includes(normAns) || normAns.includes(normGiven)) return true;
  }
  return false;
}

export function QuizCard({
  topic,
  questions,
  onComplete,
  onDismiss,
  grader = defaultGrader,
}: QuizCardProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [textAnswer, setTextAnswer] = useState("");
  const [results, setResults] = useState<QuizResultItem[]>([]);
  const [finished, setFinished] = useState(false);

  if (!questions || questions.length === 0) {
    return null;
  }

  const currentQ = questions[currentIndex];
  const total = questions.length;
  const isLast = currentIndex >= total - 1;

  function submitAnswer(given: string) {
    if (answered || finished) return;
    const verdict = grader(currentQ, given);
    const item: QuizResultItem = {
      question: currentQ.question,
      type: currentQ.type || (currentQ.options?.length ? "multiple-choice" : "text"),
      given: given.trim(),
      answer: currentQ.answer,
      correct: verdict,
    };
    const nextResults = [...results, item];
    setResults(nextResults);
    setSelectedOption(given);
    setAnswered(true);
  }

  function handleTextSubmit(e: FormEvent) {
    e.preventDefault();
    if (!textAnswer.trim() || answered) return;
    submitAnswer(textAnswer);
  }

  function handleNext() {
    if (isLast) {
      setFinished(true);
      const rightCount = results.filter((r) => r.correct === true).length;
      onComplete?.({
        topic,
        total,
        correct: rightCount,
        results,
      });
    } else {
      setCurrentIndex((prev) => prev + 1);
      setAnswered(false);
      setSelectedOption(null);
      setTextAnswer("");
    }
  }

  function handleRestart() {
    setCurrentIndex(0);
    setAnswered(false);
    setSelectedOption(null);
    setTextAnswer("");
    setResults([]);
    setFinished(false);
  }

  if (finished) {
    const right = results.filter((r) => r.correct === true).length;
    const pct = Math.round((right / total) * 100);

    return (
      <div className="quiz-card" role="region" aria-label="Quiz Results">
        <div className="quiz-header">
          <div className="quiz-topic-badge">{topic.toUpperCase()} — COMPLETED</div>
          {onDismiss && (
            <button
              type="button"
              className="quiz-close-btn"
              onClick={onDismiss}
              aria-label="Close quiz"
            >
              ✕
            </button>
          )}
        </div>

        <div className="quiz-summary-content">
          <div className="quiz-score-badge">
            <span className="quiz-score-num">{right}</span> / {total} Correct ({pct}%)
          </div>

          <div className="quiz-results-breakdown">
            {results.map((r, i) => (
              <div
                key={i}
                className={`quiz-result-row ${r.correct === true ? "result-pass" : "result-fail"}`}
              >
                <span className="quiz-result-mark">
                  {r.correct === true ? "✓" : r.correct === false ? "✕" : "…"}
                </span>
                <div className="quiz-result-details">
                  <div className="quiz-result-q">{r.question}</div>
                  <div className="quiz-result-ans">
                    <span>Your answer: <strong>{r.given || "(blank)"}</strong></span>
                    {r.correct !== true && (
                      <span className="quiz-expected"> | Expected: {r.answer}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="quiz-actions-row">
            <button
              type="button"
              className="button button-secondary"
              onClick={handleRestart}
            >
              Try Again
            </button>
            {onDismiss && (
              <button
                type="button"
                className="button button-primary"
                onClick={onDismiss}
              >
                Done
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  const currentResult = answered ? results[currentIndex] : null;

  return (
    <div className="quiz-card" role="region" aria-label={`Quiz: ${topic}`}>
      <div className="quiz-header">
        <span className="quiz-topic-badge">{topic.toUpperCase()}</span>
        <span className="quiz-progress-text">
          Question {currentIndex + 1} of {total}
        </span>
        {onDismiss && (
          <button
            type="button"
            className="quiz-close-btn"
            onClick={onDismiss}
            aria-label="Close quiz"
          >
            ✕
          </button>
        )}
      </div>

      <div className="quiz-body">
        <h4 className="quiz-question-text">{currentQ.question}</h4>

        {currentQ.options && currentQ.options.length > 0 ? (
          <div className="quiz-options-grid">
            {currentQ.options.map((option, idx) => {
              const isSelected = selectedOption === option;
              const isCorrectOption =
                answered &&
                option.trim().toLowerCase() === currentQ.answer.trim().toLowerCase();
              const isWrongSelection = answered && isSelected && !isCorrectOption;

              let btnClass = "quiz-option-btn";
              if (answered) {
                if (isCorrectOption) btnClass += " option-correct";
                else if (isWrongSelection) btnClass += " option-wrong";
              }

              return (
                <button
                  key={idx}
                  type="button"
                  className={btnClass}
                  disabled={answered}
                  onClick={() => submitAnswer(option)}
                >
                  <span className="option-index">{String.fromCharCode(65 + idx)}</span>
                  <span className="option-label">{option}</span>
                </button>
              );
            })}
          </div>
        ) : (
          <form className="quiz-text-form" onSubmit={handleTextSubmit}>
            <input
              type="text"
              className="quiz-text-input"
              placeholder="Type your answer..."
              value={textAnswer}
              onChange={(e) => setTextAnswer(e.target.value)}
              disabled={answered}
              autoFocus
            />
            <button
              type="submit"
              className="button button-primary quiz-submit-btn"
              disabled={answered || !textAnswer.trim()}
            >
              Submit Answer
            </button>
          </form>
        )}

        {answered && currentResult && (
          <div
            className={`quiz-feedback-banner ${
              currentResult.correct === true
                ? "feedback-correct"
                : currentResult.correct === false
                ? "feedback-wrong"
                : "feedback-neutral"
            }`}
          >
            <div className="feedback-headline">
              {currentResult.correct === true ? (
                <>✓ Correct!</>
              ) : currentResult.correct === false ? (
                <>✕ Incorrect. Correct answer: <strong>{currentQ.answer}</strong></>
              ) : (
                <>… Answer recorded for review</>
              )}
            </div>
            {currentQ.note && <div className="feedback-note">{currentQ.note}</div>}
          </div>
        )}
      </div>

      <div className="quiz-footer">
        {answered && (
          <button
            type="button"
            className="button button-primary quiz-next-btn"
            onClick={handleNext}
          >
            {isLast ? "Finish Quiz →" : "Next Question →"}
          </button>
        )}
      </div>
    </div>
  );
}

