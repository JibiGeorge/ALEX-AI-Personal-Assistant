import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AlexApi, LiveVoiceEvent } from "../types/api";
import { resampleToPcm16, useLiveVoice } from "./useLiveVoice";

const bridge: AlexApi = {
  toggleFullscreen: vi.fn(),
  getStatus: vi.fn(),
  getSystemMetrics: vi.fn(),
  getSystemAlerts: vi.fn(),
  listActions: vi.fn(),
  setActionEnabled: vi.fn(),
  executeAction: vi.fn(),
  getActionHistory: vi.fn(),
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
  saveApiKey: vi.fn(),
  listMemory: vi.fn(),
  upsertMemory: vi.fn(),
  deleteMemory: vi.fn(),
  listReminders: vi.fn(),
  createReminder: vi.fn(),
  cancelReminder: vi.fn(),
  listDueReminders: vi.fn(),
  markReminderDelivered: vi.fn(),
  notifyReminder: vi.fn(),
  notifySystemAlert: vi.fn(),
  sendMessage: vi.fn(),
  captureScreen: vi.fn(),
  searchWeb: vi.fn(),
  openExternal: vi.fn(),
  openWeatherSearch: vi.fn(),
  getLoginItemStatus: vi.fn(),
  setLoginItemEnabled: vi.fn(),
  createDesktopShortcut: vi.fn(),
  startVoice: vi.fn().mockResolvedValue(undefined),
  sendVoiceAudio: vi.fn(),
  sendVoiceText: vi.fn().mockResolvedValue(undefined),
  interruptVoice: vi.fn().mockResolvedValue(undefined),
  stopVoice: vi.fn().mockResolvedValue(undefined),
  onVoiceEvent: vi.fn(),
};

let voiceListener: ((event: LiveVoiceEvent) => void) | null = null;
let workletPort: { onmessage: ((event: MessageEvent) => void) | null; close: ReturnType<typeof vi.fn> } | null =
  null;

describe("resampleToPcm16", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    voiceListener = null;
    workletPort = null;
    vi.mocked(bridge.onVoiceEvent).mockImplementation((listener) => {
      voiceListener = listener;
      return () => {
        voiceListener = null;
      };
    });
    Object.defineProperty(window, "alex", { configurable: true, value: bridge });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: vi.fn() }],
        }),
      },
    });
    vi.stubGlobal(
      "AudioContext",
      class {
        sampleRate = 48_000;
        currentTime = 0;
        state = "running";
        audioWorklet = { addModule: vi.fn().mockResolvedValue(undefined) };
        destination = {};
        resume = vi.fn().mockResolvedValue(undefined);
        close = vi.fn().mockResolvedValue(undefined);
        createMediaStreamSource = () => ({ connect: vi.fn(), disconnect: vi.fn() });
      },
    );
    vi.stubGlobal(
      "AudioWorkletNode",
      class {
        port = {
          onmessage: null as ((event: MessageEvent) => void) | null,
          close: vi.fn(),
        };
        constructor() {
          workletPort = this.port;
        }
        connect = vi.fn();
        disconnect = vi.fn();
      },
    );
  });

  it("converts 48 kHz float audio into little-endian 16 kHz PCM16", () => {
    const pcm = resampleToPcm16(
      new Float32Array([0, 0.1, 0.2, 1, 0.1, -1]),
      48_000,
    );
    const samples = new DataView(pcm);

    expect(pcm.byteLength).toBe(4);
    expect(samples.getInt16(0, true)).toBe(0);
    expect(samples.getInt16(2, true)).toBe(32767);
  });

  it("sends typed input through the active voice session and resolves its transcript", async () => {
    const onTranscript = vi.fn();
    const onError = vi.fn();
    const { result, unmount } = renderHook(() => useLiveVoice({ onTranscript, onError }));
    await act(async () => {
      await result.current.start();
    });
    expect(result.current.active).toBe(true);

    let response: Promise<{ input_text: string; output_text: string }> | undefined;
    await act(async () => {
      response = result.current.sendText("Follow up in the same session");
      await vi.waitFor(() =>
        expect(bridge.sendVoiceText).toHaveBeenCalledWith("Follow up in the same session"),
      );
    });

    act(() => {
      workletPort?.onmessage?.(
        new MessageEvent("message", { data: new Float32Array([0.25, 0.5, 0.75]) }),
      );
    });
    expect(bridge.sendVoiceAudio).not.toHaveBeenCalled();

    await act(async () => {
      voiceListener?.({
        type: "turn_complete",
        input_text: "Follow up in the same session",
        output_text: "Live answer",
        interrupted: false,
      });
      await expect(response).resolves.toEqual({
        input_text: "Follow up in the same session",
        output_text: "Live answer",
      });
    });
    expect(onTranscript).toHaveBeenCalledWith(
      "Follow up in the same session",
      "Live answer",
    );
    act(() => {
      workletPort?.onmessage?.(
        new MessageEvent("message", { data: new Float32Array([0.25, 0.5, 0.75]) }),
      );
    });
    expect(bridge.sendVoiceAudio).toHaveBeenCalledOnce();
    expect(onError).not.toHaveBeenCalled();
    unmount();
  });

  it("sends silence instead of microphone audio while push-to-talk is released", async () => {
    const { result, unmount } = renderHook(() =>
      useLiveVoice({
        onTranscript: vi.fn(),
        onError: vi.fn(),
        inputEnabled: false,
      }),
    );
    await act(async () => {
      await result.current.start();
    });

    act(() => {
      workletPort?.onmessage?.(
        new MessageEvent("message", {
          data: new Float32Array([0.25, -0.5, 0.75, 0.3, 0.2, 0.1]),
        }),
      );
    });

    expect(bridge.sendVoiceAudio).toHaveBeenCalledOnce();
    const pcm = vi.mocked(bridge.sendVoiceAudio).mock.calls[0][0];
    expect([...new Uint8Array(pcm)]).toEqual([0, 0, 0, 0]);
    unmount();
  });

  it("falls back to standard and basic constraints when ideal constraints fail", async () => {
    const mockGetUserMedia = vi
      .fn()
      // First attempt (Stage 1 with ideal constraints) rejects
      .mockRejectedValueOnce(new Error("OverconstrainedError"))
      // Second attempt (Stage 2 standard) resolves
      .mockResolvedValueOnce({
        getTracks: () => [{ stop: vi.fn() }],
      });

    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: mockGetUserMedia,
      },
    });

    const { result, unmount } = renderHook(() =>
      useLiveVoice({
        onTranscript: vi.fn(),
        onError: vi.fn(),
        inputDeviceId: "external-mic-id",
      }),
    );

    await act(async () => {
      await result.current.start();
    });

    expect(mockGetUserMedia).toHaveBeenCalledTimes(2);
    expect(result.current.active).toBe(true);
    unmount();
  });
});
