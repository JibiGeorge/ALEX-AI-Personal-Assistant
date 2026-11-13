# Platform Compatibility Matrix: Windows, Ubuntu Linux, macOS & iOS

**Document Version:** 1.0  
**Inspection Date:** 2026-11-03  
**Status:** `ACTIVE_PLATFORM_MATRIX`  

---

## 1. Operating System Compatibility & Capability Matrix

| Operational Capability | Windows 10/11 (64-bit) | Ubuntu Linux (X11) | Ubuntu Linux (Wayland) | macOS (Apple Silicon / Intel) | iOS Companion (iPhone / iPad) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Unified CLI Launcher** | FULL | FULL | FULL | FULL | N/A (Client only) |
| **Electron Desktop HUD** | FULL | FULL | FULL (Wayland flags) | FULL | N/A (Native/PWA) |
| **Unified Continuous HUD Workspace** | FULL | FULL | FULL | FULL | N/A (Client view) |
| **Floating HUD Content Window** | FULL | FULL | FULL | FULL | N/A (Client view) |
| **FastAPI Backend Sidecar** | FULL | FULL | FULL | FULL | Server connection |
| **Gemini Live Multimodal Voice**| FULL | FULL | FULL | FULL | FULL (AVAudioEngine) |
| **Offline Local STT (Whisper)** | FULL | FULL | FULL | FULL | N/A (Server offload) |
| **Offline Local LLM (Ollama)** | FULL | FULL | FULL | FULL | N/A (Server offload) |
| **Offline Local TTS (Piper)** | FULL | FULL | FULL | FULL | AVSpeechSynthesizer |
| **System Voice TTS** | FULL (SAPI5) | FULL (espeak-ng) | FULL (espeak-ng) | FULL (`say`) | FULL (iOS Voices) |
| **Hardware Camera (OpenCV)** | FULL (DirectShow/MSMF) | FULL (V4L2) | FULL (V4L2) | FULL (AVFoundation) | In-app Camera |
| **Local Wake Word ("Hey Alex")**| FULL | FULL | FULL | FULL | Foreground only |
| **A02 Mouse & Keyboard Control**| FULL (Win32) | FULL (X11 xdotool)| BLOCKED (Wayland) | FULL (Needs TCC grant)| RESTRICTED (Host only)|
| **Screen Capture (Autonomous)** | FULL (Win32 GDI) | FULL (X11 Root) | PARTIAL (PipeWire) | FULL (Needs TCC grant)| In-app camera only |
| **Window Enumeration & Raise** | FULL (EnumWindows) | FULL (wmctrl) | BLOCKED (Wayland) | FULL (AppleScript) | N/A |
| **Polite Application Close** | FULL (WM_CLOSE) | FULL (SIGTERM) | FULL (SIGTERM) | FULL (AppleScript) | N/A |
| **Audio Device Enumeration** | FULL (CoreAudio) | FULL (Pulse/PipeWire)| FULL (Pulse/PipeWire)| FULL (CoreAudio) | System default |
| **Per-Device Output Volume** | FULL (pycaw) | FULL (`pactl`) | FULL (`pactl`) | FULL (`osascript`) | Hardware rocker |
| **Live Microphone VU Meter** | FULL | FULL | FULL | FULL | FULL |
| **OS-Native Reminders** | FULL (schtasks) | FULL (systemd) | FULL (systemd) | FULL (launchd) | EventKit / APNs |
| **Credential Storage** | Windows Credential Mgr| Secret Service | Secret Service | Apple Keychain | iOS Secure Enclave |
| **File Sandboxing** | FULL | FULL | FULL | FULL | App Container |
| **Remote Mobile Dashboard** | Server Host | Server Host | Server Host | Server Host | Client Client |
| **Packaging & Distribution** | NSIS Installer (.exe)| AppImage / DEB | AppImage / DEB | DMG / Signed App | IPA / TestFlight / PWA |

---

## 2. Platform Nuances & Restrictions

### 2.1 Windows 10/11 (64-bit)
- **Primary Target:** Windows 11 (Build 23H2 or 24H2) is the primary target for full desktop automation.
- **Enterprise Restrictions:** Systems enrolled in Active Directory with AppLocker or Software Restriction Policies (SRP) may block child shell execution (`DEF-A07-001`). Requires dedicated standalone workstation or whitelisting.
- **Display Resolution:** Minimum physical 1920x1080 display at 100% DPI scaling required for coordinate-exact computer control.

### 2.2 Ubuntu Linux (X11 vs. Wayland)
- **Wayland Security Model:** Wayland is the default display server on Ubuntu 22.04 LTS and 24.04 LTS. By design, Wayland forbids one unprivileged application from snooping on or injecting synthetic inputs into other applications.
- **Wayland Behavior:** Under Wayland, `pyautogui.click()` and `pyautogui.write()` report success but have zero physical effect on target windows. Alex detects `XDG_SESSION_TYPE=wayland` and informs the model so it explains the constraint honestly.
- **X11 Session:** Logging out and choosing "Ubuntu on Xorg" at the login display manager restores full mouse, keyboard, and window management capabilities.

### 2.3 macOS (Apple Silicon & Intel)
- **Transparency, Consent, and Control (TCC):** macOS enforces strict user consent via System Settings:
  - **Accessibility (`System Settings > Privacy & Security > Accessibility`):** Required for synthetic typing and mouse clicking.
  - **Screen Recording (`System Settings > Privacy & Security > Screen Recording`):** Required for screen capture.
  - **Microphone (`System Settings > Privacy & Security > Microphone`):** Required for audio input.
- **Window Management:** Uses AppleScript and Quartz Window Server rather than Win32 APIs.

### 2.4 iOS (iPhone & iPad)
- **Sandboxed Companion Model:** Cannot run local Python or control iOS system pointers. Acts as an encrypted mobile companion client communicating with the desktop host over local Wi-Fi or secure TLS tunnel.

