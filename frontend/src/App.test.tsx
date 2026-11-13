import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { useLiveVoice } from "./hooks/useLiveVoice";
import type { AlexApi } from "./types/api";

vi.mock("./hooks/useLiveVoice", () => ({ useLiveVoice: vi.fn() }));

const voice = {
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

const bridge: AlexApi = {
  ensureMicrophoneAccess: vi.fn().mockResolvedValue({ granted: true, status: "granted" }),
  toggleFullscreen: vi.fn().mockResolvedValue(true),
  getStatus: vi.fn().mockResolvedValue({ status: "ready", name: "Alex" }),
  getSystemMetrics: vi.fn().mockResolvedValue({
    cpu_percent: 28,
    memory_percent: 45,
    network_mb_per_sec: 1.2,
    operating_system: "Windows",
    uptime_seconds: 3660,
    process_count: 190,
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
    api_key_configured: false,
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
    api_key_configured: false,
  }),
  saveApiKey: vi.fn().mockResolvedValue({ configured: true }),
  listMemory: vi.fn().mockResolvedValue({ entries: [] }),
  upsertMemory: vi.fn(),
  deleteMemory: vi.fn(),
  listReminders: vi.fn().mockResolvedValue({ reminders: [] }),
  createReminder: vi.fn(),
  cancelReminder: vi.fn(),
  listDueReminders: vi.fn().mockResolvedValue({ reminders: [] }),
  markReminderDelivered: vi.fn(),
  notifyReminder: vi.fn().mockResolvedValue(undefined),
  notifySystemAlert: vi.fn().mockResolvedValue(undefined),
  sendMessage: vi.fn().mockResolvedValue({
    conversation_id: "6f96e0a4-6c47-4bbb-8884-b14e8ab810c4",
    text: "Hello from Alex.",
  }),
  captureScreen: vi.fn().mockResolvedValue({
    name: "screen-capture.jpg",
    mime_type: "image/jpeg",
    data_base64: Buffer.from("fake-jpeg").toString("base64"),
  }),
  searchWeb: vi.fn().mockResolvedValue({
    query: "current weather",
    mode: "search",
    answer: "A grounded result.",
    sources: [{ title: "Weather source", url: "https://example.com/weather" }],
  }),
  openExternal: vi.fn().mockResolvedValue(undefined),
  openWeatherSearch: vi.fn().mockResolvedValue(undefined),
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
};

describe("Alex app shell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useLiveVoice).mockReturnValue(voice);
    vi.mocked(bridge.getSettings).mockResolvedValue({
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
      api_key_configured: false,
    });
    Object.defineProperty(window, "alex", { configurable: true, value: bridge });
  });

  it("keeps the setup and everyday controls drawers separate", async () => {
    vi.mocked(bridge.getSettings).mockResolvedValue({
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
    });
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");

    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    expect(screen.getByRole("navigation", { name: "Setup" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /AUTO-START: OFF/ }));
    await waitFor(() => expect(bridge.setLoginItemEnabled).toHaveBeenCalledWith(true));
    fireEvent.click(screen.getByRole("button", { name: /CREATE DESKTOP SHORTCUT/ }));
    await waitFor(() => expect(bridge.createDesktopShortcut).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole("button", { name: "Controls" }));
    expect(screen.queryByRole("navigation", { name: "Setup" })).not.toBeInTheDocument();
    const controlsDrawer = screen.getByRole("navigation", { name: "Controls" });
    expect(controlsDrawer).toBeInTheDocument();
    const controls = within(controlsDrawer);
    fireEvent.click(controls.getByRole("button", { name: /FULLSCREEN/ }));
    expect(bridge.toggleFullscreen).toHaveBeenCalledOnce();
    fireEvent.click(controls.getByRole("button", { name: /START MICROPHONE/ }));
    expect(voice.start).toHaveBeenCalledOnce();
    fireEvent.click(controls.getByRole("button", { name: /HUD: ANIMATED FACE/ }));
    await waitFor(() => expect(bridge.updateSettings).toHaveBeenCalledWith({ hud_style: "core" }));
    vi.mocked(bridge.updateSettings).mockResolvedValueOnce({
      settings: {
        assistant_name: "Alex",
        user_name: "",
        accent_color: "#00d4ff",
        operating_system: "Windows",
        voice_name: "Charon",
        hud_style: "core",
        audio_input_device_id: "",
        audio_output_device_id: "",
        push_to_talk_enabled: true,
      },
      api_key_configured: true,
    });
    fireEvent.click(controls.getByRole("button", { name: /PUSH-TO-TALK: OFF/ }));
    await waitFor(() => expect(bridge.updateSettings).toHaveBeenCalledWith({ push_to_talk_enabled: true }));
    await screen.findByRole("button", { name: /PUSH-TO-TALK: ON · HOLD CTRL\+SPACE/ });
    expect(vi.mocked(useLiveVoice)).toHaveBeenLastCalledWith(
      expect.objectContaining({ inputEnabled: false }),
    );
    fireEvent.keyDown(window, { key: " ", code: "Space", ctrlKey: true });
    await waitFor(() =>
      expect(vi.mocked(useLiveVoice)).toHaveBeenLastCalledWith(
        expect.objectContaining({ inputEnabled: true }),
      ),
    );
    fireEvent.keyUp(window, { key: " ", code: "Space", ctrlKey: true });
    await waitFor(() =>
      expect(vi.mocked(useLiveVoice)).toHaveBeenLastCalledWith(
        expect.objectContaining({ inputEnabled: false }),
      ),
    );
  });

  it("toggles wake-word and manual sleep/wake from the everyday controls drawer", async () => {
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Controls" }));
    const controlsDrawer = screen.getByRole("navigation", { name: "Controls" });
    const controls = within(controlsDrawer);

    const wakeBtn = controls.getByRole("button", { name: /WAKE WORD/ });
    expect(wakeBtn).toBeInTheDocument();
    fireEvent.click(wakeBtn);
    await waitFor(() => expect(bridge.toggleWakeWord).toHaveBeenCalledWith(true));

    const sleepBtn = controls.getByRole("button", { name: /STANDBY|AWAKE/ });
    expect(sleepBtn).toBeInTheDocument();
    fireEvent.click(sleepBtn);
    await waitFor(() => expect(bridge.wakeAssistant).toHaveBeenCalled());
  });

  it("opens audio device selection from the setup drawer", async () => {
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    fireEvent.click(screen.getByRole("button", { name: /AUDIO DEVICES/ }));
    expect(await screen.findByText("Choose your microphone and speakers")).toBeInTheDocument();
  });

  it("opens reminder management from the setup drawer", async () => {
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    fireEvent.click(screen.getByRole("button", { name: /REMINDERS/ }));
    expect(await screen.findByRole("heading", { name: "Reminders" })).toBeInTheDocument();
  });

  it("opens the dynamic action catalog from setup", async () => {
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    fireEvent.click(screen.getByRole("button", { name: /ACTIONS/ }));
    expect(await screen.findByRole("heading", { name: "Actions" })).toBeInTheDocument();
  });

  it("requires session permission and per-operation consent for computer control", async () => {
    let permissionEnabled = false;
    let emergencyStopRequested = false;
    let pendingRequest: {
      request_id: string;
      operation: string;
      parameters: Record<string, unknown>;
      expires_in_seconds: number;
    } | null = null;
    vi.mocked(bridge.executeAction).mockImplementation(async (actionId, parameters) => {
      if (actionId === "computer.permission") {
        permissionEnabled = parameters.enabled === true;
        if (permissionEnabled) emergencyStopRequested = false;
      } else if (actionId === "computer.stop") {
        emergencyStopRequested = true;
      } else if (actionId === "computer.approve" || actionId === "computer.dismiss") {
        pendingRequest = null;
      }
      const status = {
        permission_enabled: permissionEnabled,
        adapter_available: true,
        platform: "Windows",
        active_operation: null,
        emergency_stop_requested: emergencyStopRequested,
      };
      return {
        action_id: actionId,
        status: "success",
        data: actionId === "computer.pending"
          ? pendingRequest ? [pendingRequest] : []
          : actionId === "computer.control"
            ? { operation: parameters.operation }
            : status,
        message: "Action executed successfully.",
        error: null,
        execution_time: 0.01,
      };
    });
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    fireEvent.click(screen.getByRole("button", { name: /COMPUTER CONTROL/ }));
    expect(await screen.findByText("NOT GRANTED")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Grant session permission" }));
    const permissionDialog = screen.getByRole("alertdialog", {
      name: "Grant desktop-control permission?",
    });
    fireEvent.click(within(permissionDialog).getByRole("checkbox"));
    fireEvent.click(within(permissionDialog).getByRole("button", { name: "Grant permission" }));
    expect(await screen.findByRole("button", { name: "Revoke permission" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", {
      name: "I have reviewed these parameters and confirm one desktop operation.",
    }));
    fireEvent.click(screen.getByRole("button", { name: "Run confirmed operation" }));
    await screen.findByText("SUCCESS");
    expect(bridge.executeAction).toHaveBeenCalledWith(
      "computer.control",
      { operation: "click", x: 100, y: 100 },
      true,
    );

    fireEvent.click(screen.getByRole("button", { name: "Emergency stop" }));
    fireEvent.click(await screen.findByRole("button", { name: "Re-arm session permission" }));
    const rearmDialog = screen.getByRole("alertdialog", { name: "Re-arm desktop control?" });
    fireEvent.click(within(rearmDialog).getByRole("checkbox"));
    fireEvent.click(within(rearmDialog).getByRole("button", { name: "Re-arm permission" }));
    expect(await screen.findByRole("button", { name: "Revoke permission" })).toBeInTheDocument();

    pendingRequest = {
      request_id: "request-123",
      operation: "click",
      parameters: { operation: "click", x: 40, y: 50 },
      expires_in_seconds: 60,
    };
    fireEvent.click(await screen.findByRole("button", { name: "Approve and execute" }));
    await waitFor(() => expect(bridge.executeAction).toHaveBeenCalledWith(
      "computer.approve",
      { request_id: "request-123" },
      true,
    ));
    await waitFor(() => expect(bridge.sendMessage).toHaveBeenCalledWith(
      expect.stringContaining("Execution status: success"),
      null,
    ));

    pendingRequest = {
      request_id: "request-rejected",
      operation: "press",
      parameters: { operation: "press", key: "enter" },
      expires_in_seconds: 60,
    };
    fireEvent.click(await screen.findByRole("button", { name: "Reject request" }));
    await waitFor(() => expect(bridge.executeAction).toHaveBeenCalledWith(
      "computer.dismiss",
      { request_id: "request-rejected" },
      true,
    ));
    await waitFor(() => expect(bridge.sendMessage).toHaveBeenCalledWith(
      expect.stringContaining("Execution status: not executed (rejected)"),
      expect.any(String),
    ));
  }, 15_000);

  it("shows a native notification for an available system alert", async () => {
    vi.mocked(bridge.getSystemAlerts).mockResolvedValueOnce({
      alerts: [{
        metric: "memory",
        value: 93,
        message: "Memory usage is nearly exhausted.",
      }],
    });
    render(<App />);
    await waitFor(() =>
      expect(bridge.notifySystemAlert).toHaveBeenCalledWith(
        "Memory usage is nearly exhausted.",
      ),
    );
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the HUD, live telemetry, and first-run initialisation", async () => {
    render(<App />);
    expect(await screen.findByText("AT YOUR SERVICE")).toBeInTheDocument();
    expect(screen.getByText("INITIALISATION REQUIRED")).toBeInTheDocument();
    expect(screen.getByText("LOCAL CORE")).toBeInTheDocument();
    expect(screen.getByText("28%")).toBeInTheDocument();
    expect(screen.getByText("01:01")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start microphone" })).toBeDisabled();
  });

  it("navigates to settings and submits a preference update", async () => {
    vi.mocked(bridge.getSettings).mockResolvedValue({
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
    });
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    fireEvent.click(screen.getByRole("button", { name: /CUSTOMISE ASSISTANT/ }));
    expect(await screen.findByText("Make Alex yours")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Assistant name"), {
      target: { value: "Nova" },
    });
    fireEvent.change(screen.getByLabelText(/Assistant voice/), {
      target: { value: "Puck" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save preferences" }));
    await waitFor(() => expect(bridge.updateSettings).toHaveBeenCalledWith(
      expect.objectContaining({ assistant_name: "Nova", voice_name: "Puck" }),
    ));
  });

  it("sends a chat turn through the desktop bridge and renders the answer", async () => {
    vi.mocked(bridge.getSettings).mockResolvedValue({
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
    });
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    fireEvent.click(screen.getByRole("button", { name: /CONVERSATION/ }));
    fireEvent.change(screen.getByRole("textbox", { name: "Message" }), {
      target: { value: "Hello Alex" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect((await screen.findAllByText("Hello from Alex.")).length).toBeGreaterThanOrEqual(2);
    expect(bridge.sendMessage).toHaveBeenCalledWith("Hello Alex", null);
    expect(screen.getAllByText("Hello Alex").length).toBeGreaterThanOrEqual(2);
  });

  it("captures a display for local preview and sends it only with a message", async () => {
    vi.mocked(bridge.getSettings).mockResolvedValue({
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
    });
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "CAPTURE SCREEN" }));
    expect(await screen.findByAltText("Screen capture preview")).toBeInTheDocument();
    expect(bridge.captureScreen).toHaveBeenCalledOnce();
    expect(bridge.sendMessage).not.toHaveBeenCalled();

    fireEvent.change(screen.getByRole("textbox", { name: "Command or question" }), {
      target: { value: "What is on this display?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send command" }));
    await waitFor(() => expect(bridge.sendMessage).toHaveBeenCalledWith(
      "What is on this display?",
      null,
      expect.objectContaining({ name: "screen-capture.jpg", mime_type: "image/jpeg" }),
    ));
  });

  it("routes typed chat through an active live voice session", async () => {
    vi.mocked(bridge.getSettings).mockResolvedValue({
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
    });
    vi.mocked(useLiveVoice).mockReturnValue({ ...voice, active: true });
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    fireEvent.click(screen.getByRole("button", { name: /CONVERSATION/ }));
    fireEvent.change(screen.getByRole("textbox", { name: "Message" }), {
      target: { value: "Hello Alex" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    await waitFor(() => expect(voice.sendText).toHaveBeenCalledWith("Hello Alex"));
    expect(bridge.sendMessage).not.toHaveBeenCalled();
  });

  it("directs users to settings if chat has no Gemini key", async () => {
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    fireEvent.click(screen.getByRole("button", { name: /CONVERSATION/ }));
    expect(await screen.findByText("Gemini API key required")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open Settings" }));
    expect(await screen.findByText("Make Alex yours")).toBeInTheDocument();
  });

  it("searches the web and displays grounded sources", async () => {
    vi.mocked(bridge.getSettings).mockResolvedValue({
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
    });
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    fireEvent.click(screen.getByRole("button", { name: /WEB SEARCH/ }));
    fireEvent.change(screen.getByLabelText("Search query"), {
      target: { value: "current weather" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("A grounded result.")).toBeInTheDocument();
    expect(screen.getByText("Weather source")).toBeInTheDocument();
    expect(bridge.searchWeb).toHaveBeenCalledWith({
      query: "current weather",
      mode: "search",
    });
    fireEvent.click(screen.getByRole("button", { name: /Weather source/ }));
    await waitFor(() => expect(bridge.openExternal).toHaveBeenCalledWith(
      "https://example.com/weather",
    ));
  });

  it("opens a weather search page for a city without claiming forecast data", async () => {
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    fireEvent.click(screen.getByRole("button", { name: "Setup" }));
    fireEvent.click(screen.getByRole("button", { name: /WEB SEARCH/ }));
    fireEvent.change(screen.getByLabelText("City"), {
      target: { value: "New York" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Open weather search" }));

    await waitFor(() => expect(bridge.openWeatherSearch).toHaveBeenCalledWith(
      "New York",
      "today",
    ));
  });

  it("attaches a supported file to a chat turn through the desktop bridge", async () => {
    vi.mocked(bridge.getSettings).mockResolvedValue({
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
    });
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");
    const file = new File(["some code"], "hello.py", { type: "text/x-python" });
    fireEvent.change(screen.getByLabelText(/Drop file here/), { target: { files: [file] } });

    await screen.findByText(/ATTACHED: hello\.py/);
    fireEvent.click(screen.getByRole("button", { name: "Send command" }));

    await waitFor(() => expect(bridge.sendMessage).toHaveBeenCalledWith(
      "Please review this attached file.",
      null,
      {
        name: "hello.py",
        mime_type: "text/plain",
        data_base64: "c29tZSBjb2Rl",
      },
    ));
  });

  it("opens youtube on the HUD stage and can close it", async () => {
    vi.mocked(bridge.getSettings).mockResolvedValue({
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
    });
    render(<App />);
    await screen.findByText("AT YOUR SERVICE");

    // Give command: "open youtube on the hud"
    const input = screen.getByPlaceholderText(/Type a command or ask anything/i);
    fireEvent.change(input, { target: { value: "open youtube on the hud" } });
    fireEvent.click(screen.getByRole("button", { name: "Send command" }));

    // HUD stage activates VideoPlayer / iframe for YouTube
    await screen.findByTestId("media-player-stage");
    expect(screen.getByText("YOUTUBE HUD STREAM")).toBeInTheDocument();

    // Close button dismisses player and restores avatar
    const closeBtn = screen.getByRole("button", { name: "Close video player" });
    fireEvent.click(closeBtn);
    await waitFor(() => {
      expect(screen.queryByTestId("media-player-stage")).not.toBeInTheDocument();
    });
  });
});
