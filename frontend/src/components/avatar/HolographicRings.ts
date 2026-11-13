/**
 * 3D Holographic HUD Rings & Orbital Particle System
 *
 * Renders concentric, segmented, rotating cyan holographic rings and
 * orbital energy particles behind the humanoid robot head.
 */

import * as THREE from "three";
import type { AssistantVisualMode } from "./FacialAnimationController";

export class HolographicRings {
  public group = new THREE.Group();
  private rings: THREE.LineSegments[] = [];
  private ringSpeeds = [0.4, -0.6, 0.8, -0.3];
  private particles: THREE.Points | null = null;
  private particlePositions: Float32Array<ArrayBuffer> | null = null;

  constructor(primaryColor: string = "#00e5ff") {
    this.createRings(primaryColor);
    this.createParticles(primaryColor);
    // Position rings centered behind head at Y = 1.48, Z = -0.06
    this.group.position.set(0, 1.48, -0.06);
  }

  private createRings(primaryColor: string) {
    const ringRadii = [0.28, 0.36, 0.45, 0.54];
    const cyan = new THREE.Color(primaryColor);

    ringRadii.forEach((radius, idx) => {
      const segments = 64;
      const step = (Math.PI * 2) / segments;
      const vertices: number[] = [];

      for (let i = 0; i < segments; i++) {
        // Create segmented dashes by skipping segments
        if (idx === 1 && i % 4 === 0) continue;
        if (idx === 2 && i % 6 === 0) continue;
        if (idx === 3 && (i % 8 === 0 || i % 8 === 1)) continue;

        const theta1 = i * step;
        const theta2 = (i + 1) * step;

        vertices.push(
          Math.cos(theta1) * radius,
          Math.sin(theta1) * radius,
          0,
          Math.cos(theta2) * radius,
          Math.sin(theta2) * radius,
          0
        );
      }

      const geom = new THREE.BufferGeometry();
      geom.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

      const mat = new THREE.LineBasicMaterial({
        color: cyan,
        transparent: true,
        opacity: 0.35 + idx * 0.12,
        blending: THREE.AdditiveBlending,
        linewidth: 1.5,
      });

      const line = new THREE.LineSegments(geom, mat);
      this.rings.push(line);
      this.group.add(line);
    });
  }

  private createParticles(primaryColor: string) {
    const count = 48;
    this.particlePositions = new Float32Array(new ArrayBuffer(count * 3 * 4));
    const geom = new THREE.BufferGeometry();

    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const radius = 0.45 + (i % 4) * 0.08;
      this.particlePositions[i * 3] = Math.cos(angle) * radius;
      this.particlePositions[i * 3 + 1] = Math.sin(angle) * radius;
      this.particlePositions[i * 3 + 2] = (Math.random() - 0.5) * 0.1;
    }

    geom.setAttribute("position", new THREE.BufferAttribute(this.particlePositions, 3));

    const mat = new THREE.PointsMaterial({
      color: new THREE.Color(primaryColor),
      size: 0.018,
      transparent: true,
      opacity: 0.7,
      blending: THREE.AdditiveBlending,
    });

    this.particles = new THREE.Points(geom, mat);
    this.group.add(this.particles);
  }

  public update(delta: number, mode: AssistantVisualMode, amplitude: number) {
    let speedMult = 1.0;
    if (mode === "listening") speedMult = 2.2;
    if (mode === "thinking") speedMult = 3.5;
    if (mode === "speaking") speedMult = 1.6 + amplitude * 2.0;
    if (mode === "sleep") speedMult = 0.2;

    this.rings.forEach((ring, i) => {
      const dir = this.ringSpeeds[i] || 0.5;
      ring.rotation.z += dir * delta * speedMult;

      // Pulse brightness with voice
      const mat = ring.material as THREE.LineBasicMaterial;
      if (mat) {
        const baseOp = 0.35 + i * 0.12;
        mat.opacity = THREE.MathUtils.clamp(baseOp + amplitude * 0.3, 0.1, 0.95);
      }
    });

    if (this.particles) {
      this.particles.rotation.z -= delta * 0.4 * speedMult;
    }
  }

  public dispose() {
    this.rings.forEach((r) => {
      r.geometry.dispose();
      (r.material as THREE.Material).dispose();
    });
    if (this.particles) {
      this.particles.geometry.dispose();
      (this.particles.material as THREE.Material).dispose();
    }
  }
}

