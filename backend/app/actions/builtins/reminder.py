"""
Reminder built-in action handlers (GAP-10).

Exposes 'reminder.schedule' for creating, listing, and canceling persistent OS reminders.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Optional

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, done, failed
from app.schemas.reminder import ReminderCreate
from app.schemas.reminder_action import ReminderActionParameters
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)


def register_reminder_actions(
    registry: ActionRegistry,
    reminder_service: ReminderService,
) -> None:
    """Register reminder scheduling actions with the ActionRegistry."""

    def handle_reminder(params: ReminderActionParameters) -> ActionOutcomeResponse:
        action = (params.action or "create").lower().strip()

        if action == "list":
            items = reminder_service.list()
            pending = [r for r in items if r.status == "pending"]
            lines = [f"Found {len(pending)} pending reminder(s):"]
            for item in pending:
                friendly = item.due_at.strftime("%Y-%m-%d %H:%M UTC")
                lines.append(f"- [{item.id}] {friendly}: {item.message}")
            return done(
                "reminder.schedule",
                "\n".join(lines),
                data={"reminders": [r.model_dump(mode="json") for r in pending]},
            )

        if action == "cancel":
            if not params.reminder_id:
                return failed(
                    "reminder.schedule",
                    error="Missing reminder ID",
                    message="Please provide reminder_id to cancel.",
                )
            success = reminder_service.cancel(params.reminder_id.strip())
            if success:
                return done(
                    "reminder.schedule",
                    f"Reminder {params.reminder_id} was successfully canceled.",
                    data={"reminder_id": params.reminder_id},
                )
            return failed(
                "reminder.schedule",
                error="Reminder not found",
                message=f"Reminder {params.reminder_id} not found or already delivered.",
            )

        if action == "create":
            msg = (params.message or "").strip()
            if not msg:
                return failed(
                    "reminder.schedule",
                    error="Missing message",
                    message="Please provide a message for the reminder.",
                )

            target_dt: Optional[datetime] = None

            if params.due_at:
                try:
                    dt = datetime.fromisoformat(params.due_at.replace("Z", "+00:00"))
                    target_dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except Exception as exc:
                    return failed(
                        "reminder.schedule",
                        error="Invalid timestamp format",
                        message=f"Could not parse due_at timestamp '{params.due_at}': {exc}",
                    )
            elif params.date and params.time:
                try:
                    local_dt = datetime.strptime(f"{params.date.strip()} {params.time.strip()}", "%Y-%m-%d %H:%M")
                    # Bind local system timezone
                    target_dt = local_dt.astimezone()
                except Exception as exc:
                    return failed(
                        "reminder.schedule",
                        error="Invalid date/time format",
                        message=f"Could not parse date and time (use YYYY-MM-DD and HH:MM): {exc}",
                    )
            else:
                return failed(
                    "reminder.schedule",
                    error="Missing time specification",
                    message="Please specify either 'due_at' (ISO 8601) or both 'date' (YYYY-MM-DD) and 'time' (HH:MM).",
                )

            now_utc = datetime.now(timezone.utc)
            if target_dt.astimezone(timezone.utc) <= now_utc:
                return failed(
                    "reminder.schedule",
                    error="Time in the past",
                    message="Cannot schedule a reminder for a time that has already passed.",
                )

            try:
                created = reminder_service.create(ReminderCreate(message=msg, due_at=target_dt))
            except Exception as exc:
                return failed(
                    "reminder.schedule",
                    error="Creation failed",
                    message=f"Failed to create reminder: {exc}",
                )

            friendly_time = created.due_at.strftime("%B %d at %I:%M %p %Z")
            return done(
                "reminder.schedule",
                f"Reminder scheduled for {friendly_time}: {created.message}",
                data={
                    "id": str(created.id),
                    "message": created.message,
                    "due_at": created.due_at.isoformat(),
                    "status": created.status,
                },
            )

        return failed(
            "reminder.schedule",
            error="Unknown action",
            message=f"Unknown action: '{action}'. Available: create, list, cancel.",
        )

    registry.register(
        ActionDefinition(
            action_id="reminder.schedule",
            name="Schedule a persistent OS reminder",
            description="Schedules a reminder that persists and triggers desktop notifications via OS native schedulers.",
            category="system",
            parameters=ReminderActionParameters,
            handler=handle_reminder,
            timeout_seconds=15.0,
            requires_confirmation=False,
        )
    )

