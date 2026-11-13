import { beforeEach, describe, expect, it, vi } from "vitest";

import { playTestChime } from "./audioChime";

describe("audioChime utility", () => {
  let mockOscillator: any;
  let mockGain: any;
  let mockContext: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockOscillator = {
      type: "sine",
      frequency: {
        setValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
      onended: null,
    };

    mockGain = {
      gain: {
        setValueAtTime: vi.fn(),
        linearRampToValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
    };

    mockContext = {
      state: "running",
      currentTime: 10,
      destination: {},
      createOscillator: vi.fn().mockReturnValue(mockOscillator),
      createGain: vi.fn().mockReturnValue(mockGain),
      resume: vi.fn().mockResolvedValue(undefined),
      close: vi.fn().mockResolvedValue(undefined),
      setSinkId: vi.fn().mockResolvedValue(undefined),
    };

    (window as any).AudioContext = vi.fn().mockImplementation(function (this: any) {
      return mockContext;
    });
  });

  it("synthesizes dual-tone chime and cleans up context", async () => {
    const playPromise = playTestChime({
      outputDeviceId: "speaker-1",
      duration: 0.2,
    });

    // Simulate oscillator ending
    mockOscillator.onended?.();
    await playPromise;

    expect(mockContext.setSinkId).toHaveBeenCalledWith("speaker-1");
    expect(mockOscillator.start).toHaveBeenCalled();
    expect(mockOscillator.stop).toHaveBeenCalled();
    expect(mockOscillator.frequency.setValueAtTime).toHaveBeenCalledWith(440, 10);
    expect(mockOscillator.frequency.exponentialRampToValueAtTime).toHaveBeenCalledWith(
      880,
      expect.any(Number),
    );
    expect(mockContext.close).toHaveBeenCalled();
  });

  it("handles missing setSinkId gracefully", async () => {
    delete mockContext.setSinkId;

    const playPromise = playTestChime({ duration: 0.1 });
    mockOscillator.onended?.();
    await expect(playPromise).resolves.not.toThrow();
  });
});
