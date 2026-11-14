"""
Job Discovery Scheduler for ALEX Job Hunting Module.
Manages automatic periodic discovery sweeps and interfaces with ALEX's scheduler.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.schemas.job_hunting import ScheduleDiscoveryConfig

logger = logging.getLogger(__name__)


class JobDiscoveryScheduler:
    """Coordinates automated, periodic job discovery sweeps."""

    def __init__(
        self,
        discovery_service: Any,
        profile_service: Any,
        os_scheduler: Any = None,
    ) -> None:
        self.discovery_service = discovery_service
        self.profile_service = profile_service
        self.os_scheduler = os_scheduler
        self._enabled = True
        self._interval_hours = 12
        self._last_run_at: Optional[str] = None
        self._task: Optional[asyncio.Task] = None

    def get_config(self) -> ScheduleDiscoveryConfig:
        next_run: Optional[str] = None
        if self._enabled and self._last_run_at:
            try:
                last_dt = datetime.fromisoformat(self._last_run_at)
                next_dt = last_dt + timedelta(hours=self._interval_hours)
                next_run = next_dt.isoformat()
            except ValueError:
                pass
        elif self._enabled:
            next_run = (datetime.now(timezone.utc) + timedelta(hours=self._interval_hours)).isoformat()

        return ScheduleDiscoveryConfig(
            enabled=self._enabled,
            interval_hours=self._interval_hours,
            last_run_at=self._last_run_at,
            next_run_at=next_run,
        )

    def update_config(self, enabled: bool, interval_hours: int) -> ScheduleDiscoveryConfig:
        self._enabled = enabled
        self._interval_hours = max(1, min(168, interval_hours))
        logger.info(
            "Job discovery schedule updated: enabled=%s, interval=%d hours",
            self._enabled,
            self._interval_hours,
        )
        return self.get_config()

    async def trigger_scheduled_run(self) -> None:
        """Executes a single scheduled sweep."""
        if not self._enabled:
            return

        now_iso = datetime.now(timezone.utc).isoformat()
        self._last_run_at = now_iso
        logger.info("Executing scheduled job discovery sweep...")
        try:
            profile = self.profile_service.get_profile()
            discovered = await self.discovery_service.discover_jobs(profile=profile)
            logger.info("Scheduled sweep finished. %d listings retrieved.", len(discovered))
        except Exception as exc:
            logger.warning("Error during scheduled discovery sweep: %s", exc)

