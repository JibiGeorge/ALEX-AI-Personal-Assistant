import { useCallback, useEffect, useRef, useState } from "react";

import { AudioMeter } from "../components/AudioMeter";
import type { AppSettings } from "../types/api";
import { playTestChime } from "../utils/audioChime";

interface AudioDevicesPageProps {
  inputDeviceId: string;
  outputDeviceId: string;
  onSave: (settings: Partial<AppSettings>) => Promise<void>;
  onError: (message: string) => void;
}

interface AudioDeviceOption {
  deviceId: string;
  label: string;
}

export function AudioDevicesPage({
  inputDeviceId,
  outputDeviceId,
  onSave,
  onError,
}: AudioDevicesPageProps) {
  const [inputs, setInputs] = useState<AudioDeviceOption[]>([]);
  const [outputs, setOutputs] = useState<AudioDeviceOption[]>([]);
  const [input, setInput] = useState(inputDeviceId);
  const [output, setOutput] = useState(outputDeviceId);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const onErrorRef = useRef(onError);

  // Live Audio VU Meter State (TASK-P4-04)
  const [liveMonitoring, setLiveMonitoring] = useState(false);
  const [rmsDb, setRmsDb] = useState(-60);
  const [peakDb, setPeakDb] = useState(-60);

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const peakHoldRef = useRef<{ value: number; timestamp: number }>({ value: -60, timestamp: 0 });

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const refreshDevices = useCallback(async () => {
    if (!navigator.mediaDevices?.enumerateDevices) {
      throw new Error("Audio-device enumeration is unavailable in this environment.");
    }
    const devices = await navigator.mediaDevices.enumerateDevices();
    setInputs(
      devices
        .filter((device) => device.kind === "audioinput" && device.deviceId)
        .map((device, index) => ({
          deviceId: device.deviceId,
          label: device.label || `Microphone ${index + 1}`,
        })),
    );
    setOutputs(
      devices
        .filter((device) => device.kind === "audiooutput" && device.deviceId)
        .map((device, index) => ({
          deviceId: device.deviceId,
          label: device.label || `Speaker ${index + 1}`,
        })),
    );
  }, []);

  useEffect(() => {
    void refreshDevices().catch((error: unknown) =>
      onErrorRef.current(error instanceof Error ? error.message : "Could not list audio devices."),
    );
    const mediaDevices = navigator.mediaDevices;
    if (!mediaDevices?.addEventListener) return;
    const handleChange = () => {
      void refreshDevices().catch((error: unknown) =>
        onErrorRef.current(error instanceof Error ? error.message : "Could not refresh audio devices."),
      );
    };
    mediaDevices.addEventListener("devicechange", handleChange);
    return () => mediaDevices.removeEventListener("devicechange", handleChange);
  }, [refreshDevices]);

  // Teardown Live VU Meter stream and context
  const stopLiveMonitor = useCallback(() => {
    if (animFrameRef.current !== null) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      void audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setLiveMonitoring(false);
    setRmsDb(-60);
    setPeakDb(-60);
    peakHoldRef.current = { value: -60, timestamp: 0 };
  }, []);

  // Safe unmount hook
  useEffect(() => {
    return () => {
      stopLiveMonitor();
    };
  }, [stopLiveMonitor]);

  // Start Live VU Meter
  const startLiveMonitor = useCallback(
    async (targetDeviceId?: string) => {
      stopLiveMonitor();
      const devId = targetDeviceId !== undefined ? targetDeviceId : input;

      if (!navigator.mediaDevices?.getUserMedia) {
        onErrorRef.current("Microphone access is unavailable in this environment.");
        return;
      }

      try {
        let stream: MediaStream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            audio: {
              ...(devId ? { deviceId: { exact: devId } } : {}),
              channelCount: 1,
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
            video: false,
          });
        } catch {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        }

        const AudioContextClass =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

        if (!AudioContextClass) {
          stream.getTracks().forEach((t) => t.stop());
          onErrorRef.current("Web Audio API is not supported in this environment.");
          return;
        }

        const context = new AudioContextClass();
        const source = context.createMediaStreamSource(stream);
        const analyser = context.createAnalyser();
        analyser.fftSize = 512;
        source.connect(analyser);

        mediaStreamRef.current = stream;
        audioContextRef.current = context;
        setLiveMonitoring(true);

        const samples = new Float32Array(analyser.fftSize);

        const updateMeter = () => {
          if (!mediaStreamRef.current) return;
          analyser.getFloatTimeDomainData(samples);

          let sum = 0;
          let maxSample = 0;
          for (let i = 0; i < samples.length; i++) {
            const val = samples[i];
            sum += val * val;
            const abs = Math.abs(val);
            if (abs > maxSample) maxSample = abs;
          }

          const rms = Math.sqrt(sum / samples.length);
          const currentRmsDb = rms > 1e-4 ? Math.max(-60, 20 * Math.log10(rms)) : -60;
          const currentPeakDb = maxSample > 1e-4 ? Math.max(-60, 20 * Math.log10(maxSample)) : -60;

          const now = Date.now();
          if (currentPeakDb >= peakHoldRef.current.value || now - peakHoldRef.current.timestamp > 1200) {
            peakHoldRef.current = { value: currentPeakDb, timestamp: now };
          } else {
            // Decay peak slowly (3 dB per 100ms)
            const decay = ((now - peakHoldRef.current.timestamp) / 100) * 3;
            peakHoldRef.current.value = Math.max(currentPeakDb, peakHoldRef.current.value - decay);
          }

          setRmsDb(Math.round(currentRmsDb * 10) / 10);
          setPeakDb(Math.round(peakHoldRef.current.value * 10) / 10);

          animFrameRef.current = requestAnimationFrame(updateMeter);
        };

        animFrameRef.current = requestAnimationFrame(updateMeter);
      } catch (err) {
        stopLiveMonitor();
        onErrorRef.current(err instanceof Error ? err.message : "Could not open audio stream for monitor.");
      }
    },
    [input, stopLiveMonitor],
  );

  const toggleLiveMonitor = useCallback(() => {
    if (liveMonitoring) {
      stopLiveMonitor();
      setStatus("Microphone live monitor stopped.");
    } else {
      void startLiveMonitor();
      setStatus("Microphone live monitor active. Speak to observe signal amplitude.");
    }
  }, [liveMonitoring, startLiveMonitor, stopLiveMonitor]);

  // Restart live monitor if input device changes while monitoring
  const handleInputChange = (newDeviceId: string) => {
    setInput(newDeviceId);
    if (liveMonitoring) {
      void startLiveMonitor(newDeviceId);
    }
  };

  async function revealDeviceLabels() {
    setBusy(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      stream.getTracks().forEach((track) => track.stop());
      await refreshDevices();
      setStatus("Audio devices refreshed. Microphone permission remains under your control.");
    } catch (error) {
      onErrorRef.current(error instanceof Error ? error.message : "Could not access the microphone.");
    } finally {
      setBusy(false);
    }
  }

  async function testMicrophone() {
    setBusy(true);
    setStatus("Evaluating microphone for 3 seconds… Speak now.");
    try {
      await startLiveMonitor();
      let peak = 0;
      const started = Date.now();

      while (Date.now() - started < 3000) {
        await new Promise((resolve) => window.setTimeout(resolve, 100));
        if (peakHoldRef.current.value > peak) {
          peak = peakHoldRef.current.value;
        }
      }

      setStatus(
        peak > -45
          ? `Microphone signal detected clearly (peak ${peak.toFixed(1)} dBFS).`
          : "Low or no microphone signal detected. Check mute switches, system input levels and privacy permissions.",
      );
    } catch (error) {
      onErrorRef.current(error instanceof Error ? error.message : "Microphone test failed.");
    } finally {
      setBusy(false);
    }
  }

  async function testSpeakers() {
    setBusy(true);
    setStatus("Playing dual-tone test chime (440 Hz -> 880 Hz)…");
    try {
      await playTestChime({
        outputDeviceId: output,
        volume: 0.15,
        duration: 0.55,
      });
      setStatus("Test chime completed. If you did not hear audio, verify speaker connection and volume.");
    } catch (error) {
      onErrorRef.current(error instanceof Error ? error.message : "Speaker test failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDevices() {
    setBusy(true);
    try {
      await onSave({
        audio_input_device_id: input,
        audio_output_device_id: output,
      });
      setStatus("Audio device choices saved. They will be used in the next voice session.");
    } catch (error) {
      onErrorRef.current(error instanceof Error ? error.message : "Could not save audio devices.");
    } finally {
      setBusy(false);
    }
  }

  function addSavedMissingDevice(list: AudioDeviceOption[], selected: string, label: string) {
    if (!selected || list.some((device) => device.deviceId === selected)) return list;
    return [...list, { deviceId: selected, label: `${label} (not currently available)` }];
  }

  return (
    <section className="page-content settings-layout audio-devices-layout">
      <div className="section-heading">
        <div>
          <div className="eyebrow">AUDIO ROUTING & DIAGNOSTICS</div>
          <h3>Choose your microphone and speakers</h3>
        </div>
      </div>
      <div className="panel settings-panel">
        <p className="audio-device-explainer">
          Device access is requested only when you refresh labels, monitor levels, or run a test.
          Saved choices are applied when the next voice session starts.
        </p>

        <label className="field">
          <span>Microphone input</span>
          <select value={input} onChange={(event) => handleInputChange(event.target.value)}>
            <option value="">System default</option>
            {addSavedMissingDevice(inputs, input, "Saved microphone").map((device) => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label}
              </option>
            ))}
          </select>
        </label>

        {/* Live Audio VU Meter (TASK-P4-04) */}
        <AudioMeter
          rmsDb={rmsDb}
          peakDb={peakDb}
          active={liveMonitoring}
          label="Microphone Live Level"
          onToggleActive={toggleLiveMonitor}
        />

        <label className="field">
          <span>Speaker output</span>
          <select value={output} onChange={(event) => setOutput(event.target.value)}>
            <option value="">System default</option>
            {addSavedMissingDevice(outputs, output, "Saved output").map((device) => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label}
              </option>
            ))}
          </select>
        </label>

        <div className="form-actions audio-device-actions">
          <button
            className="button button-secondary"
            disabled={busy}
            onClick={() => void revealDeviceLabels()}
            type="button"
          >
            Refresh device list
          </button>
          <button
            className="button button-secondary"
            disabled={busy}
            onClick={() => void testMicrophone()}
            type="button"
          >
            Test microphone
          </button>
          <button
            className="button button-secondary"
            disabled={busy}
            onClick={() => void testSpeakers()}
            type="button"
          >
            Test speakers
          </button>
          <button
            className="button button-primary"
            disabled={busy}
            onClick={() => void saveDevices()}
            type="button"
          >
            {busy ? "Working…" : "Save devices"}
          </button>
        </div>
        {status && (
          <p className="audio-device-status" role="status">
            {status}
          </p>
        )}
      </div>
    </section>
  );
}
