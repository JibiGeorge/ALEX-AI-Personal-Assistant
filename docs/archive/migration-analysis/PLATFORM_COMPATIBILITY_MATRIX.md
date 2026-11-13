# Alex – Platform Compatibility Matrix

**Document Version:** 1.0  
**Last Updated:** 2026-11-01  
**Project:** Alex Desktop Assistant  
**Authoritative References:** `Alex/docs/PROJECT_ARCHITECTURE.md`, `Alex/docs/KNOWN_ISSUES_AND_BLOCKERS.md`

---

## 1. Executive Summary

Alex is designed for cross-platform desktop execution across Windows, macOS, and Linux. However, hardware interaction, desktop window management, login items, and sidecar resolution necessarily interface with OS-specific primitives.

This matrix documents the exact operational state, verified behavior, and known platform limitations for every subsystem across all target operating systems.

---

## 2. Master Platform Support Matrix

| Subsystem / Capability | Windows 10 / 11 (Primary Target) | macOS (Darwin 13+) | Linux (Ubuntu 22.04+ / X11 / Wayland) | Implementation Mechanism & Notes |
|---|---|---|---|---|
| **FastAPI Loopback Sidecar** | **Supported** | **Supported** | **Supported** | Python 3.12, Uvicorn binding to `127.0.0.1` via loopback sockets. Platform agnostic. |
| **Python Sidecar Path Resolution** | **Supported** (`.venv\Scripts\python.exe`) | **Supported** (`.venv/bin/python`) | **Supported** (`.venv/bin/python`) | Electron `main.ts` inspects `process.platform` and resolves correct interpreter binary path. |
| **OS Credential Store** | **Supported** (Windows Credential Locker) | **Supported** (macOS Keychain) | **Supported** (SecretService / KWallet) | Python `keyring` library interfaces with native platform secure credential vaults. |
| **Local Document Storage** | **Supported** (`%APPDATA%\Alex`) | **Supported** (`~/Library/Application Support/Alex`) | **Supported** (`~/.local/share/Alex`) | Platform user data directory resolved dynamically via `_platform_data_dir()` in `core/config.py`. |
| **Desktop Notifications** | **Supported** (Action Center) | **Supported** (Notification Center) | **Supported** (libnotify / desktop portal) | Electron `Notification` API with in-app banner fallback when unsupported. |
| **Native Screen Capture** | **Supported** (`desktopCapturer`) | **Supported** (Requires Screen Recording permission) | **Supported** (X11; Wayland via PipeWire portal) | Electron `desktopCapturer` with custom display picker dialog. No file written to disk. |
| **Audio Device Enumeration** | **Supported** (MediaDevices API) | **Supported** (MediaDevices API) | **Supported** (MediaDevices API / ALSA / Pulse) | Web Audio API / navigator.mediaDevices. Platform agnostic. |
| **Push-to-Talk (Focused Window)** | **Supported** (Ctrl+Space keydown/up) | **Supported** (Cmd+Space / Ctrl+Space) | **Supported** (Ctrl+Space) | Web keyboard event listener in renderer. Global OS polling pending. |
| **Desktop Shortcut Creation** | **Supported** (`shell.writeShortcutLink`) | **Unsupported** (Alias not created) | **Unsupported** (`.desktop` entry not created) | **Windows-Only Limitation.** Electron `shell.writeShortcutLink` strictly conditioned on `win32`. |
| **Login at Startup** | **Supported** (Registry `Run` key) | **Supported** (`app.setLoginItemSettings`) | **Unsupported** (autostart desktop entry pending) | Electron `app.setLoginItemSettings`. Windows and macOS support verified in code; Linux pending. |
| **Window Enumeration & Focus** | **Supported** (Win32 `EnumWindows` & `SetForegroundWindow`) | **Unsupported** (`NSWorkspace` pending) | **Unsupported** (`XGetWindowProperty` pending) | **Explicit Windows-Only Product Limitation.** Non-Windows platforms report `available: false` via `PlatformCapabilityService`. |
| **Polite Application Close** | **Supported** (Win32 `WM_CLOSE`) | **Unsupported** (`SIGTERM` pending) | **Unsupported** (`SIGTERM` pending) | **Explicit Windows-Only Product Limitation.** Window message posted to target HWND; Alex ancestry shielded. |
| **Mouse / Keyboard Injection** | **Supported** (PyAutoGUI / Win32) | **Supported** (Requires Accessibility permissions) | **Supported** (X11 only; Wayland requires portal) | Bounded in `ComputerControlService`. Frozen implementation; physical verification blocked. |
| **Clipboard Read / Write / Paste** | **Supported** (pyperclip / win32clipboard) | **Supported** (pyperclip / pbcopy) | **Supported** (pyperclip / xclip / wl-copy) | Length-capped text operations (read <= 2000 chars, write <= 4000 chars). |
| **Production Packaging** | **Supported** (NSIS `.exe` installer) | **In Progress** (`.dmg` configured) | **In Progress** (`.AppImage` configured) | Electron Builder configured under `frontend/package.json`. Windows NSIS package verified. |

---

## 3. Explicit Documented Platform Limitations

The following limitations are formally recognized in system documentation:

1. **Window Management & Target Application Focus:**
   - *Limitation:* Finding visible application windows and focusing them by title is strictly functional on **Windows only**.
   - *Architecture:* Implemented via `ctypes.windll.user32.EnumWindows` and `SetForegroundWindow`.
   - *Status on macOS/Linux:* On macOS and Linux, the service returns empty lists and raises descriptive unsupported-platform errors. `PlatformCapabilityService` honestly reports `window_management.available = false` and `platform_restricted = true`.
2. **Polite Application Close (`close_app`):**
   - *Limitation:* Polite window termination via `WM_CLOSE` is strictly functional on **Windows only**.
   - *Architecture:* Resolves target HWND, ensures target process PID is not in Alex's ancestry, and posts `WM_CLOSE`.
   - *Status on macOS/Linux:* Not implemented. Unix `SIGTERM` / AppleScript `tell application ... to quit` adapters are scheduled for Phase 6.
3. **Desktop Shortcut Creation:**
   - *Limitation:* Automatic shortcut creation is enabled for **Windows only**.
   - *Architecture:* Invokes Electron `shell.writeShortcutLink` targeting `%USERPROFILE%\Desktop\Alex.lnk`.
   - *Status on macOS/Linux:* macOS standard user workflow relies on `/Applications` drag; Linux requires writing an XDG `.desktop` file to `~/.local/share/applications/` (pending).
4. **Linux Wayland Input Injection:**
   - *Limitation:* On Linux desktop environments using Wayland (default on Ubuntu 22.04+), direct coordinate mouse/keyboard injection via PyAutoGUI is restricted by display server security policy.
   - *Mitigation:* A future Linux input adapter will require the `xdg-desktop-portal` RemoteDesktop interface.

---

## 4. Platform Verification Requirements

Before claiming cross-platform general availability:

1. **macOS Validation Matrix:**
   - Clean macOS 14+ Sonoma execution.
   - Verify Microphone and Screen Recording entitlement prompts in macOS System Settings.
   - Verify Keychain storage and retrieval of Gemini API keys without terminal prompts.
   - Verify DMG installer mounting and `/Applications` bundle execution.
2. **Linux Validation Matrix:**
   - Verify SecretService D-Bus integration (GNOME Keyring / KWallet) on headless or standard desktop.
   - Test X11 vs Wayland display capture behavior.
   - Verify AppImage and tarball sidecar permissions (`chmod +x alex-backend`).

