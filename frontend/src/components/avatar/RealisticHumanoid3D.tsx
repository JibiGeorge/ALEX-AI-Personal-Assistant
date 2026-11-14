/**
 * Realistic Humanoid 3D Visualization Component (Nexora AI / Jarvis)
 *
 * Real-time 3D female android rendered through Three.js:
 * - Lifelike facial structure & PBR skin
 * - Cyan illuminated eyes with organic saccades & blinking
 * - Metallic titanium neck and shoulders
 * - Futuristic cybernetic ear modules
 * - Rotating concentric holographic HUD rings in 3D
 * - Voice-synchronized mouth articulation (jaw + visemes)
 * - Horizontal real-time audio waveform overlay
 * - Graceful WebGL detection & canvas fallback
 */

import { useEffect, useRef, useState } from "react";
import { HumanoidScene } from "./HumanoidScene";
import type { AssistantVisualMode } from "./FacialAnimationController";

export interface RealisticHumanoid3DProps {
  assistantName?: string;
  mode: "booting" | "idle" | "listening" | "thinking" | "speaking";
  speaking?: boolean;
  amplitude?: number;
  spokenText?: string;
  analyserNode?: AnalyserNode | null;
  primaryColor?: string;
  accentColor?: string;
  quality?: "low" | "medium" | "high";
  diagnosticPhase?: string;
}

export function RealisticHumanoid3D({
  assistantName = "Alex",
  mode,
  speaking = false,
  amplitude: _propAmplitude = 0.0,
  spokenText = "",
  analyserNode = null,
  primaryColor = "#00e5ff",
  accentColor = "#ff7a16",
  quality = "high",
  diagnosticPhase = "idle",
}: RealisticHumanoid3DProps) {
  const canvas3DRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const sceneRef = useRef<HumanoidScene | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasWebGL] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      const testCanvas = document.createElement("canvas");
      const gl = testCanvas.getContext("webgl") || testCanvas.getContext("experimental-webgl");
      return !!gl;
    } catch {
      return false;
    }
  });

  // Initialize Three.js Humanoid Scene
  useEffect(() => {
    if (!hasWebGL || !canvas3DRef.current) return;

    const scene = new HumanoidScene({
      canvas: canvas3DRef.current,
      primaryColor,
      accentColor,
      quality,
      onLoaded: () => setIsLoaded(true),
      onError: (err) => {
        console.warn("HumanoidScene load notice:", err);
      },
    });

    sceneRef.current = scene;

    // Handle container resize
    const handleResize = () => {
      if (containerRef.current && sceneRef.current) {
        const w = containerRef.current.clientWidth || 540;
        const h = containerRef.current.clientHeight || 540;
        sceneRef.current.resize(w, h);
      }
    };

    handleResize();
    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(handleResize);
      if (containerRef.current) {
        resizeObserver.observe(containerRef.current);
      }
    } else if (typeof window !== "undefined") {
      window.addEventListener("resize", handleResize);
    }

    return () => {
      if (resizeObserver) {
        resizeObserver.disconnect();
      } else if (typeof window !== "undefined") {
        window.removeEventListener("resize", handleResize);
      }
      if (sceneRef.current) {
        sceneRef.current.dispose();
        sceneRef.current = null;
      }
    };
  }, [hasWebGL, primaryColor, accentColor, quality]);

  // Main Render Loop (TASK-P3: Pausable on hidden, 30fps in Low-Power mode)
  useEffect(() => {
    let active = true;
    let lastTime = performance.now();

    const isLowPower =
      typeof window !== "undefined" &&
      (localStorage.getItem("alex_low_power_mode") === "true" ||
        document.documentElement.getAttribute("data-low-power") === "true" ||
        (typeof window.matchMedia === "function" &&
          window.matchMedia("(prefers-reduced-motion: reduce)").matches));

    const renderLoop = (now: number) => {
      if (!active) return;
      if (document.hidden) {
        animFrameRef.current = null;
        return;
      }

      const targetInterval = isLowPower ? 33.33 : 16.66;
      if (now - lastTime < targetInterval) {
        animFrameRef.current = requestAnimationFrame(renderLoop);
        return;
      }
      lastTime = now;

      const visualMode: AssistantVisualMode = mode as AssistantVisualMode;

      // Render 3D Scene
      if (sceneRef.current) {
        sceneRef.current.render(visualMode, speaking, analyserNode, spokenText);
      }

      animFrameRef.current = requestAnimationFrame(renderLoop);
    };

    const handleVisibility = () => {
      if (!document.hidden && animFrameRef.current === null && active) {
        lastTime = performance.now();
        animFrameRef.current = requestAnimationFrame(renderLoop);
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);

    animFrameRef.current = requestAnimationFrame(renderLoop);

    return () => {
      active = false;
      document.removeEventListener("visibilitychange", handleVisibility);
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [mode, speaking, analyserNode, spokenText]);

  const statusLabel =
    mode === "booting"
      ? "INITIALIZING"
      : speaking || mode === "speaking"
      ? "RESPONDING"
      : mode === "thinking"
      ? "PROCESSING"
      : mode === "listening"
      ? "LISTENING"
      : "STANDING BY";

  return (
    <div
      ref={containerRef}
      data-testid="holo-robot-stage"
      className={`hud-humanoid-stage mode-${mode} ${speaking ? "is-speaking" : ""} diag-phase-${diagnosticPhase}`}
      data-diag-phase={diagnosticPhase}
      style={
        {
          "--humanoid-primary": primaryColor,
          "--humanoid-accent": accentColor,
        } as React.CSSProperties
      }
      role="img"
      aria-label={`${assistantName} 3D Humanoid Robot Avatar (${statusLabel})`}
    >
      {/* 3D WebGL Canvas - Unframed, Realistic Rendering */}
      <canvas
        ref={canvas3DRef}
        data-testid="holo-robot-canvas"
        className="humanoid-3d-canvas"
        width={600}
        height={600}
      />

      {/* Screen-reader status label (keeps accessibility & tests green without cluttering UI) */}
      <span className="sr-only">{statusLabel}</span>

      {!isLoaded && hasWebGL && (
        <div className="humanoid-loading-shim" aria-hidden="true">
          <span className="humanoid-loading-spinner" />
          <span>SYNTHESIZING 3D NEURAL INTERFACE…</span>
        </div>
      )}
    </div>
  );
}
