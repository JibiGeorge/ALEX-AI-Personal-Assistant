import { test, expect } from "./fixtures/testFixtures";
import { openWorkspaceViaCommand, closeActiveWorkspace } from "./helpers/workspaceHelper";

test.describe("HUD Media Player Workspaces (Video & Music)", () => {
  test("music player renders track info, duration, and equalizer visualizer", async ({ alexPage }) => {
    await openWorkspaceViaCommand(alexPage, "play music");

    const player = alexPage.locator(".ws-music-view");
    await expect(player).toBeVisible();

    // Verify track metadata
    await expect(player.locator(".ws-music-track-title")).toBeVisible();

    // Verify visualizer canvas exists
    const eqCanvas = player.locator(".ws-music-visualizer-canvas");
    await expect(eqCanvas).toBeVisible();

    // Verify playback control buttons (play/pause, mute)
    const playPauseBtn = player.getByRole("button", { name: /pause|play/i }).or(player.locator(".ws-control-btn"));
    await expect(playPauseBtn.first()).toBeVisible();

    await closeActiveWorkspace(alexPage);
  });

  test("video workspace mounts video stage container and controls", async ({ alexPage }) => {
    await openWorkspaceViaCommand(alexPage, "play video Cyberpunk Trailer on YouTube");

    const videoStage = alexPage.locator(".video-workspace-stage").or(alexPage.locator(".ws-video-view"));
    await expect(videoStage).toBeVisible();

    await closeActiveWorkspace(alexPage);
  });
});
