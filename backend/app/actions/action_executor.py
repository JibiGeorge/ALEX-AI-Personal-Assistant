import asyncio
import inspect
import json
import logging
import time
from collections import deque
from threading import Lock
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.actions.action_registry import ActionDefinition, ActionRegistry

logger = logging.getLogger(__name__)


class ActionExecutionResult(BaseModel):
    action_id: str
    status: Literal["success", "failed", "rejected"]
    data: object | None = None
    message: str
    error: str | None = None
    execution_time: float


class ActionExecutor:
    def __init__(self, registry: ActionRegistry, history_limit: int = 100):
        self._registry = registry
        self._history: deque[ActionExecutionResult] = deque(maxlen=history_limit)
        self._history_lock = Lock()
        self._remote_authorizer: object | None = None

    def set_remote_authorizer(self, authorizer: object | None) -> None:
        self._remote_authorizer = authorizer

    async def execute(
        self,
        action_id: str,
        parameters: object,
        *,
        confirmed: bool = False,
    ) -> ActionExecutionResult:
        started = time.monotonic()
        action = self._registry.get(action_id)
        if action is None:
            return await self._record(ActionExecutionResult(
                action_id=action_id,
                status="rejected",
                message="Action is not registered.",
                error="unknown_action",
                execution_time=0,
            ))
        if not action.enabled or not action.public_view()["enabled"]:
            return await self._record(self._result(
                action, "rejected", "Action is disabled or has missing dependencies.",
                "action_unavailable", started,
            ))
        if action.requires_confirmation and not confirmed:
            remote_approved = False
            if self._remote_authorizer is not None and hasattr(self._remote_authorizer, "request_action_approval"):
                try:
                    params_dict = (
                        parameters.model_dump(mode="json")
                        if hasattr(parameters, "model_dump")
                        else (parameters if isinstance(parameters, dict) else {})
                    )
                    remote_approved = await self._remote_authorizer.request_action_approval(
                        action.action_id,
                        params_dict,
                        timeout=15.0,
                    )
                except Exception as exc:
                    logger.warning("Remote authorization failed: %s", exc)
                    remote_approved = False

            if not remote_approved:
                return await self._record(self._result(
                    action, "rejected", "This action requires explicit user confirmation.",
                    "confirmation_required", started,
                ))
            confirmed = True
        try:
            validated = action.parameters.model_validate(parameters)
        except ValidationError as exc:
            return await self._record(self._result(
                action,
                "rejected",
                "Action parameters are invalid.",
                exc.json(include_url=False),
                started,
            ))

        try:
            async with asyncio.timeout(action.timeout_seconds):
                if inspect.iscoroutinefunction(action.handler):
                    data = await action.handler(validated)
                else:
                    data = await asyncio.to_thread(action.handler, validated)

            from app.actions.base import ActionOutcomeResponse, ToolOutcome
            if isinstance(data, ActionOutcomeResponse):
                if data.status == ToolOutcome.FAILED:
                    return await self._record(self._result(
                        action, "failed", data.message, data, started,
                    ))
                if data.status == ToolOutcome.ASK:
                    return await self._record(self._result(
                        action, "rejected", data.message, data, started,
                    ))
                return await self._record(self._result(
                    action, "success", data.message, data, started,
                ))

            return await self._record(self._result(
                action, "success", "Action executed successfully.", data, started,
            ))
        except TimeoutError:
            logger.warning("Action %s exceeded its execution timeout", action_id)
            return await self._record(self._result(
                action, "failed", "Action execution timed out.", "timeout", started,
            ))
        except Exception as exc:
            logger.exception("Action %s failed", action_id)
            return await self._record(self._result(
                action,
                "failed",
                "Action execution failed.",
                f"{type(exc).__name__}: {exc}",
                started,
            ))

    async def history(self) -> list[ActionExecutionResult]:
        with self._history_lock:
            return list(reversed(self._history))

    async def _record(self, result: ActionExecutionResult) -> ActionExecutionResult:
        with self._history_lock:
            self._history.append(result)
        return result

    @staticmethod
    def _result(
        action: ActionDefinition,
        status: Literal["success", "failed", "rejected"],
        message: str,
        data_or_error: object,
        started: float,
    ) -> ActionExecutionResult:
        success = status == "success"
        from app.actions.base import ActionOutcomeResponse
        if isinstance(data_or_error, ActionOutcomeResponse):
            if isinstance(data_or_error.data, list):
                payload: object = data_or_error.data
            elif isinstance(data_or_error.data, dict):
                payload = {
                    **data_or_error.data,
                    "outcome_status": data_or_error.status.value,
                    "action": data_or_error.action,
                    "message": data_or_error.message,
                }
            else:
                payload = data_or_error.data
            err_msg = data_or_error.error or (data_or_error.message if not success else None)
            return ActionExecutionResult(
                action_id=action.action_id,
                status=status,
                data=payload if success else None,
                message=message,
                error=None if success else (err_msg or str(data_or_error)),
                execution_time=round(time.monotonic() - started, 4),
            )

        return ActionExecutionResult(
            action_id=action.action_id,
            status=status,
            data=data_or_error if success else None,
            message=message,
            error=None if success else str(data_or_error),
            execution_time=round(time.monotonic() - started, 4),
        )


def model_function_response(result: ActionExecutionResult) -> dict[str, object]:
    if result.status == "success":
        payload: dict[str, object] = {"output": result.data, "status": result.status}
    else:
        message = "Action was rejected." if result.status == "rejected" else "Action failed."
        payload = {"error": message, "status": result.status}
    try:
        serialized = json.dumps(payload, ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError):
        logger.exception("Action %s returned a non-JSON model result", result.action_id)
        return {"error": "Action result could not be serialized.", "status": "failed"}
    if len(serialized) > 32_000:
        return {"error": "Action result exceeded the response size limit.", "status": "failed"}
    return payload
