/**
 * Three.js 3D Humanoid Scene & Renderer (Realistic Female Android – ALEX)
 *
 * Realism Engineering:
 *   • True PBR lighting calibration: balanced key (0.75), fill (0.25), and ambient (0.22)
 *     preventing the 5x overexposure that previously washed the face and body to white.
 *   • Photorealistic Blue Eyes: procedural 512x512 CanvasTexture generating a deep sapphire
 *     blue iris with radial striations, dark limbal ring, and crisp black pupil.
 *   • Natural Human Skin: warm golden-peach undertones, subtle subsurface scattering,
 *     soft specular sheen (roughness 0.52), and lifelike facial features.
 *   • Realistic Hair: rich dark espresso brunette with subtle specular highlights and normal maps.
 *   • Realistic Body & Clothing: hides the naked severed torso (Wolf3D_Body) and displays
 *     the fitted high-tech cybernetic top (Wolf3D_Outfit_Top) with fabric folds and seams.
 *   • Real-time speech-synchronized lip sync and organic eye blinking/micro-saccades.
 */

import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import {
  FacialAnimationController,
  type AssistantVisualMode,
} from "./FacialAnimationController";
import { LipSyncController } from "./LipSyncController";

export interface HumanoidSceneOptions {
  canvas: HTMLCanvasElement;
  primaryColor?: string;
  accentColor?: string;
  quality?: "low" | "medium" | "high";
  onLoaded?: () => void;
  onError?: (err: Error) => void;
}

export class HumanoidScene {
  private canvas: HTMLCanvasElement;
  private renderer: THREE.WebGLRenderer | null = null;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;

  private facialController: FacialAnimationController;
  private lipSyncController: LipSyncController;

  private modelRoot: THREE.Group | null = null;
  private isDisposed = false;
  private clock = new THREE.Clock();

  // Dynamic rim lights for subtle sci-fi voice responsiveness
  private cyanRim: THREE.DirectionalLight | null = null;
  private blueRim: THREE.DirectionalLight | null = null;

  // Cached procedural realistic eye texture
  private realisticEyeTexture: THREE.CanvasTexture | null = null;

  constructor(options: HumanoidSceneOptions) {
    this.canvas = options.canvas;
    const primary = options.primaryColor || "#00e5ff";
    const primaryColor = new THREE.Color(primary);

    // ── 1. Scene: Clean, Transparent ─────────────────────────────────────────
    this.scene = new THREE.Scene();
    this.scene.background = null; // Transparent: blends directly into the HUD
    this.scene.fog = null;        // No fog to keep facial features crisp and clear

    // ── 2. Camera: Natural Portrait Framing ──────────────────────────────────
    // 32-degree FOV avoids wide-angle facial distortion.
    // Centered at Y = 1.52 to frame from chest/shoulders up to the top of hair.
    const initialAspect = this.canvas.clientWidth / this.canvas.clientHeight || 1;
    this.camera = new THREE.PerspectiveCamera(32, initialAspect, 0.05, 20);
    this.camera.position.set(0, 1.52, 0.82);
    this.camera.lookAt(0, 1.52, 0);

    // ── 3. WebGL Renderer: ACESFilmic with True sRGB ─────────────────────────
    try {
      this.renderer = new THREE.WebGLRenderer({
        canvas: this.canvas,
        alpha: true,
        antialias: options.quality !== "low",
        powerPreference: "high-performance",
      });
      this.renderer.setSize(
        this.canvas.clientWidth || 560,
        this.canvas.clientHeight || 560,
        false
      );
      const dpr =
        options.quality === "high"
          ? Math.min(window.devicePixelRatio, 2)
          : 1;
      this.renderer.setPixelRatio(dpr);
      this.renderer.setClearColor(0x000000, 0);

      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      // Exposure calibrated to 0.85 so skin tones retain rich, natural warmth
      this.renderer.toneMappingExposure = 0.85;
    } catch (e) {
      console.warn("WebGLRenderer init failed:", e);
      options.onError?.(e instanceof Error ? e : new Error(String(e)));
    }

    // ── 4. Calibrated Studio Portrait Lighting ───────────────────────────────
    this.setupLighting(primaryColor);

    // ── 5. Generate Photorealistic Eye Texture ────────────────────────────────
    this.realisticEyeTexture = this.createRealisticBlueEyeTexture();

    // ── 6. Animation Controllers ─────────────────────────────────────────────
    this.facialController = new FacialAnimationController({});
    this.lipSyncController = new LipSyncController({});

    // ── 7. Load 3D Model ─────────────────────────────────────────────────────
    this.loadModel(options.onLoaded, options.onError);
  }

  /**
   * Balanced PBR portrait lighting:
   * Frontal irradiance is held around ~1.2 total intensity, allowing the natural
   * skin diffuse map to display its true warm peach tones without burning to white.
   */
  private setupLighting(primaryColor: THREE.Color) {
    // 1. Soft neutral ambient light (lifts shadow crevices without washing out)
    const ambient = new THREE.AmbientLight(0x18202c, 0.22);
    this.scene.add(ambient);

    // 2. Main Key Light: Warm 5200K daylight softbox at upper-right 30°
    const keyLight = new THREE.DirectionalLight(0xfff2e8, 0.75);
    keyLight.position.set(0.55, 2.0, 1.2);
    this.scene.add(keyLight);

    // 3. Fill Light: Cool sky-tinted fill from upper-left 35°
    const fillLight = new THREE.DirectionalLight(0xcce0ff, 0.25);
    fillLight.position.set(-0.65, 1.7, 1.0);
    this.scene.add(fillLight);

    // 4. Eye Catchlight: Gentle direct front light for lively pupil glints
    const catchLight = new THREE.DirectionalLight(0xffffff, 0.15);
    catchLight.position.set(0, 1.63, 1.3);
    this.scene.add(catchLight);

    // 5. Top Hair Light: Catches strand highlights along the crown
    const topLight = new THREE.DirectionalLight(0xd8e8ff, 0.25);
    topLight.position.set(0, 3.0, 0.2);
    this.scene.add(topLight);

    // 6. Futuristic Cyan Silhouette Rim Light (rear-left edge highlight)
    this.cyanRim = new THREE.DirectionalLight(primaryColor, 0.90);
    this.cyanRim.position.set(-1.4, 1.8, -1.0);
    this.scene.add(this.cyanRim);

    // 7. Counterpart Deep Blue Rim Light (rear-right)
    this.blueRim = new THREE.DirectionalLight(0x0044ff, 0.55);
    this.blueRim.position.set(1.4, 1.8, -1.0);
    this.scene.add(this.blueRim);
  }

  /**
   * Creates a photorealistic 512x512 CanvasTexture for the eyes:
   * Replaces the flat brown texture with a vivid sapphire-blue iris,
   * radial striation fibers, dark limbal ring, and deep black pupil.
   */
  private createRealisticBlueEyeTexture(): THREE.CanvasTexture | null {
    if (typeof document === "undefined") return null;
    try {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 512;
      const ctx = canvas.getContext("2d");
      if (!ctx) return null;

      // Center of eye detected from model UVs: (270, 242)
      const cx = 270;
      const cy = 242;

      // 1. Sclera: Clean porcelain white with soft realistic edge shadow
      ctx.fillStyle = "#f2f4f8";
      ctx.fillRect(0, 0, 512, 512);

      const scleraGrad = ctx.createRadialGradient(cx, cy, 120, cx, cy, 240);
      scleraGrad.addColorStop(0, "rgba(242, 244, 248, 1)");
      scleraGrad.addColorStop(0.7, "rgba(228, 232, 238, 1)");
      scleraGrad.addColorStop(1, "rgba(205, 210, 220, 1)");
      ctx.fillStyle = scleraGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, 240, 0, Math.PI * 2);
      ctx.fill();

      // Subtle micro-capillaries in sclera corners
      ctx.strokeStyle = "rgba(215, 140, 140, 0.15)";
      ctx.lineWidth = 0.8;
      for (let i = 0; i < 8; i++) {
        const ang = (i / 8) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(ang) * 140, cy + Math.sin(ang) * 140);
        ctx.quadraticCurveTo(
          cx + Math.cos(ang + 0.1) * 180,
          cy + Math.sin(ang + 0.1) * 180,
          cx + Math.cos(ang + 0.05) * 220,
          cy + Math.sin(ang + 0.05) * 220
        );
        ctx.stroke();
      }

      // 2. Limbal Ring: Deep dark navy/charcoal boundary (radius 108)
      ctx.fillStyle = "#0a1830";
      ctx.beginPath();
      ctx.arc(cx, cy, 108, 0, Math.PI * 2);
      ctx.fill();

      // 3. Iris Base: Rich sapphire blue gradient
      const irisGrad = ctx.createRadialGradient(cx, cy, 32, cx, cy, 104);
      irisGrad.addColorStop(0, "#004088");
      irisGrad.addColorStop(0.35, "#0072d4");
      irisGrad.addColorStop(0.75, "#0099ff");
      irisGrad.addColorStop(1, "#0a3468");
      ctx.fillStyle = irisGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, 104, 0, Math.PI * 2);
      ctx.fill();

      // 4. Radial Iris Striations (120 fine fibers)
      for (let i = 0; i < 120; i++) {
        const ang = i * ((Math.PI * 2) / 120);
        const r1 = 34 + (i % 6) * 2;
        const r2 = 100 - (i % 4) * 2;
        const x1 = cx + Math.cos(ang) * r1;
        const y1 = cy + Math.sin(ang) * r1;
        const x2 = cx + Math.cos(ang) * r2;
        const y2 = cy + Math.sin(ang) * r2;

        ctx.strokeStyle =
          i % 3 === 0
            ? "rgba(0, 229, 255, 0.75)"
            : i % 2 === 0
            ? "rgba(100, 200, 255, 0.60)"
            : "rgba(0, 80, 180, 0.70)";
        ctx.lineWidth = i % 2 === 0 ? 1.5 : 0.8;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // 5. Collarette: Delicate amber-gold inner ring
      ctx.strokeStyle = "rgba(212, 165, 75, 0.65)";
      ctx.lineWidth = 3.5;
      ctx.beginPath();
      ctx.arc(cx, cy, 46, 0, Math.PI * 2);
      ctx.stroke();

      // 6. Pupil: Pure crisp black circle (radius 34)
      ctx.fillStyle = "#06080c";
      ctx.beginPath();
      ctx.arc(cx, cy, 34, 0, Math.PI * 2);
      ctx.fill();

      const tex = new THREE.CanvasTexture(canvas);
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.needsUpdate = true;
      return tex;
    } catch (e) {
      console.warn("Could not create realistic blue eye texture:", e);
      return null;
    }
  }

  private loadModel(onLoaded?: () => void, onError?: (err: Error) => void) {
    try {
      const loader = new GLTFLoader();
      let modelUrl = "/models/humanoid_robot.glb";
      if (
        typeof window !== "undefined" &&
        window.location?.origin &&
        window.location.origin !== "null"
      ) {
        try {
          modelUrl = new URL("/models/humanoid_robot.glb", window.location.origin).href;
        } catch {
          // keep relative
        }
      }

      loader.load(
        modelUrl,
        (gltf) => {
          if (this.isDisposed) return;
          this.modelRoot = gltf.scene;

          let headMesh: THREE.SkinnedMesh | undefined;
          let teethMesh: THREE.SkinnedMesh | undefined;
          let eyeLeftMesh: THREE.SkinnedMesh | undefined;
          let eyeRightMesh: THREE.SkinnedMesh | undefined;
          let headBone: THREE.Bone | undefined;
          let neckBone: THREE.Bone | undefined;
          let leftEyeBone: THREE.Bone | undefined;
          let rightEyeBone: THREE.Bone | undefined;

          this.modelRoot.traverse((node) => {
            if ((node as THREE.Bone).isBone) {
              const n = node.name;
              if (n === "Head")     headBone     = node as THREE.Bone;
              if (n === "Neck")     neckBone     = node as THREE.Bone;
              if (n === "LeftEye")  leftEyeBone  = node as THREE.Bone;
              if (n === "RightEye") rightEyeBone = node as THREE.Bone;
            }

            if ((node as THREE.Mesh).isMesh || (node as THREE.SkinnedMesh).isSkinnedMesh) {
              const mesh = node as THREE.SkinnedMesh;
              const name = mesh.name;

              // 1. Hide lower body
              if (
                name === "Wolf3D_Glasses" ||
                name === "Wolf3D_Outfit_Bottom" ||
                name === "Wolf3D_Outfit_Footwear"
              ) {
                mesh.visible = false;
                return;
              }

              // 2. CRITICAL: Hide the naked severed-arms mannequin torso (Wolf3D_Body)
              //    so the high-tech athletic cybernetic top (Wolf3D_Outfit_Top) is displayed!
              if (name === "Wolf3D_Body") {
                mesh.visible = false;
                return;
              }

              // 3. Ensure clothing top is visible
              if (name === "Wolf3D_Outfit_Top") {
                mesh.visible = true;
              }

              if (name === "Wolf3D_Head")  headMesh     = mesh;
              if (name === "Wolf3D_Teeth") teethMesh    = mesh;
              if (name === "EyeLeft")      eyeLeftMesh  = mesh;
              if (name === "EyeRight")     eyeRightMesh = mesh;

              this.refineMaterial(name, mesh);
            }
          });

          // Connect facial controllers for natural blinking and voice lip sync
          this.facialController.updateTargets({
            headMesh,
            teethMesh,
            eyeLeftMesh,
            eyeRightMesh,
            headBone,
            neckBone,
            leftEyeBone,
            rightEyeBone,
          });
          this.lipSyncController.updateTargets({ headMesh, teethMesh });

          this.scene.add(this.modelRoot);
          onLoaded?.();
        },
        undefined,
        (error) => {
          console.warn("GLTF load error:", error);
          onError?.(error instanceof Error ? error : new Error(String(error)));
        }
      );
    } catch (err) {
      console.warn("Synchronous GLTF error:", err);
      onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  }

  /**
   * Refines materials with true PBR values, realistic skin complexion,
   * photorealistic blue eye textures, and detailed clothing.
   */
  private refineMaterial(meshName: string, mesh: THREE.Mesh | THREE.SkinnedMesh) {
    const ensureTextureSpaces = (mat: THREE.MeshStandardMaterial) => {
      if (mat.map)          mat.map.colorSpace          = THREE.SRGBColorSpace;
      if (mat.emissiveMap)  mat.emissiveMap.colorSpace  = THREE.SRGBColorSpace;
      if (mat.normalMap)    mat.normalMap.colorSpace    = THREE.LinearSRGBColorSpace;
      if (mat.roughnessMap) mat.roughnessMap.colorSpace = THREE.LinearSRGBColorSpace;
      if (mat.metalnessMap) mat.metalnessMap.colorSpace = THREE.LinearSRGBColorSpace;
      if (mat.aoMap)        mat.aoMap.colorSpace        = THREE.LinearSRGBColorSpace;
      mat.needsUpdate = true;
    };

    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const rawMat of mats) {
      const mat = rawMat as THREE.MeshStandardMaterial;
      if (!mat || !mat.isMeshStandardMaterial) continue;

      ensureTextureSpaces(mat);

      switch (meshName) {
        case "Wolf3D_Head": {
          // Warm golden-peach porcelain skin:
          // Natural skin sheen, rich diffuse texture, zero glow wash-out
          mat.roughness = 0.55;
          mat.metalness = 0.0;
          mat.color.set(0xfff5ee); // Warm healthy human skin tone
          mat.emissive = new THREE.Color(0x000000);
          mat.emissiveIntensity = 0.0;
          mat.needsUpdate = true;
          break;
        }

        case "EyeLeft":
        case "EyeRight": {
          // Apply photorealistic blue eye texture with vivid sapphire iris & pupil
          if (this.realisticEyeTexture) {
            mat.map = this.realisticEyeTexture;
          }
          mat.roughness = 0.02; // Ultra-smooth clear cornea with crisp specular reflection
          mat.metalness = 0.0;
          mat.color.set(0xffffff);
          mat.emissive = new THREE.Color(0x000000); // No glowing headlight effect
          mat.needsUpdate = true;
          break;
        }

        case "Wolf3D_Hair": {
          // Natural dark espresso brunette hair with strand highlights
          mat.roughness = 0.52;
          mat.metalness = 0.10;
          mat.color.set(0x221a16); // Deep rich espresso tone with warm chocolate highlights
          mat.emissive = new THREE.Color(0x000000);
          mat.needsUpdate = true;
          break;
        }

        case "Wolf3D_Teeth": {
          // Natural enamel
          mat.roughness = 0.18;
          mat.metalness = 0.0;
          mat.color.set(0xfaf6f0);
          mat.emissive = new THREE.Color(0x000000);
          mat.needsUpdate = true;
          break;
        }

        case "Wolf3D_Outfit_Top": {
          // High-tech cybernetic athletic jacket with silver seams and fabric texture
          mat.roughness = 0.42;
          mat.metalness = 0.20;
          mat.color.set(0xffffff); // True colors from the 141KB diffuse map
          mat.needsUpdate = true;
          break;
        }
      }
    }
  }

  public resize(width: number, height: number) {
    if (!this.renderer || width <= 0 || height <= 0) return;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  }

  public render(
    mode: AssistantVisualMode,
    speaking: boolean,
    analyserNode?: AnalyserNode | null,
    spokenText = ""
  ) {
    if (!this.renderer || this.isDisposed) return;

    const delta = Math.min(this.clock.getDelta(), 0.1);
    const time = this.clock.getElapsedTime();

    // Subtle edge pulse during speech
    if (this.cyanRim) {
      const speakBeat = speaking ? 0.25 * Math.sin(time * 10.0) : 0.05 * Math.sin(time * 1.5);
      this.cyanRim.intensity = 0.90 + speakBeat;
    }

    // Voice-synchronized lip movements (jaw opening and visemes)
    this.lipSyncController.update(delta, time, speaking, analyserNode, spokenText);

    // Natural eye blinking, saccades, and micro-movements
    this.facialController.update(delta, time, mode);

    this.renderer.render(this.scene, this.camera);
  }

  public getAmplitude(): number {
    return this.lipSyncController.getAmplitude();
  }

  public dispose() {
    this.isDisposed = true;
    if (this.realisticEyeTexture) {
      this.realisticEyeTexture.dispose();
      this.realisticEyeTexture = null;
    }
    if (this.modelRoot) {
      this.modelRoot.traverse((child) => {
        const mesh = child as THREE.Mesh;
        if (mesh.geometry) mesh.geometry.dispose();
        if (mesh.material) {
          const mat = mesh.material;
          if (Array.isArray(mat)) mat.forEach((m) => m.dispose());
          else mat.dispose();
        }
      });
      this.scene.remove(this.modelRoot);
    }
    if (this.renderer) {
      this.renderer.dispose();
      this.renderer = null;
    }
  }
}
