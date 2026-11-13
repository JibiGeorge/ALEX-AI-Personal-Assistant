# Environment Variables & Configuration Reference

**Document Version:** 1.0  
**Inspection Date:** 2026-11-03  
**Status:** `AUTHORITATIVE_CONFIGURATION_SPECIFICATION`  

---

## 1. Executive Summary & Configuration Architecture

Alex AI Desktop Assistant uses a tiered configuration architecture:
1. **Operating System Credential Store (Primary for Secrets):** Secrets (API keys, session tokens) are stored in the OS Keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service).
2. **Environment Variables (Runtime & Infrastructure Overrides):** Process-level environment variables loaded via Pydantic `BaseSettings` (`ALEX_` prefix) for ports, hosts, logging, and data directories.
3. **Application Data Store (User Preferences):** User preferences (theme, assistant name, audio device selections) stored in `ALEX_DATA_DIR/settings.json`.

---

## 2. Environment Variable Inventory & Mapping Matrix

| Variable Name | Mark-LVI Reference | Alex Current | Purpose | Required | Default Value | Secret? | Supported Platforms |
| :--- | :---: | :---: | :--- | :---: | :--- | :---: | :--- |
| **`ALEX_BACKEND_HOST`** | In-process | `127.0.0.1` | Loopback bind host for FastAPI sidecar | No | `127.0.0.1` | No | Win, Linux, Mac |
| **`ALEX_BACKEND_PORT`** | In-process | `8765` | Loopback port for FastAPI sidecar | No | `8765` (Auto-reassigned if busy) | No | Win, Linux, Mac |
| **`ALEX_FRONTEND_HOST`**| N/A (PyQt) | `127.0.0.1` | Loopback host for Vite dev server | No | `127.0.0.1` | No | Win, Linux, Mac |
| **`ALEX_FRONTEND_PORT`**| N/A (PyQt) | `5173` | Loopback port for Vite dev server | No | `5173` | No | Win, Linux, Mac |
| **`ALEX_FRONTEND_URL`** | N/A (PyQt) | `http://127.0.0.1:5173/` | Target URL loaded by Electron BrowserWindow | No | `http://127.0.0.1:5173/` | No | Win, Linux, Mac |
| **`ALEX_DATA_DIR`** | Root `config/` | OS Standard | Application state and document store path | No | Windows: `%APPDATA%\Alex`<br>macOS: `~/Library/Application Support/Alex`<br>Linux: `~/.local/share/Alex` | No | Win, Linux, Mac |
| **`ALEX_LOG_LEVEL`** | Stdout | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | No | `INFO` | No | Win, Linux, Mac |
| **`ALEX_API_TOKEN`** | N/A (Threads) | Dynamic 32B | Bearer token authenticating sidecar loopback | No | Auto-generated cryptographically per launch | **YES** | Win, Linux, Mac |
| **`ALEX_PYTHON`** | System PATH | Auto-discovered | Path to preferred Python virtual environment | No | Auto-discovered (`backend/.venv` > PATH) | No | Win, Linux, Mac |
| **`GEMINI_API_KEY`** | `api_keys.json` | Keyring / Env | Google Gemini API key for Live audio & search | **YES** | Retrieved from OS Keyring (`Alex` service) | **YES** | All Platforms |
| **`OLLAMA_URL`** | `llm_url` in config | Planned | HTTP URL for local Ollama server | No | `http://127.0.0.1:11434` | No | Win, Linux, Mac |
| **`OLLAMA_MODEL`** | `llm_model` in config | Planned | Model tag to load in local Ollama | No | `llama3.2` | No | Win, Linux, Mac |
| **`OPENAI_API_KEY`** | `api_keys.json` | Keyring (Planned)| API key for OpenAI / OpenRouter endpoints | No | None (Retrieved from Keyring) | **YES** | All Platforms |
| **`GROQ_API_KEY`** | `api_keys.json` | Keyring (Planned)| API key for high-speed Groq inference | No | None (Retrieved from Keyring) | **YES** | All Platforms |
| **`DEEPSEEK_API_KEY`** | `api_keys.json` | Keyring (Planned)| API key for DeepSeek reasoning models | No | None (Retrieved from Keyring) | **YES** | All Platforms |
| **`ELEVENLABS_API_KEY`**| `api_keys.json` | Keyring (Planned)| API key for ElevenLabs neural voice stream | No | None (Retrieved from Keyring) | **YES** | All Platforms |
| **`NO_COLOR`** | N/A | Supported | Disables ANSI colored output in CLI launcher | No | Not set | No | All Platforms |

---

## 3. Configuration Security Rules

1. **Zero Raw Secrets in Files:** Real API keys must never be committed to source control or saved to `.env` files in git repositories.
2. **Safe Placeholder Standard:** Sample files and documentation must only use standard placeholders:
   - `GEMINI_API_KEY=your_gemini_api_key_here`
   - `ALEX_API_TOKEN=your_custom_bearer_token_here`
3. **Keyring Prioritization:** Alex checks the OS Keyring before checking environment variables:
   $$\text{Keyring Lookup} \longrightarrow \text{Environment Variable Fallback} \longrightarrow \text{First-Run Dialog}$$

