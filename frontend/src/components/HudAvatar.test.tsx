import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HudAvatar } from "./HudAvatar";
import { HoloAvatarRenderer } from "./avatar/avatarRenderer";
import { HEAD_MESH, JAW_MAX, JAW_PIVOT } from "./avatar/meshData";
import { CANONICAL_VISEMES, VisemeAnalyzer } from "./avatar/visemeAnalyzer";

describe("HudAvatar & 3D Face Mesh", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(cleanup);

  it("verifies 3D head mesh data integrity", () => {
    expect(HEAD_MESH.verts.length).toBe(810);
    expect(HEAD_MESH.faces.length).toBe(1554);
    expect(HEAD_MESH.edges.length).toBe(788);
    expect(HEAD_MESH.jaw.length).toBe(810);
    expect(HEAD_MESH.fade.length).toBe(810);

    // Verify key landmark rings exist
    expect(HEAD_MESH.landmarks.eye_l.length).toBeGreaterThan(5);
    expect(HEAD_MESH.landmarks.eye_r.length).toBeGreaterThan(5);
    expect(HEAD_MESH.landmarks.brow_l.length).toBeGreaterThan(3);
    expect(HEAD_MESH.landmarks.brow_r.length).toBeGreaterThan(3);
    expect(HEAD_MESH.landmarks.lips_out.length).toBeGreaterThan(10);
    expect(HEAD_MESH.landmarks.lips_in.length).toBeGreaterThan(10);

    expect(JAW_PIVOT.length).toBe(3);
    expect(JAW_MAX).toBeGreaterThan(0.05);
  });

  it("renders 3D canvas element for face style", () => {
    render(
      <HudAvatar
        assistantName="Alex"
        mode="idle"
        style="face"
      />,
    );

    const canvas = screen.getByTestId("holo-canvas");
    expect(canvas).toBeInTheDocument();
    expect(canvas).toHaveAttribute("width", "640");
    expect(canvas).toHaveAttribute("height", "720");
    expect(screen.getByText("STANDING BY")).toBeInTheDocument();
  });

  it("renders reactor core for core style", () => {
    render(
      <HudAvatar
        assistantName="Alex"
        mode="thinking"
        style="core"
      />,
    );

    expect(screen.queryByTestId("holo-canvas")).toBeNull();
    expect(screen.getByRole("img", { name: "Animated reactor core" })).toBeInTheDocument();
    expect(screen.getByText("PROCESSING")).toBeInTheDocument();
  });

  it("starts animation loop on mount and cancels on unmount", () => {
    const rafSpy = vi.spyOn(window, "requestAnimationFrame");
    const cafSpy = vi.spyOn(window, "cancelAnimationFrame");

    const { unmount } = render(
      <HudAvatar
        assistantName="Alex"
        mode="idle"
        style="face"
      />,
    );

    expect(rafSpy).toHaveBeenCalled();

    unmount();
    expect(cafSpy).toHaveBeenCalled();
  });

  it("decomposes phonemes and text characters in VisemeAnalyzer", () => {
    const analyzer = new VisemeAnalyzer();

    expect(analyzer.analyzeTextChar("a").name).toBe("aa");
    expect(analyzer.analyzeTextChar("e").name).toBe("ee");
    expect(analyzer.analyzeTextChar("o").name).toBe("oo");
    expect(analyzer.analyzeTextChar("s").name).toBe("ch");
    expect(analyzer.analyzeTextChar("m").name).toBe("sil");

    // Canonical viseme openness
    expect(CANONICAL_VISEMES.aa.open).toBeGreaterThan(0.8);
    expect(CANONICAL_VISEMES.sil.open).toBe(0.0);

    // Formant analysis
    const silence = new Uint8Array(256).fill(0);
    expect(analyzer.analyzeFormants(silence).name).toBe("sil");

    // Formant with high F1 (vowel energy around 500 Hz)
    const vowelSpectrum = new Uint8Array(256).fill(5);
    // Bin width for 44100 / 2 / 256 = ~86 Hz per bin. Bin 5..8 is 400-700 Hz
    vowelSpectrum[5] = 180;
    vowelSpectrum[6] = 200;
    vowelSpectrum[7] = 190;
    const shape = analyzer.analyzeFormants(vowelSpectrum, 44100);
    expect(shape.open).toBeGreaterThan(0.3);

    // Smooth step
    const stepped = analyzer.step(0.02, CANONICAL_VISEMES.aa);
    expect(stepped.open).toBeGreaterThan(0);
  });

  it("executes HoloAvatarRenderer step and render with mock 2D context", () => {
    const renderer = new HoloAvatarRenderer();
    renderer.step(0.016, {
      amplitude: 0.5,
      speaking: true,
      mode: "idle",
      viseme: CANONICAL_VISEMES.aa,
    });

    const mockCtx = {
      clearRect: vi.fn(),
      createRadialGradient: vi.fn().mockReturnValue({
        addColorStop: vi.fn(),
      }),
      fillStyle: "",
      strokeStyle: "",
      lineWidth: 1,
      beginPath: vi.fn(),
      arc: vi.fn(),
      ellipse: vi.fn(),
      moveTo: vi.fn(),
      lineTo: vi.fn(),
      closePath: vi.fn(),
      fill: vi.fn(),
      stroke: vi.fn(),
    } as unknown as CanvasRenderingContext2D;

    expect(() => {
      renderer.render(mockCtx, 640, 720, {
        primaryColor: "#00dfff",
        accentColor: "#ff7a16",
        mode: "idle",
      });
    }).not.toThrow();

    expect(mockCtx.clearRect).toHaveBeenCalledWith(0, 0, 640, 720);
    expect(mockCtx.beginPath).toHaveBeenCalled();
  });

  it("keeps mouth closed during idle, listening, and thinking states", () => {
    const renderer = new HoloAvatarRenderer();
    for (const mode of ["idle", "listening", "thinking"] as const) {
      renderer.step(0.016, { mode, speaking: false, amplitude: 0.0 });
      expect((renderer as any).mouth).toBe(0.0);
    }
  });

  it("articulates mouth open during speaking with positive audio amplitude", () => {
    const renderer = new HoloAvatarRenderer();
    renderer.step(0.016, {
      mode: "speaking",
      speaking: true,
      amplitude: 0.6,
      viseme: CANONICAL_VISEMES.aa,
    });
    expect((renderer as any).mouth).toBeGreaterThan(0.05);

    // Mouth decays toward zero when audio stops (silence)
    for (let i = 0; i < 10; i++) {
      renderer.step(0.016, {
        mode: "idle",
        speaking: false,
        amplitude: 0.0,
        viseme: CANONICAL_VISEMES.sil,
      });
    }
    expect((renderer as any).mouth).toBeLessThan(0.05);
  });

  it("handles AnalyserNode audio analysis inside HudAvatar without errors", () => {
    const mockAnalyser = {
      fftSize: 512,
      context: { sampleRate: 44100 },
      getByteFrequencyData: vi.fn((arr: Uint8Array) => arr.fill(10)),
      getFloatTimeDomainData: vi.fn((arr: Float32Array) => arr.fill(0.05)),
    } as unknown as AnalyserNode;

    const { unmount } = render(
      <HudAvatar
        assistantName="Alex"
        mode="speaking"
        style="face"
        speaking={true}
        analyserNode={mockAnalyser}
      />,
    );

    expect(screen.getByTestId("holo-canvas")).toBeInTheDocument();
    unmount();
  });

  it("transitions color palette to JARVIS amber during speaking and green during listening", () => {
    const renderer = new HoloAvatarRenderer();
    // Initially idle (cyan [70, 244, 255])
    expect((renderer as any).curWireRGB[0]).toBe(70);

    // Step into speaking (amber [255, 140, 25])
    for (let i = 0; i < 20; i++) {
      renderer.step(0.016, { mode: "speaking", speaking: true, amplitude: 0.5 });
    }
    // Red channel should increase towards 255
    expect((renderer as any).curWireRGB[0]).toBeGreaterThan(200);
    expect((renderer as any).curBrow).toBe("#ffaa22");

    // Step into listening (green [40, 255, 150])
    for (let i = 0; i < 25; i++) {
      renderer.step(0.016, { mode: "listening", speaking: false, amplitude: 0.0 });
    }
    expect((renderer as any).curWireRGB[0]).toBeLessThan(100);
    expect((renderer as any).curWireRGB[1]).toBeGreaterThan(230);
    expect((renderer as any).curBrow).toBe("#44ffaa");
  });

  it("animates reactor core with speaking class and caption RESPONDING during speech", () => {
    const { container } = render(
      <HudAvatar
        assistantName="Alex"
        mode="speaking"
        style="core"
        speaking={true}
      />,
    );

    const stage = container.querySelector(".holo-stage");
    expect(stage).toHaveClass("holo-speaking");
    expect(stage).toHaveClass("holo-core");
    expect(screen.getByText("RESPONDING")).toBeInTheDocument();
  });
});

