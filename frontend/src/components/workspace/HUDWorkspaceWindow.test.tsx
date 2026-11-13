import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HUDWorkspaceWindow } from "./HUDWorkspaceWindow";
import type { WorkspaceActivity } from "../../types/workspace";

describe("HUDWorkspaceWindow (ALEX Step 6 — Universal HUD Workspace Content Integration)", () => {
  let globalMockTrack: { stop: any };
  let globalMockStream: { getTracks: any };

  beforeEach(() => {
    window.HTMLMediaElement.prototype.play = vi.fn().mockImplementation(() => Promise.resolve());
    window.HTMLMediaElement.prototype.pause = vi.fn();

    globalMockTrack = { stop: vi.fn() };
    globalMockStream = {
      getTracks: vi.fn().mockReturnValue([globalMockTrack]),
    };
    Object.defineProperty(navigator, "mediaDevices", {
      value: {
        getUserMedia: vi.fn().mockResolvedValue(globalMockStream),
      },
      configurable: true,
      writable: true,
    });
  });

  it("renders empty workspace state when no activity or tool activity is provided", () => {
    const handleClose = vi.fn();
    const handleSample = vi.fn();

    render(
      <HUDWorkspaceWindow
        activity={{
          id: "empty-ws",
          type: "tool",
          title: "Holographic Workspace",
          subtitle: "Independent Floating Stage",
        }}
        onClose={handleClose}
        onOpenSampleActivity={handleSample}
      />
    );

    // Title and empty state canvas
    expect(screen.getByText("Holographic Workspace")).toBeInTheDocument();
    expect(screen.getByText("Independent Floating Stage")).toBeInTheDocument();
    expect(screen.getByTestId("ws-empty-view")).toBeInTheDocument();
    expect(screen.getByText("◈")).toBeInTheDocument();

    // Demo action buttons inside empty workspace
    const demoVideoBtn = screen.getByRole("button", { name: /DEMO VIDEO/i });
    expect(demoVideoBtn).toBeInTheDocument();
    fireEvent.click(demoVideoBtn);
    expect(handleSample).toHaveBeenCalledWith("video");
  });

  it("minimizes the floating window into a compact dock pill and restores on click", () => {
    const musicActivity: WorkspaceActivity = {
      id: "music-1",
      type: "music",
      title: "Cyberpunk Ambient Synthesis",
      subtitle: "Neural Audio Synthesis",
      isPlaying: true,
      musicData: {
        title: "Cyberpunk Ambient Synthesis",
        artist: "ALEX Audio Engine",
        album: "Holographic OST",
        duration: 210,
      },
    };

    render(
      <HUDWorkspaceWindow
        activity={musicActivity}
        onClose={vi.fn()}
      />
    );

    // Window is currently open
    expect(screen.getByRole("region", { name: "HUD Workspace Window" })).toBeInTheDocument();

    // Click Minimize button
    const minBtn = screen.getByRole("button", { name: "Minimize Window" });
    fireEvent.click(minBtn);

    // Floating window is minimized into the dock pill
    expect(screen.queryByRole("region", { name: "HUD Workspace Window" })).not.toBeInTheDocument();
    const dockPill = screen.getByRole("region", { name: "Minimized Workspace" });
    expect(dockPill).toBeInTheDocument();
    expect(screen.getByText(/Cyberpunk Ambient Synthesis/i)).toBeInTheDocument();

    // Click Restore button
    const restoreBtn = screen.getByRole("button", { name: /Restore Cyberpunk Ambient Synthesis/i });
    fireEvent.click(restoreBtn);

    // Window is restored
    expect(screen.getByRole("region", { name: "HUD Workspace Window" })).toBeInTheDocument();
  });

  it("toggles maximized state when clicking the maximize/restore button", () => {
    const docActivity: WorkspaceActivity = {
      id: "doc-1",
      type: "document",
      title: "Core Protocols.md",
      fileData: {
        name: "Core Protocols.md",
        mimeType: "text/markdown",
        content: "# Test Protocols",
      },
    };

    render(
      <HUDWorkspaceWindow
        activity={docActivity}
        onClose={vi.fn()}
      />
    );

    const winContainer = screen.getByRole("region", { name: "HUD Workspace Window" });
    expect(winContainer).not.toHaveClass("is-maximized");

    const maxBtn = screen.getByRole("button", { name: "Maximize Window" });
    fireEvent.click(maxBtn);
    expect(winContainer).toHaveClass("is-maximized");

    const restoreWinBtn = screen.getByRole("button", { name: "Restore Window" });
    fireEvent.click(restoreWinBtn);
    expect(winContainer).not.toHaveClass("is-maximized");
  });

  it("invokes onClose when clicking close control or pressing Escape", () => {
    const handleClose = vi.fn();
    const { unmount } = render(
      <HUDWorkspaceWindow
        activity={{
          id: "test-ws",
          type: "tool",
          title: "Holographic Window",
        }}
        onClose={handleClose}
      />
    );

    const closeBtn = screen.getByRole("button", { name: "Close Workspace" });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);

    // Press Escape
    fireEvent.keyDown(window, { key: "Escape" });
    expect(handleClose).toHaveBeenCalledTimes(2);

    unmount();
  });

  it("renders content zoom controls and external launcher for supported assets", () => {
    const handleExternal = vi.fn();
    const imgActivity: WorkspaceActivity = {
      id: "img-1",
      type: "image",
      title: "Blueprint.png",
      url: "https://example.com/blueprint.png",
      source: "https://example.com/blueprint.png",
    };

    render(
      <HUDWorkspaceWindow
        activity={imgActivity}
        onClose={vi.fn()}
        onOpenExternal={handleExternal}
      />
    );

    expect(screen.getByText("100%")).toBeInTheDocument();
    const zoomInBtn = screen.getByRole("button", { name: "Zoom In" });
    fireEvent.click(zoomInBtn);
    expect(screen.getByText("125%")).toBeInTheDocument();

    const extBtn = screen.getByRole("button", { name: /EXTERNAL/i });
    fireEvent.click(extBtn);
    expect(handleExternal).toHaveBeenCalledWith("https://example.com/blueprint.png");
  });

  it("renders the Music Player with full playback controls, visualizer, seek, and stop", () => {
    const onPlayPause = vi.fn();
    const onMute = vi.fn();
    const musicActivity: WorkspaceActivity = {
      id: "music-cyberpunk",
      type: "music",
      title: "Cyberpunk Ambient Synthesis",
      isPlaying: true,
      musicData: {
        title: "Cyberpunk Ambient Synthesis",
        artist: "ALEX Audio Engine",
        album: "Holographic OST",
        duration: 240,
      },
    };

    const { container } = render(
      <HUDWorkspaceWindow
        activity={musicActivity}
        onClose={vi.fn()}
        onPlayPauseToggle={onPlayPause}
        onMuteToggle={onMute}
      />
    );

    expect(screen.getByTestId("ws-music-view")).toBeInTheDocument();
    expect(container.querySelector(".ws-music-track-title")).toHaveTextContent("Cyberpunk Ambient Synthesis");
    expect(screen.getByText(/ALEX Audio Engine • Holographic OST/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Audio Visualizer")).toBeInTheDocument();

    // Play / Pause toggle
    const pauseBtn = screen.getByRole("button", { name: "Pause" });
    fireEvent.click(pauseBtn);
    expect(onPlayPause).toHaveBeenCalledWith(false);

    // Stop button resets progress
    const stopBtn = screen.getByRole("button", { name: "Stop" });
    fireEvent.click(stopBtn);
    expect(onPlayPause).toHaveBeenCalledWith(false);

    // Mute toggle
    const muteBtn = screen.getByRole("button", { name: "Mute" });
    fireEvent.click(muteBtn);
    expect(onMute).toHaveBeenCalledWith(true);

    // Seek scrubber
    const seekSlider = screen.getByLabelText("Seek track position");
    fireEvent.change(seekSlider, { target: { value: 60 } });
    expect(screen.getByText("1:00")).toBeInTheDocument();
  });

  it("renders the PDF Viewer with page navigation controls and filename", () => {
    const pdfActivity: WorkspaceActivity = {
      id: "pdf-doc",
      type: "pdf",
      title: "Architecture Specification.pdf",
      totalPages: 5,
      currentPage: 1,
      fileData: {
        name: "Architecture Specification.pdf",
        mimeType: "application/pdf",
        pageCount: 5,
      },
    };

    const { container } = render(
      <HUDWorkspaceWindow
        activity={pdfActivity}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByTestId("ws-pdf-view")).toBeInTheDocument();
    expect(screen.getByText("PAGE 1 / 5")).toBeInTheDocument();
    expect(container.querySelector(".ws-pdf-filename")).toHaveTextContent("Architecture Specification.pdf");

    // Navigate to next page
    const nextBtn = screen.getByRole("button", { name: "Next Page" });
    fireEvent.click(nextBtn);
    expect(screen.getByText("PAGE 2 / 5")).toBeInTheDocument();

    // Navigate to previous page
    const prevBtn = screen.getByRole("button", { name: "Previous Page" });
    fireEvent.click(prevBtn);
    expect(screen.getByText("PAGE 1 / 5")).toBeInTheDocument();
  });

  it("renders the Document Viewer preserving markdown and handles unsupported formats", () => {
    const docActivity: WorkspaceActivity = {
      id: "doc-sample",
      type: "document",
      title: "Protocol Guide.md",
      fileData: {
        name: "Protocol Guide.md",
        mimeType: "text/markdown",
        content: "# SYSTEM PROTOCOLS\n## Core Security\n- Verification active\n- All channels nominal",
      },
    };

    const { rerender } = render(
      <HUDWorkspaceWindow
        activity={docActivity}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByTestId("ws-document-view")).toBeInTheDocument();
    expect(screen.getByText("SYSTEM PROTOCOLS")).toBeInTheDocument();
    expect(screen.getByText("Core Security")).toBeInTheDocument();
    expect(screen.getByText("Verification active")).toBeInTheDocument();

    // Test unsupported binary format fallback
    const unsupportedActivity: WorkspaceActivity = {
      id: "bin-sample",
      type: "document",
      title: "Firmware.bin",
      unsupportedFormat: true,
      unsupportedMessage: "Binary format unsupported for text preview",
      source: "/path/to/Firmware.bin",
    };

    rerender(
      <HUDWorkspaceWindow
        activity={unsupportedActivity}
        onClose={vi.fn()}
        onOpenExternal={vi.fn()}
      />
    );

    expect(screen.getByText("BINARY / PROPRIETARY FORMAT")).toBeInTheDocument();
    expect(screen.getByText("Binary format unsupported for text preview")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /OPEN IN OS APPLICATION/i })).toBeInTheDocument();
  });

  it("renders the Browser Workspace with address bar, navigation controls, and sandboxed iframe", () => {
    const handleExternal = vi.fn();
    const browserActivity: WorkspaceActivity = {
      id: "browser-sample",
      type: "browser",
      title: "Google Search",
      url: "https://www.google.com",
      source: "https://www.google.com",
    };

    render(
      <HUDWorkspaceWindow
        activity={browserActivity}
        onClose={vi.fn()}
        onOpenExternal={handleExternal}
      />
    );

    expect(screen.getByTestId("ws-browser-view")).toBeInTheDocument();
    expect(screen.getByText("🔒 SECURE SANDBOX")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Browser Back" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Browser Forward" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Browser Reload" })).toBeInTheDocument();

    const addressInput = screen.getByLabelText("Browser Address") as HTMLInputElement;
    expect(addressInput.value).toBe("https://www.google.com");

    const extBtn = screen.getByRole("button", { name: "Open in external browser" });
    fireEvent.click(extBtn);
    expect(handleExternal).toHaveBeenCalledWith("https://www.google.com");
  });

  it("supports seamless window reuse when switching activities (Video -> PDF -> Music -> Browser)", async () => {
    const videoActivity: WorkspaceActivity = {
      id: "ws-vid",
      type: "video",
      title: "Interstellar Trailer",
      url: "https://www.youtube.com/embed/zSWdZVtXT7E",
    };

    const { rerender } = render(
      <HUDWorkspaceWindow
        activity={videoActivity}
        onClose={vi.fn()}
      />
    );

    // Initial state: Video
    expect(screen.getByTestId("media-player-stage")).toBeInTheDocument();
    expect(screen.getAllByText("Interstellar Trailer").length).toBeGreaterThan(0);

    // Reusing the window: Switch to PDF
    const pdfActivity: WorkspaceActivity = {
      id: "ws-pdf",
      type: "pdf",
      title: "System Architecture.pdf",
      totalPages: 3,
      currentPage: 1,
    };
    rerender(
      <HUDWorkspaceWindow
        activity={pdfActivity}
        onClose={vi.fn()}
      />
    );
    expect(screen.queryByTestId("media-player-stage")).not.toBeInTheDocument();
    expect(screen.getByTestId("ws-pdf-view")).toBeInTheDocument();
    expect(screen.getAllByText("System Architecture.pdf").length).toBeGreaterThan(0);

    // Reusing the window: Switch to Music
    const musicActivity: WorkspaceActivity = {
      id: "ws-music",
      type: "music",
      title: "Cyberpunk Synthesis",
      isPlaying: true,
      musicData: {
        title: "Cyberpunk Synthesis",
        artist: "ALEX Engine",
        duration: 180,
      },
    };
    rerender(
      <HUDWorkspaceWindow
        activity={musicActivity}
        onClose={vi.fn()}
      />
    );
    expect(screen.queryByTestId("ws-pdf-view")).not.toBeInTheDocument();
    expect(screen.getByTestId("ws-music-view")).toBeInTheDocument();
    expect(screen.getAllByText("Cyberpunk Synthesis").length).toBeGreaterThan(0);

    // Reusing the window: Switch to Camera
    const cameraActivity: WorkspaceActivity = {
      id: "ws-camera",
      type: "camera",
      title: "Optical Sensor Feed",
    };
    rerender(
      <HUDWorkspaceWindow
        activity={cameraActivity}
        onClose={vi.fn()}
      />
    );
    expect(screen.queryByTestId("ws-browser-view")).not.toBeInTheDocument();
    expect(screen.getByTestId("ws-camera-view")).toBeInTheDocument();
    expect(await screen.findByText("OPTICAL SENSOR // ACTIVE")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /MIRROR:/i })).toBeInTheDocument();
  });

  it("renders optical camera feed with targeting reticle and mirror controls", async () => {
    const cameraActivity: WorkspaceActivity = {
      id: "cam-1",
      type: "camera",
      title: "Live Optical Camera Sensor",
      subtitle: "Live HUD Video Feed",
    };

    const { unmount } = render(
      <HUDWorkspaceWindow
        activity={cameraActivity}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByRole("region", { name: "HUD Workspace Window" })).toBeInTheDocument();
    expect(screen.getByTestId("ws-camera-view")).toBeInTheDocument();
    expect(screen.getByTestId("hud-camera-video")).toBeInTheDocument();
    expect(await screen.findByText("OPTICAL SENSOR // ACTIVE")).toBeInTheDocument();

    // Mirror control toggle
    const mirrorBtn = screen.getByRole("button", { name: /MIRROR: ON/i });
    expect(mirrorBtn).toBeInTheDocument();
    fireEvent.click(mirrorBtn);
    expect(screen.getByRole("button", { name: /MIRROR: OFF/i })).toBeInTheDocument();

    // Frame capture action
    const captureBtn = screen.getByRole("button", { name: /CAPTURE FRAME/i });
    expect(captureBtn).toBeInTheDocument();
    fireEvent.click(captureBtn);

    // Unmount gracefully stops tracks
    unmount();
    expect(globalMockTrack.stop).toHaveBeenCalled();
  });
});
