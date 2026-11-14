import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

export async function openWorkspaceViaCommand(page: Page, commandText: string) {
  const input = page.getByRole("textbox", { name: /command or question/i }).or(page.locator(".hud-command-form input, input.hud-command-input"));
  await input.fill(commandText);
  await input.press("Enter");
  await expect(page.locator(".hud-workspace-window").or(page.locator(".hud-workspace-container"))).toBeVisible({ timeout: 10000 });
}

export async function closeActiveWorkspace(page: Page) {
  const closeBtn = page.getByRole("button", { name: /close window/i }).or(page.locator(".ws-close-btn"));
  if (await closeBtn.isVisible()) {
    await closeBtn.click();
  } else {
    // If minimized, click close on minimized dock
    const minCloseBtn = page.locator(".ws-min-close-btn");
    if (await minCloseBtn.isVisible()) {
      await minCloseBtn.click();
    }
  }
  await expect(page.locator(".hud-workspace-window")).not.toBeVisible({ timeout: 5000 });
}

export async function minimizeActiveWorkspace(page: Page) {
  const minBtn = page.getByRole("button", { name: /minimize window/i }).or(page.locator(".ws-min-btn"));
  await minBtn.click();
  await expect(page.locator(".ws-minimized-dock")).toBeVisible();
}

export async function restoreActiveWorkspace(page: Page) {
  const restoreBtn = page.getByRole("button", { name: /restore/i }).or(page.locator(".ws-minimized-chip")).first();
  await restoreBtn.click();
  await expect(page.locator(".hud-workspace-window")).toBeVisible();
  await expect(page.locator(".ws-minimized-dock")).not.toBeVisible();
}
