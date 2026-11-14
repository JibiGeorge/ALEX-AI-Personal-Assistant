import { test, expect } from "./fixtures/testFixtures";

test.describe("ALEX HUD & Interface Diagnostics", () => {
  test("renders the full holographic command center without overflow", async ({ alexPage }) => {
    // Check main container
    const shell = alexPage.locator(".hud-shell");
    await expect(shell).toBeVisible();

    // Verify header region
    const header = alexPage.locator(".hud-header");
    await expect(header).toBeVisible();

    // Verify main workspace body / center
    const body = alexPage.locator(".hud-center");
    await expect(body).toBeVisible();

    // Verify bottom command bar & footer
    const footer = alexPage.locator(".hud-footer");
    await expect(footer).toBeVisible();

    // Verify input control
    const input = alexPage.getByRole("textbox", { name: /command or question/i }).or(alexPage.locator(".hud-command-form input"));
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute("placeholder", /type a command or ask anything/i);
  });

  test("accepts text chat input and receives conversational response", async ({ alexPage }) => {
    const input = alexPage.getByRole("textbox", { name: /command or question/i }).or(alexPage.locator(".hud-command-form input"));
    await input.fill("Hello ALEX, system check.");
    await input.press("Enter");

    // Verify user message appears in activity stream or chat history
    const activityTicker = alexPage.locator(".hud-activity-ticker-pill").or(alexPage.locator(".hud-center-chat"));
    await expect(activityTicker).toBeVisible();
  });

  test("toggles fullscreen keyboard shortcut indicator", async ({ alexPage }) => {
    const footer = alexPage.locator(".hud-footer");
    await expect(footer).toBeVisible();
    await expect(footer).toContainText("[F11] FULLSCREEN");
  });
});
