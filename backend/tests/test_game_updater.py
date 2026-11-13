from __future__ import annotations

import asyncio
from pathlib import Path
import pytest

from app.actions.action_executor import ActionExecutor
from app.actions.action_registry import ActionRegistry
from app.actions.builtins.game_updater import register_game_updater_actions
from app.schemas.game_updater import GameUpdaterParams
from app.services.game_updater_service import GameUpdaterService


def test_game_updater_service_manifest_parsing(tmp_path):
    steamapps = tmp_path / "steamapps"
    steamapps.mkdir(parents=True)

    # Create dummy appmanifest_730.acf (Counter-Strike 2)
    acf_content = """
    "AppState"
    {
        "appid"     "730"
        "name"      "Counter-Strike 2"
        "installdir" "Counter-Strike Global Offensive"
    }
    """
    (steamapps / "appmanifest_730.acf").write_text(acf_content, encoding="utf-8")

    # Create dummy appmanifest_1091500.acf (Cyberpunk 2077)
    cp_content = """
    "AppState"
    {
        "appid"     "1091500"
        "name"      "Cyberpunk 2077"
        "installdir" "Cyberpunk 2077"
    }
    """
    (steamapps / "appmanifest_1091500.acf").write_text(cp_content, encoding="utf-8")

    service = GameUpdaterService(steam_path=tmp_path)
    games = service.list_steam_games()

    assert len(games) == 2
    names = [g.name for g in games]
    assert "Counter-Strike 2" in names
    assert "Cyberpunk 2077" in names


def test_game_updater_schedule_and_status():
    service = GameUpdaterService()

    # Schedule daily update at 04:30
    res_sched = service.execute_action(
        GameUpdaterParams(action="schedule", hour=4, minute=30)
    )
    assert res_sched.action == "schedule"
    assert res_sched.scheduled_time == "04:30"

    # Status check
    res_status = service.execute_action(GameUpdaterParams(action="status"))
    assert res_status.scheduled_time == "04:30"
    assert "04:30" in res_status.message

    # Cancel schedule
    res_cancel = service.execute_action(GameUpdaterParams(action="cancel_schedule"))
    assert res_cancel.scheduled_time is None


def test_action_game_update(tmp_path):
    registry = ActionRegistry()
    service = GameUpdaterService(steam_path=tmp_path)
    register_game_updater_actions(registry, service)

    executor = ActionExecutor(registry)

    async def _test():
        res = await executor.execute("game.update", {"action": "list", "platform": "steam"})
        assert res.status == "success"
        assert res.data["outcome_status"] == "done"
        assert res.data["platform"] == "steam"

        res_update = await executor.execute(
            "game.update", {"action": "update", "game_name": "Portal 2"}
        )
        assert res_update.status == "success"
        assert "Portal 2" in res_update.data["message"]

    asyncio.run(_test())
