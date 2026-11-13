# Security Gap & Licensing Audit Register

**Document Version:** 1.0  
**Inspection Date:** 2026-11-03  
**Status:** `ACTIVE_SECURITY_REGISTER`  

---

## 1. Security Gap Register

| Gap ID | Security Vulnerability / Gap | Affected Component | Severity | Evidence | Mitigation / Required Action | Acceptance Criteria |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **SEC-01** | **Plaintext Secrets in Configuration Files** | Reference Project (`Mark-LVI`) | **CRITICAL** | `Mark-LVI-main/config/api_keys.json` stores `gemini_api_key` in unencrypted JSON. | **Alex Solution:** Migrate 100% of secret storage to OS Keyring (`keyring` library). | Zero plaintext keys found on disk outside OS vault. |
| **SEC-02** | **Lack of Renderer Context Isolation** | Reference Project (`Mark-LVI`) | **CRITICAL** | `Mark-LVI-main/ui.py` runs UI directly in Python process with unrestricted shell execution. | **Alex Solution:** Electron shell with `contextIsolation: true` and `nodeIntegration: false`. | Automated test `electron-security.test.ts` passes. |
| **SEC-03** | **Unauthenticated Loopback Ports** | Reference Project (`Mark-LVI`) | **HIGH** | `Mark-LVI-main/dashboard/server.py` relies on static pairing keys without loopback token guards. | **Alex Solution:** Dynamic 32-byte cryptographically secure session token required on all loopback requests. | Unauthenticated requests receive 401 Unauthorized. |
| **SEC-04** | **Indirect Prompt Injection in Web / Doc Search** | Target Project (`Alex Current`) | **HIGH** | `web_search_service.py` returns raw search snippet text without passive `<DATA>` boundary wrappers. | **Alex Remediation:** Defang external text with closing marker escaping and enclose in `<DATA>...</DATA>` markers. | Prompt injection payloads in search results are reported as passive data, not executed. |
| **SEC-05** | **Wayland Synthetic Input Silent Failure** | Target Project (`Alex Current`) | **MEDIUM** | `computer_control_service.py` does not detect Wayland, leading to silent input injection failure on Ubuntu. | **Alex Remediation:** Port `core/platform_support.py` Wayland detection and pass constraints to LLM prompt. | Model informs user of Wayland restriction instead of pretending it clicked. |
| **SEC-06** | **Unbounded Tool Execution Loop on Small Models** | Target Project (`Alex Current`) | **HIGH** | `live_voice_service.py` allows up to 4 tool calls per turn without anti-repetition guards. | **Alex Remediation:** Implement `ToolLoopGuard` capping identical repeated calls at 2. | Small models cannot execute infinite tool calling loops. |

---

## 2. Licensing, Copyright & Attribution Audit

### 2.1 Reference Project License: `Mark-LVI-main`
- **Copyright:** Copyright (c) 2026 FatihMakes
- **License Terms:** Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
- **Canonical Legal Code:** `https://creativecommons.org/licenses/by-nc/4.0/legalcode`
- **Key Obligations & Restrictions:**
  1. **Attribution (BY):** Appropriate credit must be given, with a link to the license and an indication of whether modifications were made.
  2. **NonCommercial (NC):** The material and derivative works cannot be used for commercial purposes without an explicit commercial license from the author.
  3. **No Additional Technological Restrictions:** You may not apply DRM or technological measures that legally restrict others from exercising licensed rights.

### 2.2 Target Project License: `ALEX-AI-main`
- **File:** `Alex/LICENSE`
- **Terms:** Fully aligned with CC BY-NC 4.0.
- **Attribution Statement:** Explicitly acknowledges that Alex AI Desktop Assistant is derived in part from architectural concepts and prototype code from `MARK 56 / JARVIS` (Copyright © 2026 FatihMakes).
- **Compliance Certification:** Alex adheres to all CC BY-NC 4.0 terms. Commercialization is strictly prohibited under the current baseline.

