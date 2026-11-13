/**
 * 3D Holographic AI Head & Viseme Lip-Sync (TASK-P4-05 / CAT-02)
 *
 * Real-time 3D wireframe head rendered on HTML5 Canvas using MediaPipe 468-vertex
 * human geometry, realistic gaze/saccades, blinks, jaw-hinged mouth articulation,
 * and formant viseme analysis.
 */

import { useEffect, useRef } from "react";

import type { HudStyle } from "../types/api";
import { HoloAvatarRenderer } from "./avatar/avatarRenderer";
import { CANONICAL_VISEMES, VisemeAnalyzer } from "./avatar/visemeAnalyzer";

export interface HudAvatarProps {
  assistantName: string;
  mode: "booting" | "idle" | "listening" | "thinking" | "speaking";
  style: HudStyle;
  primaryColor?: string;
  accentColor?: string;
  speaking?: boolean;
  amplitude?: number;
  spokenText?: string;
  analyserNode?: AnalyserNode | null;
  diagnosticPhase?: string;
}

export function HudAvatar({
  assistantName,
  mode,
  style,
  primaryColor = "#00dfff",
  accentColor = "#ff7a16",
  speaking = false,
  amplitude = 0.0,
  spokenText = "",
  analyserNode = null,
  diagnosticPhase = "idle",
}: HudAvatarProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const captionTextRef = useRef<HTMLSpanElement | null>(null);
  const rendererRef = useRef<HoloAvatarRenderer | null>(null);
  const visemeAnalyzerRef = useRef<VisemeAnalyzer | null>(null);
  const animFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (style !== "core") {
      if (!rendererRef.current) {
        rendererRef.current = new HoloAvatarRenderer();
      }
      if (!visemeAnalyzerRef.current) {
        visemeAnalyzerRef.current = new VisemeAnalyzer();
      }
    }

    const canvas = canvasRef.current;
    let ctx: CanvasRenderingContext2D | null = null;
    if (canvas && style !== "core") {
      try {
        ctx = canvas.getContext("2d");
      } catch {
        ctx = null;
      }
    }
    let lastTime = performance.now();

    // Pre-allocated buffers for zero-allocation audio sampling in RAF loop
    const freqData = new Uint8Array(256);
    const timeData = new Float32Array(256);

    const loop = (now: number) => {
      const dt = Math.min(0.1, (now - lastTime) / 1000);
      lastTime = now;

      let realTimeAmp = amplitude;
      let realTimeSpeaking = speaking;
      let targetViseme = CANONICAL_VISEMES.sil;

      if (analyserNode) {
        try {
          if (typeof analyserNode.getByteFrequencyData === "function") {
            analyserNode.getByteFrequencyData(freqData);
          }
          if (typeof analyserNode.getFloatTimeDomainData === "function") {
            analyserNode.getFloatTimeDomainData(timeData);
            let sumSq = 0;
            for (let i = 0; i < timeData.length; i++) {
              sumSq += timeData[i] * timeData[i];
            }
            const rms = Math.sqrt(sumSq / timeData.length);

            // Low-amplitude threshold eliminates room/microphone noise floor
            if (rms > 0.015) {
              realTimeAmp = Math.min(1.0, (rms - 0.015) * 4.8);
              realTimeSpeaking = true;
              if (visemeAnalyzerRef.current) {
                const sampleRate = analyserNode.context?.sampleRate || 44100;
                targetViseme = visemeAnalyzerRef.current.analyzeFormants(freqData, sampleRate);
              }
            } else {
              realTimeAmp = 0.0;
              realTimeSpeaking = false;
              targetViseme = CANONICAL_VISEMES.sil;
            }
          }
        } catch {
          // Graceful fallback to prop values
          realTimeAmp = amplitude;
          realTimeSpeaking = speaking;
        }
      } else if (spokenText) {
        if (visemeAnalyzerRef.current) {
          targetViseme = visemeAnalyzerRef.current.analyzeTextChar(spokenText.slice(-1));
        }
        realTimeSpeaking = speaking;
      } else if (speaking && amplitude > 0.05) {
        targetViseme = {
          open: Math.min(1.0, amplitude * 2.0),
          wide: 0.0,
          closure: 0.0,
          name: "aa",
        };
        realTimeSpeaking = true;
      } else {
        targetViseme = CANONICAL_VISEMES.sil;
        realTimeSpeaking = false;
      }

      const activeMode = realTimeSpeaking ? "speaking" : mode;

      // Update stage DOM styling in-place (zero React re-renders)
      if (stageRef.current) {
        stageRef.current.classList.toggle("holo-speaking", realTimeSpeaking);
        if (realTimeSpeaking) {
          stageRef.current.style.setProperty("--voice-amp", realTimeAmp.toFixed(3));
          stageRef.current.style.setProperty("--voice-glow", (realTimeAmp * 35).toFixed(1) + "px");
          stageRef.current.style.setProperty("--core-scale", (1 + realTimeAmp * 0.16).toFixed(3));
        } else if (diagnosticPhase === "cpu_mem") {
          stageRef.current.style.setProperty("--core-scale", "1.08");
        } else {
          stageRef.current.style.removeProperty("--voice-amp");
          stageRef.current.style.removeProperty("--voice-glow");
          stageRef.current.style.removeProperty("--core-scale");
        }
      }

      if (captionTextRef.current) {
        const statusLabel =
          activeMode === "speaking"
            ? "RESPONDING"
            : activeMode === "listening"
            ? "LISTENING"
            : activeMode === "thinking"
            ? "PROCESSING"
            : activeMode === "booting"
            ? "INITIALISING"
            : "STANDING BY";
        if (captionTextRef.current.textContent !== statusLabel) {
          captionTextRef.current.textContent = statusLabel;
        }
      }

      // If rendering face on Canvas
      const renderer = rendererRef.current;
      const analyzer = visemeAnalyzerRef.current;
      if (renderer && analyzer && style !== "core") {
        const currentViseme = analyzer.step(dt, targetViseme);

        renderer.step(dt, {
          amplitude: realTimeAmp,
          speaking: realTimeSpeaking,
          mode: activeMode,
          viseme: currentViseme,
          diagnosticPhase,
        });

        if (ctx && canvas) {
          renderer.render(ctx, canvas.width, canvas.height, {
            primaryColor,
            accentColor,
            mode: activeMode,
            amplitude: realTimeAmp,
            speaking: realTimeSpeaking,
            viseme: currentViseme,
            diagnosticPhase,
          });
        }
      }

      animFrameRef.current = requestAnimationFrame(loop);
    };

    animFrameRef.current = requestAnimationFrame(loop);

    return () => {
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
        animFrameRef.current = null;
      }
    };
  }, [style, mode, speaking, amplitude, spokenText, analyserNode, primaryColor, accentColor, diagnosticPhase]);

  const initialMode = speaking || mode === "speaking" ? "speaking" : mode;

  return (
    <div
      ref={stageRef}
      className={`holo-stage holo-${initialMode} holo-${style} diag-phase-${diagnosticPhase}`}
      aria-label={`${assistantName} hologram`}
      data-testid="holo-stage"
      data-diag-phase={diagnosticPhase}
    >
      {style === "core" && <div className="holo-rings" aria-hidden="true" />}

      {style === "core" ? (
        <div className="reactor-core" role="img" aria-label="Animated reactor core">
          <div className="reactor-orbit reactor-orbit-one" />
          <div className="reactor-orbit reactor-orbit-two" />
          <div className="reactor-ring">
            <i />
            <i />
            <i />
            <i />
          </div>
          <div className="reactor-center" />
        </div>
      ) : (
        <canvas
          ref={canvasRef}
          width={640}
          height={720}
          className="holo-avatar holo-avatar-canvas"
          role="img"
          aria-label="3D holographic head"
          data-testid="holo-canvas"
        />
      )}

      {/* Screen-reader status label (keeps accessibility & tests green without visual leakage) */}
      <div className="sr-only" aria-live="polite">
        <span ref={captionTextRef}>
          {initialMode === "speaking"
            ? "RESPONDING"
            : initialMode === "listening"
            ? "LISTENING"
            : initialMode === "thinking"
            ? "PROCESSING"
            : initialMode === "booting"
            ? "INITIALISING"
            : "STANDING BY"}
        </span>
      </div>
    </div>
  );
}
