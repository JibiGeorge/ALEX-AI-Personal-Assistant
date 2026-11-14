import { useCallback, useEffect, useRef, useState } from "react";

import { alexApi } from "../services/alexApi";
import type { LiveVoiceEvent } from "../types/api";
import { classifyVoiceError, type VoiceErrorInfo, type VoiceState } from "../types/voice";

const INPUT_RATE = 16_000;
const OUTPUT_RATE = 24_000;

export function resampleToPcm16(samples: Float32Array, sourceRate: number): ArrayBuffer {
  const outputLength = Math.floor((samples.length * INPUT_RATE) / sourceRate);
  const output = new ArrayBuffer(outputLength * 2);
  const view = new DataView(output);
  const ratio = sourceRate / INPUT_RATE;
  for (let index = 0; index < outputLength; index += 1) {
    const position = index * ratio;
    const left = Math.floor(position);
    const fraction = position - left;
    const first = samples[left] ?? 0;
    const second = samples[Math.min(left + 1, samples.length - 1)] ?? first;
    const sample = Math.max(-1, Math.min(1, first + (second - first) * fraction));
    view.setInt16(index * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return output;
}

interface VoiceCallbacks {
  onTranscript: (input: string, output: string) => void;
  onError: (message: string) => void;
  onConnected?: (model: string) => void;
  onModelFallback?: (fromModel: string, toModel: string, reason: string) => void;
  inputDeviceId?: string;
  outputDeviceId?: string;
  inputEnabled?: boolean;
}

interface LiveTextTurn {
  input_text: string;
  output_text: string;
}

async function setAudioOutput(context: AudioContext, deviceId?: string): Promise<void> {
  if (!deviceId) return;
  if ("setSinkId" in context && typeof (context as any).setSinkId === "function") {
    try {
      await (context as any).setSinkId(deviceId);
    } catch (error) {
      console.warn("Could not assign audio output deviceId:", error);
    }
  }
}

async function acquireMicrophoneStream(inputDeviceId?: string): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Microphone access is unavailable in this environment.");
  }

  const attemptGetUserMedia = async (constraints: MediaStreamConstraints, timeoutMs: number): Promise<MediaStream> => {
    return await Promise.race([
      navigator.mediaDevices.getUserMedia(constraints),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error(`Attempt timed out after ${Math.round(timeoutMs / 1000)}s`)), timeoutMs),
      ),
    ]);
  };

  // Pre-flight check: if inputDeviceId was configured, verify it still exists among audio inputs
  let targetDeviceId: string | undefined = undefined;
  if (inputDeviceId && navigator.mediaDevices.enumerateDevices) {
    try {
      const devices = await Promise.race([
        navigator.mediaDevices.enumerateDevices(),
        new Promise<MediaDeviceInfo[]>((res) => setTimeout(() => res([]), 1500)),
      ]);
      const exists = devices.some(
        (d) => d.kind === "audioinput" && (d.deviceId === inputDeviceId || !d.deviceId),
      );
      if (exists) {
        targetDeviceId = inputDeviceId;
      } else {
        console.warn(`Configured audio input '${inputDeviceId}' not found, falling back to system default.`);
      }
    } catch {
      targetDeviceId = inputDeviceId;
    }
  }

  // Stage 1: Ideal constraints with DSP features
  try {
    return await attemptGetUserMedia(
      {
        audio: {
          ...(targetDeviceId ? { deviceId: { ideal: targetDeviceId } } : {}),
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      },
      8000,
    );
  } catch (stage1Error) {
    console.warn("Stage 1 microphone acquisition failed/timed out, attempting Stage 2 (standard audio):", stage1Error);
  }

  // Stage 2: Default microphone with DSP features (no specific deviceId)
  try {
    return await attemptGetUserMedia(
      {
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      },
      6000,
    );
  } catch (stage2Error) {
    console.warn("Stage 2 microphone acquisition failed/timed out, attempting Stage 3 (raw audio):", stage2Error);
  }

  // Stage 3: Raw, unconstrained audio fallback
  try {
    return await attemptGetUserMedia({ audio: true, video: false }, 6000);
  } catch (stage3Error) {
    console.error("Stage 3 microphone acquisition failed:", stage3Error);
    throw new Error(
      "Microphone device acquisition timed out. Please ensure your microphone is connected and authorized in System Settings.",
    );
  }
}

export function useLiveVoice({
  onTranscript,
  onError,
  onConnected,
  onModelFallback,
  inputDeviceId = "",
  outputDeviceId = "",
  inputEnabled = true,
}: VoiceCallbacks) {
  const [active, setActive] = useState(false);
  const [starting, setStarting] = useState(false);
  const [assistantSpeaking, setAssistantSpeaking] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<VoiceErrorInfo | null>(null);
  const callbacks = useRef({ onTranscript, onError, onConnected, onModelFallback });
  const streamRef = useRef<MediaStream | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const playbackAnalyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<AudioWorkletNode | null>(null);
  const playbackSources = useRef(new Set<AudioBufferSourceNode>());
  const playbackCursor = useRef(0);
  const suppressAudio = useRef(false);
  const inputEnabledRef = useRef(inputEnabled);
  const pendingTextTurn = useRef<{
    resolve: (turn: LiveTextTurn) => void;
    reject: (error: Error) => void;
  } | null>(null);

  const ensurePlaybackAnalyser = useCallback((ctx: AudioContext): AnalyserNode | null => {
    if (typeof ctx.createAnalyser !== "function") return null;
    if (!playbackAnalyserRef.current || playbackAnalyserRef.current.context !== ctx) {
      try {
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 512;
        analyser.smoothingTimeConstant = 0.35;
        if (typeof analyser.connect === "function") {
          analyser.connect(ctx.destination);
        }
        playbackAnalyserRef.current = analyser;
      } catch {
        return null;
      }
    }
    return playbackAnalyserRef.current;
  }, []);

  useEffect(() => {
    callbacks.current = { onTranscript, onError, onConnected, onModelFallback };
  }, [onError, onTranscript, onConnected, onModelFallback]);

  useEffect(() => {
    inputEnabledRef.current = inputEnabled;
  }, [inputEnabled]);

  const clearPlayback = useCallback(() => {
    for (const source of playbackSources.current) {
      try {
        source.stop();
        source.disconnect();
      } catch {
        // ignore if already stopped
      }
    }
    playbackSources.current.clear();
    playbackCursor.current = 0;
    setAssistantSpeaking(false);
    setVoiceState((prev) => (prev === "speaking" ? "listening" : prev));
  }, []);

  const releaseAudio = useCallback(async () => {
    processorRef.current?.port.close();
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    clearPlayback();
    if (playbackAnalyserRef.current) {
      try {
        playbackAnalyserRef.current.disconnect();
      } catch {
        // ignore
      }
      playbackAnalyserRef.current = null;
    }
    const context = contextRef.current;
    contextRef.current = null;
    processorRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    setAssistantSpeaking(false);
    if (context && context.state !== "closed") await context.close();
  }, [clearPlayback]);

  const stop = useCallback(async () => {
    setActive(false);
    setStarting(false);
    setAssistantSpeaking(false);
    setVoiceState((prev) => (prev === "error" ? "error" : "idle"));
    suppressAudio.current = true;
    pendingTextTurn.current?.reject(new Error("The live voice session was closed."));
    pendingTextTurn.current = null;
    try {
      await alexApi.stopVoice();
    } catch (error) {
      console.error("Could not close the local voice connection", error);
    }
    await releaseAudio();
  }, [releaseAudio]);

  const handleVoiceEvent = useCallback(
    (event: LiveVoiceEvent) => {
      if (event.type === "connected") {
        callbacks.current.onConnected?.(event.model);
      } else if (event.type === "model_fallback") {
        callbacks.current.onModelFallback?.(event.from_model, event.to_model, event.reason);
      } else if (event.type === "audio") {
        if (suppressAudio.current) return;
        const context = contextRef.current;
        if (!context || event.pcm.byteLength < 2 || event.pcm.byteLength % 2) return;
        const samples = new Float32Array(event.pcm.byteLength / 2);
        const arrayBuffer = event.pcm instanceof ArrayBuffer ? event.pcm : (event.pcm as any).buffer;
        const offset = event.pcm instanceof ArrayBuffer ? 0 : (event.pcm as any).byteOffset || 0;
        const view = new DataView(arrayBuffer, offset, event.pcm.byteLength);
        for (let index = 0; index < samples.length; index += 1) {
          samples[index] = view.getInt16(index * 2, true) / 32768;
        }
        const buffer = context.createBuffer(1, samples.length, OUTPUT_RATE);
        buffer.copyToChannel(samples, 0);
        const player = context.createBufferSource();
        player.buffer = buffer;

        const analyser = ensurePlaybackAnalyser(context);
        if (analyser) {
          player.connect(analyser);
        } else {
          player.connect(context.destination);
        }

        const startAt = Math.max(context.currentTime + 0.02, playbackCursor.current);
        playbackCursor.current = startAt + buffer.duration;
        playbackSources.current.add(player);
        setAssistantSpeaking(true);
        setVoiceState("speaking");

        player.onended = () => {
          playbackSources.current.delete(player);
          try {
            player.disconnect();
          } catch {
            // ignore
          }
          if (playbackSources.current.size === 0) {
            setAssistantSpeaking(false);
            setVoiceState("listening");
          }
        };
        player.start(startAt);
      } else if (event.type === "turn_complete") {
        const pending = pendingTextTurn.current;
        pendingTextTurn.current = null;
        if (!event.interrupted) {
          callbacks.current.onTranscript(event.input_text, event.output_text);
          pending?.resolve({
            input_text: event.input_text,
            output_text: event.output_text,
          });
        } else {
          pending?.reject(new Error("The live voice response was interrupted."));
        }
        suppressAudio.current = false;
        setVoiceState("listening");
      } else if (event.type === "interrupted") {
        suppressAudio.current = true;
        setVoiceState("listening");
      } else if (event.type === "error") {
        const errorInfo = classifyVoiceError(event.message);
        setVoiceError(errorInfo);
        setVoiceState("error");
        const pending = pendingTextTurn.current;
        pendingTextTurn.current = null;
        if (pending) pending.reject(new Error(event.message));
        else callbacks.current.onError(event.message);
        void stop();
      }
    },
    [stop],
  );

  useEffect(() => {
    const unsubscribe = alexApi.onVoiceEvent(handleVoiceEvent);
    return () => {
      unsubscribe();
      void stop();
    };
  }, [handleVoiceEvent, stop]);

  const start = useCallback(async () => {
    if (active || starting) return;
    setStarting(true);
    try {
      // Clean pre-flight track release to avoid locking device hardware
      if (streamRef.current) {
        try {
          streamRef.current.getTracks().forEach((track) => track.stop());
        } catch {
          // ignore
        }
        streamRef.current = null;
      }

      if (alexApi.ensureMicrophoneAccess) {
        const access = await Promise.race([
          alexApi.ensureMicrophoneAccess(),
          new Promise<{ granted: boolean; status: string }>((res) =>
            setTimeout(() => res({ granted: true, status: "timeout" }), 5000),
          ),
        ]).catch(() => ({ granted: true, status: "unknown" }));
        if (access && access.granted === false && access.status === "denied") {
          throw new Error("Microphone access is denied in macOS System Settings > Privacy & Security > Microphone.");
        }
      }

      const stream = await acquireMicrophoneStream(inputDeviceId);

      suppressAudio.current = false;
      streamRef.current = stream;

      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextClass) {
        throw new Error("Web Audio API is not supported in this environment.");
      }
      const context = new AudioContextClass();
      contextRef.current = context;

      await setAudioOutput(context, outputDeviceId);

      // Load worklet via URL, or fall back to inline Blob URL
      try {
        await context.audioWorklet.addModule(
          new URL("pcm-capture-worklet.js", window.location.href).toString(),
        );
      } catch (workletError) {
        console.warn("Failed to load pcm-capture-worklet.js via URL, attempting inline Blob:", workletError);
        if (typeof Blob !== "undefined" && typeof URL !== "undefined") {
          const workletCode = `class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(2048);
    this.offset = 0;
  }
  process(inputs, outputs) {
    const input = inputs[0]?.[0];
    const output = outputs[0]?.[0];
    if (output) output.fill(0);
    if (!input) return true;
    let sourceOffset = 0;
    while (sourceOffset < input.length) {
      const count = Math.min(input.length - sourceOffset, this.buffer.length - this.offset);
      this.buffer.set(input.subarray(sourceOffset, sourceOffset + count), this.offset);
      sourceOffset += count;
      this.offset += count;
      if (this.offset === this.buffer.length) {
        const chunk = this.buffer;
        this.buffer = new Float32Array(2048);
        this.offset = 0;
        this.port.postMessage(chunk, [chunk.buffer]);
      }
    }
    return true;
  }
}
registerProcessor("alex-pcm-capture", PcmCaptureProcessor);`;
          const blob = new Blob([workletCode], { type: "application/javascript" });
          const blobUrl = URL.createObjectURL(blob);
          try {
            await context.audioWorklet.addModule(blobUrl);
          } finally {
            URL.revokeObjectURL(blobUrl);
          }
        }
      }

      if (context.state === "suspended") {
        await context.resume();
      }

      // Connect to voice service with generous handshake timeout
      await Promise.race([
        alexApi.startVoice(),
        new Promise<never>((_, rej) =>
          setTimeout(() => rej(new Error("Voice service connection timed out. Check Gemini API key in Settings.")), 20000),
        ),
      ]);

      const source = context.createMediaStreamSource(stream);
      sourceRef.current = source;
      const processor = new AudioWorkletNode(context, "alex-pcm-capture", {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1],
      });
      processor.port.onmessage = (event: MessageEvent<unknown>) => {
        if (
          event.data instanceof Float32Array &&
          contextRef.current === context &&
          !pendingTextTurn.current
        ) {
          const pcm = resampleToPcm16(event.data, context.sampleRate);
          if (!inputEnabledRef.current) new Uint8Array(pcm).fill(0);
          for (let offset = 0; offset < pcm.byteLength; offset += 8192) {
            alexApi.sendVoiceAudio(pcm.slice(offset, offset + 8192));
          }
        }
      };
      source.connect(processor);
      processor.connect(context.destination);
      processorRef.current = processor;
      setActive(true);
      setVoiceState("listening");
      setVoiceError(null);
    } catch (error) {
      await releaseAudio();
      try {
        await alexApi.stopVoice();
      } catch (stopError) {
        console.error("Could not close a failed voice connection", stopError);
      }
      const message = error instanceof Error ? error.message : "Could not start voice.";
      const errorInfo = classifyVoiceError(message);
      setVoiceError(errorInfo);
      setVoiceState("error");
      callbacks.current.onError(message);
      throw error;
    } finally {
      setStarting(false);
    }
  }, [active, inputDeviceId, outputDeviceId, releaseAudio, starting]);

  const interrupt = useCallback(async () => {
    suppressAudio.current = true;
    clearPlayback();
    setVoiceState("listening");
    try {
      await alexApi.interruptVoice();
    } catch (error) {
      suppressAudio.current = false;
      callbacks.current.onError(
        error instanceof Error ? error.message : "Could not interrupt the voice response.",
      );
    }
  }, [clearPlayback]);

  const sendText = useCallback(
    async (text: string): Promise<LiveTextTurn> => {
      if (!active) throw new Error("Start the microphone to send a message in the live session.");
      if (pendingTextTurn.current) throw new Error("Wait for the current live response to finish.");
      const cleanText = text.trim();
      if (!cleanText || cleanText.length > 4000) {
        throw new Error("Message must contain 1 to 4000 characters.");
      }

      setVoiceState("thinking");
      let resolveTurn!: (turn: LiveTextTurn) => void;
      let rejectTurn!: (error: Error) => void;
      const response = new Promise<LiveTextTurn>((resolve, reject) => {
        resolveTurn = resolve;
        rejectTurn = reject;
      });
      pendingTextTurn.current = { resolve: resolveTurn, reject: rejectTurn };
      try {
        await alexApi.sendVoiceText(cleanText);
      } catch (error) {
        pendingTextTurn.current = null;
        setVoiceState("listening");
        throw error;
      }
      return response;
    },
    [active],
  );

  const reconnect = useCallback(async () => {
    setVoiceError(null);
    await stop();
    await start();
  }, [stop, start]);

  return {
    active,
    starting,
    start,
    stop,
    reconnect,
    interrupt,
    sendText,
    assistantSpeaking,
    voiceState,
    voiceError,
    setVoiceError,
    analyserNode: playbackAnalyserRef.current,
  };
}
