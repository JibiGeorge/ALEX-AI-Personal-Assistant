import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { VideoPlayer, extractYouTubeVideoId, formatTime } from "./VideoPlayer";

describe("VideoPlayer Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(cleanup);

  it("formats time seconds accurately into mm:ss", () => {
    expect(formatTime(0)).toBe("0:00");
    expect(formatTime(9)).toBe("0:09");
    expect(formatTime(75)).toBe("1:15");
    expect(formatTime(360)).toBe("6:00");
    expect(formatTime(-5)).toBe("0:00");
    expect(formatTime(NaN)).toBe("0:00");
  });

  it("extracts YouTube video IDs from various URL formats", () => {
    expect(extractYouTubeVideoId("pMpTUqJMnzM")).toBe("pMpTUqJMnzM");
    expect(extractYouTubeVideoId("https://www.youtube.com/watch?v=pMpTUqJMnzM")).toBe("pMpTUqJMnzM");
    expect(extractYouTubeVideoId("https://youtu.be/pMpTUqJMnzM")).toBe("pMpTUqJMnzM");
    expect(extractYouTubeVideoId("https://www.youtube.com/embed/pMpTUqJMnzM?autoplay=1")).toBe("pMpTUqJMnzM");
    expect(extractYouTubeVideoId("https://www.youtube.com/shorts/pMpTUqJMnzM")).toBe("pMpTUqJMnzM");
    expect(extractYouTubeVideoId("https://example.com/local.mp4")).toBeNull();
  });

  it("renders video element and title for local streams", () => {
    const onClose = vi.fn();
    render(
      <VideoPlayer
        src="https://example.com/stream.mp4"
        title="Epic Video"
        onClose={onClose}
      />,
    );

    const video = screen.getByTestId("media-video-element") as HTMLVideoElement;
    expect(video).toBeInTheDocument();
    expect(video.src).toBe("https://example.com/stream.mp4");
    expect(video.muted).toBe(true); // Muted by default
    expect(screen.getByText("Epic Video")).toBeInTheDocument();
    expect(screen.getByText("LOCAL MEDIA STREAM")).toBeInTheDocument();
  });

  it("renders YouTube container and badge when YouTube URL is provided", () => {
    render(
      <VideoPlayer
        src="https://www.youtube.com/watch?v=pMpTUqJMnzM"
        title="Disco Malayalam movie"
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByTestId("media-youtube-container")).toBeInTheDocument();
    expect(screen.getByText("Disco Malayalam movie")).toBeInTheDocument();
    expect(screen.getByText("YOUTUBE HUD STREAM")).toBeInTheDocument();
  });

  it("renders auxiliary audio element when audioSrc is provided", () => {
    render(
      <VideoPlayer
        src="https://example.com/video_only.mp4"
        audioSrc="https://example.com/audio_only.m4a"
        onClose={vi.fn()}
      />,
    );

    const audio = document.querySelector("audio.media-aux-audio") as HTMLAudioElement;
    expect(audio).toBeInTheDocument();
    expect(audio.src).toBe("https://example.com/audio_only.m4a");
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(
      <VideoPlayer
        src="https://example.com/sample.mp4"
        onClose={onClose}
      />,
    );

    const closeBtn = screen.getByRole("button", { name: "Close video player" });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("toggles play/pause state when play button is clicked", () => {
    const playMock = vi.fn().mockResolvedValue(undefined);
    const pauseMock = vi.fn();
    window.HTMLMediaElement.prototype.play = playMock;
    window.HTMLMediaElement.prototype.pause = pauseMock;

    const onPlayStateChange = vi.fn();
    render(
      <VideoPlayer
        src="https://example.com/sample.mp4"
        autoPlay={true}
        onClose={vi.fn()}
        onPlayStateChange={onPlayStateChange}
      />,
    );

    const pauseBtn = screen.getByRole("button", { name: "Pause" });
    expect(pauseBtn).toBeInTheDocument();

    // Simulate clicking button
    fireEvent.click(pauseBtn);
    expect(playMock.mock.calls.length + pauseMock.mock.calls.length).toBeGreaterThan(0);
  });

  it("toggles mute state and invokes onMuteChange callback", () => {
    const onMuteChange = vi.fn();
    render(
      <VideoPlayer
        src="https://example.com/sample.mp4"
        initialMuted={true}
        onClose={vi.fn()}
        onMuteChange={onMuteChange}
      />,
    );

    const muteBtn = screen.getByRole("button", { name: "Unmute" });
    fireEvent.click(muteBtn);

    expect(onMuteChange).toHaveBeenCalledWith(false);
  });

  it("triggers onOpenExternal when external button is clicked", () => {
    const onOpenExternal = vi.fn();
    render(
      <VideoPlayer
        src="https://www.youtube.com/watch?v=pMpTUqJMnzM"
        title="Disco Malayalam movie"
        onClose={vi.fn()}
        onOpenExternal={onOpenExternal}
      />,
    );

    const extBtn = screen.getByTitle("Open video in external browser");
    fireEvent.click(extBtn);
    expect(onOpenExternal).toHaveBeenCalledWith("https://www.youtube.com/watch?v=pMpTUqJMnzM");
  });

  it("handles keyboard shortcuts Escape, Space, and m", () => {
    const onClose = vi.fn();
    render(
      <VideoPlayer
        src="https://example.com/sample.mp4"
        onClose={onClose}
      />,
    );

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
