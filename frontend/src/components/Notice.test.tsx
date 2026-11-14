import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { Notice } from "./Notice";

describe("Notice component", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders success notice with status role and content", () => {
    const onDismiss = vi.fn();
    render(
      <Notice kind="success" onDismiss={onDismiss}>
        Preferences saved.
      </Notice>
    );

    expect(screen.getByRole("status")).toBeDefined();
    expect(screen.getByText("Preferences saved.")).toBeDefined();
  });

  it("renders error notice with alert role and content", () => {
    const onDismiss = vi.fn();
    render(
      <Notice kind="error" onDismiss={onDismiss}>
        Failed to save preferences.
      </Notice>
    );

    expect(screen.getByRole("alert")).toBeDefined();
    expect(screen.getByText("Failed to save preferences.")).toBeDefined();
  });

  it("auto-closes success notice after 4000ms by default", () => {
    const onDismiss = vi.fn();
    render(
      <Notice kind="success" onDismiss={onDismiss}>
        Preferences saved.
      </Notice>
    );

    // After 3900ms, should not have been dismissed yet
    act(() => {
      vi.advanceTimersByTime(3900);
    });
    expect(onDismiss).not.toHaveBeenCalled();

    // After 4000ms, should trigger onDismiss
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("auto-closes error notice after 6000ms by default", () => {
    const onDismiss = vi.fn();
    render(
      <Notice kind="error" onDismiss={onDismiss}>
        Network timeout.
      </Notice>
    );

    // After 4000ms, should still be visible
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(onDismiss).not.toHaveBeenCalled();

    // After 6000ms, should trigger onDismiss
    act(() => {
      vi.advanceTimersByTime(2100);
    });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("respects custom autoCloseMs duration", () => {
    const onDismiss = vi.fn();
    render(
      <Notice kind="success" onDismiss={onDismiss} autoCloseMs={2500}>
        Quick message.
      </Notice>
    );

    act(() => {
      vi.advanceTimersByTime(2400);
    });
    expect(onDismiss).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("does not auto-close when autoCloseMs is false", () => {
    const onDismiss = vi.fn();
    render(
      <Notice kind="success" onDismiss={onDismiss} autoCloseMs={false}>
        Persistent message.
      </Notice>
    );

    act(() => {
      vi.advanceTimersByTime(10000);
    });
    expect(onDismiss).not.toHaveBeenCalled();
  });

  it("calls onDismiss immediately when dismiss button is clicked", () => {
    const onDismiss = vi.fn();
    render(
      <Notice kind="success" onDismiss={onDismiss}>
        Dismiss me.
      </Notice>
    );

    const button = screen.getByRole("button", { name: "Dismiss notification" });
    fireEvent.click(button);

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("pauses timer on mouseEnter and resumes on mouseLeave", () => {
    const onDismiss = vi.fn();
    render(
      <Notice kind="success" onDismiss={onDismiss} autoCloseMs={4000}>
        Hover to read me.
      </Notice>
    );

    // Advance 2000ms
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(onDismiss).not.toHaveBeenCalled();

    // Hover over notice
    const noticeEl = screen.getByRole("status");
    fireEvent.mouseEnter(noticeEl);

    // Advance 5000ms while hovered
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(onDismiss).not.toHaveBeenCalled();

    // Mouse leave -> timer resumes
    fireEvent.mouseLeave(noticeEl);

    // Remaining time (~2000ms) elapses
    act(() => {
      vi.advanceTimersByTime(2200);
    });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("resets auto-close timer when message content updates", () => {
    const onDismiss = vi.fn();
    const { rerender } = render(
      <Notice kind="success" onDismiss={onDismiss} autoCloseMs={4000}>
        Initial message.
      </Notice>
    );

    // Advance 3000ms
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(onDismiss).not.toHaveBeenCalled();

    // Rerender with new message
    rerender(
      <Notice kind="success" onDismiss={onDismiss} autoCloseMs={4000}>
        Updated new message.
      </Notice>
    );

    // Advance another 2000ms (5000ms total from start, but 2000ms for new message)
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(onDismiss).not.toHaveBeenCalled();

    // Advance another 2100ms (4100ms since update)
    act(() => {
      vi.advanceTimersByTime(2100);
    });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
