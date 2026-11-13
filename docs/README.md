# Alex AI Desktop Assistant — Documentation Hub

Welcome to the central documentation hub for the **Alex AI Desktop Assistant**. This index organizes the architectural blueprints, migration assessments, cross-platform specifications, development workflows, security models, API references, planning roadmaps, and release governance records.

---

## 1. Documentation Directory Organization

```
docs/
├── README.md                              # Documentation Hub (This file)
├── DOCUMENTATION_CLEANUP_REPORT.md        # Consolidation & cleanup report
├── DOCUMENTATION_CLEANUP_MANIFEST.md      # Historical cleanup manifest
│
├── migration/                             # Migration & functional parity assessment
│   ├── MIGRATION_ASSESSMENT_SUMMARY.md    # Executive parity scorecard & readiness by OS
│   ├── MIGRATION_ASSESSMENT_CHANGE_MANIFEST.md # Exhaustive change manifest
│   ├── MIGRATION_MASTER_PLAN.md           # Strategic 10-phase master migration plan
│   ├── FEATURE_PARITY_MATRIX.md           # Complete 40-category parity comparison matrix
│   ├── MIGRATION_GAP_ANALYSIS.md          # Technical deep-dive into each discovered gap
│   ├── SOURCE_CODE_INVENTORY.md           # File-by-file code inventory of both repositories
│   └── MIGRATION_DECISIONS.md             # 10 formal Architectural Decision Records (ADRs)
│
├── architecture/                          # Architectural blueprints & system flows
│   ├── TARGET_ARCHITECTURE.md             # End-to-end target architecture & sequence flows
│   ├── CROSS_PLATFORM_ARCHITECTURE.md     # Hardware Abstraction Layer (HAL) & OS adapters
│   ├── IOS_ARCHITECTURE.md                # Mobile companion client architecture & pairing
│   ├── AI_PROVIDER_ARCHITECTURE.md        # Pluggable AI pipeline (Gemini, Local LLM, STT, TTS)
│   ├── ACTION_EXECUTION_ARCHITECTURE.md   # Dynamic action loader & 5-word outcome contract
│   ├── FORMAL_ARCHITECTURE_REVIEW.md      # Formal review of ADR-01..10, CRs, & Phase 3 specs
│   ├── ARCHITECTURE_GOVERNANCE.md         # Architecture governance & personal owner authorization register
│   ├── ARCHITECTURE.md                    # Core three-tier architecture overview
│   └── SYSTEM_FLOW.md                     # Application startup, action flow, and shutdown
│
├── platforms/                             # Operating system implementation guides
│   ├── PLATFORM_COMPATIBILITY_MATRIX.md   # Feature compatibility across Win, Mac, Linux, iOS
│   ├── WINDOWS.md                         # Windows 10/11 Win32, pycaw CoreAudio, NSIS packaging
│   ├── UBUNTU_LINUX.md                    # Ubuntu 22.04/24.04 Wayland/X11, pactl, AppImage/DEB
│   ├── MACOS.md                           # macOS Sonoma/Sequoia AppleScript, TCC, DMG packaging
│   └── IOS.md                             # iOS 16+ companion app, AVAudioEngine, FaceID approval
│
├── configuration/                         # Environment & secret configuration
│   ├── ENVIRONMENT_VARIABLES.md           # Authoritative environment variable inventory
│   ├── DEVELOPMENT_CONFIGURATION.md       # Developer environment setup & debug flags
│   ├── PRODUCTION_CONFIGURATION.md        # Production hardening & loopback security rules
│   └── SECRET_MANAGEMENT.md               # Zero-plaintext mandate & OS Keyring vault guide
│
├── security/                              # Threat modeling & security governance
│   ├── THREAT_MODEL.md                    # STRIDE threat model across trust boundaries
│   ├── SECURITY_GAP_REGISTER.md           # Security gap register & CC BY-NC 4.0 license audit
│   └── SECURITY.md                        # Three-tier isolation & loopback token authentication
│
├── api/                                   # API specifications & interface contracts
│   ├── API_REFERENCE.md                   # FastAPI REST endpoints & Gemini Live WebSocket
│   └── IPC_REFERENCE.md                   # Electron IPC window.alex typed preload bridge
│
├── planning/                              # Project management, roadmaps & registers
│   ├── PHASE_ROADMAP.md                   # Phased migration roadmap (Phases 0 through 9)
│   ├── PHASE_3_IMPLEMENTATION_BREAKDOWN.md # Detailed technical specs for 9 Phase 3 scopes
│   ├── PENDING_TASKS.md                   # 32 granular engineering tasks with acceptance criteria
│   ├── BLOCKER_REGISTER.md                # Consolidated blocker register (environmental & tech)
│   ├── RISK_REGISTER.md                   # STRIDE risk evaluation & contingency plans
│   └── CHANGE_REQUESTS.md                 # Formal change requests (CR-01..03) for frozen files
│
├── development/                           # Engineering workflows & guides
│   ├── SETUP.md                           # Prerequisites, installation, doctor, and packaging
│   ├── DEVELOPMENT_GUIDE.md               # Local developer workflows & debugging recipes
│   ├── TESTING.md                         # Automated test inventory & execution recipes
│   └── BUILD_AND_PACKAGING.md             # PyInstaller & Electron Builder packaging guide
│
├── release/                               # Release governance & scorecards
│   ├── RELEASE_STATUS.md                  # Live scorecard, Five Gates, blockers, human actions
│   ├── RELEASE_HISTORY.md                 # Milestone progression history (Milestones A01–A08)
│   ├── RELEASE_ACCEPTANCE_CRITERIA.md     # Measurable multi-platform release authorization gates
│   └── PROJECT_TASK_REGISTER.md           # Engineering task register & audit log
│
└── archive/                               # Historical archives & compliance evidence
    ├── external-acceptance/               # Acceptance records for Milestones A02–A08 & Evidence
    └── migration-analysis/                # Historical Mark-LVI migration and gap analysis reports
```

---

## 2. Directory Overviews & Key Documents

### [Migration & Parity Assessment](migration/)
- **[Migration Assessment Summary](migration/MIGRATION_ASSESSMENT_SUMMARY.md):** Executive scorecard summarizing parity metrics (11 FULL, 18 PARTIAL, 24 MISSING), readiness by OS, and next steps.
- **[Feature Parity Matrix](migration/FEATURE_PARITY_MATRIX.md):** Complete 40-category, 68-unit parity comparison between Mark-LVI and Alex.
- **[Technical Gap Analysis](migration/MIGRATION_GAP_ANALYSIS.md):** Technical deep-dive into AI model ladder, local models, speech pipeline, and window management.
- **[Master Migration Plan](migration/MIGRATION_MASTER_PLAN.md):** Strategic 10-phase roadmap from baseline verification to multi-platform release.
- **[Architectural Decision Records](migration/MIGRATION_DECISIONS.md):** 10 ADRs documenting architectural decisions and tradeoffs.
- **[Source Code Inventory](migration/SOURCE_CODE_INVENTORY.md):** Detailed file-by-file code inventory of both repositories.

### [Target & Cross-Platform Architecture](architecture/)
- **[Target Architecture](architecture/TARGET_ARCHITECTURE.md):** System topology, client layer, sidecar engine, and sequence flows.
- **[Cross-Platform Architecture (HAL)](architecture/CROSS_PLATFORM_ARCHITECTURE.md):** Hardware Abstraction Layer for window management, input, audio, and permissions.
- **[iOS Mobile Companion Architecture](architecture/IOS_ARCHITECTURE.md):** Mobile companion client, QR pairing, encrypted audio streaming, and FaceID action approval.
- **[AI Provider & Speech Pipeline](architecture/AI_PROVIDER_ARCHITECTURE.md):** Decoupled Hearing (STT), Thinking (LLM), and Speaking (TTS) architecture.
- **[Action Execution Architecture](architecture/ACTION_EXECUTION_ARCHITECTURE.md):** Dynamic tool discovery, 5-word outcome contract, and multi-level undo.

### [Platform Implementation Guides](platforms/)
- **[Platform Compatibility Matrix](platforms/PLATFORM_COMPATIBILITY_MATRIX.md):** Detailed capability comparison across Windows, Ubuntu Linux, macOS, and iOS.
- **[Windows Implementation Guide](platforms/WINDOWS.md):** Win32 window management, pycaw CoreAudio, Credential Manager, and NSIS installer.
- **[Ubuntu Linux Implementation Guide](platforms/UBUNTU_LINUX.md):** Wayland detection, X11 wmctrl/xdotool, pactl audio, and AppImage/DEB packaging.
- **[macOS Implementation Guide](platforms/MACOS.md):** AppleScript/Quartz window management, TCC permissions onboarding, and DMG packaging.
- **[iOS Companion Guide](platforms/IOS.md):** iPhone/iPad companion client, AVAudioEngine streaming, and App Store compliance.

### [Configuration & Secret Management](configuration/)
- **[Environment Variables](configuration/ENVIRONMENT_VARIABLES.md):** Complete variable inventory comparing Mark-LVI and Alex.
- **[Development Configuration](configuration/DEVELOPMENT_CONFIGURATION.md):** Local setup, environment overrides, and multi-terminal development.
- **[Production Configuration](configuration/PRODUCTION_CONFIGURATION.md):** Security hardening, loopback binding, and packaging configuration.
- **[Secret Management](configuration/SECRET_MANAGEMENT.md):** Zero-plaintext policy and native OS Keyring storage.

### [Security Architecture](security/)
- **[STRIDE Threat Model](security/THREAT_MODEL.md):** Threat modeling across trust boundaries, prompt injection defanging, and token security.
- **[Security Gap Register](security/SECURITY_GAP_REGISTER.md):** Security comparison and CC BY-NC 4.0 license compliance audit.
- **[Security Model](security/SECURITY.md):** Three-tier isolation, loopback bearer token, and A02 safety bounds.

### [Planning & Task Tracking](planning/)
- **[Phase Roadmap](planning/PHASE_ROADMAP.md):** Dependency-aware phased roadmap tracing Phases 0 through 9.
- **[Pending Task Register](planning/PENDING_TASKS.md):** 29 sequential engineering tasks with measurable acceptance criteria.
- **[Blocker Register](planning/BLOCKER_REGISTER.md):** Consolidated blocker register categorizing environmental, architectural, and governance blockers.
- **[Risk Register](planning/RISK_REGISTER.md):** Evaluation matrix covering quota limits, Wayland, and audio fragmentation.
- **[Change Requests](planning/CHANGE_REQUESTS.md):** Formal change requests (`CR-01..03`) proposing controlled modifications to frozen modules.

### [Release Governance](release/)
- **[Release Status Scorecard](release/RELEASE_STATUS.md):** Production certified release status (`AUTHORIZED_FOR_PRODUCTION_RELEASE`), physical score (`33/33`), and quality gates.
- **[Release Acceptance Criteria](release/RELEASE_ACCEPTANCE_CRITERIA.md):** Measurable release criteria across automated tests, Five Gates, and 33 Physical Protocols.
- **[Release History](release/RELEASE_HISTORY.md):** Chronological milestone progression history covering Milestones A01 through A08.

---

## 3. Governance Baseline Summary

- **Application Version:** `0.1.0`
- **Approved Snapshot Baseline:** `SNAPSHOT_v0.1.0-20261102`
- **Release Status:** `AUTHORIZED_FOR_PRODUCTION_RELEASE`
- **Physical Acceptance Score:** `33/33` Protocols Passed (100%)
- **Execution Authorization:** `PRODUCTION_RELEASE_AUTHORIZED`
- **Automated Tests:** 701 Passed, 1 Skipped (100% Deterministic)
