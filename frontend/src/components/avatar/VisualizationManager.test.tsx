import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  VisualizationManager,
  normalizeVisualization,
} from "./VisualizationManager";
import { RealisticHumanoidRobot } from "./RealisticHumanoidRobot";

describe("VisualizationManager & RealisticHumanoidRobot", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(cleanup);

  it("normalizes visualization IDs correctly", () => {
    expect(normalizeVisualization("face")).toBe("face");
    expect(normalizeVisualization("existing_face")).toBe("face");
    expect(normalizeVisualization("core")).toBe("core");
    expect(normalizeVisualization("reactor_core")).toBe("core");
    expect(normalizeVisualization("robot")).toBe("robot");
    expect(normalizeVisualization("realistic_humanoid")).toBe("robot");
    expect(normalizeVisualization(null)).toBe("face");
  });

  it("renders existing humanoid face when visualization is 'face' or 'existing_face'", () => {
    const { unmount } = render(
      <VisualizationManager
        assistantName="Alex"
        mode="idle"
        visualization="face"
      />,
    );

    expect(screen.getByTestId("holo-canvas")).toBeInTheDocument();
    expect(screen.getByText("STANDING BY")).toBeInTheDocument();
    unmount();
  });

  it("renders reactor core when visualization is 'core' or 'reactor_core'", () => {
    const { unmount } = render(
      <VisualizationManager
        assistantName="Alex"
        mode="thinking"
        visualization="reactor_core"
      />,
    );

    expect(screen.queryByTestId("holo-canvas")).toBeNull();
    expect(
      screen.getByRole("img", { name: "Animated reactor core" }),
    ).toBeInTheDocument();
    expect(screen.getByText("PROCESSING")).toBeInTheDocument();
    unmount();
  });

  it("renders realistic humanoid robot when visualization is 'realistic_humanoid' or 'robot'", () => {
    const { unmount } = render(
      <VisualizationManager
        assistantName="Alex"
        mode="idle"
        visualization="realistic_humanoid"
      />,
    );

    expect(screen.getByTestId("holo-robot-stage")).toBeInTheDocument();
    expect(screen.getByTestId("holo-robot-canvas")).toBeInTheDocument();
    expect(screen.getByText("STANDING BY")).toBeInTheDocument();
    unmount();
  });

  it("handles speaking state and analyserNode in RealisticHumanoidRobot without errors", () => {
    const mockAnalyser = {
      fftSize: 256,
      context: { sampleRate: 44100 },
      getByteFrequencyData: vi.fn((arr: Uint8Array) => arr.fill(50)),
      getFloatTimeDomainData: vi.fn((arr: Float32Array) => arr.fill(0.08)),
    } as unknown as AnalyserNode;

    const { unmount } = render(
      <RealisticHumanoidRobot
        assistantName="Alex"
        mode="speaking"
        speaking={true}
        analyserNode={mockAnalyser}
      />,
    );

    expect(screen.getByTestId("holo-robot-canvas")).toBeInTheDocument();
    expect(screen.getByText("RESPONDING")).toBeInTheDocument();
    unmount();
  });

  it("switches visualizations dynamically between all three representations", () => {
    const { rerender } = render(
      <VisualizationManager
        assistantName="Alex"
        mode="idle"
        visualization="face"
      />,
    );
    expect(screen.getByTestId("holo-canvas")).toBeInTheDocument();

    // Switch to core
    rerender(
      <VisualizationManager
        assistantName="Alex"
        mode="idle"
        visualization="core"
      />,
    );
    expect(
      screen.getByRole("img", { name: "Animated reactor core" }),
    ).toBeInTheDocument();

    // Switch to robot
    rerender(
      <VisualizationManager
        assistantName="Alex"
        mode="idle"
        visualization="robot"
      />,
    );
    expect(screen.getByTestId("holo-robot-canvas")).toBeInTheDocument();
  });
});

