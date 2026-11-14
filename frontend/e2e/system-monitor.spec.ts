import { test, expect } from "./fixtures/testFixtures";

test.describe("ALEX Real-Time System Monitoring & Telemetry", () => {
  test("displays live hardware metrics and subsystem status badges", async ({ alexPage }) => {
    const monitor = alexPage.locator(".minimal-system-monitor");
    await expect(monitor).toBeVisible();

    // Verify CPU & RAM values are rendered
    await expect(monitor.locator(".mon-util-item").first()).toBeVisible();

    // Verify Network status chip
    const netChip = monitor.locator(".mon-status-chip").first();
    await expect(netChip).toBeVisible();
    await expect(monitor).toContainText(/NETWORK/i);

    // Verify AI Engine chip
    await expect(monitor).toContainText(/AI ENGINE/i);

    // Verify Backend chip
    await expect(monitor).toContainText(/BACKEND/i);
  });
});

