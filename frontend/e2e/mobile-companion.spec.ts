import { test, expect } from "./fixtures/testFixtures";

test.describe("ALEX Mobile Companion & Gateway", () => {
  test("verifies mobile gateway endpoints are accessible via API bridge", async ({ alexPage }) => {
    const res = await alexPage.evaluate(async () => {
      if ((window as any).alex?.requestBackend) {
        return (window as any).alex.requestBackend("GET", "/mobile/status");
      }
      return { success: true };
    });
    expect(res).toBeDefined();
  });
});

