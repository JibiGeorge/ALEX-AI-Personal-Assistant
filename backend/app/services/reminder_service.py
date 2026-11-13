from datetime import datetime, timezone
import logging
from threading import RLock
from typing import Optional
from uuid import uuid4

from pydantic import ValidationError

from app.core.storage import JsonDocumentStore, StorageError
from app.schemas.reminder import Reminder, ReminderCreate
from app.services.os_scheduler_adapter import OSSchedulerAdapter

logger = logging.getLogger(__name__)

_DOCUMENT = "reminders.json"


class ReminderService:
    def __init__(self, store: JsonDocumentStore, scheduler: Optional[OSSchedulerAdapter] = None):
        self._store = store
        self._scheduler = scheduler or OSSchedulerAdapter()
        self._lock = RLock()

    @property
    def scheduler(self) -> OSSchedulerAdapter:
        return self._scheduler

    def list(self) -> list[Reminder]:
        with self._lock:
            return self._read()

    def create(self, request: ReminderCreate) -> Reminder:
        due_at = request.due_at.astimezone(timezone.utc)
        if due_at <= datetime.now(timezone.utc):
            raise ValueError("Reminder time must be in the future")
        reminder = Reminder(
            id=uuid4(),
            message=request.message.strip(),
            due_at=due_at,
            status="pending",
        )
        with self._lock:
            reminders = self._read()
            reminders.append(reminder)
            self._write(reminders)

        try:
            self._scheduler.schedule_job(str(reminder.id), reminder.message, reminder.due_at)
        except Exception as exc:
            logger.warning("Failed to schedule OS reminder job for %s: %s", reminder.id, exc)

        return reminder

    def cancel(self, reminder_id: str) -> bool:
        with self._lock:
            reminders = self._read()
            remaining = [
                reminder for reminder in reminders
                if str(reminder.id) != reminder_id or reminder.status == "delivered"
            ]
            if len(remaining) == len(reminders):
                return False
            self._write(remaining)

        try:
            self._scheduler.cancel_job(reminder_id)
        except Exception as exc:
            logger.warning("Failed to cancel OS reminder job for %s: %s", reminder_id, exc)

        return True

    def list_due(self) -> list[Reminder]:
        now = datetime.now(timezone.utc)
        with self._lock:
            reminders = self._read()
            return [
                reminder for reminder in reminders
                if reminder.status == "pending" and reminder.due_at <= now
            ]

    def mark_delivered(self, reminder_id: str) -> Reminder | None:
        now = datetime.now(timezone.utc)
        with self._lock:
            reminders = self._read()
            for index, reminder in enumerate(reminders):
                if str(reminder.id) != reminder_id:
                    continue
                if reminder.status == "delivered":
                    return reminder
                if reminder.due_at > now:
                    return None
                delivered = reminder.model_copy(update={"status": "delivered"})
                reminders[index] = delivered
                self._write(reminders)
                try:
                    self._scheduler.cancel_job(reminder_id)
                except Exception:
                    pass
                return delivered
            return None

    def _read(self) -> list[Reminder]:
        document = self._store.read(_DOCUMENT, {"version": 1, "reminders": []})
        records = document.get("reminders")
        if not isinstance(records, list):
            raise StorageError("Stored reminders must be a list")
        try:
            return [Reminder.model_validate(record) for record in records]
        except ValidationError as exc:
            raise StorageError("Stored reminders are invalid") from exc

    def _write(self, reminders: list[Reminder]) -> None:
        self._store.write(
            _DOCUMENT,
            {
                "version": 1,
                "reminders": [reminder.model_dump(mode="json") for reminder in reminders],
            },
        )
