import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { useLiveVoice } from "./hooks/useLiveVoice";
import type { AlexApi } from "./types/api";

vi.mock("./hooks/useLiveVoice", () => ({ useLiveVoice: vi.fn() }));

let capturedVoiceCallbacks: any = null;

const voiceMock = {
  active: true,
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

const bridge: AlexApi = {
  ensureMicrophoneAccess: vi.fn().mockResolvedValue({ granted: true, status: "granted" }),
  ensureCameraAccess: vi.fn().mockResolvedValue({ granted: true, status: "granted" }),
  toggleFullscreen: vi.fn().mockResolvedValue(true),
  getStatus: vi.fn().mockResolvedValue({ status: "ready", name: "Alex" }),
  getSystemMetrics: vi.fn().mockResolvedValue({
    cpu_percent: 24,
    memory_percent: 42,
    network_mb_per_sec: 1.5,
    operating_system: "Windows",
    uptime_seconds: 3600,
    process_count: 180,
    gpu_percent: null,
    temperature_c: null,
  }),
  getSystemAlerts: vi.fn().mockResolvedValue({ alerts: [] }),
  listActions: vi.fn().mockResolvedValue({ actions: [] }),
  setActionEnabled: vi.fn(),
  executeAction: vi.fn(),
  getActionHistory: vi.fn().mockResolvedValue({ executions: [] }),
  getSettings: vi.fn().mockResolvedValue({
    settings: {
      assistant_name: "Alex",
      user_name: "",
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
  updateSettings: vi.fn().mockResolvedValue({
    settings: {
      assistant_name: "Alex",
      user_name: "",
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
  listMemory: vi.fn().mockResolvedValue({ entries: [] }),
  upsertMemory: vi.fn().mockResolvedValue({
    category: "general",
    key: "favorite_color",
    value: "cyan",
    confidence: 1,
    source: "user",
    updated_at: new Date().toISOString(),
  }),
  deleteMemory: vi.fn().mockResolvedValue(undefined),
  searchWeb: vi.fn().mockResolvedValue({ query: "", summary: "", citations: [] }),
  listReminders: vi.fn().mockResolvedValue({ reminders: [] }),
  createReminder: vi.fn().mockResolvedValue({
    id: "rem-1",
    text: "Test reminder",
    due_at: new Date(Date.now() + 60000).toISOString(),
    completed: false,
    created_at: new Date().toISOString(),
  }),
  cancelReminder: vi.fn().mockResolvedValue(undefined),
  listDueReminders: vi.fn().mockResolvedValue({ reminders: [] }),
  markReminderDelivered: vi.fn().mockResolvedValue(undefined),
  notifyReminder: vi.fn().mockResolvedValue(undefined),
  notifySystemAlert: vi.fn().mockResolvedValue(undefined),
  sendMessage: vi.fn().mockResolvedValue({
    conversation_id: "conv-1",
    text: "I am ready.",
  }),
  getMediaStatus: vi.fn().mockResolvedValue({
    active: false,
    source: "",
    title: "",
    url: "",
    is_playing: false,
    is_muted: false,
  }),
  resolveMedia: vi.fn().mockImplementation((source: string) => {
    return Promise.resolve({
      url: `https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&enablejsapi=1`,
      audio_url: "",
      title: `DISCO | Official Teaser | ${source}`,
      source_type: "youtube",
      error: null,
    });
  }),
  controlMedia: vi.fn().mockResolvedValue({
    active: true,
    source: "youtube",
    title: "Media",
    url: "https://youtube.com",
    is_playing: true,
    is_muted: false,
  }),
  captureScreen: vi.fn().mockResolvedValue({
    data_base64: "AQID",
    mime_type: "image/png",
    width: 1920,
    height: 1080,
  }),
  getWakeStatus: vi.fn().mockResolvedValue({
    enabled: false,
    running: false,
    ready: true,
    model: "hey_jarvis",
    threshold: 0.5,
  }),
  toggleWakeWord: vi.fn().mockResolvedValue({
    enabled: true,
    running: true,
    ready: true,
    model: "hey_jarvis",
    threshold: 0.5,
  }),
  installWakeModels: vi.fn().mockResolvedValue({ ok: true, message: "Wake word ready", ready: true }),
  wakeAssistant: vi.fn().mockResolvedValue({ status: "ok", state: "LISTENING" }),
  sleepAssistant: vi.fn().mockResolvedValue({ status: "ok", state: "SLEEPING" }),
  openExternal: vi.fn().mockResolvedValue(undefined),
  openWeatherSearch: vi.fn().mockResolvedValue(undefined),
  saveApiKey: vi.fn().mockResolvedValue({ configured: true }),
  getLoginItemStatus: vi.fn().mockResolvedValue({
    supported: true,
    enabled: false,
    shortcutSupported: true,
  }),
  setLoginItemEnabled: vi.fn().mockResolvedValue({
    supported: true,
    enabled: true,
    shortcutSupported: true,
  }),
  createDesktopShortcut: vi.fn().mockResolvedValue(undefined),
  startVoice: vi.fn().mockResolvedValue(undefined),
  sendVoiceAudio: vi.fn(),
  sendVoiceText: vi.fn().mockResolvedValue(undefined),
  interruptVoice: vi.fn().mockResolvedValue(undefined),
  stopVoice: vi.fn().mockResolvedValue(undefined),
  onVoiceEvent: vi.fn().mockReturnValue(() => {}),
};

describe("ALEX Step 7: Voice-Controlled Dynamic HUD Workspace", () => {
  beforeEach(() => {
    (window as any).alex = bridge;
    vi.mocked(useLiveVoice).mockImplementation((callbacks: any) => {
      capturedVoiceCallbacks = callbacks;
      return voiceMock as any;
    });
  });

  afterEach(() => {
    delete (window as any).alex;
    cleanup();
    vi.clearAllMocks();
  });

  it("handles Command 1: 'ALEX, play video Disco Malayalam movie.' via voice", async () => {
    const { container } = render(<App />);
    await waitFor(() => expect(capturedVoiceCallbacks).toBeTruthy());

    // Send voice transcript
    await capturedVoiceCallbacks.onTranscript("ALEX, play video Disco Malayalam movie.", "");

    // Verify resolveMedia was called with query
    await waitFor(() => {
      expect(bridge.resolveMedia).toHaveBeenCalledWith("disco malayalam movie");
    });

    // Verify floating video workspace opened and avatar docked bottom-right
    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
      expect(container.querySelector(".hud-avatar-stage")).toHaveClass("in-workspace-mode");
    });
  });

  it("handles Command 2: 'ALEX, pause the video.' and Command 3: 'ALEX, resume video.' via voice", async () => {
    const { container } = render(<App />);
    await waitFor(() => expect(capturedVoiceCallbacks).toBeTruthy());

    // 1. First open video
    await capturedVoiceCallbacks.onTranscript("ALEX, play video Disco Malayalam movie.", "");
    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
    });

    // 2. Pause video via voice
    await capturedVoiceCallbacks.onTranscript("ALEX, pause the video.", "");
    await waitFor(() => {
      expect(bridge.controlMedia).toHaveBeenCalledWith("pause", undefined, undefined, undefined);
      // Window remains open
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
    });

    // 3. Resume video via voice
    await capturedVoiceCallbacks.onTranscript("ALEX, resume video.", "");
    await waitFor(() => {
      expect(bridge.controlMedia).toHaveBeenCalledWith("resume", undefined, undefined, undefined);
      // Window remains open
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
    });
  });

  it("handles Command 4: 'ALEX, open this PDF.' via voice", async () => {
    const { container } = render(<App />);
    await waitFor(() => expect(capturedVoiceCallbacks).toBeTruthy());

    await capturedVoiceCallbacks.onTranscript("ALEX, open this PDF.", "");

    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
      expect(container.querySelector(".ws-activity-badge")).toHaveTextContent("PDF PREVIEW");
      expect(container.querySelector(".hud-avatar-stage")).toHaveClass("in-workspace-mode");
    });
  });

  it("handles Command 5: 'ALEX, play music.' via voice", async () => {
    const { container } = render(<App />);
    await waitFor(() => expect(capturedVoiceCallbacks).toBeTruthy());

    await capturedVoiceCallbacks.onTranscript("ALEX, play music.", "");

    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
      expect(container.querySelector(".ws-activity-badge")).toHaveTextContent("AUDIO PLAYER");
      expect(container.querySelector(".ws-music-track-title")).toHaveTextContent(/cyberpunk ambient synthesis/i);
      expect(container.querySelector(".hud-avatar-stage")).toHaveClass("in-workspace-mode");
    });
  });

  it("handles Command 6: 'ALEX, open this image.' via voice", async () => {
    const { container } = render(<App />);
    await waitFor(() => expect(capturedVoiceCallbacks).toBeTruthy());

    await capturedVoiceCallbacks.onTranscript("ALEX, open this image.", "");

    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
      expect(container.querySelector(".ws-activity-badge")).toHaveTextContent("IMAGE VIEWER");
      expect(container.querySelector(".hud-avatar-stage")).toHaveClass("in-workspace-mode");
    });
  });

  it("handles Command 7: 'ALEX, minimize this window.' and Command 8: 'ALEX, restore the window.' via voice", async () => {
    const { container } = render(<App />);
    await waitFor(() => expect(capturedVoiceCallbacks).toBeTruthy());

    // Open workspace first
    await capturedVoiceCallbacks.onTranscript("ALEX, play music.", "");
    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
    });

    // Minimize via voice
    await capturedVoiceCallbacks.onTranscript("ALEX, minimize this window.", "");
    await waitFor(() => {
      expect(container.querySelector(".ws-minimized-dock")).toBeInTheDocument();
      // Compact avatar positioning is preserved!
      expect(container.querySelector(".hud-avatar-stage")).toHaveClass("in-workspace-mode");
    });

    // Restore via voice
    await capturedVoiceCallbacks.onTranscript("ALEX, restore the window.", "");
    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
      expect(container.querySelector(".ws-minimized-dock")).toBeNull();
      expect(container.querySelector(".hud-avatar-stage")).toHaveClass("in-workspace-mode");
    });
  });

  it("handles Command 9: 'ALEX, close this window.' via voice and returns avatar to centre", async () => {
    const { container } = render(<App />);
    await waitFor(() => expect(capturedVoiceCallbacks).toBeTruthy());

    // Open workspace first
    await capturedVoiceCallbacks.onTranscript("ALEX, play music.", "");
    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
      expect(container.querySelector(".hud-avatar-stage")).toHaveClass("in-workspace-mode");
    });

    // Close via voice
    await capturedVoiceCallbacks.onTranscript("ALEX, close this window.", "");
    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeNull();
      // Avatar returned to center!
      expect(container.querySelector(".hud-avatar-stage")).not.toHaveClass("in-workspace-mode");
    });
  });

  it("handles Command 10: 'ALEX, return to normal mode.' via voice", async () => {
    const { container } = render(<App />);
    await waitFor(() => expect(capturedVoiceCallbacks).toBeTruthy());

    // Open video first
    await capturedVoiceCallbacks.onTranscript("ALEX, play video Disco Malayalam movie.", "");
    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
      expect(container.querySelector(".hud-avatar-stage")).toHaveClass("in-workspace-mode");
    });

    // Return to normal mode via voice
    await capturedVoiceCallbacks.onTranscript("ALEX, return to normal mode.", "");
    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeNull();
      expect(bridge.controlMedia).toHaveBeenCalledWith("stop", undefined, undefined, undefined);
      // Avatar returned to center
      expect(container.querySelector(".hud-avatar-stage")).not.toHaveClass("in-workspace-mode");
    });
  });

  it("handles voice command: 'Open camera and show me in head up display.'", async () => {
    const { container } = render(<App />);
    await waitFor(() => expect(capturedVoiceCallbacks).toBeTruthy());

    // Initially avatar is centered
    expect(container.querySelector(".hud-avatar-stage")).not.toHaveClass("in-workspace-mode");

    // Issue the voice command
    await capturedVoiceCallbacks.onTranscript("Open camera and show me in head up display.", "");

    // Verify workspace opened with camera and avatar moved to bottom-right
    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeInTheDocument();
      expect(container.querySelector(".ws-camera-view")).toBeInTheDocument();
      expect(container.querySelector(".hud-avatar-stage")).toHaveClass("in-workspace-mode");
    });

    // Close camera via voice
    await capturedVoiceCallbacks.onTranscript("ALEX, close camera", "");
    await waitFor(() => {
      expect(container.querySelector(".hud-workspace-window")).toBeNull();
      // Avatar returned to center
      expect(container.querySelector(".hud-avatar-stage")).not.toHaveClass("in-workspace-mode");
    });
  });
});
