import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

// Replicate the exact origin and canonical path validation from frontend/electron/main.ts
function isAllowedDevOrigin(testUrl: string, expectedDevUrl: string): boolean {
  try {
    const targetOrigin = new URL(testUrl).origin;
    const expectedOrigin = new URL(expectedDevUrl).origin;
    return targetOrigin === expectedOrigin;
  } catch {
    return false;
  }
}

function isAllowedProdFile(testUrl: string, expectedDistPath: string): boolean {
  try {
    if (!testUrl.startsWith("file://")) return false;
    const expectedPath = path.resolve(expectedDistPath);
    const actualPath = path.resolve(fileURLToPath(testUrl));
    return actualPath === expectedPath;
  } catch {
    return false;
  }
}

describe("Electron Security: Origin-based URL Validation", () => {
  const allowedDevUrl = "http://127.0.0.1:5173/";

  it("permits exact loopback development origins", () => {
    expect(isAllowedDevOrigin("http://127.0.0.1:5173/", allowedDevUrl)).toBe(true);
    expect(isAllowedDevOrigin("http://127.0.0.1:5173/chat", allowedDevUrl)).toBe(true);
    expect(isAllowedDevOrigin("http://127.0.0.1:5173/#/settings", allowedDevUrl)).toBe(true);
  });

  it("rejects malicious string-prefix domain bypass attempts", () => {
    // String prefix checks like url.startsWith("http://127.0.0.1:5173") would mistakenly match these
    expect(isAllowedDevOrigin("http://127.0.0.1:5173.attacker.com/", allowedDevUrl)).toBe(false);
    expect(isAllowedDevOrigin("http://127.0.0.1:51730/", allowedDevUrl)).toBe(false);
    expect(isAllowedDevOrigin("http://127.0.0.1:5173-evil.com/", allowedDevUrl)).toBe(false);
  });

  it("rejects unauthorized external protocols and ports", () => {
    expect(isAllowedDevOrigin("https://google.com/", allowedDevUrl)).toBe(false);
    expect(isAllowedDevOrigin("http://127.0.0.1:8765/", allowedDevUrl)).toBe(false);
    expect(isAllowedDevOrigin("http://localhost:5173/", allowedDevUrl)).toBe(false);
    expect(isAllowedDevOrigin("about:blank", allowedDevUrl)).toBe(false);
    expect(isAllowedDevOrigin("javascript:alert(1)", allowedDevUrl)).toBe(false);
  });

  it("handles malformed URLs gracefully without throwing uncaught exceptions", () => {
    expect(isAllowedDevOrigin("not a url", allowedDevUrl)).toBe(false);
    expect(isAllowedDevOrigin("", allowedDevUrl)).toBe(false);
    expect(isAllowedDevOrigin("://bad-url", allowedDevUrl)).toBe(false);
  });
});

describe("Electron Security: Production Canonical File Path Validation", () => {
  const mockDistIndex = path.resolve("/app/Alex/frontend/dist/index.html");

  it("permits exact canonical file URL matching the production bundle", () => {
    const fileUrl = `file://${mockDistIndex.replace(/\\/g, "/")}`;
    expect(isAllowedProdFile(fileUrl, mockDistIndex)).toBe(true);
  });

  it("rejects non-file protocols in production mode", () => {
    expect(isAllowedProdFile("http://127.0.0.1:5173/", mockDistIndex)).toBe(false);
    expect(isAllowedProdFile("https://evil.com/dist/index.html", mockDistIndex)).toBe(false);
  });

  it("rejects unauthorized local file URLs", () => {
    expect(isAllowedProdFile("file:///etc/passwd", mockDistIndex)).toBe(false);
    expect(isAllowedProdFile("file:///C:/Windows/System32/calc.exe", mockDistIndex)).toBe(false);
    expect(isAllowedProdFile("file:///tmp/attacker-payload.html", mockDistIndex)).toBe(false);
  });

  it("rejects path traversal escape attempts", () => {
    const traversalUrl = `file://${mockDistIndex.replace(/\\/g, "/")}/../../secret.txt`;
    expect(isAllowedProdFile(traversalUrl, mockDistIndex)).toBe(false);
  });
});

describe("Electron Settings Validation: HUD Style Support", () => {
  function validateHudStyle(hudStyle: unknown): string {
    if (
      hudStyle !== "face" &&
      hudStyle !== "core" &&
      hudStyle !== "robot" &&
      hudStyle !== "realistic_humanoid" &&
      hudStyle !== "existing_face" &&
      hudStyle !== "reactor_core"
    ) {
      throw new TypeError("HUD style must be face, core, or robot");
    }
    return hudStyle as string;
  }

  it("permits face, core, and robot HUD styles", () => {
    expect(validateHudStyle("face")).toBe("face");
    expect(validateHudStyle("core")).toBe("core");
    expect(validateHudStyle("robot")).toBe("robot");
    expect(validateHudStyle("realistic_humanoid")).toBe("realistic_humanoid");
  });

  it("rejects invalid HUD styles", () => {
    expect(() => validateHudStyle("invalid_style")).toThrow(TypeError);
    expect(() => validateHudStyle(123)).toThrow(TypeError);
    expect(() => validateHudStyle(null)).toThrow(TypeError);
  });
});

