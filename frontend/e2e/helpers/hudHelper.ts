import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

export async function openSetupDrawer(page: Page) {
  const setupBtn = page.getByRole("button", { name: "Setup" });
  await setupBtn.click();
  await expect(page.locator(".hud-drawer")).toBeVisible();
}

export async function openControlsDrawer(page: Page) {
  const controlsBtn = page.getByRole("button", { name: "Controls" });
  await controlsBtn.click();
  await expect(page.locator(".hud-drawer")).toBeVisible();
}

export async function openPanelFromDrawer(page: Page, drawerName: "setup" | "controls", buttonText: string | RegExp) {
  if (drawerName === "setup") {
    await openSetupDrawer(page);
  } else {
    await openControlsDrawer(page);
  }
  const itemBtn = page.locator(".hud-drawer").getByRole("button", { name: buttonText });
  await itemBtn.click();
  await expect(page.locator(".hud-modal-backdrop")).toBeVisible();
}

export async function closeActiveModal(page: Page) {
  const closeBtn = page.getByRole("button", { name: /close panel/i });
  if (await closeBtn.isVisible()) {
    await closeBtn.click();
  } else {
    await page.keyboard.press("Escape");
  }
  await expect(page.locator(".hud-modal-backdrop")).not.toBeVisible({ timeout: 5000 });
}

export async function checkAvatarIsDocked(page: Page, isDocked: boolean) {
  const avatarStage = page.locator(".hud-avatar-stage");
  if (isDocked) {
    await expect(avatarStage).toHaveClass(/is-docked/);
  } else {
    await expect(avatarStage).not.toHaveClass(/is-docked/);
  }
}

