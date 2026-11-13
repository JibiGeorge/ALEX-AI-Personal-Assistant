# Production Configuration & Hardening Guide

**Document Version:** 1.0  
**Inspection Date:** 2026-11-03  
**Status:** `ACTIVE_CONFIG_GUIDE`  

---

## 1. Production Architecture Overview

In a production environment, Alex runs as a packaged desktop application:
- The Python FastAPI sidecar is compiled into a standalone directory (`dist/alex-sidecar/`) via PyInstaller, eliminating the external Python runtime dependency.
- The React application is built into optimized static production assets (`frontend/dist/`).
- Electron Builder packages the executable installer with code signing.

---

## 2. Production Security Hardening Rules

1. **Strict Loopback Binding:** The backend sidecar must bind exclusively to `127.0.0.1`. Never set `ALEX_BACKEND_HOST=0.0.0.0` or expose the API to the public network.
2. **Dynamic Bearer Token Generation:** In production, `ALEX_API_TOKEN` should never be hardcoded. The Unified Launcher or Electron Main generates a cryptographically secure 32-byte token at process launch.
3. **OS Keyring Secret Storage:** The Gemini API key must be saved to the operating system credential manager using `keyring` (Windows Credential Manager, macOS Keychain, Linux Secret Service).
4. **Log Sanitization:** Ensure `ALEX_LOG_LEVEL=INFO` or `WARNING` in production to prevent sensitive user text, screen coordinates, or prompt variables from reaching logs.
5. **Renderer Context Isolation:** Production Electron BrowserWindow must enforce:
   ```typescript
   webPreferences: {
     contextIsolation: true,
     nodeIntegration: false,
     sandbox: true,
     webSecurity: true,
   }
   ```

