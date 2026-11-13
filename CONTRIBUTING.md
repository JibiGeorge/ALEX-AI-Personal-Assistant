# Contributing to Alex AI Desktop Assistant

Thank you for your interest in contributing to the **Alex AI Desktop Assistant**! This document outlines our engineering standards, contribution workflows, quality expectations, and governance rules.

---

## 1. Governance & Implementation Freezes

To maintain stability, traceability, and strict external acceptance criteria, several critical components of this repository are subject to **mandatory governance freezes**. Contributors MUST NOT modify these components without formal architectural review and unfreezing authorization:

1. **A02 Computer Control Implementation (`backend/app/services/computer_control_service.py`):**
   - **Status:** **FROZEN**.
   - Coordinate validation, multi-monitor display bounds checks, emergency corner aborts, and event injection rate limits are locked. Proposed changes must submit a formal Change Request under [`docs/planning/CHANGE_REQUESTS.md`](docs/planning/CHANGE_REQUESTS.md).
2. **Unified Launcher Implementation (`launcher/`):**
   - **Status:** **FROZEN**.
   - Process lifecycle orchestration, readiness polling, and IPC socket signaling logic are locked.
3. **Electron Main & Preload Scripts (`frontend/electron/main.ts`, `frontend/electron/preload.ts`):**
   - **Status:** **FROZEN**.
   - Context isolation, preload bridging, and window geometry management are locked.
4. **Reference Codebase (`Mark-LVI-main/`):**
   - **Status:** **READ-ONLY**.
   - Historical reference prototype must remain completely unmodified.
5. **Application Version & Baseline Snapshot:**
   - **Status:** **LOCKED at `0.1.0`** (`SNAPSHOT_v0.1.0-20261102`).
6. **Physical Acceptance Framework:**
   - **Status:** **LOCKED**.
   - The 33 acceptance protocols (`A03-LCH-01..11`, `A03-CTRL-01..11`, `A03-GEM-01..11`) and their pass/fail criteria cannot be altered or reduced.
7. **Migration Roadmap Alignment:**
   - Feature additions must align with the phased roadmap defined in [`docs/migration/MIGRATION_MASTER_PLAN.md`](docs/migration/MIGRATION_MASTER_PLAN.md) and [`docs/planning/PENDING_TASKS.md`](docs/planning/PENDING_TASKS.md).

---

## 2. Core Architectural Principles

All contributions must strictly respect the application's three-tier security and isolation model:
- **Renderer Isolation:** The React frontend runs in a sandboxed renderer with `contextIsolation: true` and `nodeIntegration: false`. Do not expose Node.js primitives or Electron internals to the web context. All host interactions must traverse the typed `window.alex` bridge defined in `preload.ts`.
- **Sidecar Security:** The FastAPI backend binds exclusively to `127.0.0.1` and authenticates every request via a dynamically generated bearer token passed at launch. Never bind backend services to external network interfaces (`0.0.0.0`).
- **Credential Storage:** Secrets, API keys, and sensitive tokens must never be written to plaintext files, git-tracked configs, or terminal logs. Store credentials in the OS keyring via `keyring`.

---

## 3. Development Workflow

### Prerequisites
- Python 3.10+ (64-bit)
- Node.js 18.0+ (LTS recommended) and npm
- Git

### Setup
```bash
# 1. Backend environment
cd backend
python -m venv .venv
# On Windows: .venv\Scripts\activate | On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. Frontend environment
cd ../frontend
npm install
```

### Running Locally
To launch the complete application stack in development mode:
```bash
# From repository root
python -m launcher.cli launch --dev
```

---

## 4. Quality & Testing Standards

Every contribution must pass the entire automated test baseline before submission. Regressions are not tolerated.

### Verification Checklist

1. **Backend Tests:**
   ```bash
   cd backend
   pytest tests/ -v
   ```
   *Requirement: All 113 unit/integration tests must pass.*

2. **Frontend Tests & Typechecks:**
   ```bash
   cd frontend
   npm run test
   npm run build
   npx tsc -p tsconfig.electron.json --noEmit
   ```
   *Requirement: All 33 Vitest tests must pass. TypeScript compilation must produce zero errors.*

3. **Code Quality & Linting:**
   ```bash
   # Python
   ruff check backend/
   # Frontend
   npm run lint
   ```

---

## 5. Physical Acceptance & Zero-Simulation Policy

- **No Simulated Results:** Automated mocks must never be substituted for physical hardware tests. Physical acceptance is governed by the 33 protocols evaluated by a human test engineer on dedicated Windows 11 hardware.
- **No Security Bypasses:** Do not commit workarounds that disable AppLocker, bypass corporate proxies, or alter operating system security policies.

---

## 6. Pull Request Process

1. Create a feature branch off `main` with a descriptive name (e.g., `fix/memory-leak-cleanup`, `docs/setup-clarification`).
2. Verify all automated tests pass and lint checks are clean.
3. Update relevant documentation in `docs/` for any user-facing or architectural changes.
4. Submit a Pull Request with a clear description of the problem, the solution, and verification evidence.
5. Ensure PR checks pass and obtain review approval from project maintainers.

