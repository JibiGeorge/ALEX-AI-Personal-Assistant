/**
 * Lip Sync Controller (Realistic Humanoid 3D)
 *
 * Synchronizes facial mouth articulation and jaw movement with:
 * 1. Web Audio API AnalyserNode (frequency & amplitude spectrum)
 * 2. Phoneme / Viseme speech synthesis timing
 * 3. ARKit & Oculus Viseme blendshapes
 */

import * as THREE from "three";
import { CANONICAL_VISEMES, VisemeAnalyzer } from "./visemeAnalyzer";

export interface LipSyncTargets {
  headMesh?: THREE.Mesh | THREE.SkinnedMesh;
  teethMesh?: THREE.Mesh | THREE.SkinnedMesh;
}

export class LipSyncController {
  private targets: LipSyncTargets = {};
  private visemeAnalyzer = new VisemeAnalyzer();

  // Audio frequency analysis buffer
  private audioDataArray: Uint8Array<ArrayBuffer> | null = null;
  private currentAmplitude = 0;
  private smoothedMouthOpen = 0;

  constructor(targets: LipSyncTargets) {
    this.targets = targets;
  }

  public updateTargets(targets: LipSyncTargets) {
    this.targets = targets;
  }

  public update(
    delta: number,
    time: number,
    speaking: boolean,
    analyserNode?: AnalyserNode | null,
    spokenText: string = "",
  ) {
    if (!speaking) {
      // Smoothly snap mouth closed when speech ends or is interrupted
      this.smoothedMouthOpen = THREE.MathUtils.lerp(this.smoothedMouthOpen, 0, delta * 15);
      this.resetAllVisemes();
      this.applyMorph("mouthOpen", this.smoothedMouthOpen);
      this.applyMorph("jawOpen", this.smoothedMouthOpen * 0.7);
      return;
    }

    // 1. Measure real-time audio amplitude from AnalyserNode if available
    let measuredAmp = 0;
    if (analyserNode) {
      if (!this.audioDataArray || this.audioDataArray.length !== analyserNode.frequencyBinCount) {
        this.audioDataArray = new Uint8Array(new ArrayBuffer(analyserNode.frequencyBinCount));
      }
      analyserNode.getByteFrequencyData(this.audioDataArray);

      // Focus on human vocal frequencies (~120 Hz to 2400 Hz)
      let sum = 0;
      const binCount = Math.min(this.audioDataArray.length, 64);
      for (let i = 2; i < binCount; i++) {
        sum += this.audioDataArray[i];
      }
      measuredAmp = Math.min(1.0, (sum / (binCount - 2)) / 110);
    } else {
      // Dynamic fallback based on speech cadence and viseme text
      const baseWave = (Math.sin(time * 16) + 1) * 0.35;
      const accentWave = Math.max(0, Math.sin(time * 8)) * 0.3;
      measuredAmp = baseWave + accentWave;
    }

    this.currentAmplitude = THREE.MathUtils.lerp(this.currentAmplitude, measuredAmp, delta * 20);
    const targetMouthOpen = Math.min(1.0, this.currentAmplitude * 1.35);
    this.smoothedMouthOpen = THREE.MathUtils.lerp(this.smoothedMouthOpen, targetMouthOpen, delta * 25);

    // 2. Compute phoneme-to-viseme targets
    let targetShape = CANONICAL_VISEMES.sil;
    if (analyserNode && this.audioDataArray) {
      targetShape = this.visemeAnalyzer.analyzeFormants(
        this.audioDataArray,
        analyserNode.context.sampleRate,
      );
    } else if (spokenText) {
      const charIdx = Math.floor((time * 12) % Math.max(1, spokenText.length));
      targetShape = this.visemeAnalyzer.analyzeTextChar(spokenText[charIdx] || "a");
    } else {
      const vowelCycle = ["aa", "ee", "oo", "ch"] as const;
      const v = vowelCycle[Math.floor((time * 4) % vowelCycle.length)] || "aa";
      targetShape = CANONICAL_VISEMES[v];
    }

    const currentShape = this.visemeAnalyzer.step(delta, targetShape);

    // Map viseme to Oculus & ARKit morph shapes
    this.resetAllVisemes();
    this.blendViseme(currentShape.name, this.currentAmplitude, currentShape.wide);

    // Apply primary mouth open & jaw articulation
    const openAmount = Math.max(this.smoothedMouthOpen, currentShape.open * this.currentAmplitude);
    this.applyMorph("mouthOpen", openAmount);
    this.applyMorph("jawOpen", openAmount * 0.75);
    this.applyMorph("mouthSmile", 0.08 + openAmount * 0.1);
  }

  public getAmplitude(): number {
    return this.currentAmplitude;
  }

  private blendViseme(visemeName: string, weight: number, wide: number) {
    const oculusMap: Record<string, string> = {
      aa: "viseme_aa",
      ee: "viseme_E",
      oo: "viseme_O",
      ch: "viseme_CH",
      sil: "viseme_sil",
    };

    const targetMorph = oculusMap[visemeName];
    if (targetMorph) {
      this.applyMorph(targetMorph, weight * 0.85);
    }

    // Blend lip stretch vs pucker
    if (wide > 0) {
      this.applyMorph("mouthStretchLeft", wide * weight * 0.5);
      this.applyMorph("mouthStretchRight", wide * weight * 0.5);
    } else if (wide < 0) {
      this.applyMorph("mouthPucker", -wide * weight * 0.7);
      this.applyMorph("mouthFunnel", -wide * weight * 0.5);
    }
  }

  private resetAllVisemes() {
    const list = [
      "viseme_sil",
      "viseme_PP",
      "viseme_FF",
      "viseme_TH",
      "viseme_DD",
      "viseme_kk",
      "viseme_CH",
      "viseme_SS",
      "viseme_nn",
      "viseme_RR",
      "viseme_aa",
      "viseme_E",
      "viseme_I",
      "viseme_O",
      "viseme_U",
      "mouthPucker",
      "mouthFunnel",
      "mouthStretchLeft",
      "mouthStretchRight",
    ];

    for (const name of list) {
      this.applyMorph(name, 0);
    }
  }

  private applyMorph(name: string, value: number) {
    const meshes = [this.targets.headMesh, this.targets.teethMesh];

    for (const mesh of meshes) {
      if (!mesh || !mesh.morphTargetDictionary || !mesh.morphTargetInfluences) continue;
      const index = mesh.morphTargetDictionary[name];
      if (index !== undefined) {
        mesh.morphTargetInfluences[index] = THREE.MathUtils.clamp(value, 0, 1);
      }
    }
  }
}
