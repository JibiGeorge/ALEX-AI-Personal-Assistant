# Dependency and Integration Gap Analysis

This comparison covers project-owned manifests and configuration, not vendored packages in either virtual environment.

## Dependency stacks

| Area | Mark-LVI-main | Alex | Assessment |
|---|---|---|---|
| Desktop UI | PyQt6/Qt application | Electron, React, TypeScript, Vite, Electron Builder | Intentional replacement; UI behavior still requires parity tests. |
| Backend/API | Python application; optional FastAPI phone dashboard | FastAPI + Uvicorn sidecar | Existing source UI/backend is not a separate REST service; Alex's API is an architecture change. |
| Validation | Action JSON-schema structure checks; handler-specific parsing | Pydantic v2 schemas and strict request validation | Alex is stricter for registered actions; source action schema parity is not yet modeled. |
| Gemini | Google GenAI/Gemini Live, grounding/model helpers | `google-genai` for text, Live and grounded search | Main provider migrated; action coverage/call behavior only on narrow set. |
| Audio/STT/TTS | `sounddevice`, `numpy`, optional Whisper/Piper/system/ElevenLabs integrations | Renderer/browser media devices and Gemini Live audio | Different stack; no full provider/device feature parity. |
| Automation | `playwright`, `pyautogui`, `pyperclip` and platform GUI/native utilities | Electron safe URL and desktop lifecycle APIs | Browser/GUI automation absent; do not install automation libraries until capability and policy are designed. |
| Files/media | `pillow`, `opencv-python`, `mss`, `python-pptx`, `pdfplumber`, `PyPDF2`, `python-docx`, `yt-dlp`, and platform tools | Renderer-selected MIME-allowlisted attachments forwarded to Gemini | Only a bounded attachment slice; not equivalent to processing dependencies/workflows. |
| Remote access | `fastapi`, `uvicorn[standard]`, `cryptography`, `python-multipart`, `qrcode[pil]`; dashboard pairing/auth and optional TLS | No phone dashboard | Missing product capability; source's HTTP/LAN transport must not be copied without secure redesign. |
| System | OS-specific packages/utilities and platform detection | psutil, keyring and Electron platform APIs | Metrics/secret storage are migrated; broad OS integration missing. |

### Mark-LVI-main declared packages

The source `requirements.txt` groups packages as follows; package names are preserved as declared:

| Purpose | Packages |
|---|---|
| UI/audio/Gemini/provider HTTP | `PyQt6`, `sounddevice`, `numpy`, `google-genai`, `httpx` |
| Search/browser/video | `requests`, `beautifulsoup4`, `playwright`, `yt-dlp` |
| Input automation | `pyautogui`, `pyperclip` |
| Vision/media | `pillow`, `opencv-python`, `mss` |
| System/files/documents | `psutil`, `send2trash`, `python-pptx`, `pdfplumber`, `PyPDF2`, `python-docx`, `pynvml` |
| Dashboard | `fastapi`, `uvicorn[standard]`, `cryptography`, `python-multipart`, `qrcode[pil]` |
| Declared plugin extras | `google-api-python-client`, `google-auth-oauthlib`, `tinytuya`, `paho-mqtt`, `openpyxl`, `youtube-transcript-api`, `pygetwindow` |
| Windows-only platform markers | `comtypes`, `pycaw`, `win10toast`, `pywin32`, `wmi`, `pywinauto` |

Optional/manual dependencies include `pandas`, `pydub` (normally needs native `ffmpeg`), `mediapipe`, `faster-whisper`, `piper-tts`, and `openwakeword`. `setup.py` targets Python 3.11+, installs requirements, and installs Chromium and Firefox through Playwright; WebKit is an extra manual install. Linux/macOS system utilities also affect feature availability.

The project has a dependency discrepancy: `core/installer.py` describes automatic installation but no source caller of `install_for_config` was found, and its package lists differ from `requirements.txt` (including `soundfile`, `miniaudio`, Vosk, Edge TTS, and Kokoro).

## Alex backend dependencies

`backend/pyproject.toml` declares Python `>=3.11` and these bounded dependencies: `fastapi>=0.115,<1`, `uvicorn[standard]>=0.34,<1`, `pydantic>=2.10,<3`, `pydantic-settings>=2.7,<3`, `keyring>=25,<26`, `google-genai>=1.30,<2`, `httpx>=0.28,<1`, and `psutil>=5.9,<8`. `backend/requirements.txt` also includes `pytest>=8.3,<9` and `pyinstaller>=6.11,<7`. Pytest discovers `backend/tests` and adds the backend root to the Python path. Ruff is configured in `pyproject.toml`, but it was not installed in the virtual environment when invoked.

## Alex frontend/runtime dependencies

`frontend/package.json` declares React `^19.1.0` and React DOM `^19.1.0`; its development dependencies include `@vitejs/plugin-react ^4.4.1`, `@tailwindcss/vite ^4.1.11`, `@testing-library/jest-dom ^6.6.4`, `@testing-library/react ^16.3.0`, `@types/node ^22.15.30`, `@types/react ^19.1.6`, `@types/react-dom ^19.1.6`, `concurrently ^9.2.0`, `electron ^45.1.0`, `electron-builder ^26.0.12`, `jsdom ^26.1.0`, `tailwindcss ^4.1.11`, `typescript ^5.8.3`, `vite ^6.3.5`, `vitest ^5.0.5`, and `wait-on ^8.0.3`. Scripts cover dev, build/typecheck, Vitest, packaging tests, sidecar verification, preview/start, and distribution. The Python sidecar is included in Windows packaging according to deployment documentation.

## Source configuration and secrets

- Mark-LVI settings include Gemini key, assistant/user names, voice, wake-word/PTT/HUD, audio devices, plugins/plugin settings, provider mode/config/pipeline/sidecar. `config/api_keys.json` stores Gemini key material in JSON; no encryption is shown in the audited implementation. Dashboard HTTPS is a separate setting.
- Alex `RuntimeSettings` reads the `ALEX_` prefix and `.env`; known fields are `data_dir`, `api_token`, and `log_level` (default `INFO`). `.env.example` lists `ALEX_DATA_DIR`, `ALEX_LOG_LEVEL`, and optional development override `ALEX_PYTHON`. Electron injects a per-run `ALEX_API_TOKEN`, `ALEX_DATA_DIR` (Electron user data), and `ALEX_LOG_LEVEL` when spawning the sidecar.
- Alex uses an OS credential store for Gemini keys; persistent application settings and memory use the backend data directory. Environment-variable parity with source config is not exact, and automated source settings/memory import is not established.
- Optional source modules and OS utilities mean declared dependencies do not guarantee runtime availability. The action loader may skip failed module imports. Whisper/Piper and dashboard/TLS options are conditional.

## Entrypoint and lifecycle

Mark-LVI's `main()` constructs `JarvisUI`, starts a daemon runner thread, enters Qt's main loop, waits for API-key setup, constructs `JarvisLive`, then enters `asyncio.run(jarvis.run())`. `run()` binds confirmation/memory callbacks, attempts optional dashboard startup, builds the selected engine/config, and loops through session connection/recovery.

Alex Electron selects an available loopback port, generates the API token, starts Python in development or the packaged backend executable, polls authenticated health for up to 20 seconds, and only then creates the renderer and IPC surface. Quit stops Live voice, requests `/api/v1/shutdown`, and escalates if graceful termination fails. See `frontend/electron/main.ts` and `backend/app/main.py`.

## Integration gaps tracked

The following **11 integration groups** are not fully migrated (some have partial equivalents):

| ID | Integration group | Alex status |
|---|---|---|
| I01 | Alternate LLM/STT/TTS providers | Missing |
| I02 | Browser automation and page interaction | Missing |
| I03 | Platform GUI/accessibility and OS settings | Missing |
| I04 | Full filesystem/archive/document/media processing | Partial |
| I05 | Native OS reminder scheduler | Partial; app-running delivery only |
| I06 | Steam/Epic launchers and game scheduling | Missing |
| I07 | External messaging clients | Missing |
| I08 | YouTube search/player/transcripts | Missing |
| I09 | Flight search/format/save integration | Missing |
| I10 | LAN phone dashboard/pairing/audio/file APIs | Missing |
| I11 | Screen/webcam capture and analysis | Missing |

These are functional capability integrations, not a list of install requests. Do not add a package just to make an inventory look complete. Each needs a design and safety approval in its roadmap task.

## Dependency validation gaps

1. Compare exact pinned/transitive dependency versions and native platform markers before packaging a release.
2. Verify optional dependency capability reporting rather than silently hiding failed action modules.
3. Test clean installation and sidecar resource lookup on Windows; macOS/Linux packaging remains unverified.
4. Review data migration for source JSON settings/memory and key rotation; never import source plaintext secrets automatically.
5. Run lint/lockfile audit when the relevant toolchain is installed; no Ruff result is claimed here.
