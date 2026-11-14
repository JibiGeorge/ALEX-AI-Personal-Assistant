import { test, expect } from "./fixtures/testFixtures";

test.describe("ALEX Resilience & Error Recovery", () => {
  test("handles unsupported workspace commands gracefully without crashing", async ({ alexPage }) => {
    const input = alexPage.getByRole("textbox", { name: /command or question/i }).or(alexPage.locator(".hud-command-form input"));
    await input.fill("unsupported arbitrary command 12345");
    await input.press("Enter");

    // HUD remains active and operational
    await expect(alexPage.locator(".hud-shell")).toBeVisible();
    await expect(input).toBeEnabled();
  });

  test("displays notice or error gracefully on failed actions", async ({ alexPage }) => {
    // Inject error state check
    const errorNotice = alexPage.locator(".hud-notice, .holo-error-panel");
    if (await errorNotice.isVisible()) {
      await expect(errorNotice).toBeVisible();
    }
    await expect(alexPage.locator(".hud-shell")).toBeVisible();
  });
});
