import { test, expect } from "./fixtures/testFixtures";
import { openSetupDrawer, openControlsDrawer, closeActiveModal } from "./helpers/hudHelper";

test.describe("ALEX Main Navigation & Drawers", () => {
  test("toggles Setup Drawer and reveals system setup options", async ({ alexPage }) => {
    await openSetupDrawer(alexPage);
    const drawer = alexPage.locator(".hud-drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer.getByRole("button", { name: /customise assistant/i })).toBeVisible();
    await expect(drawer.getByRole("button", { name: /audio devices/i })).toBeVisible();
    await expect(drawer.getByRole("button", { name: /memory/i })).toBeVisible();
    await expect(drawer.getByRole("button", { name: /reminders/i })).toBeVisible();
    await expect(drawer.getByRole("button", { name: /actions/i })).toBeVisible();
    await expect(drawer.getByRole("button", { name: /computer control/i })).toBeVisible();
    await expect(drawer.getByRole("button", { name: /job hunting/i })).toBeVisible();
  });

  test("toggles Controls Drawer and reveals everyday switches", async ({ alexPage }) => {
    await openControlsDrawer(alexPage);
    const drawer = alexPage.locator(".hud-drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer.getByRole("button", { name: /fullscreen/i })).toBeVisible();
    await expect(drawer.getByRole("button", { name: /job hunting radar/i })).toBeVisible();
    await expect(drawer.getByRole("button", { name: /activity logs/i })).toBeVisible();
    await expect(drawer.getByRole("button", { name: /wake-up briefing/i })).toBeVisible();
  });

  test("opens modal panel from drawer and closes via close button and Escape key", async ({ alexPage }) => {
    await openSetupDrawer(alexPage);
    const settingsBtn = alexPage.locator(".hud-drawer").getByRole("button", { name: /customise assistant/i });
    await settingsBtn.click();

    // Verify modal panel backdrop and header
    const modal = alexPage.locator(".hud-modal-backdrop");
    await expect(modal).toBeVisible();
    await expect(modal).toContainText("CUSTOMISE ASSISTANT");

    // Close modal
    await closeActiveModal(alexPage);
    await expect(modal).not.toBeVisible();
  });

  test("toggles Activity Log drawer and renders live activity stream", async ({ alexPage }) => {
    const activityBtn = alexPage.getByRole("button", { name: /activity logs/i });
    await activityBtn.click();

    const activityDrawer = alexPage.locator(".activity-drawer");
    await expect(activityDrawer).toBeVisible();
    await expect(activityDrawer).toContainText(/ALEX \/\/ ACTIVITY LOGS/i);
  });
});
