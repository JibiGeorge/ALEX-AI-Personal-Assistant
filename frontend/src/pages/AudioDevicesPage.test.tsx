import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AudioDevicesPage } from "./AudioDevicesPage";

describe("AudioDevicesPage", () => {
  const onSave = vi.fn().mockResolvedValue(undefined);
  const onError = vi.fn();
  let mockTrack: { stop: any };
  let mockStream: { getTracks: any };
  let mockContext: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockTrack = { stop: vi.fn() };
    mockStream = {
      getTracks: vi.fn().mockReturnValue([mockTrack]),
    };

    mockContext = {
      state: "running",
      currentTime: 0,
      destination: {},
      createMediaStreamSource: vi.fn().mockReturnValue({ connect: vi.fn() }),
      createAnalyser: vi.fn().mockReturnValue({
        fftSize: 512,
        connect: vi.fn(),
        getFloatTimeDomainData: vi.fn((arr: Float32Array) => {
          arr.fill(0.1);
        }),
      }),
      createOscillator: vi.fn().mockReturnValue({
        type: "sine",
        frequency: { setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() },
        connect: vi.fn(),
        start: vi.fn(),
        stop: vi.fn(),
        onended: null,
      }),
      createGain: vi.fn().mockReturnValue({
        gain: {
          setValueAtTime: vi.fn(),
          linearRampToValueAtTime: vi.fn(),
          exponentialRampToValueAtTime: vi.fn(),
        },
        connect: vi.fn(),
      }),
      resume: vi.fn().mockResolvedValue(undefined),
      close: vi.fn().mockResolvedValue(undefined),
      setSinkId: vi.fn().mockResolvedValue(undefined),
    };

    (window as any).AudioContext = vi.fn().mockImplementation(function (this: any) {
      return mockContext;
    });

    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        enumerateDevices: vi.fn().mockResolvedValue([
          { kind: "audioinput", deviceId: "mic-1", label: "USB Microphone" },
          { kind: "audiooutput", deviceId: "speaker-1", label: "Headphones" },
        ]),
        getUserMedia: vi.fn().mockResolvedValue(mockStream),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });
  });

  afterEach(cleanup);

  it("lists available input/output devices and saves the selected IDs", async () => {
    render(
      <AudioDevicesPage
        inputDeviceId=""
        outputDeviceId=""
        onSave={onSave}
        onError={onError}
      />,
    );

    await screen.findByRole("option", { name: "USB Microphone" });
    fireEvent.change(screen.getByLabelText("Microphone input"), {
      target: { value: "mic-1" },
    });
    fireEvent.change(screen.getByLabelText("Speaker output"), {
      target: { value: "speaker-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save devices" }));

    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith({
        audio_input_device_id: "mic-1",
        audio_output_device_id: "speaker-1",
      }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Audio device choices saved. They will be used in the next voice session.",
    );
  });

  it("renders live audio meter and toggles live monitoring", async () => {
    render(
      <AudioDevicesPage
        inputDeviceId="mic-1"
        outputDeviceId="speaker-1"
        onSave={onSave}
        onError={onError}
      />,
    );

    expect(screen.getByText("STANDBY")).toBeInTheDocument();
    const toggleButton = screen.getByRole("button", { name: "Start live monitor" });

    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith(
        expect.objectContaining({
          audio: expect.objectContaining({
            deviceId: { exact: "mic-1" },
          }),
        }),
      );
    });

    await waitFor(() => {
      expect(screen.getByText("LIVE")).toBeInTheDocument();
    });

    // Toggle off
    fireEvent.click(screen.getByRole("button", { name: "Stop live monitor" }));
    await waitFor(() => {
      expect(screen.getByText("STANDBY")).toBeInTheDocument();
    });
    expect(mockTrack.stop).toHaveBeenCalled();
  });

  it("plays dual-tone test chime on 'Test speakers' click", async () => {
    render(
      <AudioDevicesPage
        inputDeviceId=""
        outputDeviceId="speaker-1"
        onSave={onSave}
        onError={onError}
      />,
    );

    const testSpeakersButton = screen.getByRole("button", { name: "Test speakers" });
    fireEvent.click(testSpeakersButton);

    await waitFor(() => {
      expect(mockContext.createOscillator).toHaveBeenCalled();
      expect(mockContext.createGain).toHaveBeenCalled();
    });
  });

  it("releases audio tracks and closes context on unmount", async () => {
    const { unmount } = render(
      <AudioDevicesPage
        inputDeviceId="mic-1"
        outputDeviceId="speaker-1"
        onSave={onSave}
        onError={onError}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Start live monitor" }));
    await waitFor(() => expect(screen.getByText("LIVE")).toBeInTheDocument());

    unmount();
    expect(mockTrack.stop).toHaveBeenCalled();
    expect(mockContext.close).toHaveBeenCalled();
  });
});
