import {
  app,
  BrowserWindow,
  desktopCapturer,
  dialog,
  ipcMain,
  Notification,
  session,
  shell,
  screen,
  systemPreferences,
  type IpcMainInvokeEvent,
} from "electron";
import { spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import { createServer } from "node:net";
import path from "node:path";
import { randomBytes } from "node:crypto";
import { fileURLToPath } from "node:url";

import type {
  ApiStatus,
  AppSettings,
  FileAttachment,
  MemoryCategory,
  MemoryEntry,
  MemoryWrite,
  LiveVoiceEvent,
  SettingsView,
  SystemMetrics,
  SystemAlert,
  ActionDescriptor,
  ActionExecution,
  Reminder,
  WebSearchRequest,
} from "../src/types/api";
import { createScreenAttachment } from "./screenCapture";

const isDevelopment = !app.isPackaged;
app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");
const allowedCategories: MemoryCategory[] = [
  "identity",
  "preferences",
  "projects",
  "relationships",
  "wishes",
  "notes",
];

let mainWindow: BrowserWindow | null = null;
let backend: ChildProcess | null = null;
let backendPort = 0;
let backendToken = "";
let backendOutput = "";
let backendSpawnError: Error | null = null;
let quittingAfterBackendStop = false;
let isLauncherManagedBackend = false;
let liveSocket: WebSocket | null = null;
let liveConnectPromise: Promise<void> | null = null;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validateSettings(value: unknown): Partial<AppSettings> {
  if (!isRecord(value)) throw new TypeError("Settings must be an object");
  const allowed = new Set([
    "assistant_name",
    "user_name",
    "accent_color",
    "operating_system",
    "voice_name",
    "hud_style",
    "audio_input_device_id",
    "audio_output_device_id",
    "push_to_talk_enabled",
  ]);
  if (Object.keys(value).some((key) => !allowed.has(key))) {
    throw new TypeError("Settings contain an unsupported field");
  }
  const settings: Partial<AppSettings> = {};
  if (
    "assistant_name" in value &&
    (typeof value.assistant_name !== "string" ||
      value.assistant_name.trim().length < 1 ||
      value.assistant_name.length > 50)
  ) {
    throw new TypeError("Assistant name must contain 1 to 50 characters");
  }
  if ("assistant_name" in value && typeof value.assistant_name === "string") {
    settings.assistant_name = value.assistant_name;
  }
  if (
    "user_name" in value &&
    (typeof value.user_name !== "string" || value.user_name.length > 80)
  ) {
    throw new TypeError("User name must be at most 80 characters");
  }
  if ("user_name" in value && typeof value.user_name === "string") {
    settings.user_name = value.user_name;
  }
  if (
    "accent_color" in value &&
    (typeof value.accent_color !== "string" ||
      !/^#[0-9a-fA-F]{6}$/.test(value.accent_color))
  ) {
    throw new TypeError("Accent color must be a six-digit hex color");
  }
  if ("accent_color" in value && typeof value.accent_color === "string") {
    settings.accent_color = value.accent_color;
  }
  if ("operating_system" in value) {
    const operatingSystem = value.operating_system;
    if (
      operatingSystem !== "Windows" &&
      operatingSystem !== "macOS" &&
      operatingSystem !== "Linux"
    ) {
      throw new TypeError("Operating system must be Windows, macOS, or Linux");
    }
    settings.operating_system = operatingSystem;
  }
  if ("voice_name" in value) {
    const voice = value.voice_name;
    if (
      voice !== "Charon" &&
      voice !== "Puck" &&
      voice !== "Kore" &&
      voice !== "Fenrir" &&
      voice !== "Aoede"
    ) {
      throw new TypeError("Assistant voice is not supported");
    }
    settings.voice_name = voice;
  }
  if ("hud_style" in value) {
    const hudStyle = value.hud_style;
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
    settings.hud_style = hudStyle;
  }
  for (const key of ["audio_input_device_id", "audio_output_device_id"] as const) {
    if (key in value) {
      const deviceId = value[key];
      if (typeof deviceId !== "string" || deviceId.length > 512) {
        throw new TypeError("Audio device selection is invalid");
      }
      settings[key] = deviceId;
    }
  }
  if ("push_to_talk_enabled" in value) {
    if (typeof value.push_to_talk_enabled !== "boolean") {
      throw new TypeError("Push-to-talk setting must be a boolean");
    }
    settings.push_to_talk_enabled = value.push_to_talk_enabled;
  }
  return settings;
}

function validateApiKey(value: unknown): string {
  if (
    typeof value !== "string" ||
    value.trim().length < 16 ||
    value.length > 512
  ) {
    throw new TypeError("API key must contain between 16 and 512 characters");
  }
  return value;
}

function validateMemoryWrite(value: unknown): MemoryWrite {
  if (!isRecord(value) || typeof value.value !== "string") {
    throw new TypeError("Memory entry must contain a text value");
  }
  if (value.value.trim().length < 1 || value.value.length > 4000) {
    throw new TypeError("Memory value must contain 1 to 4000 characters");
  }
  return { value: value.value };
}

function validateMemoryAddress(category: unknown, key: unknown): [MemoryCategory, string] {
  if (
    typeof category !== "string" ||
    !allowedCategories.includes(category as MemoryCategory)
  ) {
    throw new TypeError("Memory category is not supported");
  }
  if (typeof key !== "string" || key.trim().length < 1 || key.length > 80) {
    throw new TypeError("Memory key must contain 1 to 80 characters");
  }
  return [category as MemoryCategory, key];
}

function validateReminderMessage(value: unknown): string {
  if (typeof value !== "string" || value.trim().length < 1 || value.length > 200) {
    throw new TypeError("Reminder message must contain 1 to 200 characters");
  }
  return value.trim();
}

function validateReminderDate(value: unknown): string {
  if (typeof value !== "string" || value.length > 64 || !Number.isFinite(Date.parse(value))) {
    throw new TypeError("Reminder time must be a valid ISO date-time");
  }
  if (!/(Z|[+-]\d{2}:\d{2})$/i.test(value)) {
    throw new TypeError("Reminder time must include a timezone");
  }
  return value;
}

function validateReminderId(value: unknown): string {
  if (
    typeof value !== "string" ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
  ) {
    throw new TypeError("Reminder identifier is invalid");
  }
  return value;
}

function validateActionId(value: unknown): string {
  if (
    typeof value !== "string" ||
    !/^[a-z][a-z0-9_.-]{0,99}$/.test(value)
  ) {
    throw new TypeError("Action identifier is invalid");
  }
  return value;
}

function validateConversationTurn(
  text: unknown,
  conversationId: unknown,
  attachmentValue: unknown,
): { text: string; conversation_id: string | null; attachment?: FileAttachment } {
  if (typeof text !== "string" || text.trim().length < 1 || text.length > 4000) {
    throw new TypeError("Message must contain 1 to 4000 characters");
  }
  if (
    conversationId !== null &&
    (typeof conversationId !== "string" ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
        conversationId,
      ))
  ) {
    throw new TypeError("Conversation identifier is invalid");
  }
  if (attachmentValue === undefined || attachmentValue === null) {
    return { text: text.trim(), conversation_id: conversationId };
  }
  if (!isRecord(attachmentValue)) {
    throw new TypeError("Attachment must be a file object");
  }
  const { name, mime_type: mimeType, data_base64: dataBase64 } = attachmentValue;
  const supportedMimeTypes = new Set([
    "application/json",
    "application/pdf",
    "application/xml",
    "audio/aac",
    "audio/flac",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/csv",
    "text/markdown",
    "text/plain",
    "video/mp4",
    "video/quicktime",
    "video/webm",
  ]);
  if (
    typeof name !== "string" ||
    name.length < 1 ||
    name.length > 255 ||
    /[\\/]/.test(name) ||
    typeof mimeType !== "string" ||
    !supportedMimeTypes.has(mimeType) ||
    typeof dataBase64 !== "string" ||
    dataBase64.length < 4 ||
    dataBase64.length > 11_184_812 ||
    !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(
      dataBase64,
    ) ||
    Buffer.from(dataBase64, "base64").byteLength > 8 * 1024 * 1024
  ) {
    throw new TypeError("Attachment is invalid or exceeds the supported 8 MiB limit");
  }
  return {
    text: text.trim(),
    conversation_id: conversationId,
    attachment: { name, mime_type: mimeType, data_base64: dataBase64 },
  };
}

function validateWebSearchRequest(value: unknown): WebSearchRequest {
  if (!isRecord(value)) throw new TypeError("Search request must be an object");
  const allowed = new Set(["query", "mode", "items", "aspect"]);
  if (Object.keys(value).some((key) => !allowed.has(key))) {
    throw new TypeError("Search request contains an unsupported field");
  }
  const modes = ["search", "news", "research", "price", "compare"] as const;
  if (
    typeof value.query !== "string" ||
    !value.query.trim() ||
    value.query.length > 4000 ||
    (value.mode !== undefined &&
      (typeof value.mode !== "string" || !modes.includes(value.mode as (typeof modes)[number])))
  ) {
    throw new TypeError("Search query or mode is invalid");
  }
  if (
    value.items !== undefined &&
    (!Array.isArray(value.items) ||
      value.items.length > 8 ||
      value.items.some(
        (item) => typeof item !== "string" || !item.trim() || item.length > 100,
      ))
  ) {
    throw new TypeError("Comparison items must be non-empty text with at most 8 entries");
  }
  if (
    value.aspect !== undefined &&
    (typeof value.aspect !== "string" || !value.aspect.trim() || value.aspect.length > 200)
  ) {
    throw new TypeError("Comparison aspect is invalid");
  }
  return {
    query: value.query.trim(),
    mode: (value.mode as (typeof modes)[number] | undefined) ?? "search",
    ...(value.items === undefined ? {} : { items: value.items as string[] }),
    ...(value.aspect === undefined ? {} : { aspect: value.aspect as string }),
  };
}

function validateExternalUrl(value: unknown): string {
  if (typeof value !== "string" || value.length > 2048) {
    throw new TypeError("External URL is invalid");
  }
  let url: URL;
  try {
    url = new URL(value);
  } catch (error) {
    throw new TypeError("External URL must be a valid HTTP or HTTPS address", { cause: error });
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new TypeError("Only HTTP and HTTPS external links can be opened");
  }
  return url.href;
}

function weatherSearchUrl(cityValue: unknown, whenValue: unknown): string {
  if (
    typeof cityValue !== "string" ||
    cityValue.trim().length < 1 ||
    cityValue.length > 150
  ) {
    throw new TypeError("City must contain 1 to 150 characters");
  }
  if (whenValue !== undefined && typeof whenValue !== "string") {
    throw new TypeError("Weather search time must be text");
  }
  const when = typeof whenValue === "string" ? whenValue.trim() : "";
  if (when.length > 100) {
    throw new TypeError("Weather search time must be at most 100 characters");
  }
  const url = new URL("https://www.google.com/search");
  url.searchParams.set(
    "q",
    `weather in ${cityValue.trim()} ${when || "today"}`,
  );
  return validateExternalUrl(url.href);
}

function getLoginItemStatus() {
  const supported = process.platform === "win32" || process.platform === "darwin";
  return {
    supported,
    enabled: supported ? app.getLoginItemSettings().openAtLogin : false,
    shortcutSupported: process.platform === "win32",
  };
}

function setLoginItemEnabled(value: unknown) {
  if (typeof value !== "boolean") {
    throw new TypeError("Auto-start state must be a boolean");
  }
  if (process.platform !== "win32" && process.platform !== "darwin") {
    throw new Error("Auto-start is not supported on this platform");
  }
  app.setLoginItemSettings({
    openAtLogin: value,
    path: process.execPath,
    args: isDevelopment ? [app.getAppPath()] : [],
  });
  return getLoginItemStatus();
}

function createDesktopShortcut(): void {
  if (process.platform !== "win32") {
    throw new Error("Desktop shortcut creation is currently supported on Windows only");
  }
  const shortcutPath = path.join(app.getPath("desktop"), `${app.getName()}.lnk`);
  if (existsSync(shortcutPath)) {
    throw new Error("An Alex desktop shortcut already exists");
  }
  const created = shell.writeShortcutLink(shortcutPath, "create", {
    target: process.execPath,
    args: isDevelopment ? `"${app.getAppPath()}"` : "",
    description: "Open Alex, your desktop assistant",
    icon: process.execPath,
  });
  if (!created) {
    throw new Error("Windows could not create the Alex desktop shortcut");
  }
}

function dispatchVoiceEvent(event: LiveVoiceEvent): void {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("alex:voice:event", event);
  }
}

function handleVoiceSocketMessage(data: unknown): void {
  if (typeof data === "string") {
    let payload: unknown;
    try {
      payload = JSON.parse(data);
    } catch (error) {
      console.error("Python backend sent invalid voice-event JSON", error);
      return;
    }
    if (!isRecord(payload) || typeof payload.type !== "string") return;
    if (payload.type === "connected" && typeof payload.model === "string") {
      dispatchVoiceEvent({ type: "connected", model: payload.model });
    } else if (
      payload.type === "turn_complete" &&
      typeof payload.input_text === "string" &&
      typeof payload.output_text === "string" &&
      typeof payload.interrupted === "boolean"
    ) {
      dispatchVoiceEvent({
        type: "turn_complete",
        input_text: payload.input_text,
        output_text: payload.output_text,
        interrupted: payload.interrupted,
      });
    } else if (payload.type === "interrupted") {
      dispatchVoiceEvent({ type: "interrupted" });
    } else if (payload.type === "error" && typeof payload.message === "string") {
      dispatchVoiceEvent({ type: "error", message: payload.message });
    }
    return;
  }
  if (data instanceof ArrayBuffer) {
    if (data.byteLength <= 8192) {
      dispatchVoiceEvent({ type: "audio", pcm: new Uint8Array(data) });
    }
    return;
  }
  if (ArrayBuffer.isView(data)) {
    const bytes = new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
    if (bytes.byteLength <= 8192) {
      dispatchVoiceEvent({ type: "audio", pcm: Uint8Array.from(bytes) });
    }
  }
}

async function startLiveVoice(): Promise<void> {
  if (liveSocket?.readyState === WebSocket.OPEN) return;
  if (liveConnectPromise) return liveConnectPromise;

  if (!backendPort) {
    throw new Error("Python backend is initializing. Please wait a moment and try again.");
  }

  const url = new URL(`ws://127.0.0.1:${backendPort}/api/v1/conversation/live`);
  url.searchParams.set("token", backendToken);
  const socket = new WebSocket(url);
  socket.binaryType = "arraybuffer";
  liveSocket = socket;

  let ready = false;
  let lastErrorMessage = "";
  const connection = new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => {
      socket.close();
      reject(new Error("Voice connection timed out. Check your internet connection or Gemini API key in Settings."));
    }, 18000);
    socket.addEventListener(
      "error",
      () => {
        if (liveSocket !== socket) return;
        clearTimeout(timeout);
        if (!ready) reject(new Error(lastErrorMessage || "Could not connect to the Python voice service."));
        else dispatchVoiceEvent({
          type: "error",
          message: "The local voice connection encountered an error.",
        });
      },
      { once: true },
    );
    socket.addEventListener(
      "close",
      (event) => {
        clearTimeout(timeout);
        const isCurrentSocket = liveSocket === socket;
        if (isCurrentSocket) liveSocket = null;
        if (isCurrentSocket && !ready) {
          const defaultMsg = event.code === 1008
            ? "Gemini API key is required for voice. Please configure it in Settings."
            : `Voice session closed before connecting (${event.code}).`;
          reject(new Error(lastErrorMessage || defaultMsg));
        }
        if (isCurrentSocket && ready && event.code !== 1000 && event.code !== 1008) {
          dispatchVoiceEvent({
            type: "error",
            message: "The voice session disconnected unexpectedly.",
          });
        }
      },
    );
    socket.addEventListener("message", (event) => {
      if (liveSocket !== socket) return;
      if (typeof event.data === "string") {
        let payload: unknown;
        try {
          payload = JSON.parse(event.data);
        } catch (error) {
          handleVoiceSocketMessage(event.data);
          return;
        }
        if (
          isRecord(payload) &&
          payload.type === "connected" &&
          typeof payload.model === "string"
        ) {
          ready = true;
          clearTimeout(timeout);
          resolve();
        } else if (
          isRecord(payload) &&
          payload.type === "error" &&
          typeof payload.message === "string"
        ) {
          lastErrorMessage = payload.message;
          if (!ready) {
            clearTimeout(timeout);
            reject(new Error(payload.message));
            return;
          }
        }
      }
      handleVoiceSocketMessage(event.data);
    });
  });
  liveConnectPromise = connection;
  try {
    await connection;
  } catch (error) {
    if (liveSocket === socket) liveSocket = null;
    if (error instanceof Error) throw error;
    throw new Error("Could not start the voice session.");
  } finally {
    if (liveConnectPromise === connection) liveConnectPromise = null;
  }
}

function stopLiveVoice(): void {
  const socket = liveSocket;
  liveSocket = null;
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "stop" }));
    socket.close(1000, "User stopped voice session");
  } else if (socket && socket.readyState < WebSocket.CLOSING) {
    socket.close();
  }
}

function isAllowedDevOrigin(testUrl: string, expectedDevUrl: string): boolean {
  try {
    const target = new URL(testUrl);
    const expected = new URL(expectedDevUrl);
    if (target.origin === expected.origin) return true;
    const isLocalhostTarget = target.hostname === "localhost" || target.hostname === "127.0.0.1";
    const isLocalhostExpected = expected.hostname === "localhost" || expected.hostname === "127.0.0.1";
    return (
      isLocalhostTarget &&
      isLocalhostExpected &&
      (target.port === expected.port || (!target.port && !expected.port))
    );
  } catch {
    return false;
  }
}

function isAllowedProdFile(testUrl: string): boolean {
  try {
    if (!testUrl.startsWith("file://")) return false;
    const expectedPath = path.resolve(__dirname, "../../dist/index.html");
    const actualPath = path.resolve(fileURLToPath(testUrl));
    return actualPath === expectedPath;
  } catch {
    return false;
  }
}

async function configureMicrophonePermission(): Promise<void> {
  if (process.platform === "darwin") {
    try {
      const status = systemPreferences.getMediaAccessStatus("microphone");
      if (status === "not-determined") {
        await systemPreferences.askForMediaAccess("microphone");
      }
    } catch (error) {
      console.warn("Could not query or request macOS microphone access:", error);
    }
  }

  const devUrl = process.env.ALEX_FRONTEND_URL || "http://127.0.0.1:5173/";
  const isTrustedWindow = (contents: Electron.WebContents) => {
    if (!mainWindow || contents !== mainWindow.webContents) return false;
    const senderUrl = contents.getURL();
    if (!senderUrl || senderUrl === "about:blank") return true;
    if (isDevelopment) return isAllowedDevOrigin(senderUrl, devUrl);
    return isAllowedProdFile(senderUrl);
  };
  session.defaultSession.setPermissionRequestHandler(
    (contents, permission, callback, details) => {
      if (!isTrustedWindow(contents)) {
        callback(false);
        return;
      }
      if ((permission as string) === "microphone") {
        callback(true);
        return;
      }
      if (permission === "media") {
        const mediaTypes = (details as any).mediaTypes as string[] | undefined;
        const mediaType = (details as any).mediaType as string | undefined;
        const audioRequested =
          (Array.isArray(mediaTypes) && mediaTypes.includes("audio")) ||
          mediaType === "audio" ||
          (!mediaTypes && !mediaType);
        const videoRequested =
          (Array.isArray(mediaTypes) && mediaTypes.includes("video")) ||
          mediaType === "video";
        callback(audioRequested && !videoRequested);
        return;
      }
      callback(false);
    },
  );
  session.defaultSession.setPermissionCheckHandler((contents, permission, _origin, details) => {
    if (!contents || !isTrustedWindow(contents)) return false;
    if ((permission as string) === "microphone") return true;
    if (permission === "media") {
      const mediaType = (details as any).mediaType as string | undefined;
      return mediaType === "audio" || !mediaType;
    }
    return false;
  });

  // Rewrite YouTube headers to bypass external domain embedding restrictions (Errors 150 / 101)
  const ytFilter = {
    urls: [
      "*://*.youtube.com/*",
      "*://*.youtube-nocookie.com/*",
      "*://*.googlevideo.com/*",
    ],
  };

  session.defaultSession.webRequest.onBeforeSendHeaders(ytFilter, (details, callback) => {
    const requestHeaders = { ...details.requestHeaders };
    requestHeaders["Referer"] = "https://www.youtube.com/";
    requestHeaders["Origin"] = "https://www.youtube.com";
    callback({ requestHeaders });
  });

  session.defaultSession.webRequest.onHeadersReceived(ytFilter, (details, callback) => {
    const responseHeaders = { ...details.responseHeaders };
    delete responseHeaders["x-frame-options"];
    delete responseHeaders["X-Frame-Options"];
    delete responseHeaders["content-security-policy"];
    delete responseHeaders["Content-Security-Policy"];
    callback({ responseHeaders });
  });
}

function assertTrustedSender(event: IpcMainInvokeEvent): void {
  if (
    !mainWindow ||
    event.sender !== mainWindow.webContents ||
    event.senderFrame !== mainWindow.webContents.mainFrame
  ) {
    throw new Error("Untrusted IPC sender");
  }
  const senderUrl = event.senderFrame.url;
  if (isDevelopment) {
    const devUrl = process.env.ALEX_FRONTEND_URL || "http://127.0.0.1:5173/";
    if (!isAllowedDevOrigin(senderUrl, devUrl)) {
      throw new Error("IPC sender origin is not allowed");
    }
  } else if (!isAllowedProdFile(senderUrl)) {
    throw new Error("IPC sender file is not allowed");
  }
}

async function findAvailablePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        server.close();
        reject(new Error("Could not allocate a backend port"));
        return;
      }
      const { port } = address;
      server.close((error) => (error ? reject(error) : resolve(port)));
    });
  });
}

async function startBackend(): Promise<void> {
  if (process.env.ALEX_BACKEND_PORT && process.env.ALEX_API_TOKEN) {
    isLauncherManagedBackend = true;
    backendPort = parseInt(process.env.ALEX_BACKEND_PORT, 10);
    backendToken = process.env.ALEX_API_TOKEN;
    console.info(`[electron] Connecting to launcher-managed backend on port ${backendPort}`);
    await waitForBackend();
    return;
  }
  backendPort = await findAvailablePort();
  backendToken = randomBytes(32).toString("base64url");
  backendOutput = "";

  const backendSource = path.resolve(__dirname, "../../../backend");
  const developmentPython =
    process.env.ALEX_PYTHON ||
    (process.platform === "win32"
      ? path.join(backendSource, ".venv", "Scripts", "python.exe")
      : path.join(backendSource, ".venv", "bin", "python"));
  const executable = isDevelopment
    ? process.env.ALEX_PYTHON ||
      (existsSync(developmentPython) ? developmentPython : "python")
    : path.join(
        process.resourcesPath,
        "backend",
        process.platform === "win32" ? "alex-backend.exe" : "alex-backend",
      );
  const args = isDevelopment
    ? ["-m", "app.main", "--host", "127.0.0.1", "--port", String(backendPort)]
    : ["--host", "127.0.0.1", "--port", String(backendPort)];
  const backendCwd = isDevelopment ? backendSource : process.resourcesPath;

  backend = spawn(executable, args, {
    cwd: backendCwd,
    env: {
      ...process.env,
      ALEX_API_TOKEN: backendToken,
      ALEX_DATA_DIR: app.getPath("userData"),
      ALEX_LOG_LEVEL: process.env.ALEX_LOG_LEVEL || "INFO",
    },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });
  backendSpawnError = null;
  backend.on("error", (error) => {
    backendSpawnError = error;
  });

  backend.stdout?.on("data", (chunk: Buffer) => {
    backendOutput = `${backendOutput}${chunk.toString("utf8")}`.slice(-8000);
    for (const line of chunk.toString("utf8").split(/\r?\n/)) {
      if (line.trim()) console.info(`[backend] ${line}`);
    }
  });
  backend.stderr?.on("data", (chunk: Buffer) => {
    backendOutput = `${backendOutput}${chunk.toString("utf8")}`.slice(-8000);
    for (const line of chunk.toString("utf8").split(/\r?\n/)) {
      if (line.trim()) console.error(`[backend] ${line}`);
    }
  });

  await waitForBackend();
}

async function waitForBackend(): Promise<void> {
  const deadline = Date.now() + 20_000;
  let lastError = "No response";
  while (Date.now() < deadline) {
    if (!isLauncherManagedBackend && backendSpawnError) {
      throw new Error(`Could not launch Python backend: ${backendSpawnError.message}`);
    }
    if (!isLauncherManagedBackend && (!backend || backend.exitCode !== null)) {
      throw new Error(
        `Python backend exited before becoming ready. ${backendOutput.slice(-1500)}`,
      );
    }
    try {
      const response = await fetch(
        `http://127.0.0.1:${backendPort}/api/v1/health`,
        {
          headers: { Authorization: `Bearer ${backendToken}` },
          signal: AbortSignal.timeout(1200),
        },
      );
      if (response.ok) return;
      lastError = `Health check returned HTTP ${response.status}`;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error(`Python backend did not become ready: ${lastError}`);
}

async function backendRequest<T>(
  method: string,
  route: string,
  body?: unknown,
): Promise<T> {
  if (!isLauncherManagedBackend && (!backend || backend.exitCode !== null)) {
    throw new Error("Python backend is not running");
  }
  const response = await fetch(
    `http://127.0.0.1:${backendPort}${route}`,
    {
      method,
      headers: {
        Authorization: `Bearer ${backendToken}`,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(
        route === "/api/v1/wake/install"
          ? 300_000
          : route === "/api/v1/conversation/turn"
            ? 35_000
            : 10_000,
      ),
    },
  );
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => undefined);
    const detail =
      isRecord(payload) && typeof payload.detail === "string"
        ? payload.detail
        : `Backend request failed (${response.status})`;
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function registerIpc(): void {
  ipcMain.handle("alex:window:toggle-fullscreen", (event) => {
    assertTrustedSender(event);
    if (!mainWindow) throw new Error("Application window is unavailable");
    mainWindow.setFullScreen(true);
    return mainWindow.isFullScreen();
  });
  ipcMain.handle("alex:microphone:ensure-access", async (event) => {
    assertTrustedSender(event);
    if (process.platform === "darwin") {
      try {
        let status = systemPreferences.getMediaAccessStatus("microphone");
        if (status === "not-determined") {
          const granted = await systemPreferences.askForMediaAccess("microphone");
          return { granted, status: granted ? "granted" : "denied" };
        }
        return { granted: status === "granted", status };
      } catch (err) {
        return { granted: true, status: "unknown" };
      }
    }
    return { granted: true, status: "granted" };
  });
  ipcMain.handle("alex:status", async (event) => {
    assertTrustedSender(event);
    return backendRequest<ApiStatus>("GET", "/api/v1/health");
  });
  ipcMain.handle("alex:system:metrics", async (event) => {
    assertTrustedSender(event);
    return backendRequest<SystemMetrics>("GET", "/api/v1/system/metrics");
  });
  ipcMain.handle("alex:system:verification", async (event) => {
    assertTrustedSender(event);
    return backendRequest("GET", "/api/v1/system/verification");
  });
  ipcMain.handle("alex:system:alerts", async (event) => {
    assertTrustedSender(event);
    return backendRequest<{ alerts: SystemAlert[] }>("GET", "/api/v1/system/alerts");
  });
  ipcMain.handle("alex:system:briefing", async (event) => {
    assertTrustedSender(event);
    return backendRequest<any>("GET", "/api/v1/system/briefing");
  });
  ipcMain.handle("alex:system:alert:notify", (event, message: unknown) => {
    assertTrustedSender(event);
    const body = validateReminderMessage(message);
    if (!Notification.isSupported()) {
      throw new Error("Desktop notifications are unavailable on this system");
    }
    new Notification({ title: "Alex system alert", body }).show();
  });
  ipcMain.handle("alex:actions:list", async (event) => {
    assertTrustedSender(event);
    return backendRequest<{ actions: ActionDescriptor[] }>("GET", "/api/v1/actions");
  });
  ipcMain.handle("alex:actions:history", async (event) => {
    assertTrustedSender(event);
    return backendRequest<{ executions: ActionExecution[] }>(
      "GET",
      "/api/v1/actions/history",
    );
  });
  ipcMain.handle(
    "alex:actions:enable",
    async (event, actionId: unknown, enabled: unknown) => {
      assertTrustedSender(event);
      if (typeof enabled !== "boolean") throw new TypeError("Enabled must be a boolean");
      return backendRequest<ActionDescriptor>(
        "PATCH",
        `/api/v1/actions/${encodeURIComponent(validateActionId(actionId))}`,
        { enabled },
      );
    },
  );
  ipcMain.handle(
    "alex:actions:execute",
    async (event, actionId: unknown, parameters: unknown, confirmed: unknown) => {
      assertTrustedSender(event);
      if (!isRecord(parameters) || typeof confirmed !== "boolean") {
        throw new TypeError("Action execution request is invalid");
      }
      return backendRequest<ActionExecution>(
        "POST",
        `/api/v1/actions/${encodeURIComponent(validateActionId(actionId))}/execute`,
        { parameters, confirmed },
      );
    },
  );
  ipcMain.handle("alex:settings:get", async (event) => {
    assertTrustedSender(event);
    return backendRequest<SettingsView>("GET", "/api/v1/settings");
  });
  ipcMain.handle("alex:settings:update", async (event, settings: unknown) => {
    assertTrustedSender(event);
    return backendRequest<SettingsView>(
      "PATCH",
      "/api/v1/settings",
      validateSettings(settings),
    );
  });
  ipcMain.handle("alex:settings:key", async (event, key: unknown) => {
    assertTrustedSender(event);
    return backendRequest<{ configured: boolean }>(
      "PUT",
      "/api/v1/settings/api-key",
      { api_key: validateApiKey(key) },
    );
  });
  ipcMain.handle("alex:memory:list", async (event) => {
    assertTrustedSender(event);
    return backendRequest<{ entries: MemoryEntry[] }>("GET", "/api/v1/memory");
  });
  ipcMain.handle("alex:reminders:list", async (event) => {
    assertTrustedSender(event);
    return backendRequest<{ reminders: Reminder[] }>("GET", "/api/v1/reminders");
  });
  ipcMain.handle("alex:reminders:create", async (event, message: unknown, dueAt: unknown) => {
    assertTrustedSender(event);
    return backendRequest<Reminder>("POST", "/api/v1/reminders", {
      message: validateReminderMessage(message),
      due_at: validateReminderDate(dueAt),
    });
  });
  ipcMain.handle("alex:reminders:cancel", async (event, reminderId: unknown) => {
    assertTrustedSender(event);
    await backendRequest<void>(
      "DELETE",
      `/api/v1/reminders/${encodeURIComponent(validateReminderId(reminderId))}`,
    );
  });
  ipcMain.handle("alex:reminders:due", async (event) => {
    assertTrustedSender(event);
    return backendRequest<{ reminders: Reminder[] }>("GET", "/api/v1/reminders/due");
  });
  ipcMain.handle("alex:reminders:delivered", async (event, reminderId: unknown) => {
    assertTrustedSender(event);
    return backendRequest<Reminder>(
      "POST",
      `/api/v1/reminders/${encodeURIComponent(validateReminderId(reminderId))}/delivered`,
    );
  });
  ipcMain.handle("alex:reminders:notify", (event, message: unknown) => {
    assertTrustedSender(event);
    const body = validateReminderMessage(message);
    if (!Notification.isSupported()) {
      throw new Error("Desktop notifications are unavailable on this system");
    }
    new Notification({ title: "Alex reminder", body }).show();
  });
  ipcMain.handle(
    "alex:memory:upsert",
    async (event, category: unknown, key: unknown, body: unknown) => {
      assertTrustedSender(event);
      const [validCategory, validKey] = validateMemoryAddress(category, key);
      return backendRequest<MemoryEntry>(
        "PUT",
        `/api/v1/memory/${encodeURIComponent(validCategory)}/${encodeURIComponent(validKey)}`,
        validateMemoryWrite(body),
      );
    },
  );
  ipcMain.handle(
    "alex:memory:delete",
    async (event, category: unknown, key: unknown) => {
      assertTrustedSender(event);
      const [validCategory, validKey] = validateMemoryAddress(category, key);
      await backendRequest<void>(
        "DELETE",
        `/api/v1/memory/${encodeURIComponent(validCategory)}/${encodeURIComponent(validKey)}`,
      );
      return true;
    },
  );
  ipcMain.handle(
    "alex:conversation:turn",
    async (event, text: unknown, conversationId: unknown, attachment: unknown) => {
      assertTrustedSender(event);
      return backendRequest(
        "POST",
        "/api/v1/conversation/turn",
        validateConversationTurn(text, conversationId, attachment),
      );
    },
  );
  ipcMain.handle("alex:screen:capture", async (event) => {
    assertTrustedSender(event);
    if (!mainWindow) throw new Error("Application window is unavailable");
    const displays = screen.getAllDisplays();
    if (displays.length === 0) throw new Error("No displays are available for screen capture.");
    const buttons = displays.map((_, index) => `Capture display ${index + 1}`);
    const cancelId = buttons.length;
    buttons.push("Cancel");
    const selection = await dialog.showMessageBox(mainWindow, {
      type: "question",
      title: "Capture screen",
      message: "Choose a display to capture.",
      detail: "Alex will show a preview. Nothing is sent until you send a message.",
      buttons,
      cancelId,
      defaultId: cancelId,
      noLink: true,
    });
    if (selection.response === cancelId) return null;

    const selectedDisplay = displays[selection.response];
    if (!selectedDisplay) throw new Error("The selected display is no longer available.");
    const sources = await desktopCapturer.getSources({
      types: ["screen"],
      thumbnailSize: { width: 1280, height: 720 },
      fetchWindowIcons: false,
    });
    const source = sources.find((candidate) =>
      candidate.display_id === String(selectedDisplay.id),
    ) ?? (displays.length === 1 && sources.length === 1 ? sources[0] : undefined);
    if (!source) {
      throw new Error("The selected display could not be captured. Check screen recording permissions.");
    }
    return createScreenAttachment(
      [{ thumbnail: source.thumbnail }],
      async () => 0,
    );
  });
  ipcMain.handle("alex:web:search", async (event, request: unknown) => {
    assertTrustedSender(event);
    return backendRequest(
      "POST",
      "/api/v1/web/search",
      validateWebSearchRequest(request),
    );
  });
  ipcMain.handle("alex:open-external", async (event, value: unknown) => {
    assertTrustedSender(event);
    await shell.openExternal(validateExternalUrl(value));
  });
  ipcMain.handle(
    "alex:weather:search",
    async (event, city: unknown, when: unknown) => {
      assertTrustedSender(event);
      await shell.openExternal(weatherSearchUrl(city, when));
    },
  );
  ipcMain.handle("alex:app:autostart:get", (event) => {
    assertTrustedSender(event);
    return getLoginItemStatus();
  });
  ipcMain.handle("alex:app:autostart:set", (event, enabled: unknown) => {
    assertTrustedSender(event);
    return setLoginItemEnabled(enabled);
  });
  ipcMain.handle("alex:app:shortcut:create", (event) => {
    assertTrustedSender(event);
    createDesktopShortcut();
  });
  ipcMain.handle("alex:voice:start", async (event) => {
    assertTrustedSender(event);
    await startLiveVoice();
  });
  ipcMain.on("alex:voice:audio", (event, pcm: unknown) => {
    assertTrustedSender(event);
    if (
      !(pcm instanceof ArrayBuffer) ||
      pcm.byteLength < 2 ||
      pcm.byteLength > 8192 ||
      pcm.byteLength % 2 !== 0
    ) {
      console.warn("Discarded invalid microphone PCM chunk");
      return;
    }
    if (liveSocket?.readyState === WebSocket.OPEN) liveSocket.send(pcm);
  });
  ipcMain.handle("alex:voice:text", (event, text: unknown) => {
    assertTrustedSender(event);
    if (typeof text !== "string" || !text.trim() || text.length > 4000) {
      throw new TypeError("Voice message must contain 1 to 4000 characters");
    }
    if (liveSocket?.readyState !== WebSocket.OPEN) {
      throw new Error("No live voice session is active");
    }
    liveSocket.send(JSON.stringify({ type: "text", text: text.trim() }));
  });
  ipcMain.handle("alex:voice:interrupt", (event) => {
    assertTrustedSender(event);
    if (liveSocket?.readyState !== WebSocket.OPEN) {
      throw new Error("No voice session is active");
    }
    liveSocket.send(JSON.stringify({ type: "interrupt" }));
  });
  ipcMain.handle("alex:voice:stop", (event) => {
    assertTrustedSender(event);
    stopLiveVoice();
  });
  ipcMain.handle("alex:wake-word:status", async (event) => {
    assertTrustedSender(event);
    return backendRequest("GET", "/api/v1/wake/status");
  });
  ipcMain.handle("alex:wake-word:toggle", async (event, enabled: unknown, model?: unknown, threshold?: unknown) => {
    assertTrustedSender(event);
    return backendRequest("POST", "/api/v1/wake/toggle", {
      enabled: Boolean(enabled),
      model: typeof model === "string" ? model : undefined,
      threshold: typeof threshold === "number" ? threshold : undefined,
    });
  });
  ipcMain.handle("alex:wake-word:install", async (event) => {
    assertTrustedSender(event);
    return backendRequest("POST", "/api/v1/wake/install", {});
  });
  ipcMain.handle("alex:voice:wake", async (event) => {
    assertTrustedSender(event);
    return backendRequest("POST", "/api/v1/voice/wake", {});
  });
  ipcMain.handle("alex:voice:sleep", async (event) => {
    assertTrustedSender(event);
    return backendRequest("POST", "/api/v1/voice/sleep", {});
  });
  ipcMain.handle("alex:media:status", async (event) => {
    assertTrustedSender(event);
    return backendRequest("GET", "/api/v1/media/status");
  });
  ipcMain.handle("alex:media:resolve", async (event, source: unknown) => {
    assertTrustedSender(event);
    if (typeof source !== "string") throw new TypeError("Media source must be a string");
    return backendRequest("POST", "/api/v1/media/resolve", { source });
  });
  ipcMain.handle("alex:media:control", async (event, action: unknown, source?: unknown, title?: unknown, muted?: unknown) => {
    assertTrustedSender(event);
    if (typeof action !== "string") throw new TypeError("Media action must be a string");
    return backendRequest("POST", "/api/v1/media/control", {
      action,
      source: typeof source === "string" ? source : undefined,
      title: typeof title === "string" ? title : undefined,
      muted: typeof muted === "boolean" ? muted : undefined,
    });
  });
}

function createWindow(): void {
  const localDevUrl = process.env.ALEX_FRONTEND_URL || "http://127.0.0.1:5173/";
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 800,
    minWidth: 880,
    minHeight: 640,
    backgroundColor: "#00060a",
    title: "Alex",
    fullscreen: true,
    fullscreenable: true,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.maximize();
  mainWindow.setFullScreen(true);

  mainWindow.once("ready-to-show", () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.setFullScreen(true);
      mainWindow.show();
    }
  });

  mainWindow.on("leave-full-screen", () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      setTimeout(() => {
        if (mainWindow && !mainWindow.isDestroyed() && !mainWindow.isFullScreen()) {
          mainWindow.setFullScreen(true);
        }
      }, 100);
    }
  });

  mainWindow.on("restore", () => {
    if (mainWindow && !mainWindow.isDestroyed() && !mainWindow.isFullScreen()) {
      mainWindow.setFullScreen(true);
    }
  });

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  mainWindow.webContents.on("will-navigate", (event, url) => {
    const isAllowed = isDevelopment
      ? isAllowedDevOrigin(url, localDevUrl)
      : isAllowedProdFile(url);
    if (!isAllowed) {
      event.preventDefault();
    }
  });

  if (isDevelopment) {
    void mainWindow.loadURL(localDevUrl);
  } else {
    void mainWindow.loadFile(path.resolve(__dirname, "../../dist/index.html"));
  }
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

async function stopBackend(): Promise<void> {
  if (isLauncherManagedBackend) return;
  if (!backend || backend.exitCode !== null) return;
  const child = backend;
  backend = null;
  const exited = new Promise<void>((resolve) => {
    child.once("exit", () => resolve());
  });
  try {
    await fetch(`http://127.0.0.1:${backendPort}/api/v1/shutdown`, {
      method: "POST",
      headers: { Authorization: `Bearer ${backendToken}` },
      signal: AbortSignal.timeout(800),
    });
  } catch (error) {
    console.warn(
      "Graceful backend shutdown failed; terminating the sidecar.",
      error instanceof Error ? error.message : String(error),
    );
  }
  if (child.exitCode === null) child.kill();
  await Promise.race([
    exited,
    new Promise<void>((resolve) => setTimeout(resolve, 2500)),
  ]);
  if (child.exitCode === null) child.kill("SIGKILL");
}

app.whenReady().then(async () => {
  let stepDescription = "initialize the desktop application";
  try {
    stepDescription = "configure microphone permissions";
    await configureMicrophonePermission();

    stepDescription = "start or connect to the Python backend";
    await startBackend();

    stepDescription = "register application IPC handlers";
    registerIpc();

    stepDescription = "create the application window";
    createWindow();
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    await dialog.showMessageBox({
      type: "error",
      title: "Alex could not start",
      message: `Failed to ${stepDescription}.`,
      detail,
    });
    await stopBackend();
    app.quit();
  }
});

app.on("before-quit", (event) => {
  if (quittingAfterBackendStop) return;
  event.preventDefault();
  quittingAfterBackendStop = true;
  stopLiveVoice();
  void stopBackend().finally(() => app.quit());
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0 && (isLauncherManagedBackend || backend?.exitCode === null)) {
    createWindow();
  }
});
