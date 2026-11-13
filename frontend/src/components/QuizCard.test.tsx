import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { QuizCard, type QuizQuestion } from "./QuizCard";

const sampleQuestions: QuizQuestion[] = [
  {
    question: "What is the capital of France?",
    options: ["Berlin", "London", "Paris", "Madrid"],
    answer: "Paris",
    type: "multiple-choice",
    note: "Paris has been the capital since 508 AD.",
  },
  {
    question: "What is 2 + 2?",
    options: ["3", "4", "5"],
    answer: "4",
  },
  {
    question: "What does HTML stand for?",
    answer: "HyperText Markup Language",
    type: "text",
    note: "Standard markup language for documents designed to be displayed in a web browser.",
  },
];

describe("QuizCard Component", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders the quiz topic, first question, and option buttons", () => {
    render(<QuizCard topic="General Knowledge" questions={sampleQuestions} />);

    expect(screen.getByText("GENERAL KNOWLEDGE")).toBeInTheDocument();
    expect(screen.getByText("Question 1 of 3")).toBeInTheDocument();
    expect(screen.getByText("What is the capital of France?")).toBeInTheDocument();
    expect(screen.getByText("Berlin")).toBeInTheDocument();
    expect(screen.getByText("Paris")).toBeInTheDocument();
  });

  it("handles correct option selection, displays feedback, and enables next button", () => {
    render(<QuizCard topic="Geography" questions={sampleQuestions} />);

    const parisBtn = screen.getByText("Paris");
    fireEvent.click(parisBtn);

    expect(screen.getByText("✓ Correct!")).toBeInTheDocument();
    expect(
      screen.getByText("Paris has been the capital since 508 AD.")
    ).toBeInTheDocument();

    const nextBtn = screen.getByText("Next Question →");
    expect(nextBtn).toBeInTheDocument();
  });

  it("handles incorrect option selection and displays expected answer", () => {
    render(<QuizCard topic="Geography" questions={sampleQuestions} />);

    const wrongBtn = screen.getByText("Berlin");
    fireEvent.click(wrongBtn);

    expect(screen.getByText(/Incorrect\. Correct answer:/i)).toBeInTheDocument();
    expect(screen.getAllByText("Paris").length).toBeGreaterThanOrEqual(2);
  });

  it("advances to subsequent questions on clicking Next", () => {
    render(<QuizCard topic="Math & Web" questions={sampleQuestions} />);

    fireEvent.click(screen.getByText("Paris"));
    fireEvent.click(screen.getByText("Next Question →"));

    expect(screen.getByText("Question 2 of 3")).toBeInTheDocument();
    expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument();
  });

  it("renders text input form for open questions and submits answer", () => {
    render(
      <QuizCard
        topic="Open Q"
        questions={[sampleQuestions[2]]}
      />
    );

    expect(screen.getByText("What does HTML stand for?")).toBeInTheDocument();
    const input = screen.getByPlaceholderText("Type your answer...");
    fireEvent.change(input, { target: { value: "hypertext markup language" } });

    const submitBtn = screen.getByText("Submit Answer");
    fireEvent.click(submitBtn);

    expect(screen.getByText("✓ Correct!")).toBeInTheDocument();
  });

  it("shows final completion summary and calls onComplete with results", () => {
    const onComplete = vi.fn();
    const questions = sampleQuestions.slice(0, 2);

    render(
      <QuizCard
        topic="Mini Quiz"
        questions={questions}
        onComplete={onComplete}
      />
    );

    // Q1: Choose Paris (correct)
    fireEvent.click(screen.getByText("Paris"));
    fireEvent.click(screen.getByText("Next Question →"));

    // Q2: Choose 3 (incorrect)
    fireEvent.click(screen.getByText("3"));
    fireEvent.click(screen.getByText("Finish Quiz →"));

    expect(screen.getByText(/MINI QUIZ — COMPLETED/i)).toBeInTheDocument();
    const summary = screen.getByRole("region", { name: "Quiz Results" });
    expect(summary.textContent).toContain("1 / 2 Correct (50%)");
    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({
        topic: "Mini Quiz",
        total: 2,
        correct: 1,
      })
    );
  });

  it("allows retrying the quiz after completion", () => {
    const questions = [sampleQuestions[0]];
    render(<QuizCard topic="Single Q" questions={questions} />);

    fireEvent.click(screen.getByText("Berlin"));
    fireEvent.click(screen.getByText("Finish Quiz →"));

    const summary = screen.getByRole("region", { name: "Quiz Results" });
    expect(summary.textContent).toContain("0 / 1 Correct (0%)");

    const retryBtn = screen.getByText("Try Again");
    fireEvent.click(retryBtn);

    expect(screen.getByText("Question 1 of 1")).toBeInTheDocument();
    expect(screen.getByText("What is the capital of France?")).toBeInTheDocument();
  });

  it("calls onDismiss when close button is clicked", () => {
    const onDismiss = vi.fn();
    render(
      <QuizCard
        topic="Dismissable"
        questions={sampleQuestions}
        onDismiss={onDismiss}
      />
    );

    const closeBtn = screen.getByLabelText("Close quiz");
    fireEvent.click(closeBtn);
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("returns null if questions array is empty", () => {
    const { container } = render(<QuizCard topic="Empty" questions={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
