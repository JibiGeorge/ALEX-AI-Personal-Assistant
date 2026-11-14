import { test, expect } from "./fixtures/testFixtures";

test.describe("ALEX Voice, Audio & Speech Controls", () => {
  test("displays voice channel status and mic live toggle controls", async ({ alexPage }) => {
    const bottomBar = alexPage.locator(".hud-bottom-command-bar");
    await expect(bottomBar).toBeVisible();

    // Verify Mic button (Start Mic or Mic Live)
    const micLiveBtn = bottomBar.getByRole("button", { name: /^start microphone|^mic live/i });
    await expect(micLiveBtn).toBeVisible();

    // Verify Interrupt button
    const interruptBtn = bottomBar.getByRole("button", { name: /interrupt/i });
    await expect(interruptBtn).toBeVisible();

    // Verify Stop Mic button
    const stopMicBtn = bottomBar.getByRole("button", { name: /stop mic/i });
    await expect(stopMicBtn).toBeVisible();
  });

  test("toggles mic channel without crashing audio subsystem", async ({ alexPage }) => {
    const micLiveBtn = alexPage.getByRole("button", { name: /^start microphone|^mic live/i });
    await micLiveBtn.click();

    // Telemetry reflects state update
    const telemetry = alexPage.locator(".hud-status-stack, .minimal-system-monitor, .hud-waveform-status-label");
    await expect(telemetry.first()).toBeVisible();
  });
});

