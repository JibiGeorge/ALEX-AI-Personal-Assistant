import { test, expect } from "./fixtures/testFixtures";
import { openPanelFromDrawer, closeActiveModal } from "./helpers/hudHelper";

test.describe("ALEX Job Hunting & Career Radar Module", () => {
  test("opens Job Hunting Control Center from Controls Drawer", async ({ alexPage }) => {
    await openPanelFromDrawer(alexPage, "controls", /job hunting/i);

    const modal = alexPage.locator(".hud-modal-backdrop");
    await expect(modal).toBeVisible();
    await expect(modal).toContainText(/JOB HUNTING/i);

    // Verify sub-navigation bar
    const navBar = modal.locator(".job-nav-bar");
    await expect(navBar).toBeVisible();

    // Verify tabs exist
    await expect(navBar.getByRole("button", { name: /dashboard/i })).toBeVisible();
    await expect(navBar.getByRole("button", { name: /discover/i })).toBeVisible();
    await expect(navBar.getByRole("button", { name: /recommended/i })).toBeVisible();
    await expect(navBar.getByRole("button", { name: /resume studio/i })).toBeVisible();
    await expect(navBar.getByRole("button", { name: /cover letter/i })).toBeVisible();
    await expect(navBar.getByRole("button", { name: /approvals/i })).toBeVisible();
    await expect(navBar.getByRole("button", { name: /applications/i })).toBeVisible();
    await expect(navBar.getByRole("button", { name: /interviews/i })).toBeVisible();
    await expect(navBar.getByRole("button", { name: /settings/i })).toBeVisible();

    await closeActiveModal(alexPage);
  });

  test("opens Job Hunting via natural command 'open job hunting on hud'", async ({ alexPage }) => {
    const input = alexPage.getByRole("textbox", { name: /command or question/i }).or(alexPage.locator(".hud-command-form input"));
    await input.fill("open job hunting on hud");
    await input.press("Enter");

    // Modal opens directly without playing YouTube video
    const modal = alexPage.locator(".hud-modal-backdrop");
    await expect(modal).toBeVisible({ timeout: 10000 });
    await expect(modal).toContainText(/JOB HUNTING/i);

    // Verify video workspace is NOT open
    await expect(alexPage.locator(".ws-video-view")).not.toBeVisible();

    await closeActiveModal(alexPage);
  });

  test("navigates to Discover tab and displays search filters and jobs list", async ({ alexPage }) => {
    await openPanelFromDrawer(alexPage, "controls", /job hunting/i);
    const modal = alexPage.locator(".hud-modal-backdrop");

    // Click Discover tab
    const discoverBtn = modal.locator(".job-nav-bar").getByRole("button", { name: /discover/i });
    await discoverBtn.click();

    // Verify search query input
    const queryInput = modal.locator("input[placeholder*='Search jobs']").or(modal.locator(".search-input-field"));
    await expect(queryInput.first()).toBeVisible();

    await closeActiveModal(alexPage);
  });
});
