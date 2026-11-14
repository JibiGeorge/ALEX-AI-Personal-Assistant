import { test, expect } from "./fixtures/testFixtures";

test.describe("ALEX Desktop Security & Sandbox Boundaries", () => {
  test("enforces context isolation and disables renderer Node integration", async ({ alexPage }) => {
    const securityStatus = await alexPage.evaluate(() => {
      return {
        hasProcessVersions: typeof (window as any).process?.versions?.node !== "undefined",
        hasRequire: typeof (window as any).require !== "undefined",
        hasBuffer: typeof (window as any).Buffer !== "undefined",
        hasAlexBridge: typeof (window as any).alex !== "undefined",
      };
    });

    // Renderer must NOT have direct Node globals exposed in renderer world
    expect(securityStatus.hasRequire).toBe(false);
    expect(securityStatus.hasBuffer).toBe(false);

    // Desktop bridge MUST be present and structured
    expect(securityStatus.hasAlexBridge).toBe(true);
  });

  test("preload bridge exposes only allowlisted API methods", async ({ alexPage }) => {
    const bridgeMethods = await alexPage.evaluate(() => {
      return Object.keys((window as any).alex || {});
    });

    expect(bridgeMethods).toContain("getStatus");
    expect(bridgeMethods).toContain("getSystemMetrics");
    expect(bridgeMethods).toContain("getSettings");
    expect(bridgeMethods).toContain("sendMessage");
    expect(bridgeMethods).not.toContain("spawn");
    expect(bridgeMethods).not.toContain("exec");
  });
});

