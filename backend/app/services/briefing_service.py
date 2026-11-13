from datetime import datetime, timezone

from app.schemas.briefing import (
    BriefingReminderSummary,
    BriefingResponse,
    BriefingSystemSummary,
)
from app.services.memory_service import MemoryService
from app.services.reminder_service import ReminderService
from app.services.settings_service import SettingsService
from app.services.system_metrics_service import SystemMetricsService
from app.services.system_monitor_service import SystemMonitorService


class BriefingService:
    def __init__(
        self,
        settings_service: SettingsService,
        memory_service: MemoryService,
        reminder_service: ReminderService,
        system_metrics_service: SystemMetricsService,
        system_monitor_service: SystemMonitorService,
    ) -> None:
        self._settings_service = settings_service
        self._memory_service = memory_service
        self._reminder_service = reminder_service
        self._metrics_service = system_metrics_service
        self._monitor_service = system_monitor_service

    def generate_briefing(self) -> BriefingResponse:
        settings, _ = self._settings_service.get()
        assistant_name = settings.assistant_name or "Alex"
        user_name = settings.user_name or "User"

        # Reminders
        pending_reminders = self._reminder_service.list()
        due_reminders = self._reminder_service.list_due()
        reminder_messages = [r.message for r in pending_reminders[:5]]

        reminders_summary = BriefingReminderSummary(
            total_pending=len(pending_reminders),
            due_now=len(due_reminders),
            upcoming_messages=reminder_messages,
        )

        # System telemetry & alerts
        metrics = self._metrics_service.snapshot()
        alerts = self._monitor_service.check(metrics)
        alert_count = len(alerts)
        system_status = "Normal" if alert_count == 0 else f"{alert_count} Active Alerts"

        system_summary = BriefingSystemSummary(
            cpu_percent=metrics.cpu_percent,
            ram_percent=metrics.memory_percent,
            active_alerts_count=alert_count,
            system_status=system_status,
        )

        # Identity memories
        identity_facts = [
            f"{entry.key}: {entry.value}"
            for entry in self._memory_service.list_entries()
            if entry.category == "identity"
        ]

        # Greeting logic based on UTC/local hour
        now = datetime.now(timezone.utc)
        hour = now.hour
        if 5 <= hour < 12:
            time_greeting = "Good morning"
        elif 12 <= hour < 17:
            time_greeting = "Good afternoon"
        elif 17 <= hour < 22:
            time_greeting = "Good evening"
        else:
            time_greeting = "Greetings"

        greeting = f"{time_greeting}, {user_name}. {assistant_name} online and all systems nominal."

        return BriefingResponse(
            greeting=greeting,
            assistant_name=assistant_name,
            user_name=user_name,
            timestamp_iso=now.isoformat(),
            system=system_summary,
            reminders=reminders_summary,
            known_identity_facts=identity_facts,
        )

