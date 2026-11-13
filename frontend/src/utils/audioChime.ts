/**
 * Audio Chime Utility (TASK-P4-04 / CAT-11)
 *
 * Synthesizes a high-fidelity two-tone test chime (440 Hz -> 880 Hz with exponential decay)
 * using the HTML5 Web Audio API with zero external audio asset dependencies.
 */

export interface PlayChimeOptions {
  outputDeviceId?: string;
  volume?: number;
  duration?: number;
}

export async function setAudioOutput(context: AudioContext, deviceId?: string): Promise<void> {
  if (!deviceId) return;
  if ("setSinkId" in context && typeof (context as { setSinkId?: (id: string) => Promise<void> }).setSinkId === "function") {
    await (context as { setSinkId: (id: string) => Promise<void> }).setSinkId(deviceId);
  }
}

export async function playTestChime(options: PlayChimeOptions = {}): Promise<void> {
  const { outputDeviceId, volume = 0.15, duration = 0.55 } = options;

  if (typeof window === "undefined") {
    return;
  }

  const AudioContextClass =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

  if (!AudioContextClass) {
    return;
  }

  let context: AudioContext | null = null;
  try {
    context = new AudioContextClass();

    if (outputDeviceId) {
      await setAudioOutput(context, outputDeviceId);
    }

    if (context.state === "suspended") {
      await context.resume();
    }

    const now = context.currentTime;
    const osc = context.createOscillator();
    const gain = context.createGain();

    // Two-tone chime: start at 440 Hz (A4) and transition cleanly to 880 Hz (A5)
    osc.type = "sine";
    if (osc.frequency.setValueAtTime) {
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.setValueAtTime(440, now + duration * 0.35);
      if (osc.frequency.exponentialRampToValueAtTime) {
        osc.frequency.exponentialRampToValueAtTime(880, now + duration * 0.42);
      }
    }

    // Envelope: rapid attack, gentle sustain, exponential decay to zero
    if (gain.gain.setValueAtTime) {
      gain.gain.setValueAtTime(0.0001, now);
      if (gain.gain.linearRampToValueAtTime) {
        gain.gain.linearRampToValueAtTime(volume, now + 0.04);
      }
      gain.gain.setValueAtTime(volume, now + duration * 0.45);
      if (gain.gain.exponentialRampToValueAtTime) {
        gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      }
    }

    osc.connect(gain);
    gain.connect(context.destination);

    osc.start(now);
    osc.stop(now + duration);

    await new Promise<void>((resolve) => {
      osc.onended = () => resolve();
      // Safety timeout for virtual/mock DOM environments
      setTimeout(() => resolve(), Math.ceil(duration * 1000) + 120);
    });
  } catch (err) {
    // If audio engine fails or setSinkId is not supported, log warning but don't crash
    console.warn("Could not play speaker test chime:", err);
    throw err;
  } finally {
    if (context && context.state !== "closed") {
      try {
        await context.close();
      } catch {
        // ignore teardown errors
      }
    }
  }
}

