/**
 * 3D Holographic Avatar Canvas Renderer (TASK-P4-05 / CAT-02)
 *
 * Real-time HTML5 Canvas 2D renderer for MediaPipe canonical 3D human head mesh.
 * Poses jaw, lips, brows, eyes (saccades + blinks), and head rotation (pitch/yaw/roll/sway)
 * with perspective projection, respiration dynamics, cybernetic optic rings,
 * volumetric holographic energy motes, synaptic neural nodes, and depth-shaded facets.
 */

import {
  BROW_LIFT,
  CAM_D,
  HEAD_MESH,
  JAW_MAX,
  JAW_PIVOT,
} from "./meshData";
import type { VisemeShape } from "./visemeAnalyzer";

export interface RenderOptions {
  primaryColor?: string; // e.g. '#00dfff'
  accentColor?: string; // e.g. '#ff7a16'
  backgroundColor?: string;
  amplitude?: number; // 0..1 audio energy
  speaking?: boolean;
  mode?: "booting" | "idle" | "listening" | "thinking" | "speaking";
  viseme?: VisemeShape;
  diagnosticPhase?: string;
}

// Synaptic neural cranial landmarks (MediaPipe canonical head indices)
const NEURAL_NODES = [10, 151, 168, 127, 356] as const;
const NEURAL_AXONS: readonly [number, number][] = [
  [127, 151],
  [151, 10],
  [151, 356],
  [151, 168],
];

export class HoloAvatarRenderer {
  private t = 0.0;
  private yaw = 0.0;
  private pitch = 0.0;
  private roll = 0.0; // Inquisitive head tilt on Z-axis
  private breathY = 0.0; // Organic 3D respiration cadence
  private mouth = 0.0;
  private wide = 0.0;
  private brow = 0.0;
  private glow = 0.0;
  private scan = -1.6;
  private scan2 = -1.6; // Secondary high-frequency holographic raster scan
  private blink = 0.0;
  private blinkAt = 3.0;

  private gaze = [0.0, 0.0];
  private gazeTarget = [0.0, 0.0];
  private gazeAt = 0.0;

  // Dynamic state color palette with smooth interpolation
  private curWireRGB = [70, 244, 255];
  private curFacetRGB = [0, 180, 220];
  private curBrow = "#29eafa";
  private curLip = "#44efff";
  private curAuraInner = "rgba(0, 223, 255, 0.22)";
  private curAuraMid = "rgba(0, 160, 200, 0.08)";
  private isSpeaking = false;
  private curMode: "booting" | "idle" | "listening" | "thinking" | "speaking" = "idle";

  // Pre-allocated buffers for vertices and projected points
  private posedVerts: Float32Array;
  private projX: Float32Array;
  private projY: Float32Array;
  private projZ: Float32Array;

  // Volumetric Holographic Energy Motes (Pre-allocated 3D particle field)
  private static readonly NUM_PARTICLES = 36;
  private particleX: Float32Array;
  private particleY: Float32Array;
  private particleZ: Float32Array;
  private particleSpeedY: Float32Array;
  private particlePhase: Float32Array;
  private particleSize: Float32Array;

  constructor() {
    const numVerts = HEAD_MESH.verts.length;
    this.posedVerts = new Float32Array(numVerts * 3);
    this.projX = new Float32Array(numVerts);
    this.projY = new Float32Array(numVerts);
    this.projZ = new Float32Array(numVerts);

    // Initialize floating volumetric particles around the head volume
    const n = HoloAvatarRenderer.NUM_PARTICLES;
    this.particleX = new Float32Array(n);
    this.particleY = new Float32Array(n);
    this.particleZ = new Float32Array(n);
    this.particleSpeedY = new Float32Array(n);
    this.particlePhase = new Float32Array(n);
    this.particleSize = new Float32Array(n);

    for (let i = 0; i < n; i++) {
      this.particleX[i] = (Math.sin(i * 1.7) * 0.95);
      this.particleY[i] = ((i / n) * 2.6 - 1.3);
      this.particleZ[i] = (Math.cos(i * 2.3) * 0.75);
      this.particleSpeedY[i] = 0.12 + (i % 5) * 0.04;
      this.particlePhase[i] = (i * 0.45);
      this.particleSize[i] = 1.0 + (i % 3) * 0.7;
    }
  }

  /**
   * Advance one simulation tick (dt in seconds).
   */
  public step(dt: number, options: RenderOptions = {}): void {
    const { amplitude = 0.0, speaking = false, mode = "idle", viseme, diagnosticPhase } = options;
    this.t += dt;
    this.curMode = mode;

    // Organic head sway: yaw, pitch, roll, and respiration cadence
    const isSpeakingMode = speaking || mode === "speaking";
    const isInDiagnostics = Boolean(diagnosticPhase && diagnosticPhase !== "idle") || mode === "booting";
    this.isSpeaking = isSpeakingMode;

    const swayAmp = mode === "thinking" ? 0.04 : isSpeakingMode ? 0.09 : isInDiagnostics ? 0.055 : 0.07;
    const swaySpeed = isSpeakingMode ? 0.65 : isInDiagnostics ? 0.38 : 0.45;

    // Subtle multi-harmonic micro-tremor eliminates rigid wireframe feel
    const microYaw = Math.sin(this.t * 3.7) * 0.004 + Math.sin(this.t * 8.1) * 0.002;
    const microPitch = Math.cos(this.t * 4.3) * 0.003;

    this.yaw = Math.sin(this.t * swaySpeed) * swayAmp + microYaw;
    this.pitch = Math.cos(this.t * (swaySpeed * 1.4)) * (swayAmp * 0.6) + microPitch;

    // Inquisitive head tilt (roll around Z)
    const targetRoll = mode === "thinking"
      ? -0.045 + Math.sin(this.t * 0.4) * 0.02
      : mode === "listening"
      ? 0.035 * Math.sin(this.t * 0.6)
      : isSpeakingMode
      ? Math.sin(this.t * 0.9) * 0.025
      : Math.sin(this.t * 0.35) * 0.015;
    this.roll += (targetRoll - this.roll) * 0.14;

    // Natural 3D respiration cadence (~0.22 Hz = 13 breaths/min human resting rhythm)
    const breathCadence = 1.38; // radians per sec
    const breathDepth = isSpeakingMode ? 0.012 : mode === "thinking" ? 0.018 : 0.014;
    this.breathY = Math.sin(this.t * breathCadence) * breathDepth;

    // Volumetric energy motes drift and wrap-around
    const n = HoloAvatarRenderer.NUM_PARTICLES;
    for (let i = 0; i < n; i++) {
      this.particleY[i] += this.particleSpeedY[i] * dt;
      // Gentle spiral drift
      this.particleX[i] += Math.sin(this.t * 0.8 + this.particlePhase[i]) * 0.02 * dt;
      this.particleZ[i] += Math.cos(this.t * 0.7 + this.particlePhase[i]) * 0.02 * dt;
      if (this.particleY[i] > 1.35) {
        this.particleY[i] = -1.35;
        this.particleX[i] = Math.sin(this.t + i * 2.1) * 0.9;
        this.particleZ[i] = Math.cos(this.t + i * 1.8) * 0.7;
      }
    }

    // Dynamic state palette targets matching classic JARVIS colors:
    // Responding/Speaking = Stark Amber/Orange (#ff7a16 / #ff6b00)
    // Listening = Cyber Neon Green (#00ff88)
    // Thinking = Radiant Gold/Yellow (#ffcc00)
    // Diagnostics AI Engine = Synaptic Gold/Amber
    // Diagnostics Completed = Verified Emerald Cyan
    // Idle/Booting = Arc Electric Cyan (#00d4ff)
    let targetWire = [70, 244, 255];
    let targetFacet = [0, 180, 220];
    let targetBrowCol = "#29eafa";
    let targetLipCol = "#44efff";
    let targetAuraInner = "rgba(0, 223, 255, 0.22)";
    let targetAuraMid = "rgba(0, 160, 200, 0.08)";

    if (isSpeakingMode) {
      targetWire = [255, 140, 25];          // Vibrant JARVIS Amber
      targetFacet = [240, 110, 15];         // Warm Orange facet depth
      targetBrowCol = "#ffaa22";            // Warm golden brow
      targetLipCol = this.mouth > 0.04 ? "#ff8c19" : "#ffa834";
      targetAuraInner = "rgba(255, 107, 0, 0.32)";
      targetAuraMid = "rgba(255, 150, 30, 0.12)";
    } else if (diagnosticPhase === "completed") {
      targetWire = [0, 255, 180];           // Verified Emerald Cyan
      targetFacet = [0, 200, 150];
      targetBrowCol = "#44ffcc";
      targetLipCol = "#33ffbb";
      targetAuraInner = "rgba(0, 255, 170, 0.30)";
      targetAuraMid = "rgba(0, 220, 150, 0.12)";
    } else if (diagnosticPhase === "ai") {
      targetWire = [255, 195, 45];          // Synaptic Gold for AI Engine
      targetFacet = [220, 150, 20];
      targetBrowCol = "#ffe066";
      targetLipCol = "#ffd13b";
      targetAuraInner = "rgba(255, 195, 45, 0.30)";
      targetAuraMid = "rgba(255, 160, 20, 0.10)";
    } else if (mode === "listening") {
      targetWire = [40, 255, 150];          // Cyber Neon Green
      targetFacet = [0, 210, 110];
      targetBrowCol = "#44ffaa";
      targetLipCol = "#33ff99";
      targetAuraInner = "rgba(0, 255, 136, 0.26)";
      targetAuraMid = "rgba(0, 210, 110, 0.10)";
    } else if (mode === "thinking") {
      targetWire = [255, 210, 40];          // Radiant Gold
      targetFacet = [230, 175, 20];
      targetBrowCol = "#ffe066";
      targetLipCol = "#ffd13b";
      targetAuraInner = "rgba(255, 204, 0, 0.28)";
      targetAuraMid = "rgba(255, 180, 0, 0.10)";
    }

    // Smooth color lerp across simulation ticks (prevents jarring color jumps)
    const colorRate = 0.16;
    for (let c = 0; c < 3; c++) {
      this.curWireRGB[c] += (targetWire[c] - this.curWireRGB[c]) * colorRate;
      this.curFacetRGB[c] += (targetFacet[c] - this.curFacetRGB[c]) * colorRate;
    }
    this.curBrow = targetBrowCol;
    this.curLip = targetLipCol;
    this.curAuraInner = targetAuraInner;
    this.curAuraMid = targetAuraMid;

    // Audio / speech mouth animation
    let targetMouth = 0.0;
    let targetWide = 0.0;
    if (isSpeakingMode && amplitude > 0.02) {
      if (viseme) {
        if (viseme.closure > 0.5) {
          // Closed bilabial sounds (m, b, p)
          targetMouth = 0.0;
          targetWide = viseme.wide;
        } else {
          targetMouth = Math.min(1.0, viseme.open * Math.max(0.35, amplitude * 1.6));
          targetWide = viseme.wide;
        }
      } else {
        targetMouth = Math.min(1.0, amplitude * 1.8);
      }
    } else {
      // Natural resting mouth when idle, listening, thinking, or silent
      targetMouth = 0.0;
      targetWide = 0.0;
    }

    const mouthRate = targetMouth > this.mouth ? 0.32 : 0.18;
    this.mouth += (targetMouth - this.mouth) * mouthRate;
    this.wide += (targetWide - this.wide) * 0.22;

    // Brow expression: raises subtly during speaking and accentuates words
    const targetBrowLift = isSpeakingMode && amplitude > 0.05
      ? 0.35 * amplitude
      : mode === "thinking"
      ? -0.22
      : mode === "listening"
      ? 0.12
      : 0.0;
    this.brow += (targetBrowLift - this.brow) * 0.12;

    // Glow / energy following speech intensity or diagnostic scanning
    const targetGlow = isSpeakingMode
      ? Math.max(0.15, amplitude * 1.2)
      : diagnosticPhase === "cpu_mem"
      ? 0.38 + Math.sin(this.t * 5.0) * 0.18
      : diagnosticPhase === "completed"
      ? 0.42
      : isInDiagnostics
      ? 0.22 + Math.sin(this.t * 2.8) * 0.10
      : mode === "thinking"
      ? 0.3
      : 0.0;
    this.glow += (targetGlow - this.glow) * 0.22;

    // Dual-frequency holographic scan lines
    this.scan += dt * (0.6 + 1.2 * this.glow);
    if (this.scan > 1.4) {
      this.scan = -1.6;
    }

    this.scan2 += dt * 1.85;
    if (this.scan2 > 1.4) {
      this.scan2 = -1.6;
    }

    // Blinking
    if (this.blink > 0.0) {
      this.blink = Math.max(0.0, this.blink - dt * 8.0);
    } else if (this.t >= this.blinkAt) {
      this.blink = 1.0;
      this.blinkAt = this.t + 3.0 + Math.random() * 3.5;
    }

    // Gaze saccades
    if (this.t >= this.gazeAt) {
      const reach = mode === "thinking" ? 0.35 : 0.65;
      this.gazeTarget = [(Math.random() * 2 - 1) * reach, (Math.random() * 2 - 1) * reach * 0.5];
      this.gazeAt = this.t + 1.5 + Math.random() * 2.0;
    }
    this.gaze[0] += (this.gazeTarget[0] - this.gaze[0]) * 0.15;
    this.gaze[1] += (this.gazeTarget[1] - this.gaze[1]) * 0.15;
  }

  /**
   * Apply 3D transformations: jaw, lips, brows, head rotation matrix (yaw/pitch/roll),
   * and organic respiration vertical elevation.
   */
  private pose(): void {
    const rawVerts = HEAD_MESH.verts;
    const jawWeights = HEAD_MESH.jaw;
    const browWeights = HEAD_MESH.brow;
    const lipWeights = HEAD_MESH.lips;
    const lipCenter = HEAD_MESH.lip_centre;
    const [, pivY, pivZ] = JAW_PIVOT;

    const cy = Math.cos(this.yaw);
    const sy = Math.sin(this.yaw);
    const cp = Math.cos(this.pitch);
    const sp = Math.sin(this.pitch);
    const cr = Math.cos(this.roll);
    const sr = Math.sin(this.roll);

    // Primary Head Rotation Matrix: R = Ryaw * Rpitch
    const m00 = cy;
    const m01 = 0.0;
    const m02 = sy;
    const m10 = sp * sy;
    const m11 = cp;
    const m12 = -sp * cy;
    const m20 = -cp * sy;
    const m21 = sp;
    const m22 = cp * cy;

    const numVerts = rawVerts.length;
    for (let i = 0; i < numVerts; i++) {
      let x = rawVerts[i][0];
      let y = rawVerts[i][1];
      let z = rawVerts[i][2];

      // 1. Brow lift
      if (Math.abs(this.brow) > 0.005) {
        y += browWeights[i] * (this.brow * BROW_LIFT);
      }

      // 2. Lip spread / rounding
      if (Math.abs(this.wide) > 0.01 && this.mouth > 0.01) {
        const k = lipWeights[i] * (this.wide * this.mouth);
        x += k * (x - lipCenter[0]) * 0.55;
        y += k * (y - lipCenter[1]) * 0.30;
        z -= k * 0.055;
      }

      // 3. Jaw drop rotation
      if (this.mouth > 0.005) {
        const ang = jawWeights[i] * (this.mouth * JAW_MAX);
        const ca = Math.cos(ang);
        const sa = Math.sin(ang);
        const dy = y - pivY;
        const dz = z - pivZ;
        y = pivY + dy * ca - dz * sa;
        z = pivZ + dy * sa + dz * ca;
      }

      // 4. Head rotation matrix (Yaw & Pitch)
      const rx = x * m00 + y * m01 + z * m02;
      const ry = x * m10 + y * m11 + z * m12;
      const rz = x * m20 + y * m21 + z * m22;

      // 5. Inquisitive Head Roll (Z-axis) & Organic Respiration Translation (Y-axis)
      const finalX = rx * cr - ry * sr;
      const finalY = rx * sr + ry * cr + this.breathY;
      const finalZ = rz;

      this.posedVerts[i * 3] = finalX;
      this.posedVerts[i * 3 + 1] = finalY;
      this.posedVerts[i * 3 + 2] = finalZ;
    }
  }

  /**
   * Project 3D vertices to 2D canvas coordinates.
   */
  private project(cx: number, cy: number, scaleRadius: number): void {
    const numVerts = HEAD_MESH.verts.length;
    for (let i = 0; i < numVerts; i++) {
      const x = this.posedVerts[i * 3];
      const y = this.posedVerts[i * 3 + 1];
      const z = this.posedVerts[i * 3 + 2];

      const w = Math.max(0.35, CAM_D - z);
      const k = (CAM_D / w) * scaleRadius;

      this.projX[i] = cx + x * k;
      this.projY[i] = cy - y * k;
      this.projZ[i] = z;
    }
  }

  /**
   * Render the 3D head mesh onto the HTML5 Canvas 2D context.
   */
  public render(
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number,
    options: RenderOptions = {},
  ): void {
    if (!ctx || width <= 0 || height <= 0) return;

    const {
      primaryColor = "#00dfff",
      accentColor = "#ff7a16",
    } = options;

    ctx.clearRect(0, 0, width, height);

    const cx = width / 2;
    const cy = height / 2;
    const scaleRadius = Math.min(width, height) * 0.42;

    // 1. Aura glow background (adapts smoothly to state colors)
    const auraRadius = scaleRadius * 1.6;
    const aura = ctx.createRadialGradient(cx, cy, scaleRadius * 0.1, cx, cy, auraRadius);
    aura.addColorStop(0, this.curAuraInner);
    aura.addColorStop(0.5, this.curAuraMid);
    aura.addColorStop(1, "rgba(0, 10, 25, 0)");

    ctx.fillStyle = aura;
    ctx.beginPath();
    ctx.arc(cx, cy, auraRadius, 0, Math.PI * 2);
    ctx.fill();

    // 2. Pose & Project 3D Mesh
    this.pose();
    this.project(cx, cy, scaleRadius);

    // 3. Volumetric Holographic Atmosphere (Floating Energy Motes)
    this.renderAtmosphere(ctx, cx, cy, scaleRadius);

    // 4. Render Shaded Facets (Depth sorted)
    this.renderShadedFacets(ctx);

    // 5. Render Wireframe Edges with Dual Scanlines
    this.renderWireframe(ctx);

    // 6. Render Synaptic Neural Nodes (Cognition Pulse)
    this.renderNeuralNodes(ctx, scaleRadius);

    // 7. Render Eyes & Eyebrows with Cybernetic Optic Rings
    this.renderFeatures(ctx, cx, cy, scaleRadius, primaryColor, accentColor);
  }

  /**
   * Render volumetric holographic floating motes / data dust.
   */
  private renderAtmosphere(
    ctx: CanvasRenderingContext2D,
    cx: number,
    cy: number,
    scaleRadius: number,
  ): void {
    const n = HoloAvatarRenderer.NUM_PARTICLES;
    const [wr, wg, wb] = this.curWireRGB.map(Math.round);

    for (let i = 0; i < n; i++) {
      const z = this.particleZ[i];
      const w = Math.max(0.35, CAM_D - z);
      const k = (CAM_D / w) * scaleRadius;

      const px = cx + this.particleX[i] * k;
      const py = cy - this.particleY[i] * k;
      const radius = Math.max(0.7, (this.particleSize[i] * (CAM_D / w)) * 0.85);

      // Depth attenuation & vertical boundary fade
      const yFade = 1.0 - Math.pow(Math.abs(this.particleY[i]) / 1.35, 2);
      const depthAlpha = Math.max(0.05, Math.min(0.65, (0.28 + z * 0.15) * yFade * (0.8 + 0.3 * this.glow)));

      ctx.fillStyle = `rgba(${wr}, ${wg}, ${wb}, ${depthAlpha.toFixed(3)})`;
      ctx.beginPath();
      ctx.arc(px, py, radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  private renderShadedFacets(ctx: CanvasRenderingContext2D): void {
    const faces = HEAD_MESH.faces;
    const fade = HEAD_MESH.fade;
    const numFaces = faces.length;

    // Filter and collect visible front-facing facets
    interface Facet {
      a: number;
      b: number;
      c: number;
      depth: number;
      bright: number;
    }
    const visibleFacets: Facet[] = [];

    for (let f = 0; f < numFaces; f++) {
      const [a, b, c] = faces[f];

      const ax = this.projX[a];
      const ay = this.projY[a];
      const bx = this.projX[b];
      const by = this.projY[b];
      const cxx = this.projX[c];
      const cyy = this.projY[c];

      // Signed 2D area (cross product) for back-face culling
      const area = (bx - ax) * (cyy - ay) - (cxx - ax) * (by - ay);
      if (area <= 2.0) continue;

      // Normal vector approximation
      const vax = this.posedVerts[a * 3];
      const vay = this.posedVerts[a * 3 + 1];
      const vaz = this.posedVerts[a * 3 + 2];
      const vbx = this.posedVerts[b * 3];
      const vby = this.posedVerts[b * 3 + 1];
      const vbz = this.posedVerts[b * 3 + 2];
      const vcx = this.posedVerts[c * 3];
      const vcy = this.posedVerts[c * 3 + 1];
      const vcz = this.posedVerts[c * 3 + 2];

      const abx = vbx - vax;
      const aby = vby - vay;
      const abz = vbz - vaz;
      const acx = vcx - vax;
      const acy = vcy - vay;
      const acz = vcz - vaz;

      let nx = aby * acz - abz * acy;
      let ny = abz * acx - abx * acz;
      let nz = abx * acy - aby * acx;
      const len = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1e-6;
      nx /= len;
      ny /= len;
      nz /= len;

      if (nz <= 0.01) continue;

      // Lambertian key light (-0.55, 0.50, 0.52) + Fresnel
      const lam = Math.max(0, -nx * 0.55 + ny * 0.50 + nz * 0.52);
      const fres = Math.pow(Math.max(0, 1.0 - nz), 1.6);
      let bright = 0.22 + 0.18 * fres + 0.60 * Math.pow(lam, 1.1);
      bright *= (fade[a] + fade[b] + fade[c]) / 3.0;
      bright *= 0.85 + 0.25 * this.glow;

      const depth = (this.projZ[a] + this.projZ[b] + this.projZ[c]) / 3.0;
      visibleFacets.push({ a, b, c, depth, bright });
    }

    // Sort far to near
    visibleFacets.sort((f1, f2) => f1.depth - f2.depth);

    const [fr, fg, fb] = this.curFacetRGB.map(Math.round);

    // Draw facets
    for (let i = 0; i < visibleFacets.length; i++) {
      const facet = visibleFacets[i];
      const alpha = Math.max(0.04, Math.min(0.55, facet.bright * 0.45));
      ctx.fillStyle = `rgba(${fr}, ${fg}, ${fb}, ${alpha.toFixed(3)})`;

      ctx.beginPath();
      ctx.moveTo(this.projX[facet.a], this.projY[facet.a]);
      ctx.lineTo(this.projX[facet.b], this.projY[facet.b]);
      ctx.lineTo(this.projX[facet.c], this.projY[facet.c]);
      ctx.closePath();
      ctx.fill();
    }
  }

  private renderWireframe(ctx: CanvasRenderingContext2D): void {
    const edges = HEAD_MESH.edges;
    const fade = HEAD_MESH.fade;
    const numEdges = edges.length;

    ctx.lineWidth = 1.0;
    const [wr, wg, wb] = this.curWireRGB.map(Math.round);

    for (let i = 0; i < numEdges; i++) {
      const [u, v] = edges[i];
      const uz = this.posedVerts[u * 3 + 2];
      const vz = this.posedVerts[v * 3 + 2];
      if (uz < -0.15 && vz < -0.15) continue; // cull far-back edges

      const avgFade = (fade[u] + fade[v]) / 2.0;
      const uy = this.posedVerts[u * 3 + 1];

      // Dual-frequency scanline glow
      const scanDist1 = Math.abs(uy - this.scan);
      const scanGlow1 = Math.exp(-Math.pow(scanDist1 / 0.16, 2)) * 0.38;
      const scanDist2 = Math.abs(uy - this.scan2);
      const scanGlow2 = Math.exp(-Math.pow(scanDist2 / 0.08, 2)) * 0.18;
      const wirePulse = Math.sin(this.t * 3.5) * 0.08;

      const alpha = Math.min(0.92, (0.16 + scanGlow1 + scanGlow2 + wirePulse) * avgFade * (0.85 + 0.35 * this.glow));
      if (alpha < 0.05) continue;

      ctx.strokeStyle = `rgba(${wr}, ${wg}, ${wb}, ${alpha.toFixed(3)})`;
      ctx.beginPath();
      ctx.moveTo(this.projX[u], this.projY[u]);
      ctx.lineTo(this.projX[v], this.projY[v]);
      ctx.stroke();
    }
  }

  /**
   * Render synaptic neural cranial nodes & axons (visualize AI cognition).
   */
  private renderNeuralNodes(ctx: CanvasRenderingContext2D, scaleRadius: number): void {
    const isThinking = this.curMode === "thinking";
    const [wr, wg, wb] = this.curWireRGB.map(Math.round);

    // 1. Synaptic axon lines connecting forehead and temples
    ctx.lineWidth = 0.8;
    for (let i = 0; i < NEURAL_AXONS.length; i++) {
      const [u, v] = NEURAL_AXONS[i];
      const uz = this.posedVerts[u * 3 + 2];
      const vz = this.posedVerts[v * 3 + 2];
      if (uz < -0.1 || vz < -0.1) continue;

      // Pulse traveling along the axon
      const axonPulse = isThinking
        ? Math.sin(this.t * 6.0 + i * 0.8) * 0.35 + 0.45
        : 0.12;

      ctx.strokeStyle = `rgba(${wr}, ${wg}, ${wb}, ${axonPulse.toFixed(2)})`;
      ctx.beginPath();
      ctx.moveTo(this.projX[u], this.projY[u]);
      ctx.lineTo(this.projX[v], this.projY[v]);
      ctx.stroke();
    }

    // 2. Synaptic node hubs
    const nodeBaseRadius = scaleRadius * 0.007;
    for (let i = 0; i < NEURAL_NODES.length; i++) {
      const idx = NEURAL_NODES[i];
      const z = this.posedVerts[idx * 3 + 2];
      if (z < -0.1) continue;

      const px = this.projX[idx];
      const py = this.projY[idx];

      const nodePulse = isThinking
        ? 0.5 + Math.sin(this.t * 5.0 + i * 1.2) * 0.45
        : 0.15;

      const r = Math.max(1.0, nodeBaseRadius * (1.0 + nodePulse * 0.5));

      // Luminous node glow
      ctx.fillStyle = `rgba(${wr}, ${wg}, ${wb}, ${nodePulse.toFixed(2)})`;
      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fill();

      // Outer halo ring ONLY for active thinking cranial hubs
      if (isThinking && nodePulse > 0.6) {
        ctx.strokeStyle = `rgba(255, 255, 255, ${(nodePulse * 0.6).toFixed(2)})`;
        ctx.lineWidth = 0.7;
        ctx.beginPath();
        ctx.arc(px, py, r * 1.6, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
  }

  private renderFeatures(
    ctx: CanvasRenderingContext2D,
    _cx: number,
    _cy: number,
    scaleRadius: number,
    _primaryColor: string,
    accentColor: string,
  ): void {
    const lm = HEAD_MESH.landmarks;

    // Eyebrows: dynamic stroke weight responding to vocal inflection
    ctx.lineWidth = 2.0 + Math.abs(this.brow) * 1.5;
    ctx.strokeStyle = this.curBrow;
    for (const browKey of ["brow_l", "brow_r"]) {
      const ring = lm[browKey];
      if (!ring || ring.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(this.projX[ring[0]], this.projY[ring[0]]);
      for (let i = 1; i < ring.length; i++) {
        ctx.lineTo(this.projX[ring[i]], this.projY[ring[i]]);
      }
      ctx.stroke();
    }

    // Eyes: Cybernetic Optic Rings, Pupils, Dilation & Specular Glint
    const eyeOpen = 1.0 - this.blink;
    if (eyeOpen > 0.08) {
      for (const eyeKey of ["eye_l", "eye_r"]) {
        const ring = lm[eyeKey];
        if (!ring || ring.length < 4) continue;

        // Eye center
        let ecx = 0;
        let ecy = 0;
        for (let i = 0; i < ring.length; i++) {
          ecx += this.projX[ring[i]];
          ecy += this.projY[ring[i]];
        }
        ecx /= ring.length;
        ecy /= ring.length;

        // Gaze offset & natural top-down eyelid biomechanics
        const gx = ecx + this.gaze[0] * (scaleRadius * 0.035);
        const lidOffset = (1.0 - eyeOpen) * (scaleRadius * 0.010);
        const gy = ecy + this.gaze[1] * (scaleRadius * 0.02) + lidOffset;

        const irisRx = Math.max(2, scaleRadius * 0.036);
        const irisRy = Math.max(1, scaleRadius * 0.030 * eyeOpen);

        // 1. Concentric Cybernetic Optic Ring (Reticle aperture)
        ctx.strokeStyle = this.curBrow;
        ctx.lineWidth = 0.9;
        ctx.beginPath();
        ctx.ellipse(gx, gy, irisRx * 1.25, irisRy * 1.25, 0, 0, Math.PI * 2);
        ctx.stroke();

        // 2. Dynamic Pupil Dilation
        const dilation = this.curMode === "thinking"
          ? 0.65
          : this.isSpeaking
          ? 0.52 + this.glow * 0.18
          : 0.48;
        const pupilRx = Math.max(1, irisRx * dilation);
        const pupilRy = Math.max(1, irisRy * dilation);

        // Pupil glow - warm golden amber when speaking
        ctx.fillStyle = this.isSpeaking ? "#ffd580" : (accentColor || "#ff7a16");
        ctx.beginPath();
        ctx.ellipse(gx, gy, pupilRx, pupilRy, 0, 0, Math.PI * 2);
        ctx.fill();

        // 3. Corneal Specular Glint (Brings the gaze to life)
        const glintX = gx - irisRx * 0.32;
        const glintY = gy - irisRy * 0.32;
        const glintR = Math.max(0.9, scaleRadius * 0.008 * eyeOpen);
        ctx.fillStyle = "rgba(255, 255, 255, 0.92)";
        ctx.beginPath();
        ctx.arc(glintX, glintY, glintR, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Lips Outer Contour
    const lipsOut = lm["lips_out"];
    if (lipsOut && lipsOut.length > 3) {
      ctx.lineWidth = 1.6 + 0.5 * this.mouth;
      ctx.strokeStyle = this.curLip;
      ctx.beginPath();
      ctx.moveTo(this.projX[lipsOut[0]], this.projY[lipsOut[0]]);
      for (let i = 1; i < lipsOut.length; i++) {
        ctx.lineTo(this.projX[lipsOut[i]], this.projY[lipsOut[i]]);
      }
      ctx.closePath();
      ctx.stroke();
    }

    // Lips Inner Contour & Articulated Oral Cavity
    const lipsIn = lm["lips_in"];
    if (lipsIn && lipsIn.length > 3 && this.mouth > 0.02) {
      ctx.beginPath();
      ctx.moveTo(this.projX[lipsIn[0]], this.projY[lipsIn[0]]);
      for (let i = 1; i < lipsIn.length; i++) {
        ctx.lineTo(this.projX[lipsIn[i]], this.projY[lipsIn[i]]);
      }
      ctx.closePath();

      // Translucent volumetric oral cavity shading
      const mouthAlpha = Math.min(0.35, this.mouth * 0.5);
      ctx.fillStyle = `rgba(0, 16, 28, ${mouthAlpha.toFixed(2)})`;
      ctx.fill();

      // Inner lip glowing perimeter
      ctx.lineWidth = 0.9;
      ctx.strokeStyle = this.isSpeaking
        ? `rgba(255, 160, 45, ${(mouthAlpha * 0.75).toFixed(2)})`
        : `rgba(0, 217, 255, ${(mouthAlpha * 0.5).toFixed(2)})`;
      ctx.stroke();
    }
  }
}
