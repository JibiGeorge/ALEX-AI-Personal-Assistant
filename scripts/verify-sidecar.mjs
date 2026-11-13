import { existsSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptPath = fileURLToPath(import.meta.url);
const projectRoot = path.resolve(path.dirname(scriptPath), "..");

export function verifySidecar(root = projectRoot, platform = process.platform) {
  const executableName = platform === "win32" ? "alex-backend.exe" : "alex-backend";
  const bundle = path.join(root, "backend", "dist", "alex-backend");
  const executable = path.join(bundle, executableName);

  if (!existsSync(bundle) || !statSync(bundle).isDirectory()) {
    throw new Error(`Python sidecar bundle is missing: ${bundle}`);
  }
  if (!existsSync(executable) || !statSync(executable).isFile()) {
    throw new Error(
      `Python sidecar executable for ${platform} is missing: ${executable}. ` +
        "Build the backend on this OS before packaging.",
    );
  }
  if (platform !== "win32" && (statSync(executable).mode & 0o111) === 0) {
    throw new Error(`Python sidecar is not executable: ${executable}`);
  }

  return executable;
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  try {
    console.info(`Verified Python sidecar: ${verifySidecar()}`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
