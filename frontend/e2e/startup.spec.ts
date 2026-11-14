import { test, expect } from "./fixtures/testFixtures";

test.describe("ALEX Application Startup & Lifecycle", () => {
  test("loads the holographic HUD and verifies cognitive core status", async ({ alexPage }) => {
    // 1. Verify assistant branding is rendered
    const brand = alexPage.getByRole("button", { name: "Home" });
    await expect(brand).toBeVisible();
    await expect(brand).toContainText("ALEX");

    // 2. Verify title status and local cognitive core
    const titleArea = alexPage.locator(".hud-title");
    await expect(titleArea).toBeVisible();
    await expect(titleArea).toContainText("LOCAL COGNITIVE CORE");

    // 3. Verify digital clock and date
    const clock = alexPage.locator(".hud-clock");
    await expect(clock).toBeVisible();
  });

  test("runs startup diagnostic sequence when not skipping startup", async ({ page, injectDesktopBridge }) => {
    await injectDesktopBridge(page);
    await page.goto("/");
    // Verify startup sequence element or settling into ready state
    const readyHUD = page.locator(".hud-shell");
    await expect(readyHUD).toBeVisible({ timeout: 15000 });
  });

  test("displays System Monitor telemetry row without layout distortion", async ({ alexPage }) => {
    const monitor = alexPage.locator(".minimal-system-monitor");
    await expect(monitor).toBeVisible();
    await expect(monitor).toContainText("SYSTEM MONITOR");
    await expect(monitor).toContainText("CPU");
    await expect(monitor).toContainText("RAM");
  });
});

