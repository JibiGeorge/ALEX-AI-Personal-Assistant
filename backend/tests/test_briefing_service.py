from datetime import datetime, timezone, timedelta
import pytest

from app.core.storage import JsonDocumentStore
from app.schemas.memory import MemoryWrite
from app.schemas.reminder import ReminderCreate
from app.services.briefing_service import BriefingService
from app.services.memory_service import MemoryService
from app.services.reminder_service import ReminderService
from app.services.settings_service import SettingsService
from app.services.system_metrics_service import SystemMetricsService
from app.services.system_monitor_service import SystemMonitorService


def test_briefing_service_generates_complete_briefing(tmp_path):
    store = JsonDocumentStore(tmp_path)
    settings_service = SettingsService(store)
    memory_service = MemoryService(store)
    reminder_service = ReminderService(store)
    metrics_service = SystemMetricsService()
    monitor_service = SystemMonitorService()

    # Populate some memory
    memory_service.upsert("identity", "full_name", MemoryWrite(value="Dr. Henry Pym"))
    memory_service.upsert("identity", "role", MemoryWrite(value="Quantum Physicist"))

    # Populate a reminder
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    reminder_service.create(ReminderCreate(message="Particle test", due_at=future_time))

    service = BriefingService(
        settings_service=settings_service,
        memory_service=memory_service,
        reminder_service=reminder_service,
        system_metrics_service=metrics_service,
        system_monitor_service=monitor_service,
    )

    briefing = service.generate_briefing()

    assert briefing.assistant_name != ""
    assert "Dr. Henry Pym" in briefing.known_identity_facts[0] or "Dr. Henry Pym" in briefing.known_identity_facts[1]
    assert briefing.reminders.total_pending == 1
    assert "Particle test" in briefing.reminders.upcoming_messages
    assert briefing.system.cpu_percent >= 0.0
    assert briefing.system.system_status in ("Normal", "1 Active Alerts")
    assert "online and all systems nominal" in briefing.greeting

