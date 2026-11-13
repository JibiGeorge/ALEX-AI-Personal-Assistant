"""
Unit tests for OS Native Scheduled Reminders Adapter & Actions (GAP-10).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import uuid

import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.reminder import register_reminder_actions
from app.core.storage import JsonDocumentStore
from app.schemas.reminder import ReminderCreate
from app.schemas.reminder_action import ReminderActionParameters
from app.services.os_scheduler_adapter import (
    OSSchedulerAdapter,
    get_current_os,
    sanitise_message,
)
from app.services.reminder_service import ReminderService


@pytest.fixture
def temp_dirs(tmp_path: Path):
    scripts_dir = tmp_path / "scripts"
    agents_dir = tmp_path / "agents"
    scripts_dir.mkdir()
    agents_dir.mkdir()
    return scripts_dir, agents_dir


@pytest.fixture
def scheduler(temp_dirs):
    scripts_dir, agents_dir = temp_dirs
    return OSSchedulerAdapter(scripts_dir=scripts_dir, agents_dir=agents_dir, enabled=True)


@pytest.fixture
def reminder_service(tmp_path: Path, scheduler: OSSchedulerAdapter):
    store = JsonDocumentStore(tmp_path)
    return ReminderService(store, scheduler=scheduler)


# =============================================================================
# 1. Message Sanitization & OS Detection Tests
# =============================================================================

def test_sanitise_message():
    raw = 'Call "John" \\ Meeting\n\r Urgent!'
    clean = sanitise_message(raw)
    assert clean == "Call John  Meeting  Urgent!"
    assert len(sanitise_message("a" * 300, max_len=50)) == 50


def test_get_current_os():
    os_name = get_current_os()
    assert os_name in ("mac", "windows", "linux")


# =============================================================================
# 2. Notification Script Generation Tests
# =============================================================================

def test_write_notify_script(scheduler: OSSchedulerAdapter):
    task_name = "AlexReminder_test123_20261105_100000"
    script = scheduler.write_notify_script(task_name, "Check oven", "rem-123")
    assert script.exists()
    content = script.read_text(encoding="utf-8")
    assert "Check oven" in content
    assert "rem-123" in content
    assert "Alex Reminder" in content


# =============================================================================
# 3. macOS LaunchAgent Scheduling Tests
# =============================================================================

def test_schedule_mac(scheduler: OSSchedulerAdapter):
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    with patch("app.services.os_scheduler_adapter.get_current_os", return_value="mac"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            job_id = scheduler.schedule_job("11112222-3333-4444-5555-666677778888", "Dental appointment", future)
            assert job_id is not None
            assert "com.alex.reminder" in job_id
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "launchctl"
            assert args[1] == "load"

            # Check plist exists
            plists = list(scheduler.agents_dir.glob("*.plist"))
            assert len(plists) == 1
            plist_content = plists[0].read_text(encoding="utf-8")
            assert "StartCalendarInterval" in plist_content


# =============================================================================
# 4. Windows Task Scheduler Tests
# =============================================================================

def test_schedule_windows(scheduler: OSSchedulerAdapter):
    future = datetime.now(timezone.utc) + timedelta(hours=3)
    with patch("app.services.os_scheduler_adapter.get_current_os", return_value="windows"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            job_id = scheduler.schedule_job("22223333-4444-5555-6666-777788889999", "Submit report", future)
            assert job_id is not None
            assert job_id.startswith("AlexReminder_")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "schtasks"
            assert args[1] == "/Create"


# =============================================================================
# 5. Linux Scheduling Tests
# =============================================================================

def test_schedule_linux_systemd(scheduler: OSSchedulerAdapter):
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    with patch("app.services.os_scheduler_adapter.get_current_os", return_value="linux"):
        with patch("shutil.which", side_effect=lambda cmd: "/bin/" + cmd if cmd == "systemd-run" else None):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                job_id = scheduler.schedule_job("33334444-5555-6666-7777-888899990000", "Standup meeting", future)
                assert job_id is not None
                args = mock_run.call_args[0][0]
                assert args[0] == "systemd-run"


# =============================================================================
# 6. Cancellation Tests
# =============================================================================

def test_cancel_mac_job(scheduler: OSSchedulerAdapter):
    rem_id = "44445555-6666-7777-8888-999900001111"
    slug = rem_id.replace("-", "")[:12]

    # Pre-create a dummy plist and script
    plist = scheduler.agents_dir / f"com.alex.reminder.AlexReminder_{slug}_20261105.plist"
    plist.write_text("dummy plist", encoding="utf-8")
    script = scheduler.scripts_dir / f"AlexReminder_{slug}_20261105.py"
    script.write_text("dummy script", encoding="utf-8")

    with patch("app.services.os_scheduler_adapter.get_current_os", return_value="mac"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            cancelled = scheduler.cancel_job(rem_id)
            assert cancelled is True
            assert not plist.exists()
            assert not script.exists()
            mock_run.assert_called_once()
            assert mock_run.call_args[0][0][0] == "launchctl"
            assert mock_run.call_args[0][0][1] == "unload"


def test_disabled_scheduler(scheduler: OSSchedulerAdapter):
    scheduler.enabled = False
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    job_id = scheduler.schedule_job("dummy-id", "Test", future)
    assert job_id is None


# =============================================================================
# 7. ReminderService Integration Tests
# =============================================================================

def test_reminder_service_create_and_cancel_triggers_os_scheduler(reminder_service: ReminderService):
    future = datetime.now(timezone.utc) + timedelta(hours=4)
    with patch.object(reminder_service.scheduler, "schedule_job", return_value="test-job-id") as mock_sched:
        with patch.object(reminder_service.scheduler, "cancel_job", return_value=True) as mock_cancel:
            created = reminder_service.create(ReminderCreate(message="Team sync", due_at=future))
            assert created.message == "Team sync"
            mock_sched.assert_called_once_with(str(created.id), "Team sync", created.due_at)

            cancelled = reminder_service.cancel(str(created.id))
            assert cancelled is True
            mock_cancel.assert_called_once_with(str(created.id))


# =============================================================================
# 8. ActionRegistry 'reminder.schedule' Action Tests
# =============================================================================

def test_action_reminder_create_due_at(reminder_service: ReminderService):
    registry = ActionRegistry()
    register_reminder_actions(registry, reminder_service)

    action = registry.get("reminder.schedule")
    assert action is not None
    assert action.category == "system"
    assert action.requires_confirmation is False

    future = datetime.now(timezone.utc) + timedelta(days=1)
    params = ReminderActionParameters(
        action="create",
        message="Review quarterly metrics",
        due_at=future.isoformat(),
    )
    res = action.handler(params)
    assert res.status == ToolOutcome.DONE
    assert "Review quarterly metrics" in res.message
    assert "id" in res.data


def test_action_reminder_create_date_time(reminder_service: ReminderService):
    registry = ActionRegistry()
    register_reminder_actions(registry, reminder_service)
    action = registry.get("reminder.schedule")

    future = datetime.now() + timedelta(days=2)
    params = ReminderActionParameters(
        action="create",
        message="Water the plants",
        date=future.strftime("%Y-%m-%d"),
        time="15:30",
    )
    res = action.handler(params)
    assert res.status == ToolOutcome.DONE
    assert "Water the plants" in res.message


def test_action_reminder_list_and_cancel(reminder_service: ReminderService):
    registry = ActionRegistry()
    register_reminder_actions(registry, reminder_service)
    action = registry.get("reminder.schedule")

    future = datetime.now(timezone.utc) + timedelta(days=3)
    create_res = action.handler(
        ReminderActionParameters(action="create", message="Buy groceries", due_at=future.isoformat())
    )
    rem_id = create_res.data["id"]

    list_res = action.handler(ReminderActionParameters(action="list"))
    assert list_res.status == ToolOutcome.DONE
    assert "Buy groceries" in list_res.message

    cancel_res = action.handler(ReminderActionParameters(action="cancel", reminder_id=rem_id))
    assert cancel_res.status == ToolOutcome.DONE
    assert "successfully canceled" in cancel_res.message


def test_action_reminder_validation_failures(reminder_service: ReminderService):
    registry = ActionRegistry()
    register_reminder_actions(registry, reminder_service)
    action = registry.get("reminder.schedule")

    # Missing message
    res = action.handler(ReminderActionParameters(action="create", message=""))
    assert res.status == ToolOutcome.FAILED
    assert "provide a message" in res.message

    # Past date
    past = datetime.now(timezone.utc) - timedelta(days=1)
    res2 = action.handler(
        ReminderActionParameters(action="create", message="Past reminder", due_at=past.isoformat())
    )
    assert res2.status == ToolOutcome.FAILED
    assert "passed" in res2.message
