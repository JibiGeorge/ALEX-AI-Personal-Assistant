import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HolographicAssistant } from "./HolographicAssistant";
import type { WorkspaceActivity } from "../../types/workspace";

describe("HolographicAssistant Dynamic Avatar Positioning (ALEX Step 4)", () => {
  beforeEach(() => {
    window.HTMLMediaElement.prototype.play = vi.fn().mockImplementation(() => Promise.resolve());
    window.HTMLMediaElement.prototype.pause = vi.fn();
  });

  it("renders in normal centered mode when no workspace is active", () => {
    const { container } = render(
      <HolographicAssistant
        assistantName="ALEX"
        userName="Commander"
        mode="idle"
        hudStyle="face"
        booting={false}
        chatBusy={false}
        voiceActive={false}
        apiKeyConfigured={true}
        activeWorkspace={null}
        activeMedia={null}
      />
    );

    const avatarStage = container.querySelector(".hud-avatar-stage");
    expect(avatarStage).toBeInTheDocument();
    expect(avatarStage).not.toHaveClass("in-workspace-mode");

    const concentricRings = container.querySelector(".holo-concentric-rings");
    expect(concentricRings).toBeInTheDocument();
    expect(concentricRings).not.toHaveClass("in-workspace-mode");

    // Welcome copy is visible in normal mode
    expect(screen.getByText(/WELCOME BACK, COMMANDER/i)).toBeInTheDocument();
    // Compact status pill is not rendered in normal mode
    expect(container.querySelector(".compact-avatar-status-pill")).not.toBeInTheDocument();
  });

  it("transitions avatar to compact bottom-right mode when workspace opens", () => {
    const handleClose = vi.fn();
    const videoActivity: WorkspaceActivity = {
      id: "ws-video-1",
      type: "video",
      title: "Interstellar Holographic Sequence",
      url: "https://example.com/video.mp4",
      isPlaying: true,
    };

    const { container } = render(
      <HolographicAssistant
        assistantName="ALEX"
        userName="Commander"
        mode="idle"
        hudStyle="face"
        booting={false}
        chatBusy={false}
        voiceActive={false}
        apiKeyConfigured={true}
        activeWorkspace={videoActivity}
        onCloseWorkspace={handleClose}
      />
    );

    const avatarStage = container.querySelector(".hud-avatar-stage");
    expect(avatarStage).toHaveClass("in-workspace-mode");

    const concentricRings = container.querySelector(".holo-concentric-rings");
    expect(concentricRings).toHaveClass("in-workspace-mode");

    // Compact status badge appears in bottom-right mode
    const statusPill = container.querySelector(".compact-avatar-status-pill");
    expect(statusPill).toBeInTheDocument();
    expect(statusPill).toHaveTextContent("STANDING BY");

    // Welcome copy is hidden in workspace mode
    expect(screen.queryByText(/WELCOME BACK, COMMANDER/i)).not.toBeInTheDocument();

    // Floating workspace window is active
    expect(screen.getByRole("region", { name: "HUD Workspace Window" })).toBeInTheDocument();
  });

  it("maintains compact avatar mode when workspace window is minimized", () => {
    const musicActivity: WorkspaceActivity = {
      id: "ws-music-1",
      type: "music",
      title: "Cyberpunk Ambient Synthesis",
      isPlaying: true,
    };

    const { container } = render(
      <HolographicAssistant
        assistantName="ALEX"
        userName="Commander"
        mode="idle"
        hudStyle="face"
        booting={false}
        chatBusy={false}
        voiceActive={false}
        apiKeyConfigured={true}
        activeWorkspace={musicActivity}
      />
    );

    // Minimize the window
    const minBtn = screen.getByRole("button", { name: "Minimize Window" });
    fireEvent.click(minBtn);

    // Dock pill is displayed
    expect(screen.getByRole("region", { name: "Minimized Workspace" })).toBeInTheDocument();

    // Avatar stage STILL stays in compact bottom-right mode because activity is active
    const avatarStage = container.querySelector(".hud-avatar-stage");
    expect(avatarStage).toHaveClass("in-workspace-mode");

    const concentricRings = container.querySelector(".holo-concentric-rings");
    expect(concentricRings).toHaveClass("in-workspace-mode");
  });

  it("returns avatar to center when workspace is closed", () => {
    const musicActivity: WorkspaceActivity = {
      id: "ws-music-1",
      type: "music",
      title: "Cyberpunk Ambient Synthesis",
    };

    const { container, rerender } = render(
      <HolographicAssistant
        assistantName="ALEX"
        userName="Commander"
        mode="idle"
        hudStyle="face"
        booting={false}
        chatBusy={false}
        voiceActive={false}
        apiKeyConfigured={true}
        activeWorkspace={musicActivity}
      />
    );

    expect(container.querySelector(".hud-avatar-stage")).toHaveClass("in-workspace-mode");

    // Re-render with activeWorkspace = null (simulating onClose)
    rerender(
      <HolographicAssistant
        assistantName="ALEX"
        userName="Commander"
        mode="idle"
        hudStyle="face"
        booting={false}
        chatBusy={false}
        voiceActive={false}
        apiKeyConfigured={true}
        activeWorkspace={null}
      />
    );

    // Avatar returns to centered normal mode
    const avatarStage = container.querySelector(".hud-avatar-stage");
    expect(avatarStage).not.toHaveClass("in-workspace-mode");
    expect(container.querySelector(".holo-concentric-rings")).not.toHaveClass("in-workspace-mode");
    expect(screen.getByText(/WELCOME BACK, COMMANDER/i)).toBeInTheDocument();
  });
});
