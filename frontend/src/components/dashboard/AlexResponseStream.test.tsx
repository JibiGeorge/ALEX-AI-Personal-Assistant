import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AlexResponseStream, type AlexResponseItem } from "./AlexResponseStream";

describe("AlexResponseStream", () => {
  const mockResponses: AlexResponseItem[] = [
    {
      id: "1",
      time: "17:27:57",
      text: "Playing 'How I Landed 10 Interviews in 1 Week' in the HUD workspace.",
    },
    {
      id: "2",
      time: "17:27:58",
      text: "Displaying live camera feed in HUD workspace.",
    },
    {
      id: "3",
      time: "17:28:10",
      text: "Opening job hunting on HUD.",
    },
  ];

  beforeEach(() => {
    // Mock Element.prototype.scrollTo
    Element.prototype.scrollTo = vi.fn();
  });

  it("renders empty state placeholder when no responses exist", () => {
    render(<AlexResponseStream responses={[]} />);

    expect(screen.getByText(/Awaiting incoming transmission from ALEX.../i)).toBeInTheDocument();
    expect(screen.getByText("00")).toBeInTheDocument();
  });

  it("renders list of ALEX responses with timestamps", () => {
    render(<AlexResponseStream responses={mockResponses} />);

    expect(screen.getByText("17:27:57")).toBeInTheDocument();
    expect(
      screen.getByText("Playing 'How I Landed 10 Interviews in 1 Week' in the HUD workspace.")
    ).toBeInTheDocument();
    expect(screen.getByText("17:27:58")).toBeInTheDocument();
    expect(screen.getByText("Displaying live camera feed in HUD workspace.")).toBeInTheDocument();
    expect(screen.getByText("17:28:10")).toBeInTheDocument();
    expect(screen.getByText("Opening job hunting on HUD.")).toBeInTheDocument();
    expect(screen.getByText("03")).toBeInTheDocument();
  });

  it("calls scrollTo when new responses arrive and autoscroll is enabled", () => {
    const { rerender } = render(<AlexResponseStream responses={mockResponses} />);

    expect(Element.prototype.scrollTo).toHaveBeenCalled();

    const updatedResponses: AlexResponseItem[] = [
      ...mockResponses,
      {
        id: "4",
        time: "17:29:00",
        text: "Engine run finished.",
      },
    ];

    rerender(<AlexResponseStream responses={updatedResponses} />);
    expect(Element.prototype.scrollTo).toHaveBeenCalled();
  });

  it("toggles autoscroll state when clicking the autoscroll button", () => {
    render(<AlexResponseStream responses={mockResponses} />);

    const autoScrollBtn = screen.getByRole("button", { name: /autoscroll/i });
    expect(autoScrollBtn).toHaveTextContent("AUTOSCROLL");

    fireEvent.click(autoScrollBtn);
    expect(autoScrollBtn).toHaveTextContent("PAUSED");

    fireEvent.click(autoScrollBtn);
    expect(autoScrollBtn).toHaveTextContent("AUTOSCROLL");
  });

  it("collapses and expands when clicking the minimize button", () => {
    render(<AlexResponseStream responses={mockResponses} />);

    const collapseBtn = screen.getByRole("button", { name: /minimize stream/i });
    fireEvent.click(collapseBtn);

    // List should be collapsed
    expect(screen.queryByText("17:27:57")).not.toBeInTheDocument();
    expect(collapseBtn).toHaveAttribute("aria-label", "Expand Stream");

    // Click expand
    fireEvent.click(collapseBtn);
    expect(screen.getByText("17:27:57")).toBeInTheDocument();
  });

  it("renders in workspace mode with correct styling class", () => {
    const { container } = render(
      <AlexResponseStream responses={mockResponses} isWorkspaceActive={true} />
    );

    expect(container.querySelector(".alex-response-stream-panel")).toHaveClass(
      "in-workspace-mode"
    );
  });
});

