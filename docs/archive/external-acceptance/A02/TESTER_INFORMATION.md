# A02 – External Tester & Environment Specification

This document records the hardware, operating system, runtime dependencies, and configuration of the authorized external tester validating milestone **A02 (Computer Control)**.

---

## 1. Authorized Tester Identity

| Field | Tester Entry |
|---|---|
| **Full Name** | *[Enter Authorized Tester Name]* |
| **Role / Title** | *[e.g. Lead QA Engineer / Security Auditor]* |
| **Organization** | *[e.g. Platform QA Team]* |
| **Test Execution Date** | *[YYYY-MM-DD]* |
| **Sign-Off Authority** | *[Authorized Verification Signatory]* |

---

## 2. Workstation Hardware & Display Configuration

*Recommended Display Setting:* Primary display set to **100% DPI Scaling** to avoid OS coordinate translation interpolation.

| Hardware Specification | Tester Value | Verification Command / Check |
|---|---|---|
| **Machine Model** | *[e.g. Dell Latitude 7440 / Custom Desktop]* | `systeminfo \| findstr /B /C:"System Model"` |
| **CPU Architecture** | *[x86_64 / AMD64]* | `echo %PROCESSOR_ARCHITECTURE%` |
| **Primary Display Resolution** | *[e.g. 1920x1080 / 2560x1440]* | Windows Display Settings |
| **Display DPI Scaling** | *[e.g. 100%]* | Windows Display Settings |
| **Physical Display Access** | *[Physical Monitor / Interactive Console RDP]* | Must have active graphical desktop session |

---

## 3. Operating System & Security Policy Verification

| OS Parameter | Required Value | Actual Workstation Value | Check Command |
|---|---|---|---|
| **OS Name** | Windows 10 or Windows 11 | *[e.g. Windows 11 Enterprise]* | `systeminfo \| findstr /B /C:"OS Name"` |
| **OS Version / Build** | 10.0.19045+ or 10.0.22000+ | *[e.g. 10.0.22631 Build 22631]* | `winver` or `systeminfo` |
| **Execution Policy** | Permitted to run Python & Tkinter GUI scripts | *[PERMITTED / UNRESTRICTED]* | Must execute without GPO block |
| **Software Restriction / AppLocker** | Host GPO allows Python desktop automation | *[NO BLOCK ENCOUNTERED]* | `python -c "print('OK')"` |

---

## 4. Software Runtimes & Dependency State

| Software Component | Required Version | Workstation Actual Version | Verification Command |
|---|---|---|---|
| **Python Runtime** | Python 3.11+ | *[e.g. Python 3.11.8]* | `backend\.venv\Scripts\python --version` |
| **Virtual Environment** | `Alex/backend/.venv` | *[Configured & active]* | `Test-Path backend\.venv` |
| **Backend Packages** | 10 required packages | *[10/10 verified]* | `backend\.venv\Scripts\python -m pip check` |
| **Node.js Runtime** | Node 20+ | *[e.g. v20.12.0]* | `node --version` |
| **npm Package Manager** | npm 10+ | *[e.g. v10.5.0]* | `npm --version` |
| **Frontend Packages** | `frontend/node_modules` | *[Installed & verified]* | `npm --prefix frontend list electron vite` |

---

## 5. Network Connectivity & AI Endpoint Reachability

| Service Target | Port / Protocol | Expected State | Actual Workstation Outcome |
|---|---|---|---|
| **Local Backend Loopback** | `127.0.0.1:8765` (HTTP) | Open & Bindable | *[Pass / Open]* |
| **Local Frontend Loopback** | `127.0.0.1:5173` (HTTP) | Open & Bindable | *[Pass / Open]* |
| **Google Gemini API** | `generativelanguage.googleapis.com:443` | Reachable over HTTPS | *[Pass / Reachable]* |

---

## 6. Runner Host Status (Prior to External Handoff)

- **Development Host Observation (2026-11-01):**  
  On the agent development runner, attempting command line execution was halted by workstation Active Directory Group Policy (`This program is blocked by group policy`).  
- **Handoff Requirement:**  
  The external tester must execute the test suites on an authorized, unrestricted Windows machine and confirm in Section 3 that no Group Policy block was encountered.

