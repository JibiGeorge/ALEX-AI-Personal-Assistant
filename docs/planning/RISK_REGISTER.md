# Risk Assessment & Mitigation Register: Alex AI Assistant

**Document Version:** 1.0  
**Inspection Date:** 2026-11-03  
**Status:** `ACTIVE_RISK_REGISTER`  

---

## 1. Risk Evaluation Matrix

```
       ▲
C      │                                 [RSK-01]
R      │                                 API Quota Depletion
I      │
T      │            [RSK-03]             [RSK-02]
I      │            Wayland Synthetic    Local Dependency
C      │            Input Block          Footprint Size
A      │
L      │ [RSK-05]   [RSK-04]
       │ Electron   Audio Hardware
       │ Renderer   Fragmentation
       +─────────────────────────────────────────►
         LOW        MEDIUM               HIGH
                      LIKELIHOOD
```

---

## 2. Granular Risk Analysis & Mitigation Strategies

### `RSK-01`: Google Gemini Live Cloud Quota Exhaustion (429 Rate Limits)
- **Risk Event:** Heavy voice or text usage rapidly depletes free/tier Gemini quota, causing live audio stream termination mid-conversation.
- **Likelihood:** HIGH \| **Impact:** CRITICAL
- **Mitigation Strategy:**
  1. Implement **Multi-Model Fallback Ladder (`CAT-05`)** that automatically rotates between 9 Gemini model tiers when receiving a 429 error.
  2. Implement **Sidecar Request Offloading**: Route background document parsing and screen reasoning to local Ollama or cheap Groq endpoints, reserving Gemini quota strictly for real-time conversational voice.
  3. Support seamless fallback to **Offline Local Pipeline (Whisper + Ollama + Piper)** when cloud quota is completely exhausted.
- **Contingency Plan:** Alert user via HUD status drawer: "Cloud quota exhausted; switched to offline local AI mode."
- **Owner:** AI Systems Architect.

---

### `RSK-02`: Dependency Bloat & Packaging Footprint Growth
- **Risk Event:** Adding `faster-whisper`, `piper-tts`, `opencv-python`, and `playwright` inflates repository and installer sizes by over 1.5 GB.
- **Likelihood:** HIGH \| **Impact:** HIGH
- **Mitigation Strategy:**
  1. Make heavy AI models and voice packages **optional one-click downloads** from the Settings UI (matching Mark-LVI design).
  2. Implement **Lazy Module Loading (`core/lazyimport.py`)**: Heavy modules are imported only when their specific action is triggered.
  3. Strip unnecessary native binaries and unused language models during packaging.
- **Contingency Plan:** Distribute a "Lite" installer (Gemini cloud-only, ~120 MB) and an "All-in-One Offline" installer (~1.2 GB).
- **Owner:** Build & Release Engineer.

---

### `RSK-03`: Wayland Incompatibility on Modern Linux Distributions
- **Risk Event:** Users running Ubuntu 22.04/24.04, Fedora, or modern GNOME/KDE under Wayland report that mouse/keyboard actions do nothing.
- **Likelihood:** MEDIUM \| **Impact:** HIGH
- **Mitigation Strategy:**
  1. Actively detect `XDG_SESSION_TYPE=wayland` on startup.
  2. Inject explicit limitations into the LLM system prompt so the assistant explains the constraint honestly.
  3. Display an activity log notification recommending that users select "Ubuntu on Xorg" at the login screen for full automation.
- **Contingency Plan:** Implement experimental XDG Desktop Portal input synthesis where compositors support the Remote Desktop Portal API.
- **Owner:** Linux Platform Specialist.

---

### `RSK-04`: Audio Hardware Fragmentation & Driver Latency Spikes
- **Risk Event:** Exotic Bluetooth headsets, virtual audio cables, or ASIO interfaces experience buffer under-runs or high latency during live voice streaming.
- **Likelihood:** MEDIUM \| **Impact:** MEDIUM
- **Mitigation Strategy:**
  1. Standardize internal audio transport on 16kHz 16-bit Mono Linear PCM.
  2. Provide live visual VU metering and speaker test chimes in the Audio Devices settings page.
  3. Filter out Windows disconnected/virtual ghost devices.
- **Contingency Plan:** Provide an audio buffer size slider (64ms to 256ms) in Advanced Audio settings.
- **Owner:** Audio & DSP Engineer.

---

### `RSK-05`: Electron Renderer Privilege Escalation / XSS Vulnerability
- **Risk Event:** Malicious web content fetched during web search exploits an Electron vulnerability to execute shell commands.
- **Likelihood:** LOW \| **Impact:** CRITICAL
- **Mitigation Strategy:**
  1. Enforce strict `contextIsolation: true`, `nodeIntegration: false`, and `sandbox: true`.
  2. Disallow external navigation; open external links in system default browser.
  3. Enforce loopback bearer token authentication on sidecar endpoints.
  4. Defang untrusted external text with `<DATA>` boundaries.
- **Contingency Plan:** Emergency security patch revoking IPC channels and updating Electron runtime.
- **Owner:** Application Security Architect.

