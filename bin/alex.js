#!/usr/bin/env node
// Alex Unified CLI Launcher for Node.js / npm environments
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");

const venvPython =
  process.platform === "win32"
    ? path.join(projectRoot, "backend", ".venv", "Scripts", "python.exe")
    : path.join(projectRoot, "backend", ".venv", "bin", "python");

const python =
  process.env.ALEX_PYTHON ||
  (existsSync(venvPython)
    ? venvPython
    : process.platform === "win32"
      ? "python"
      : "python3");

const args = ["-m", "launcher.cli", ...process.argv.slice(2)];

const child = spawn(python, args, {
  cwd: projectRoot,
  stdio: "inherit",
  env: {
    ...process.env,
    PYTHONPATH: `${projectRoot}${path.delimiter}${process.env.PYTHONPATH || ""}`,
  },
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 0);
  }
});

