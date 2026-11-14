import { test, expect } from "./fixtures/testFixtures";
import { openWorkspaceViaCommand, closeActiveWorkspace } from "./helpers/workspaceHelper";

test.describe("HUD Sandboxed Browser Workspace", () => {
  test("mounts browser stage with navigation toolbar, security pill, and address bar", async ({ alexPage }) => {
    await openWorkspaceViaCommand(alexPage, "open browser to https://example.com");

    const browserView = alexPage.locator(".ws-browser-view");
    await expect(browserView).toBeVisible();

    // Verify security pill
    const securityPill = browserView.locator(".ws-browser-security-pill");
    await expect(securityPill).toBeVisible();
    await expect(securityPill).toContainText("SECURE SANDBOX");

    // Verify address input
    const addressInput = browserView.locator("input.ws-browser-address-input");
    await expect(addressInput).toBeVisible();
    await expect(addressInput).toHaveValue(/example\.com/);

    // Verify navigation buttons (Back, Forward, Reload)
    const backBtn = browserView.getByRole("button", { name: /browser back/i });
    const forwardBtn = browserView.getByRole("button", { name: /browser forward/i });
    const reloadBtn = browserView.getByRole("button", { name: /browser reload/i });
    await expect(backBtn).toBeVisible();
    await expect(forwardBtn).toBeVisible();
    await expect(reloadBtn).toBeVisible();

    // Verify sandboxed iframe
    const iframe = browserView.locator("iframe.ws-browser-iframe");
    await expect(iframe).toBeVisible();
    await expect(iframe).toHaveAttribute("sandbox", /allow-scripts/);

    await closeActiveWorkspace(alexPage);
  });
});

