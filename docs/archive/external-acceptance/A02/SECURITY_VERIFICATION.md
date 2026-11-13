# A02 – Security & Negative Verification Results

**Target Invariant:** Zero unconfirmed computer control; tamper-proof proposals; latched emergency stop; watchdog protection.  
**Authoritative Implementation:** [`Alex/backend/app/services/computer_control_service.py`](file:///d:/Workspace/Jibi/Alex/backend/app/services/computer_control_service.py)  
**Authoritative Action Registration:** [`Alex/backend/app/actions/builtins/computer_control.py`](file:///d:/Workspace/Jibi/Alex/backend/app/actions/builtins/computer_control.py)  
**Current Verification Status:** **`AUTOMATED VERIFIED / PENDING RUNTIME CONFIRMATION`**

---

## 1. Security Invariants & Test Outcomes Table

| Test ID | Security Control | Verification Procedure | Expected Security Outcome | Automated Test Proof | Runtime Evidence | Result |
|---|---|---|---|---|---|---|
| **SEC-01** | **Direct Model Bypass Defense** | Inspect `ActionRegistry.model_declarations()`; attempt unconfirmed call to `computer.control`. | Confirmation-gated actions are **omitted from Gemini tool declarations**. Invoking without `confirmed=True` returns `error="confirmation_required"`. | `test_action_registry.py#L43-L70`<br>`test_api.py#L418-L426` | `evidence/security/model_declarations.json` | *[PASS / PENDING]* |
| **SEC-02** | **Proposal Rejection (`dismiss`)** | Generate proposal -> Click "Reject request" in Controls UI. | Proposal UUID is popped and discarded. Zero desktop input occurs. Replaying dismissal returns error. | `test_api.py#L620-L638` | `evidence/security/dismiss_request.json` | *[PASS / PENDING]* |
| **SEC-03** | **Proposal Expiration (300s TTL)** | Generate proposal -> Wait 300 seconds without user approval. | `_expire_pending_requests` deletes proposal. Subsequent approval returns `ValueError("Desktop-control request is missing, expired, or already handled.")`. | `test_computer_control_service.py#L270-L280` | `evidence/security/expired_request.json` | *[PASS / PENDING]* |
| **SEC-04** | **Parameter Tampering Defense** | Generate proposal -> Attempt to pass modified coordinates in `computer.approve`. | `computer.approve` accepts **only** `request_id: UUID` (`extra="forbid"`). Modified payloads are rejected with HTTP 422. Parameters cannot be changed after review. | `test_api.py#L583-L596` | `evidence/security/tamper_rejection.json` | *[PASS / PENDING]* |
| **SEC-05** | **Duplicate Approval Prevention** | Generate proposal -> Approve it once -> Attempt to replay the approval with the same UUID. | `_pending_requests.pop(request_id)` consumes the token on first execution. Second approval returns `ValueError` ("already handled"). | `test_api.py#L612-L619` | `evidence/security/replay_rejection.json` | *[PASS / PENDING]* |
| **SEC-06** | **Emergency Stop Latch & Mouse Release** | Trigger emergency stop in Controls UI or call `computer.stop`. | Sets `_stop_requested`, clears all pending requests, forcibly dispatches `adapter.mouseUp()`. Stops execution and **stays latched** until explicitly re-armed via `set_permission(True)`. | `test_computer_control_service.py#L208-L222`<br>`test_api.py#L466-L487` | `evidence/security/emergency_stop.json` | *[PASS / PENDING]* |
| **SEC-07** | **12-Second Operation Watchdog** | Dispatch a long-running drag or wait exceeding 12 seconds. | Daemon timer triggers `_timeout_operation`, sets `_timed_out`, and releases mouse button. Checkpoints abort with `TimeoutError`. | `test_computer_control_service.py#L282-L307` | Unit test log | *[PASS / PENDING]* |
| **SEC-08** | **Shutdown Revocation** | Stop backend or teardown FastAPI lifespan. | Lifespan context manager executes `set_permission(False)` in `finally` block, revoking session permission and latching stop state. | `test_api.py#L502-L525` | Unit test log | *[PASS / PENDING]* |

---

## 2. Test Execution Notes for External Tester

To execute SEC-01 through SEC-06 in the UI:
1. **Rejection:** Request a click via chat. In Controls drawer, click **"Reject request"**. Confirm no click occurs.
2. **Replay:** Attempt to send a duplicate approval via API or browser developer tools using the same UUID. Confirm rejection.
3. **Emergency Stop:** While a pointer drag or sequence is in progress, click **"Emergency Stop"**. Confirm cursor halts, button releases, and subsequent requests are rejected until permission is toggled off and back on.
4. **Capture Evidence:** Save screenshots of error toasts or copy API responses into `Alex/docs/external-acceptance/A02/evidence/security/`.

