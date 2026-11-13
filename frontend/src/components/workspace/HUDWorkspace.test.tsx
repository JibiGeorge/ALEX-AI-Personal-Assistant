import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HUDWorkspace } from "./HUDWorkspace";
import type { WorkspaceActivity } from "../../types/workspace";

describe("HUDWorkspace Component", () => {
  beforeEach(() => {
    window.HTMLMediaElement.prototype.play = vi.fn().mockImplementation(() => Promise.resolve());
    window.HTMLMediaElement.prototype.pause = vi.fn();
  });

  it("renders a video activity and triggers close on dismiss button", () => {
    const handleClose = vi.fn();
    const videoActivity: WorkspaceActivity = {
      id: "video-1",
      type: "video",
      title: "Interstellar Holographic Sequence",
      url: "https://example.com/video.mp4",
      isPlaying: true,
      isMuted: true,
    };

    render(<HUDWorkspace activity={videoActivity} onClose={handleClose} />);

    expect(screen.getByText("◆ VIDEO WORKSPACE")).toBeInTheDocument();
    expect(screen.getAllByText("Interstellar Holographic Sequence").length).toBeGreaterThanOrEqual(1);

    const closeBtn = screen.getByRole("button", { name: "Close Workspace" });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("renders a music activity with audio visualizer, track info and play/pause controls", () => {
    const handlePlayPause = vi.fn();
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
      <HUDWorkspace
        activity={musicActivity}
        onClose={vi.fn()}
        onPlayPauseToggle={handlePlayPause}
      />
    );

    expect(screen.getByText("◆ AUDIO PLAYER")).toBeInTheDocument();
    expect(screen.getAllByText("Cyberpunk Ambient Synthesis").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/ALEX Audio Engine • Holographic OST/i)).toBeInTheDocument();

    const playPauseBtn = screen.getByRole("button", { name: "Pause" });
    fireEvent.click(playPauseBtn);
    expect(handlePlayPause).toHaveBeenCalledWith(false);
  });

  it("renders an image activity with zoom controls", () => {
    const imageActivity: WorkspaceActivity = {
      id: "img-1",
      type: "image",
      title: "Architectural Blueprint.png",
      url: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    };

    render(<HUDWorkspace activity={imageActivity} onClose={vi.fn()} />);

    expect(screen.getByText("◆ IMAGE VIEWER")).toBeInTheDocument();
    expect(screen.getAllByText("Architectural Blueprint.png").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("100%")).toBeInTheDocument();

    const zoomInBtn = screen.getByRole("button", { name: "Zoom In" });
    fireEvent.click(zoomInBtn);
    expect(screen.getByText("125%")).toBeInTheDocument();

    const fitBtn = screen.getByRole("button", { name: "Reset Zoom" });
    fireEvent.click(fitBtn);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("renders a document activity with syntax formatting", () => {
    const docActivity: WorkspaceActivity = {
      id: "doc-1",
      type: "document",
      title: "Security Protocols.md",
      fileData: {
        name: "Security Protocols.md",
        mimeType: "text/markdown",
        content: "# PROTOCOL 01\nAssertTrustedSender active.",
        size: 512,
      },
    };

    render(<HUDWorkspace activity={docActivity} onClose={vi.fn()} />);

    expect(screen.getByText("◆ DOCUMENT VIEWER")).toBeInTheDocument();
    expect(screen.getAllByText("Security Protocols.md").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/PROTOCOL 01/)).toBeInTheDocument();
  });

  it("closes when user presses the Escape key", () => {
    const handleClose = vi.fn();
    const docActivity: WorkspaceActivity = {
      id: "doc-2",
      type: "document",
      title: "System Notes.txt",
    };

    render(<HUDWorkspace activity={docActivity} onClose={handleClose} />);

    fireEvent.keyDown(window, { key: "Escape" });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
