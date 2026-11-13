/**
 * Facial Animation Controller (Realistic Humanoid 3D)
 *
 * Coordinates:
 * - Natural random blinking (every 2.5 - 4.5s)
 * - Eye saccades & focus (subtle organic gaze wandering)
 * - Head micro-movements & breathing motion
 * - Emotional states: IDLE, LISTENING, THINKING, SPEAKING, SLEEP
 */

import * as THREE from "three";

export type AssistantVisualMode = "booting" | "idle" | "listening" | "thinking" | "speaking" | "sleep";

export interface FacialControllerTargets {
  headMesh?: THREE.Mesh | THREE.SkinnedMesh;
  teethMesh?: THREE.Mesh | THREE.SkinnedMesh;
  eyeLeftMesh?: THREE.Mesh | THREE.SkinnedMesh;
  eyeRightMesh?: THREE.Mesh | THREE.SkinnedMesh;
  headBone?: THREE.Bone | THREE.Object3D;
  neckBone?: THREE.Bone | THREE.Object3D;
  leftEyeBone?: THREE.Bone | THREE.Object3D;
  rightEyeBone?: THREE.Bone | THREE.Object3D;
}

export class FacialAnimationController {
  private targets: FacialControllerTargets = {};
  private blinkTime = 0;
  private nextBlink = 3.0;
  private isBlinking = false;
  private blinkWeight = 0;

  // Saccade / eye gaze
  private gazeCurrent = new THREE.Vector2(0, 0);
  private gazeTarget = new THREE.Vector2(0, 0);
  private nextGazeTime = 2.0;

  // Head idle sway
  private headRotation = new THREE.Euler(0, 0, 0);

  constructor(targets: FacialControllerTargets) {
    this.targets = targets;
  }

  public updateTargets(targets: FacialControllerTargets) {
    this.targets = targets;
  }

  public update(delta: number, time: number, mode: AssistantVisualMode) {
    // 1. Blinking Logic
    this.updateBlinking(delta, mode);

    // 2. Eye Gaze (Saccades)
    this.updateGaze(delta, time, mode);

    // 3. Head & Neck Posture / Breathing
    this.updateHeadPose(time, mode);
  }

  private updateBlinking(delta: number, mode: AssistantVisualMode) {
    if (mode === "sleep") {
      this.blinkWeight = THREE.MathUtils.lerp(this.blinkWeight, 1.0, delta * 8);
      this.applyMorph("eyeBlinkLeft", this.blinkWeight);
      this.applyMorph("eyeBlinkRight", this.blinkWeight);
      return;
    }

    this.blinkTime += delta;
    if (this.blinkTime >= this.nextBlink && !this.isBlinking) {
      this.isBlinking = true;
      this.blinkTime = 0;
      this.nextBlink = 2.5 + Math.random() * 2.5;
    }

    if (this.isBlinking) {
      // 160ms complete blink cycle
      const blinkProgress = this.blinkTime / 0.16;
      if (blinkProgress >= 1.0) {
        this.isBlinking = false;
        this.blinkWeight = 0;
      } else {
        // Smooth sine curve for eyelid motion
        this.blinkWeight = Math.sin(blinkProgress * Math.PI);
      }
    } else {
      this.blinkWeight = 0;
    }

    this.applyMorph("eyeBlinkLeft", this.blinkWeight);
    this.applyMorph("eyeBlinkRight", this.blinkWeight);
  }

  private updateGaze(delta: number, _time: number, mode: AssistantVisualMode) {
    if (mode === "sleep") {
      this.gazeCurrent.set(0, -0.3);
      return;
    }

    this.nextGazeTime -= delta;
    if (this.nextGazeTime <= 0) {
      if (mode === "listening") {
        // Direct attention to user / camera
        this.gazeTarget.set((Math.random() - 0.5) * 0.05, (Math.random() - 0.5) * 0.04);
        this.nextGazeTime = 3.0 + Math.random() * 2.0;
      } else if (mode === "thinking") {
        // Glance slightly upward and sideways
        this.gazeTarget.set(0.25, 0.2);
        this.nextGazeTime = 1.5 + Math.random() * 1.0;
      } else {
        // Natural wandering saccades
        this.gazeTarget.set((Math.random() - 0.5) * 0.25, (Math.random() - 0.5) * 0.15);
        this.nextGazeTime = 1.8 + Math.random() * 2.5;
      }
    }

    this.gazeCurrent.lerp(this.gazeTarget, delta * 10);

    // Apply eye gaze to eye morph targets or bones
    if (this.targets.leftEyeBone && this.targets.rightEyeBone) {
      this.targets.leftEyeBone.rotation.y = this.gazeCurrent.x * 0.4;
      this.targets.leftEyeBone.rotation.x = -this.gazeCurrent.y * 0.3;
      this.targets.rightEyeBone.rotation.y = this.gazeCurrent.x * 0.4;
      this.targets.rightEyeBone.rotation.x = -this.gazeCurrent.y * 0.3;
    }

    // Secondary morph targets for subtle eye direction
    const lx = this.gazeCurrent.x;
    const ly = this.gazeCurrent.y;
    this.applyMorph("eyeLookInLeft", lx < 0 ? -lx : 0);
    this.applyMorph("eyeLookOutLeft", lx > 0 ? lx : 0);
    this.applyMorph("eyeLookInRight", lx > 0 ? lx : 0);
    this.applyMorph("eyeLookOutRight", lx < 0 ? -lx : 0);
    this.applyMorph("eyeLookUpLeft", ly > 0 ? ly : 0);
    this.applyMorph("eyeLookUpRight", ly > 0 ? ly : 0);
    this.applyMorph("eyeLookDownLeft", ly < 0 ? -ly : 0);
    this.applyMorph("eyeLookDownRight", ly < 0 ? -ly : 0);
  }

  private updateHeadPose(time: number, mode: AssistantVisualMode) {
    if (!this.targets.headBone) return;

    let targetPitch = Math.sin(time * 0.8) * 0.02; // breathing up/down
    let targetYaw = Math.cos(time * 0.5) * 0.025; // gentle sway left/right
    let targetRoll = Math.sin(time * 0.6) * 0.015;

    if (mode === "listening") {
      targetPitch += 0.04; // Head tilts slightly forward, attentive
      targetYaw += this.gazeCurrent.x * 0.1;
    } else if (mode === "thinking") {
      targetRoll += 0.06; // Inquisitive head tilt
      targetPitch += -0.03;
    } else if (mode === "speaking") {
      targetPitch += Math.sin(time * 3.5) * 0.035; // Speaking cadence nod
      targetYaw += Math.cos(time * 2.2) * 0.02;
    } else if (mode === "sleep") {
      targetPitch += -0.08; // Head rests down
    }

    this.headRotation.x = THREE.MathUtils.lerp(this.headRotation.x, targetPitch, 0.05);
    this.headRotation.y = THREE.MathUtils.lerp(this.headRotation.y, targetYaw, 0.05);
    this.headRotation.z = THREE.MathUtils.lerp(this.headRotation.z, targetRoll, 0.05);

    this.targets.headBone.rotation.copy(this.headRotation);
  }

  private applyMorph(name: string, value: number) {
    const meshes = [
      this.targets.headMesh,
      this.targets.eyeLeftMesh,
      this.targets.eyeRightMesh,
      this.targets.teethMesh,
    ];

    for (const mesh of meshes) {
      if (!mesh || !mesh.morphTargetDictionary || !mesh.morphTargetInfluences) continue;
      const index = mesh.morphTargetDictionary[name];
      if (index !== undefined) {
        mesh.morphTargetInfluences[index] = THREE.MathUtils.clamp(value, 0, 1);
      }
    }
  }
}

