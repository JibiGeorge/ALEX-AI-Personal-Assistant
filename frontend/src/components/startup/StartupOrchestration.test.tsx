import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HolographicStartup } from "./HolographicStartup";
import { App } from "../../App";
import { useLiveVoice } from "../../hooks/useLiveVoice";
import type { AlexApi } from "../../types/api";

vi.mock("../../hooks/useLiveVoice", () => ({ useLiveVoice: vi.fn() }));

const mockVoice = {
  active: false,
  starting: false,
  assistantSpeaking: false,
  analyserNode: null,
  start: vi.fn().mockResolvedValue(undefined),
  stop: vi.fn().mockResolvedValue(undefined),
  interrupt: vi.fn().mockResolvedValue(undefined),
  sendText: vi.fn().mockResolvedValue({
    input_text: "Hello Alex",
    output_text: "Live answer",
  }),
};

const mockBridge: Partial<AlexApi> = {
  ensureMicrophoneAccess: vi.fn().mockResolvedValue({ granted: true, status: "granted" }),
  toggleFullscreen: vi.fn().mockResolvedValue(true),
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
    cpu_percent: 20,
    memory_percent: 40,
    network_mb_per_sec: 2.5,
    operating_system: "Darwin / macOS",
    uptime_seconds: 4200,
    process_count: 210,
    gpu_percent: 25,
    temperature_c: 48,
  }),
  getSystemAlerts: vi.fn().mockResolvedValue({ alerts: [] }),
  listReminders: vi.fn().mockResolvedValue({ reminders: [] }),
  listMemory: vi.fn().mockResolvedValue({ entries: [] }),
  listActions: vi.fn().mockResolvedValue({ actions: [] }),
  getLoginItemStatus: vi.fn().mockResolvedValue({ supported: true, enabled: false, shortcutSupported: true }),
  onVoiceEvent: vi.fn().mockReturnValue(() => {}),
  getWakeStatus: vi.fn().mockResolvedValue({ enabled: false, ready: true }),
};

class MockSpeechSynthesisUtterance {
  text: string;
  rate: number = 1;
  constructor(text: string) {
    this.text = text;
  }
}

describe("Intelligent Startup Orchestration Lifecycle", () => {
  let speakMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.mocked(useLiveVoice).mockReturnValue(mockVoice as any);
    speakMock = vi.fn();
    Object.defineProperty(window, "SpeechSynthesisUtterance", {
      configurable: true,
      value: MockSpeechSynthesisUtterance,
    });
    Object.defineProperty(window, "alex", { configurable: true, value: mockBridge });
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        speak: speakMock,
        cancel: vi.fn(),
      },
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("notifies parent of Stage 2 transition so dashboard can reveal only the central avatar", async () => {
    const handleStageChange = vi.fn();
    const handleComplete = vi.fn();

    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={handleComplete}
        onSkipToDashboard={vi.fn()}
        onStageChange={handleStageChange}
        showAvatarInOverlay={false}
        assistantName="Alex"
        userName="Commander"
      />
    );

    // Initial stage is stage1
    expect(handleStageChange).toHaveBeenCalledWith("stage1");

    // After discovery completes in test mode, it must notify stage2
    await waitFor(() => {
      expect(handleStageChange).toHaveBeenCalledWith("stage2");
    });
  });

  it("runs full system configuration checks with animations and categories verified", async () => {
    const handleComplete = vi.fn();

    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={handleComplete}
        onSkipToDashboard={vi.fn()}
        initialStage="stage2"
        showAvatarInOverlay={false}
        assistantName="Alex"
        userName="Commander"
      />
    );

    expect(screen.getByText("SYSTEM INITIALIZATION & DIAGNOSTICS")).toBeInTheDocument();

    await waitFor(
      () => {
        expect(handleComplete).toHaveBeenCalledTimes(1);
      },
      { timeout: 3000 }
    );

    const report = handleComplete.mock.calls[0][0];
    expect(report.overallHealthPercent).toBe(100);
    expect(report.completedCount).toBe(7);
    expect(screen.getByText("ALEX SYSTEM ONLINE")).toBeInTheDocument();
    expect(screen.getByText("ALL SYSTEM DIAGNOSTICS COMPLETED.")).toBeInTheDocument();
  });

  it("orchestrates App startup: welcome -> avatar-only dashboard with checks -> ALEX SYSTEM ONLINE (direct HUD status) -> sequential reveal -> voice announcement 'All systems ready' -> READY", async () => {
    render(<App forceStartupLifecycle={true} />);

    // 1. Initial screen is Stage 1 Welcome Boot Screen
    expect(screen.getByText("ALEX SYSTEM INITIALIZATION")).toBeInTheDocument();
    expect(screen.getByText("A.L.E.X")).toBeInTheDocument();
    expect(screen.getByText("CALIBRATING")).toBeInTheDocument();

    // 2. Automated transition: Stage 2 Diagnostics and Stage 3 Direct HUD System Online
    // The dashboard reveals sequentially
    await waitFor(
      () => {
        expect(screen.getAllByText("ALEX").length).toBeGreaterThanOrEqual(1);
        expect(screen.getByRole("button", { name: "Setup" })).toBeInTheDocument();
      },
      { timeout: 4000 }
    );

    // 3. Voice Announcement occurs only AFTER dashboard is revealed and settled
    await waitFor(
      () => {
        expect(speakMock).toHaveBeenCalled();
      },
      { timeout: 4000 }
    );

    expect(speakMock).toHaveBeenCalledTimes(1);
    const uttered = speakMock.mock.calls[0][0];
    expect(uttered.text).toBe("All systems ready. How may I assist you?");
    expect(uttered.rate).toBe(0.95);

    // Verify popup modal is completely removed
    expect(screen.queryByText("HELLO. I AM READY.")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ENTER COMMAND CENTER ❯" })).not.toBeInTheDocument();
  });

  it("communicates degraded status when AI credentials are not configured", async () => {
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
      api_key_configured: false,
    });

    const handleComplete = vi.fn();
    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={handleComplete}
        onSkipToDashboard={vi.fn()}
        initialStage="stage2"
        showAvatarInOverlay={false}
        assistantName="Alex"
        userName="Commander"
      />
    );

    await waitFor(
      () => {
        expect(handleComplete).toHaveBeenCalledTimes(1);
      },
      { timeout: 3000 }
    );

    const report = handleComplete.mock.calls[0][0];
    expect(report.statusType).toBe("degraded");
    expect(report.statusTitle).toBe("ALEX SYSTEM ONLINE — DEGRADED");
    expect(report.warningCount).toBeGreaterThanOrEqual(1);
    expect(report.overallHealthPercent).toBeLessThan(100);
  });

  it("communicates degraded status when microphone permission is denied", async () => {
    vi.mocked(mockBridge.ensureMicrophoneAccess!).mockResolvedValueOnce({
      granted: false,
      status: "denied",
    });

    const handleComplete = vi.fn();
    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={handleComplete}
        onSkipToDashboard={vi.fn()}
        initialStage="stage2"
        showAvatarInOverlay={false}
        assistantName="Alex"
        userName="Commander"
      />
    );

    await waitFor(
      () => {
        expect(handleComplete).toHaveBeenCalledTimes(1);
      },
      { timeout: 3000 }
    );

    const report = handleComplete.mock.calls[0][0];
    expect(report.statusType).toBe("degraded");
    expect(report.statusTitle).toBe("ALEX SYSTEM ONLINE — DEGRADED");
    const voiceCategory = report.categories.find((c: any) => c.id === "integrations");
    expect(voiceCategory.status).toBe("warning");
    expect(voiceCategory.detail).toMatch(/denied/i);
  });

  it("communicates degraded status when voice engine / speech synthesis is unavailable", async () => {
    // Remove speechSynthesis from window
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: undefined,
    });

    const handleComplete = vi.fn();
    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={handleComplete}
        onSkipToDashboard={vi.fn()}
        initialStage="stage2"
        showAvatarInOverlay={false}
        assistantName="Alex"
        userName="Commander"
      />
    );

    await waitFor(
      () => {
        expect(handleComplete).toHaveBeenCalledTimes(1);
      },
      { timeout: 3000 }
    );

    const report = handleComplete.mock.calls[0][0];
    expect(report.statusType).toBe("degraded");
    const voiceCategory = report.categories.find((c: any) => c.id === "integrations");
    expect(voiceCategory.status).toBe("warning");
    expect(voiceCategory.detail).toMatch(/Speech Synthesizer offline/i);
  });

  it("communicates degraded status when hardware telemetry sensors are passive", async () => {
    vi.mocked(mockBridge.getSystemMetrics!).mockRejectedValueOnce(new Error("Telemetry unavailable"));

    const handleComplete = vi.fn();
    render(
      <HolographicStartup
        active={true}
        onDiagnosticsComplete={handleComplete}
        onSkipToDashboard={vi.fn()}
        initialStage="stage2"
        showAvatarInOverlay={false}
        assistantName="Alex"
        userName="Commander"
      />
    );

    await waitFor(
      () => {
        expect(handleComplete).toHaveBeenCalledTimes(1);
      },
      { timeout: 3000 }
    );

    const report = handleComplete.mock.calls[0][0];
    const cpuCategory = report.categories.find((c: any) => c.id === "cpu_mem");
    expect(cpuCategory.status).toBe("warning");
    expect(cpuCategory.detail).toMatch(/Telemetry sensors passive/i);
  });
});
