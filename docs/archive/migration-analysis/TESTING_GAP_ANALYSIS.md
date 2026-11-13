# Testing and Runtime Verification Gap Analysis

## Evidence available

| Area | Evidence | Result / limitation |
|---|---|---|
| Alex backend | Last recorded full backend suite | **58 passed**, 3 dependency/deprecation warnings. Includes API, settings/memory/reminder/search, action registry/executor, fake Gemini text tool dispatch, Live tool response/configuration and per-turn limit tests. |
| Alex frontend | Previous recorded frontend suite | **19 passed**. Covers tested UI pages/components; no whole-source regression run. |
| TypeScript/Electron/Vite | Previous validation | Renderer and Electron TypeScript checks and Vite production build passed before the recent backend-only tool-call changes. |
| Windows Live audio | Historical hardware smoke test | Real key and microphone tested on Windows before Gemini tool-call integration; user transcript, visible reply and spoken output were observed. Does not verify current tool declarations. |
| Packaged sidecar | Historical packaged smoke check | Bundled Python process started and unauthenticated health returned HTTP 401. Clean install/uninstall and graceful shutdown not established. |
| Mark-LVI-main runtime | This assessment | Not executed. No parity or source test success is claimed. |
| Lint | Ruff attempt | Not run successfully: Ruff module was missing from Alex's active virtual environment. |

## Missing test coverage

| ID | Test gap | Required evidence | Priority |
|---|---|---|---|
| T01 | Source-vs-target observable regression | Input/output/error fixtures for each source action that is safe to reproduce | P0 |
| T02 | Gemini function calling against current SDK/provider | Real key, one safe read-only action in text and Live; verify returned user response, no duplicate execution | P1 |
| T03 | Malformed/untrusted model calls | Unknown/disabled IDs, unexpected schema, non-JSON, oversized args/results, tool limit, handler failure | P0 |
| T04 | Confirmation boundary | Ensure confirmation-gated actions never appear in model declarations and HTTP/UI confirmations are independent | P0 |
| T05 | Live lifecycle | WebSocket disconnect, model failure, sidecar shutdown, cancellation and repeated connect/close | P1 |
| T06 | PTT/audio device routing | Real selected mic/output, hotplug, permission denial, release silence, interruption, echo | P1 |
| T07 | Platform capability matrix | Windows/macOS/Linux startup, notification, keyring, audio and supported sensor behavior | P1 |
| T08 | Reminder closed-app behavior | Native scheduler install/cancel/fire exactly once, timezone/DST/reboot | P1 |
| T09 | Side-effect policy tests | Temp workspace only for file writes/moves, undo/restore, app launch, settings and user-confirmed irreversible effects | P0 |
| T10 | Phone dashboard security | Pairing, HTTPS, replay/expiry, LAN boundary, auth, upload limits and command allowlist | P2 |
| T11 | Installer lifecycle | Clean machine install/uninstall, backend process ownership, readiness/failure report, graceful shutdown, signing | P1 |
| T12 | External service contracts | Mocked plus opt-in live tests for grounded search, weather, flight, YouTube and messaging if approved | P2 |
| T13 | Frontend end-to-end workflows | Chat, attachments, setup, reminders, actions, errors/loading, accessibility and navigation | P1 |

## Safe verification plan

- Keep all file mutation tests in temporary directories; never test delete/organize against a user's desktop.
- Use fake Gemini sessions for tool-call loops and mocked external services for deterministic unit/integration coverage.
- Live Gemini testing should use the existing credential store, a read-only action only, user approval, and no key output in logs or reports.
- Test screen/camera, app control, messaging, power, and package installation only after a clear user confirmation and isolated test account/device exists.
- Mark unavailable sensors, optional modules, and missing credentials as `NEEDS_VERIFICATION`, not as passing or as a fabricated success.

## Exit criteria

For each feature ID, require a test ID, exact inputs and observable results, expected error case, platform scope, and recorded evidence. “Implementation exists” is not a passing parity test. Source actions that are unsafe or source-missing must be excluded explicitly rather than simulated as successful.
