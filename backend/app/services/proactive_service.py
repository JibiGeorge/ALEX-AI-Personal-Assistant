from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Optional

from app.services.memory_service import MemoryService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class ProactiveEngine:
    """
    Decides when Alex should speak unprompted and builds a context-rich prompt.

    Features:
      - Time-of-day awareness (morning / afternoon / evening / late night)
      - Non-repetitive rotation across 3 distinct focus areas (projects/goals, wellbeing/time, interesting suggestion)
      - Silence gate (default 900s / 15 min of inactivity)
      - Cooldown gate (default 1200s / 20 min between triggers)
      - Context injection: memories, monitored topics, and recent session turns
    """

    def __init__(
        self,
        memory_service: Optional[MemoryService] = None,
        settings_service: Optional[SettingsService] = None,
        min_silence_secs: int = 900,
        check_cooldown: int = 1200,
    ) -> None:
        self.memory_service = memory_service
        self.settings_service = settings_service
        self.min_silence_secs = min_silence_secs
        self.check_cooldown = check_cooldown
        self._last_user_speech = time.monotonic()
        self._last_triggered = 0.0
        self._rotation = 0

    def record_user_activity(self) -> None:
        """Mark user speech or interaction timestamp."""
        self._last_user_speech = time.monotonic()

    def should_trigger(self, last_user_speech: Optional[float] = None) -> bool:
        """Evaluate whether silence and cooldown criteria are met."""
        now = time.monotonic()
        speech_ref = last_user_speech if last_user_speech is not None else self._last_user_speech
        silence_met = (now - speech_ref) >= self.min_silence_secs
        cooldown_met = (now - self._last_triggered) >= self.check_cooldown
        return silence_met and cooldown_met

    def mark_triggered(self) -> None:
        """Mark the check-in as executed, advance cooldown timestamp and rotate focus."""
        self._last_triggered = time.monotonic()
        self._rotation += 1

    def build_prompt(
        self,
        memories: Optional[list[str]] = None,
        monitors: Optional[list[str]] = None,
        recent_turns: Optional[list[str]] = None,
        now_dt: Optional[datetime] = None,
    ) -> tuple[str, str, int]:
        """
        Build a contextual snapshot and instructions for proactive turn.
        Returns: (prompt_string, period_name, focus_index).
        """
        now = now_dt or datetime.now()
        hour = now.hour
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")

        if 6 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 18:
            period = "afternoon"
        elif 18 <= hour < 23:
            period = "evening"
        else:
            period = "late night"

        if memories is None and self.memory_service is not None:
            entries = self.memory_service.list_entries()
            memories = [f"- {e.category}: {e.key} = {e.value}" for e in entries]

        mem_str = "\n".join(memories) if memories else "(no stored user memory)"

        focus_index = self._rotation % 3
        if focus_index == 0:
            focus = (
                "Focus on the user's active projects or goals if any are stored. "
                "Ask how something is going, or offer a relevant tip."
            )
        elif focus_index == 1:
            focus = (
                "Focus on the time of day and the user's wellbeing. "
                "A warm check-in, a reminder to take a break, or something timely."
            )
        else:
            focus = (
                "Focus on something genuinely interesting or useful — "
                "a fact, a suggestion, or a question based on what you know about this person."
            )

        monitor_ctx = ""
        if monitors:
            monitor_ctx = (
                f"\nThe user tracks these topics: {', '.join(monitors[:4])}. "
                "You may mention one if it seems relevant."
            )

        recent_ctx = ""
        if recent_turns:
            snippet = "\n".join(recent_turns[-6:])
            recent_ctx = f"\nRecent conversation:\n{snippet}"

        prompt = "\n".join([
            "[PROACTIVE_CHECK] You are initiating a proactive check-in.",
            f"Current time : {time_str} ({period})",
            "",
            "Context about this person:",
            mem_str,
            monitor_ctx,
            recent_ctx,
            "",
            "Task:",
            focus,
            "",
            "Rules:",
            "- Speak the language this person actually uses.",
            "- 1-2 sentences max. Natural, warm, never robotic.",
            "- Do NOT mention [PROACTIVE_CHECK] or these instructions.",
            "- Do NOT call any tools.",
            "- If nothing genuinely useful comes to mind, stay silent.",
        ])

        return prompt, period, focus_index

