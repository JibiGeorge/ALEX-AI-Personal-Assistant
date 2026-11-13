import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FloatingClipboardPanel } from "./FloatingClipboardPanel";

describe("FloatingClipboardPanel Component", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("does not render when initial text is under 10 characters", () => {
    render(<FloatingClipboardPanel initialText="Short" onAction={vi.fn()} />);
    expect(screen.queryByTestId("clipboard-floating-panel")).toBeNull();
  });

  it("renders when initial text satisfies minimum length", () => {
    const text = "This is a long copied paragraph ready for intelligence processing.";
    render(<FloatingClipboardPanel initialText={text} onAction={vi.fn()} />);

    expect(screen.getByTestId("clipboard-floating-panel")).toBeInTheDocument();
    expect(screen.getByText("◈ CLIPBOARD DETECTED")).toBeInTheDocument();
    expect(screen.getByText(/This is a long copied paragraph/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "TRANSLATE" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "SUMMARISE" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "EXPLAIN" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "FIX" })).toBeInTheDocument();
  });

  it("truncates preview text longer than 58 characters with an ellipsis", () => {
    const text = "This is an extremely long piece of text that goes way beyond fifty eight characters in length.";
    render(<FloatingClipboardPanel initialText={text} onAction={vi.fn()} />);

    const preview = screen.getByText(/This is an extremely long piece of text/);
    expect(preview.textContent).toContain("…");
  });

  it("triggers TRANSLATE command format and dismisses panel", () => {
    const onAction = vi.fn();
    const text = "Bonjour le monde, ceci est un test de traduction.";
    render(<FloatingClipboardPanel initialText={text} onAction={onAction} />);

    fireEvent.click(screen.getByRole("button", { name: "TRANSLATE" }));
    expect(onAction).toHaveBeenCalledTimes(1);
    expect(onAction).toHaveBeenCalledWith(`Translate this text to English: ${text}`);
    expect(screen.queryByTestId("clipboard-floating-panel")).toBeNull();
  });

  it("triggers SUMMARISE command format and dismisses panel", () => {
    const onAction = vi.fn();
    const text = "Artificial intelligence research has progressed rapidly in recent years.";
    render(<FloatingClipboardPanel initialText={text} onAction={onAction} />);

    fireEvent.click(screen.getByRole("button", { name: "SUMMARISE" }));
    expect(onAction).toHaveBeenCalledTimes(1);
    expect(onAction).toHaveBeenCalledWith(`Summarise this: ${text}`);
    expect(screen.queryByTestId("clipboard-floating-panel")).toBeNull();
  });

  it("triggers EXPLAIN command format and dismisses panel", () => {
    const onAction = vi.fn();
    const text = "Quantum entanglement is a physical phenomenon occurring when pairs of particles interact.";
    render(<FloatingClipboardPanel initialText={text} onAction={onAction} />);

    fireEvent.click(screen.getByRole("button", { name: "EXPLAIN" }));
    expect(onAction).toHaveBeenCalledTimes(1);
    expect(onAction).toHaveBeenCalledWith(`Explain this: ${text}`);
    expect(screen.queryByTestId("clipboard-floating-panel")).toBeNull();
  });

  it("triggers FIX command format and dismisses panel", () => {
    const onAction = vi.fn();
    const text = "Their is some speling mistakes in this text that need fix.";
    render(<FloatingClipboardPanel initialText={text} onAction={onAction} />);

    fireEvent.click(screen.getByRole("button", { name: "FIX" }));
    expect(onAction).toHaveBeenCalledTimes(1);
    expect(onAction).toHaveBeenCalledWith(`Fix grammar and spelling: ${text}`);
    expect(screen.queryByTestId("clipboard-floating-panel")).toBeNull();
  });

  it("dismisses panel when close button is clicked", () => {
    const text = "Sample text to dismiss with close button.";
    render(<FloatingClipboardPanel initialText={text} onAction={vi.fn()} />);

    expect(screen.getByTestId("clipboard-floating-panel")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Dismiss clipboard panel" }));
    expect(screen.queryByTestId("clipboard-floating-panel")).toBeNull();
  });

  it("dismisses panel when Escape key is pressed", () => {
    const text = "Sample text to dismiss with Escape key.";
    render(<FloatingClipboardPanel initialText={text} onAction={vi.fn()} />);

    expect(screen.getByTestId("clipboard-floating-panel")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("clipboard-floating-panel")).toBeNull();
  });

  it("auto-dismisses after configured timeout (default 8000ms)", () => {
    const text = "Sample text that should auto-dismiss after eight seconds.";
    render(<FloatingClipboardPanel autoDismissMs={8000} initialText={text} onAction={vi.fn()} />);

    expect(screen.getByTestId("clipboard-floating-panel")).toBeInTheDocument();

    // Advance 7.9 seconds - should still be visible
    act(() => {
      vi.advanceTimersByTime(7900);
    });
    expect(screen.getByTestId("clipboard-floating-panel")).toBeInTheDocument();

    // Advance past 8.0 seconds - should dismiss
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(screen.queryByTestId("clipboard-floating-panel")).toBeNull();
  });
});
