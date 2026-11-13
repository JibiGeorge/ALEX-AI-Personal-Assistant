import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});

if (typeof HTMLCanvasElement !== "undefined") {
  // Mock getContext to avoid jsdom's "Not implemented: HTMLCanvasElement.prototype.getContext" console output
  HTMLCanvasElement.prototype.getContext = () => null;
}
