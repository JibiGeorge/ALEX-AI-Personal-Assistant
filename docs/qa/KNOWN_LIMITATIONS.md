# ALEX AI Desktop Assistant — Known Limitations & Production Constraints

**Date**: November 14, 2026  
**Auditor**: Senior QA Automation Engineer

This document catalogs deliberate architectural boundaries, hardware dependencies, and platform constraints within the ALEX AI Desktop Assistant application.

---

## 1. External Video & Platform Policies

### YouTube Embedded Playback Restrictions
- **Limitation**: Certain YouTube videos cannot be played inline inside the floating HUD video iframe due to content owners disabling third-party domain embedding (`Error 150` / `Playback Restricted`).
- **Mitigation**: The HUD Video Workspace detects iframe player errors and provides an immediate fallback banner:
  - `"PLAYBACK RESTRICTED: YouTube playback error occurred."`
  - Direct action button: `OPEN IN YOUTUBE ↗` (opens the user's default system browser) alongside `CLOSE STAGE`.
- **Deliberate Design**: ALEX does not attempt to scrape or circumvent YouTube content protection policies.

---

## 2. Platform & OS Capabilities

### Windows vs. macOS System Control Adapters
- **macOS / Linux**: System metrics utilize standard POSIX and `psutil` calls.
- **Windows (Win32 Adapter)**: `test_win32_adapter.py` is skipped when executing tests on macOS/Linux hosts (`sys.platform != "win32"`). This is expected platform-specific behavior and does not indicate an issue.

### Wake-Word Engines
- **Limitation**: OpenWakeWord and Porcupine models require local voice model weights. If model weights are missing or the microphone is muted by hardware switch, the HUD displays `"AUDIO SENSORS STANDBY"` and prompts the operator to configure audio input in Settings.

---

## 3. Job Hunting & Social Platform Ingestion

### LinkedIn Platform Boundaries
- **Deliberate Constraint**: ALEX **strictly prohibits** automated website scraping or headless browser automation against LinkedIn to protect the user's account from suspension and comply with platform terms of service.
- **Supported Channels**:
  - Direct user-pasted LinkedIn job post URLs (via `/api/job-hunting/ingest/linkedin-url`).
  - Raw text copy-paste of LinkedIn job alert emails (via `/api/job-hunting/ingest/linkedin-alert`).
  - Public Greenhouse and Lever ATS job board ingestion.
  - Authorized web career search.

### Human-in-the-Loop Application Approvals
- **Deliberate Constraint**: The AI assistant is architecturally forbidden from submitting external job applications without human approval. Every application must pass through the `Pending Approvals` queue and require explicit operator confirmation.

---

## 4. Hardware Acceleration & 3D Avatar Rendering

### Three.js WebGL Fallback
- **Limitation**: If WebGL 2.0 context cannot be created (e.g. low-resource VMs without GPU emulation or extreme software rasterization), the 3D humanoid avatar gracefully falls back to a 2D canvas procedural waveform audio visualizer without crashing the application shell.

