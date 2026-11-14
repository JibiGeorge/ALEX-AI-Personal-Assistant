import { test, expect } from "./fixtures/testFixtures";
import { openWorkspaceViaCommand, closeActiveWorkspace } from "./helpers/workspaceHelper";

test.describe("ALEX Avatar Synchronization & Docking", () => {
  test("avatar remains centrally positioned in normal dashboard mode", async ({ alexPage }) => {
    const avatarStage = alexPage.locator(".hud-avatar-stage");
    await expect(avatarStage).toBeVisible();
    await expect(avatarStage).not.toHaveClass(/in-workspace-mode/);
  });

  test("avatar docks smoothly to bottom-right when workspace opens and restores on close", async ({ alexPage }) => {
    const avatarStage = alexPage.locator(".hud-avatar-stage");

    // 1. Initially centered
    await expect(avatarStage).not.toHaveClass(/in-workspace-mode/);

    // 2. Open workspace window via command
    await openWorkspaceViaCommand(alexPage, "open workspace");

    // 3. Avatar must transition to docked bottom-right state
    await expect(avatarStage).toHaveClass(/in-workspace-mode/);

    // 4. Close workspace
    await closeActiveWorkspace(alexPage);

    // 5. Avatar must return to central position
    await expect(avatarStage).not.toHaveClass(/in-workspace-mode/);
  });

  test("avatar canvas renders WebGL/Canvas visualizer without errors", async ({ alexPage }) => {
    const canvas = alexPage.locator(".hud-avatar-canvas, .three-canvas, canvas").first();
    await expect(canvas).toBeVisible();
  });
});

