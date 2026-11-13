import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HolographicStartup } from "./HolographicStartup";
import type { AlexApi } from "../../types/api";

const mockBridge: Partial<AlexApi> = {
  getStatus: vi.fn().mockResolvedValue({ status: "ready", name: "Alex" }),
  getSettings: vi.fn().mockResolvedValue({
    settings: {
      assistant_name: "Alex",
      user_name: "Commander",
      accent_color: "#00d4ff",
      operating_system: "Windows",
      voice_name: "Charon",
      hud_style: "face",
      audio_input_device_id: "",
      audio_output_device_id: "",
      push_to_talk_enabled: false,
    },
    api_key_configured: true,
  }),
  getSystemMetrics: vi.fn().mockResolvedValue({
    cpu_percent: 24,
    memory_percent: 48,
    network_mb_per_sec: 3.2,
    operating_system: "Windows 11 Pro",
    uptime_seconds: 7200,
    process_count: 165,
    gpu_percent: 30,
    temperature_c: 55,
  }),
  getSystemAlerts: vi.fn().mockResolvedValue({ alerts: [] }),
  listReminders: vi.fn().mockResolvedValue({ reminders: [] }),
  getLoginItemStatus: vi.fn().mockResolvedValue({ supported: true, enabled: false, shortcutSupported: true }),
};

describe("HolographicStartup Component", () => {
  beforeEach(() => {
    Object.defineProperty(window, "alex", { configurable: true, value: mockBridge });
    // Mock speechSynthesis
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        speak: vi.fn(),
        cancel: vi.fn(),
      },
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders the Stage 1 Cinematic Startup screen with A.L.E.X logo and boot sequence elements", async () => {
    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={vi.fn()}
        onSkipToDashboard={vi.fn()}
        assistantName="Alex"
        userName="Commander"
      />
    );

    expect(screen.getByText("ALEX COMMAND CENTER")).toBeInTheDocument();
    expect(screen.getByText("A.L.E.X")).toBeInTheDocument();
    expect(screen.getByText("ADVANCED LOGICAL ELECTRONIC X-SYSTEM")).toBeInTheDocument();
    expect(screen.getByText("CALIBRATING")).toBeInTheDocument();
    expect(screen.getByText("DASHBOARD ✕")).toBeInTheDocument();
  });

  it("renders J.A.R.V.I.S logo and subtitle when assistantName is Jarvis", () => {
    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={vi.fn()}
        onSkipToDashboard={vi.fn()}
        assistantName="Jarvis"
        userName="Tony"
      />
    );

    expect(screen.getByText("J.A.R.V.I.S")).toBeInTheDocument();
    expect(screen.getByText("JUST A RATHER VERY INTELLIGENT SYSTEM")).toBeInTheDocument();
    expect(screen.getByText("CALIBRATING")).toBeInTheDocument();
  });

  it("triggers onSkipToDashboard when the user clicks DASHBOARD ✕ button", () => {
    const handleSkip = vi.fn();
    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={vi.fn()}
        onSkipToDashboard={handleSkip}
        assistantName="Alex"
        userName="Commander"
      />
    );

    const skipBtn = screen.getByRole("button", { name: "Skip to Dashboard" });
    fireEvent.click(skipBtn);
    expect(handleSkip).toHaveBeenCalledTimes(1);
  });

  it("executes diagnostics and completes with a full diagnostic report", async () => {
    const handleComplete = vi.fn();
    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={handleComplete}
        onSkipToDashboard={vi.fn()}
        assistantName="Alex"
        userName="Commander"
      />
    );

    // In test environment, it transitions into stage2 diagnostics
    await waitFor(
      () => {
        expect(handleComplete).toHaveBeenCalledTimes(1);
      },
      { timeout: 3000 }
    );

    const report = handleComplete.mock.calls[0][0];
    expect(report.overallHealthPercent).toBe(100);
    expect(report.completedCount).toBe(7);
    expect(report.failedCount).toBe(0);
    expect(report.categories.length).toBe(7);
  });

  it("handles backend connection failure with retry and degraded mode options", async () => {
    vi.mocked(mockBridge.getStatus!).mockRejectedValueOnce(new Error("Connection refused"));
    const handleSkip = vi.fn();

    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={vi.fn()}
        onSkipToDashboard={handleSkip}
        assistantName="Alex"
        userName="Commander"
      />
    );

    await waitFor(() => {
      expect(screen.getByText("MANDATORY INITIALIZATION FAILURE")).toBeInTheDocument();
    });

    expect(screen.getByText(/Could not connect to local backend sidecar/i)).toBeInTheDocument();

    const degradedBtn = screen.getByText("CONTINUE IN DEGRADED MODE ❯");
    fireEvent.click(degradedBtn);
    expect(handleSkip).toHaveBeenCalledTimes(1);
  });

  it("never exposes passwords, api keys, or secrets in the UI", async () => {
    vi.mocked(mockBridge.getSettings!).mockResolvedValueOnce({
      settings: {
        assistant_name: "Alex",
        user_name: "Commander",
        accent_color: "#00d4ff",
        operating_system: "Windows",
        voice_name: "Charon",
        hud_style: "face",
        audio_input_device_id: "",
        audio_output_device_id: "",
        push_to_talk_enabled: false,
      },
      api_key_configured: true,
    });

    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={vi.fn()}
        onSkipToDashboard={vi.fn()}
        assistantName="Alex"
        userName="Commander"
      />
    );

    await waitFor(() => {
      expect(screen.queryByText(/AIza[0-9A-Za-z-_]{35}/)).not.toBeInTheDocument();
      expect(screen.queryByText(/secret/i)).not.toBeInTheDocument();
    });
  });
});
