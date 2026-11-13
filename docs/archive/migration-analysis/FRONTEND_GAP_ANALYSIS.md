# Frontend Gap Analysis

## Present Alex workflows

Alex provides an Electron shell with a React HUD and Setup/Controls flows. The audited renderer exposes chat with bounded user-selected attachments, settings, memory management, system telemetry/alerts, web search, reminders, audio controls, and a registry-driven Actions view. The renderer calls a typed `window.alex` bridge; Electron validates trusted sender/origin and routes only allowlisted operations to the authenticated Python API. It does not receive arbitrary filesystem or shell access.

## Gaps against source workflows

| ID | Source UI workflow | Alex evidence | Gap and status | Priority |
|---|---|---|---|---|
| UI01 | Qt native HUD, overlay, status and controls | React HUD/animated face, drawers and dialogs | Reference-inspired layout exists, but source measured face mesh, expressions, visemes, native overlays and synchronized lip-sync are absent. Partial. | P2 |
| UI02 | Live voice/chat activity and session controls | Live voice hook and typed chat | Core flow exists; reconnect, unified history, assistant session summary, wake/sleep and global PTT absent. Partial. | P1 |
| UI03 | Action result/status affordances | Dynamic Actions page reads API registry/history | Only registered actions appear; confirmation-gated actions cannot be run through model chat. Surface is real, not a source action parity claim. Partial. | P1 |
| UI04 | Computer/browser controls | No corresponding interaction page | No safe GUI/browser automation or permission/preview interface. Missing. | P0 |
| UI05 | File manager/organization | Attachment picker and file analysis | No local file browser, management, safe write preview, trash/undo, or processing result workflow. Partial. | P0 |
| UI06 | Media/video controls | Video attachments allowed | No HUD player, YouTube controls, transcript results, mute state or playback lifecycle. Missing. | P2 |
| UI07 | Monitoring and proactive workflows | System alert notifications | No topic-monitor manager, briefing/check-in consent, quiet hours, or session summary controls. Partial. | P2 |
| UI08 | Alternate provider/settings menus | Gemini credential, voice/settings/device controls | No provider/model selection, local model setup/download, STT/TTS configuration, or plugin settings. Partial. | P1 |
| UI09 | Phone dashboard | None | No QR/pairing, remote command, remote audio, or upload interface. Missing. | P2 |
| UI10 | Undo and action confirmation | Confirmation checkbox for sensitive registered actions | No general preview/undo history for file/desktop/system side effects; broad safety UX missing. Partial. | P0 |
| UI11 | Screen/webcam privacy workflow | Browser microphone permission only | No screen/camera capture confirmation, indicator, stop control, or privacy history. Missing. | P0 |
| UI12 | App and OS controls | Login startup, desktop shortcut and external URL opening | No installed-app picker or OS-setting/shortcut workflow. Partial. | P1 |

## Incorrect or stale UI state

The audited Alex `OverviewPage` states voice is not enabled, which conflicts with the Live voice implementation and historical Windows microphone smoke test. Treat this as stale status copy; correct it when the UI is next changed, and derive the indicator from actual backend/voice state rather than a static assertion.

## UI interaction validation

Frontend tests previously reported 19 passing tests, and renderer/Electron TypeScript checks plus Vite production build passed before the latest backend-only tool-call changes. Tests cover page-level operations documented in the feature status; there is no end-to-end regression comparison with the Qt source UI, no UI test for the new model-driven Live tool call, and no real hardware/browser workflow test in this assessment.

High-risk controls must not be surfaced as ordinary buttons with model-filled parameters. Before implementing them, define a human-readable preview, explicit user confirmation, cancellation, result/error state, and a reversal path where feasible.
