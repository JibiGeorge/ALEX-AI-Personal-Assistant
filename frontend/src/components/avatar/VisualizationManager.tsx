/**
 * Centralized Multi-Visualization Manager (Nexora AI / Jarvis)
 *
 * Coordinates between available visual representations:
 * 1. ExistingHumanoidFace (MediaPipe 3D wireframe head)
 * 2. ReactorCore (Iron Man Arc Reactor Fusion)
 * 3. RealisticHumanoidRobot (Realistic 3D female android with dynamic waveform)
 *
 * Requirements:
 * - Preserves existing visual components without breaking existing behavior
 * - Only mounts/renders the active visualization to conserve GPU/CPU resources
 * - Automatically normalizes visualization keys:
 *     "existing_face" | "face" -> ExistingHumanoidFace
 *     "reactor_core" | "core"  -> ReactorCore
 *     "realistic_humanoid" | "robot" -> RealisticHumanoidRobot
 */

import { type ReactElement } from "react";
import type { HudStyle } from "../../types/api";
import { HudAvatar } from "../HudAvatar";
import { RealisticHumanoid3D } from "./RealisticHumanoid3D";

export type VisualizationId =
  | "existing_face"
  | "reactor_core"
  | "realistic_humanoid"
  | "face"
  | "core"
  | "robot";

export interface VisualizationManagerProps {
  visualization?: HudStyle | VisualizationId;
  assistantName?: string;
  mode: "booting" | "idle" | "listening" | "thinking" | "speaking";
  speaking?: boolean;
  amplitude?: number;
  spokenText?: string;
  analyserNode?: AnalyserNode | null;
  primaryColor?: string;
  accentColor?: string;
  diagnosticPhase?: string;
}

export function normalizeVisualization(
  vis?: HudStyle | VisualizationId | null,
): "face" | "core" | "robot" {
  if (vis === "reactor_core" || vis === "core") {
    return "core";
  }
  if (vis === "realistic_humanoid" || vis === "robot") {
    return "robot";
  }
  return "face";
}

export function VisualizationManager({
  visualization = "face",
  assistantName = "Alex",
  mode,
  speaking = false,
  amplitude = 0.0,
  spokenText = "",
  analyserNode = null,
  primaryColor = "#00dfff",
  accentColor = "#ff7a16",
  diagnosticPhase = "idle",
}: VisualizationManagerProps): ReactElement {
  const activeKey = normalizeVisualization(visualization);

  // Render ONLY the active visualization to prevent CPU/WebGL contention
  if (activeKey === "robot") {
    return (
      <RealisticHumanoid3D
        assistantName={assistantName}
        mode={mode}
        speaking={speaking}
        amplitude={amplitude}
        spokenText={spokenText}
        analyserNode={analyserNode}
        primaryColor={primaryColor}
        accentColor={accentColor}
        diagnosticPhase={diagnosticPhase}
      />
    );
  }

  // Uses the existing HudAvatar for "face" and "core"
  return (
    <HudAvatar
      assistantName={assistantName}
      mode={mode}
      style={activeKey}
      speaking={speaking}
      amplitude={amplitude}
      spokenText={spokenText}
      analyserNode={analyserNode}
      primaryColor={primaryColor}
      accentColor={accentColor}
      diagnosticPhase={diagnosticPhase}
    />
  );
}

