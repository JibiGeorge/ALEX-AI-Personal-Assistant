from __future__ import annotations

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, done
from app.schemas.game_updater import GameUpdaterParams
from app.services.game_updater_service import GameUpdaterService


def register_game_updater_actions(
    registry: ActionRegistry,
    updater_service: GameUpdaterService,
) -> None:
    def game_updater_handler(params: GameUpdaterParams) -> ActionOutcomeResponse:
        res = updater_service.execute_action(params)
        return done(
            action="game.update",
            data=res.model_dump(),
            message=res.message,
        )

    registry.register(
        ActionDefinition(
            action_id="game.update",
            name="Game Launcher and Updater",
            description="Lists installed games, launches titles, triggers updates, and schedules daily updates across Steam and Epic Games.",
            category="system",
            parameters=GameUpdaterParams,
            handler=game_updater_handler,
            requires_confirmation=False,
            timeout_seconds=10.0,
        )
    )

