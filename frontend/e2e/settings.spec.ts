import { test, expect } from "./fixtures/testFixtures";
import { openPanelFromDrawer, closeActiveModal } from "./helpers/hudHelper";

test.describe("ALEX Settings & Configuration Management", () => {
  test("opens Settings modal and inspects customizable options", async ({ alexPage }) => {
    await openPanelFromDrawer(alexPage, "setup", /customise assistant/i);

    const modal = alexPage.locator(".hud-modal-backdrop");
    await expect(modal).toBeVisible();
    await expect(modal).toContainText("CUSTOMISE ASSISTANT");

    // Verify settings fields
    const assistantNameInput = modal.locator("input#assistant-name, input[name='assistant_name']").first();
    if (await assistantNameInput.isVisible()) {
      await expect(assistantNameInput).toHaveValue("ALEX");
    }

    await closeActiveModal(alexPage);
  });
});

