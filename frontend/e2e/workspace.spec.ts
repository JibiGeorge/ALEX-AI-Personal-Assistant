import { test, expect } from "./fixtures/testFixtures";
import {
  openWorkspaceViaCommand,
  minimizeActiveWorkspace,
  restoreActiveWorkspace,
  closeActiveWorkspace,
} from "./helpers/workspaceHelper";

test.describe("Floating HUD Workspace Window Lifecycle", () => {
  test("opens, minimizes, restores, and closes workspace window", async ({ alexPage }) => {
    // 1. Open floating window
    await openWorkspaceViaCommand(alexPage, "open workspace");
    const wsWindow = alexPage.locator(".hud-workspace-window");
    await expect(wsWindow).toBeVisible();

    // 2. Minimize window
    await minimizeActiveWorkspace(alexPage);
    await expect(alexPage.locator(".ws-minimized-dock")).toBeVisible();

    // 3. Restore window
    await restoreActiveWorkspace(alexPage);
    await expect(wsWindow).toBeVisible();

    // 4. Close window
    await closeActiveWorkspace(alexPage);
    await expect(wsWindow).not.toBeVisible();
  });

  test("reuses the single window when opening new content without stacking duplicate windows", async ({ alexPage }) => {
    // 1. Open first activity
    await openWorkspaceViaCommand(alexPage, "open workspace");
    await expect(alexPage.locator(".hud-workspace-window")).toHaveCount(1);

    // 2. Open second activity (e.g. music)
    const input = alexPage.getByRole("textbox", { name: /command or question/i }).or(alexPage.locator(".hud-command-form input"));
    await input.fill("play music");
    await input.press("Enter");

    // 3. Verify exactly one window remains active with new content
    await expect(alexPage.locator(".hud-workspace-window")).toHaveCount(1);
    await expect(alexPage.locator(".ws-music-view")).toBeVisible();

    // Cleanup
    await closeActiveWorkspace(alexPage);
  });
});
