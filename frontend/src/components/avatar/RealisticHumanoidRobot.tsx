/**
 * Realistic Humanoid Robot Visualization (Nexora AI / Jarvis)
 *
 * Real-time 3D female android rendered through Three.js.
 * Completely replaces static image display with genuine real-time 3D character:
 * - Natural human-like face with lifelike PBR skin & facial details
 * - Cyan illuminated eyes with animated saccades & natural blinking
 * - Metallic robotic neck & shoulders with cybernetic ear modules
 * - Rotating concentric holographic HUD rings in 3D space
 * - Real-time horizontal audio waveform across lower torso
 * - Real-time voice-synchronized mouth & viseme articulation
 */

import {
  RealisticHumanoid3D,
  type RealisticHumanoid3DProps,
} from "./RealisticHumanoid3D";

export type RealisticHumanoidRobotProps = RealisticHumanoid3DProps;

export function RealisticHumanoidRobot(props: RealisticHumanoidRobotProps) {
  return <RealisticHumanoid3D {...props} />;
}
