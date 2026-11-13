import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { StartupBriefing } from "./StartupBriefing";
import type { AlexApi } from "../types/api";

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
    memory_percent: 52,
    network_mb_per_sec: 2.4,
    operating_system: "Windows 11 Pro",
    uptime_seconds: 7200,
    process_count: 165,
    gpu_percent: 35,
    temperature_c: 58,
  }),
  getSystemAlerts: vi.fn().mockResolvedValue({ alerts: [] }),
  listReminders: vi.fn().mockResolvedValue({
    reminders: [
      { id: "rem-1", message: "Review quarterly report", due_at: new Date(Date.now() + 3600000).toISOString(), status: "pending" },
    ],
  }),
  getSystemBriefing: vi.fn().mockResolvedValue({
    greeting: "Good morning, Commander.",
    assistant_name: "Alex",
    user_name: "Commander",
    timestamp_iso: new Date().toISOString(),
    system: {
      cpu_percent: 24,
      ram_percent: 52,
      active_alerts_count: 0,
      system_status: "Normal",
    },
    reminders: {
      total_pending: 1,
      due_now: 0,
      upcoming_messages: ["Review quarterly report"],
    },
    known_identity_facts: [],
  }),
};

describe("StartupBriefing Component", () => {
  beforeEach(() => {
    Object.defineProperty(window, "alex", { configurable: true, value: mockBridge });
    // Mock speechSynthesis
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        speak: vi.fn((utterance: SpeechSynthesisUtterance) => {
          setTimeout(() => {
            if (utterance.onend) utterance.onend(new Event("end") as SpeechSynthesisEvent);
          }, 50);
        }),
        cancel: vi.fn(),
      },
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders the welcome and initialization checklist with 8 real services", async () => {
    render(<StartupBriefing active={true} onComplete={vi.fn()} isColdBoot={true} />);

    expect(screen.getByText("ALEX ASSISTANT")).toBeInTheDocument();
    expect(screen.getByText("INITIALIZING SYSTEM")).toBeInTheDocument();
    expect(screen.getByText("Configuration & Profile")).toBeInTheDocument();
    expect(screen.getByText("Local Backend Sidecar")).toBeInTheDocument();
    expect(screen.getByText("AI Model Provider")).toBeInTheDocument();
    expect(screen.getByText("Hardware Telemetry")).toBeInTheDocument();
    expect(screen.getByText("Audio Endpoints")).toBeInTheDocument();
    expect(screen.getByText("Scheduler & Reminders")).toBeInTheDocument();
    expect(screen.getByText("Platform Health & Alerts")).toBeInTheDocument();
    expect(screen.getByText("Speech & Live Voice")).toBeInTheDocument();
  });

  it("advances directly to briefing when isColdBoot is false (manual wake-up)", async () => {
    render(<StartupBriefing active={true} onComplete={vi.fn()} isColdBoot={false} />);

    // Starts directly in briefing mode
    expect(screen.getByText("DAILY BRIEFING")).toBeInTheDocument();
    expect(screen.getByText("Processor Utilization")).toBeInTheDocument();
    expect(screen.getByText("HARDWARE TELEMETRY")).toBeInTheDocument();
  });

  it("advances through sequential briefing items when NEXT is clicked", async () => {
    render(<StartupBriefing active={true} onComplete={vi.fn()} isColdBoot={false} />);

    expect(screen.getByText("Processor Utilization")).toBeInTheDocument();

    const nextBtn = screen.getByRole("button", { name: "Next Item" });
    fireEvent.click(nextBtn);

    // Step 2: Memory Utilization
    expect(await screen.findByText("Memory Utilization")).toBeInTheDocument();

    fireEvent.click(nextBtn);
    // Step 3: Storage
    expect(await screen.findByText("Primary Volume & Workspace")).toBeInTheDocument();

    fireEvent.click(nextBtn);
    // Step 4: GPU
    expect(await screen.findByText("GPU Telemetry")).toBeInTheDocument();
  });

  it("calls onComplete when the user clicks DASHBOARD (skip button)", async () => {
    const handleComplete = vi.fn();
    render(<StartupBriefing active={true} onComplete={handleComplete} isColdBoot={false} />);

    const skipBtn = screen.getByRole("button", { name: "Skip to Dashboard" });
    fireEvent.click(skipBtn);

    expect(handleComplete).toHaveBeenCalledTimes(1);
  });

  it("supports pausing and resuming the briefing", async () => {
    render(<StartupBriefing active={true} onComplete={vi.fn()} isColdBoot={false} />);

    const pauseBtn = screen.getByRole("button", { name: "Pause Briefing" });
    expect(pauseBtn).toHaveTextContent("⏸ PAUSE");

    fireEvent.click(pauseBtn);
    expect(screen.getByRole("button", { name: "Resume Briefing" })).toHaveTextContent("▶ RESUME");

    fireEvent.click(screen.getByRole("button", { name: "Resume Briefing" }));
    expect(screen.getByRole("button", { name: "Pause Briefing" })).toHaveTextContent("⏸ PAUSE");
  });

  it("supports muting and unmuting voice announcements", async () => {
    render(<StartupBriefing active={true} onComplete={vi.fn()} isColdBoot={false} voiceEnabledDefault={true} />);

    const muteBtn = screen.getByRole("button", { name: "Mute Voice" });
    expect(muteBtn).toHaveTextContent("🔊 VOICE");

    fireEvent.click(muteBtn);
    expect(screen.getByRole("button", { name: "Unmute Voice" })).toHaveTextContent("🔇 MUTED");
  });

  it("displays reminders information when on the reminders step", async () => {
    render(<StartupBriefing active={true} onComplete={vi.fn()} isColdBoot={false} />);

    // Step through to reminders (step 7)
    const nextBtn = screen.getByRole("button", { name: "Next Item" });
    for (let i = 0; i < 6; i++) {
      fireEvent.click(nextBtn);
    }

    expect(await screen.findByText("Reminders & Scheduled Tasks")).toBeInTheDocument();
  });

  it("handles backend connection failure during checklist gracefully", async () => {
    vi.mocked(mockBridge.getStatus!).mockRejectedValueOnce(new Error("Connection refused"));
    render(<StartupBriefing active={true} onComplete={vi.fn()} isColdBoot={true} />);

    await waitFor(() => {
      expect(screen.getByText("Could not reach 127.0.0.1:8765")).toBeInTheDocument();
    });
  });
});

