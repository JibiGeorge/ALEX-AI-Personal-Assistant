# Development Configuration Guide

**Document Version:** 1.0  
**Inspection Date:** 2026-11-03  
**Status:** `ACTIVE_CONFIG_GUIDE`  

---

## 1. Local Development Setup

To configure Alex for local development:

```bash
# 1. From repository root, copy the environment template
cp .env.example .env

# 2. Configure Python Virtual Environment
cd backend
python -m venv .venv
# On Windows: .venv\Scripts\activate | On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure Frontend Dependencies
cd ../frontend
npm install
```

---

## 2. Recommended Development Environment Flags

In your local `.env` file, configure the following developer overrides:

```bash
# Enable verbose debug logging in terminal and sidecar
ALEX_LOG_LEVEL=DEBUG

# Run backend sidecar on standard loopback port
ALEX_BACKEND_PORT=8765

# Vite development server port
ALEX_FRONTEND_PORT=5173

# Optional: Set Gemini API key for local dev (Alternative to OS Keyring)
# GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 3. Pre-Flight System Diagnostics

Before running the application, always verify your environment using the CLI doctor:

```bash
# Run system doctor
python -m launcher.cli doctor

# Run with verbose remediation instructions
python -m launcher.cli doctor --verbose
```

---

## 4. Multi-Terminal Manual Development

If developing the frontend and backend in separate editor terminals:
1. **Terminal 1 (Backend FastAPI Sidecar):**
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
   ```
2. **Terminal 2 (Frontend React Vite Server):**
   ```bash
   cd frontend
   npm run dev
   ```
3. **Terminal 3 (Electron Shell):**
   ```bash
   cd frontend
   npm run electron:dev
   ```

