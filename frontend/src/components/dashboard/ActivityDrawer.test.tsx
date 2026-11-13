import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ActivityDrawer } from "./ActivityDrawer";
import { ActivityLauncher } from "./ActivityLauncher";
import type { ActivityEntry } from "./ActivityLog";

describe("ActivityLauncher and ActivityDrawer", () => {
  afterEach(() => {
    cleanup();
  });

  const sampleActivities: ActivityEntry[] = [
    { id: "1", kind: "SYS", text: "Local sidecar initialized", time: "12:00:01" },
    { id: "2", kind: "YOU", text: "Hello Alex", time: "12:00:02" },
    { id: "3", kind: "ALEX", text: "At your service, Commander", time: "12:00:03" },
    { id: "4", kind: "ERR", text: "Connection timeout retry", time: "12:00:04" },
  ];

  describe("ActivityLauncher", () => {
    it("renders button with activity count and triggers onOpen on click", () => {
      const handleOpen = vi.fn();
      render(
        <ActivityLauncher
          activity={sampleActivities}
          onOpen={handleOpen}
        />
      );

      expect(screen.getByText("OPEN ACTIVITY LOGS")).toBeInTheDocument();
      expect(screen.getByText("4")).toBeInTheDocument();
      expect(screen.getByText(/4 events logged/)).toBeInTheDocument();

      const btn = screen.getByRole("button", { name: "Open Activity Logs" });
      fireEvent.click(btn);
      expect(handleOpen).toHaveBeenCalledTimes(1);
    });

    it("renders live mini activity stream with auto-scrollable responses", () => {
      const { rerender } = render(
        <ActivityLauncher
          activity={sampleActivities}
          onOpen={vi.fn()}
        />
      );

      expect(screen.getByText("LIVE TELEMETRY STREAM")).toBeInTheDocument();
      expect(screen.getByText("Local sidecar initialized")).toBeInTheDocument();
      expect(screen.getByText("At your service, Commander")).toBeInTheDocument();

      const logBox = screen.getByRole("log");
      expect(logBox).toBeInTheDocument();

      // Add a new activity item and verify it renders
      const updated = [
        ...sampleActivities,
        { id: "5", kind: "ALEX" as const, text: "Mission parameters confirmed.", time: "12:00:05" },
      ];
      rerender(<ActivityLauncher activity={updated} onOpen={vi.fn()} />);

      expect(screen.getByText("Mission parameters confirmed.")).toBeInTheDocument();
    });

    it("renders empty state placeholder when activity is empty", () => {
      render(<ActivityLauncher activity={[]} onOpen={vi.fn()} />);
      expect(screen.getByText(/No activity recorded/i)).toBeInTheDocument();
    });
  });

  describe("ActivityDrawer", () => {
    it("is hidden when isOpen is false", () => {
      render(
        <ActivityDrawer
          isOpen={false}
          onClose={vi.fn()}
          activity={sampleActivities}
        />
      );

      const dialog = screen.getByRole("dialog", { hidden: true });
      expect(dialog).toHaveStyle({ display: "none" });
      expect(dialog).toHaveAttribute("aria-hidden", "true");
    });

    it("renders full activity stream when open", () => {
      render(
        <ActivityDrawer
          isOpen={true}
          onClose={vi.fn()}
          activity={sampleActivities}
        />
      );

      expect(screen.getByText("ALEX // ACTIVITY LOGS")).toBeInTheDocument();
      expect(screen.getByText("Local sidecar initialized")).toBeInTheDocument();
      expect(screen.getByText("Hello Alex")).toBeInTheDocument();
      expect(screen.getByText("At your service, Commander")).toBeInTheDocument();
      expect(screen.getByText("Connection timeout retry")).toBeInTheDocument();
    });

    it("filters entries by kind tabs", () => {
      render(
        <ActivityDrawer
          isOpen={true}
          onClose={vi.fn()}
          activity={sampleActivities}
        />
      );

      // Click SYS tab
      const sysTab = screen.getByRole("tab", { name: /SYS/ });
      fireEvent.click(sysTab);

      expect(screen.getByText("Local sidecar initialized")).toBeInTheDocument();
      expect(screen.queryByText("Hello Alex")).not.toBeInTheDocument();
      expect(screen.queryByText("At your service, Commander")).not.toBeInTheDocument();

      // Click ALL tab
      const allTab = screen.getByRole("tab", { name: /ALL/ });
      fireEvent.click(allTab);
      expect(screen.getByText("Hello Alex")).toBeInTheDocument();
    });

    it("searches and filters entries by search query", () => {
      render(
        <ActivityDrawer
          isOpen={true}
          onClose={vi.fn()}
          activity={sampleActivities}
        />
      );

      const searchInput = screen.getByLabelText("Filter logs");
      fireEvent.change(searchInput, { target: { value: "Commander" } });

      expect(screen.getByText("At your service, Commander")).toBeInTheDocument();
      expect(screen.queryByText("Local sidecar initialized")).not.toBeInTheDocument();
    });

    it("calls onClear when clear button is clicked", () => {
      const handleClear = vi.fn();
      render(
        <ActivityDrawer
          isOpen={true}
          onClose={vi.fn()}
          activity={sampleActivities}
          onClear={handleClear}
        />
      );

      const clearBtn = screen.getByText("CLEAR");
      fireEvent.click(clearBtn);
      expect(handleClear).toHaveBeenCalledTimes(1);
    });

    it("triggers onClose after animation delay when close button is clicked", async () => {
      vi.useFakeTimers();
      const handleClose = vi.fn();
      render(
        <ActivityDrawer
          isOpen={true}
          onClose={handleClose}
          activity={sampleActivities}
        />
      );

      const closeBtn = screen.getByRole("button", { name: "Close activity log" });
      fireEvent.click(closeBtn);

      expect(handleClose).not.toHaveBeenCalled();
      vi.advanceTimersByTime(300);
      expect(handleClose).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });
  });
});
