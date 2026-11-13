# Dependency Analysis

## Original application dependencies

The original dependency manifest is `../../Mark-LVI-main/requirements.txt`; `setup.py` installs it using the current interpreter and attempts an OS-filtered Playwright browser install. The list below groups dependencies by actual source use and install policy.

| Dependency | Role in Mark LVI | Requiredness / notes |
|---|---|---|
| PyQt6 | Desktop GUI, QPainter avatar and Qt Multimedia playback | Core desktop runtime; multimedia plugins may be unavailable independently. |
| numpy | PCM, spectral analysis, audio/vision transforms, avatar/echo work | Core runtime. |
| sounddevice | Microphone and speaker PCM streams | Core runtime; host audio backend/device behavior is platform-dependent. |
| google-genai | Gemini Live and model generation | Core assistant API; requires a user-provided key and network. |
| httpx | Provider calls and direct HTTP integrations | Declared direct dependency; also used by provider implementations. |
| requests, beautifulsoup4 | Scraping/search and related web actions | Declared; some modules use requests, BeautifulSoup usage is feature-specific. |
| playwright | Browser automation and flight search | Required for browser action discovery; browser binaries installed separately and optionally. |
| ddgs | DuckDuckGo web/news search | Primary maintained package; old `duckduckgo_search` is a compatibility fallback, not declared. |
| yt-dlp | YouTube stream resolution | Unbounded version by design to keep up with YouTube changes. |
| pyautogui, pyperclip | Keyboard/mouse/clipboard automation | Heavy imports are deferred in current action modules; still declared. |
| Pillow | Image processing and screenshots | Core/optional feature depending on path. |
| opencv-python, mss | Webcam capture and screen capture support | OpenCV is lazily imported; mss is used for desktop capture. |
| psutil | Process identity and system metrics | Core action dependency. |
| send2trash | Recoverable file deletion | Optional import/fallback behavior. |
| python-pptx | PowerPoint document processing | Feature dependency. |
| FastAPI, uvicorn[standard] | Phone dashboard | Optional service at runtime; installed by base manifest. |
| cryptography | Dashboard cryptographic routines | Optional dashboard dependency; installed by base manifest. |
| python-multipart | Dashboard upload routes | Optional feature dependency. |
| qrcode[pil] | Dashboard QR pairing display | UI integration dependency. |
| Google API client, google-auth-oauthlib | Gmail/calendar integrations in README/plugin scope | Declared but concrete plugin source is missing in this checkout. |
| tinytuya | Tuya/Smart Life integration | Declared for absent plugin source. |
| paho-mqtt | Printer/MQTT integration | Declared for absent plugin source. |
| openpyxl | Spreadsheet output | Declared for absent plugin source; `file_processor` has Excel operations. |
| youtube-transcript-api | YouTube transcript summaries | Feature dependency; import is optional in action code. |
| pygetwindow | Window geometry/game/chat automation | Feature dependency; platform behavior varies. |
| pdfplumber, PyPDF2, python-docx | PDF/Word reading | Feature-specific; code guards optional paths. |
| pynvml | NVIDIA telemetry | Optional; code also attempts ctypes NVML/WMI paths. |
| comtypes, pycaw, win10toast, pywin32, wmi, pywinauto | Windows audio, notifications, COM, accessibility and system tools | Installed only on Windows using PEP 508 markers. |
| openwakeword | Local wake-word model/runtime | Deliberately not installed by default; UI offers opt-in installation and download. |
| faster-whisper, piper-tts | Local STT and neural TTS | Not in base manifest; optional provider installation from settings. |
| pandas, pydub, mediapipe | Additional spreadsheet/audio/vision features | Documented as optional, not installed by default. Some depend on ffmpeg or model downloads. |

## Dependency and architecture findings

1. **Heavy install surface:** the manifest combines core conversation, automation, document handling, web service and plugin extras. A clean Alex install should not download unused models or platform-inappropriate packages.
2. **Runtime vs optional mismatch:** many packages are installed even though their associated plugin code is absent; the source and README disagree about concrete plugin availability.
3. **Native/runtime requirements:** Playwright browsers, audio host APIs, Qt Multimedia codecs, OS notifications/schedulers, screen permissions and accessibility permissions are not fully represented by `pip install`.
4. **Unbounded yt-dlp:** intentional compatibility tradeoff, but it should be version-tested and packaged deliberately.
5. **On-demand provider downloads:** Whisper/Piper models and wake-word assets are large and have first-use network/storage implications.
6. **Legacy overlap:** `core/installer.py`, `core/llm_client.py`, `core/stt.py` and `core/tts.py` describe a different MARK XL engine stack. Trace live imports before carrying these packages or behaviors into Alex.
7. **No lockfile:** version ranges are used, but there is no reproducible full lock or build environment definition in the original checkout.
8. **Python packaging:** no `pyproject.toml` is present; setup is an imperative script invoking pip, and there is no backend executable bundling configuration.

## Alex dependency policy

- Keep runtime dependencies lean and separate core from opt-in providers, hardware automation, dashboard and document/media extras.
- Pin supported ranges and produce a lock/install set for development and each packaged target.
- The frontend currently has a generated `package-lock.json`; `npm audit` reports no known vulnerabilities for the resolved dependency tree. Re-run both after dependency changes.
- Use FastAPI and Pydantic at the backend boundary; React/TypeScript and Electron at the UI boundary.
- Alex currently uses `google-genai` for text chat and HTTPX for bounded network requests; the Gemini API key stays in the OS credential store. The packaged sidecar explicitly collects the GenAI SDK runtime.
- Alex uses `psutil` for the CPU, memory, network, uptime and process telemetry shown in the HUD; GPU/temperature remain unavailable where the host exposes no sensor API.
- Add React only for the renderer's component/state needs, Electron/Vite tooling for desktop development, Tailwind for design tokens/utilities, pytest for Python tests, Vitest for renderer tests and electron-builder for packaging.
- Do not add a package until a source-backed feature needs it. External model/voice assets should be fetched only through explicit user action with progress and storage checks.
- Build and test Python as a standalone service first, then package it as a sidecar process and test shutdown/error reporting on each target OS.

## API/service integrations to provision separately

Gemini key; optional provider credentials/endpoints; ElevenLabs key/voice ID; browser binaries; local model server; Whisper/Piper model files; wake-word models; and platform-native schedulers/audio/permission APIs. None should be embedded in the renderer bundle or committed in source.
