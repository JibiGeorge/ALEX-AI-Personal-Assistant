import assert from "node:assert/strict";
import { chmodSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { verifySidecar } from "./verify-sidecar.mjs";

function temporaryProject() {
  const root = mkdtempSync(path.join(os.tmpdir(), "alex-sidecar-"));
  const bundle = path.join(root, "backend", "dist", "alex-backend");
  mkdirSync(bundle, { recursive: true });
  return { root, bundle };
}

test("requires a platform-matching Windows sidecar executable", () => {
  const { root, bundle } = temporaryProject();
  try {
    writeFileSync(path.join(bundle, "alex-backend"), "");
    assert.throws(() => verifySidecar(root, "win32"), /Build the backend on this OS/);

    const executable = path.join(bundle, "alex-backend.exe");
    writeFileSync(executable, "");
    assert.equal(verifySidecar(root, "win32"), executable);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test(
  "requires an executable Unix sidecar",
  { skip: process.platform === "win32" ? "Unix execute bits are unavailable on Windows" : false },
  () => {
  const { root, bundle } = temporaryProject();
  const executable = path.join(bundle, "alex-backend");
  try {
    writeFileSync(executable, "");
    assert.throws(() => verifySidecar(root, "linux"), /not executable/);
    chmodSync(executable, 0o755);
    assert.equal(verifySidecar(root, "linux"), executable);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
  },
);

test("rejects a missing sidecar bundle", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "alex-sidecar-empty-"));
  try {
    assert.throws(() => verifySidecar(root, "win32"), /bundle is missing/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
