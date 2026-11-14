import { test, expect } from "./fixtures/testFixtures";
import { openPanelFromDrawer, closeActiveModal } from "./helpers/hudHelper";

test.describe("ALEX Reminders & Scheduling Integration", () => {
  test("opens Reminders modal and lists pending reminders", async ({ alexPage }) => {
    await openPanelFromDrawer(alexPage, "setup", /reminders/i);

    const modal = alexPage.locator(".hud-modal-backdrop");
    await expect(modal).toBeVisible();
    await expect(modal).toContainText("REMINDERS");

    // Verify reminder item or input
    const reminderItem = modal.locator(".reminders-list, .reminder-item, p");
    await expect(reminderItem.first()).toBeVisible();

    await closeActiveModal(alexPage);
  });
});

