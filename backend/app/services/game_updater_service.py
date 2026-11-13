from __future__ import annotations

import logging
import os
import platform
import re
from pathlib import Path
from typing import Optional

from app.schemas.game_updater import GameItem, GameUpdaterParams, GameUpdaterResponse

logger = logging.getLogger(__name__)


class GameUpdaterService:
    def __init__(self, steam_path: Optional[Path] = None) -> None:
        self.steam_path = steam_path or self._detect_steam_path()
        self._scheduled_time: Optional[str] = None

    def _detect_steam_path(self) -> Optional[Path]:
        system = platform.system().lower()
        candidates: list[Path] = []

        if "windows" in system:
            candidates.extend([
                Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Steam",
                Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Steam",
            ])
        elif "darwin" in system:
            candidates.append(Path.home() / "Library" / "Application Support" / "Steam")
        else:
            candidates.extend([
                Path.home() / ".steam" / "steam",
                Path.home() / ".local" / "share" / "Steam",
            ])

        for c in candidates:
            if c.exists() and c.is_dir():
                return c
        return None

    def list_steam_games(self) -> list[GameItem]:
        if not self.steam_path or not self.steam_path.exists():
            return []

        steamapps = self.steam_path / "steamapps"
        if not steamapps.exists():
            return []

        games: list[GameItem] = []
        try:
            for acf in steamapps.glob("appmanifest_*.acf"):
                content = acf.read_text(encoding="utf-8", errors="ignore")
                name_match = re.search(r'"name"\s+"([^"]+)"', content)
                appid_match = re.search(r'"appid"\s+"([^"]+)"', content)
                installdir_match = re.search(r'"installdir"\s+"([^"]+)"', content)

                if name_match and appid_match:
                    name = name_match.group(1).strip()
                    app_id = appid_match.group(1).strip()
                    # Skip Steamworks Common Redistributables or Proton internal runtimes
                    if "Steamworks" in name or "Proton" in name:
                        continue
                    games.append(
                        GameItem(
                            name=name,
                            app_id=app_id,
                            platform="steam",
                            install_dir=installdir_match.group(1) if installdir_match else None,
                            status="installed",
                        )
                    )
        except OSError as exc:
            logger.warning("Error reading Steam library manifests: %s", exc)

        return games

    def execute_action(self, params: GameUpdaterParams) -> GameUpdaterResponse:
        action = params.action.lower()

        if action == "schedule":
            time_str = f"{params.hour:02d}:{params.minute:02d}"
            self._scheduled_time = time_str
            return GameUpdaterResponse(
                action="schedule",
                platform=params.platform,
                games=[],
                message=f"Game updates scheduled daily at {time_str}",
                scheduled_time=time_str,
            )

        if action == "cancel_schedule":
            self._scheduled_time = None
            return GameUpdaterResponse(
                action="cancel_schedule",
                platform=params.platform,
                games=[],
                message="Scheduled game update cancelled",
            )

        if action == "status":
            return GameUpdaterResponse(
                action="status",
                platform=params.platform,
                games=[],
                message=f"Game updater active. Scheduled time: {self._scheduled_time or 'None'}",
                scheduled_time=self._scheduled_time,
            )

        games: list[GameItem] = []
        if params.platform in ("steam", "both"):
            games.extend(self.list_steam_games())

        if action == "list":
            msg = (
                f"Found {len(games)} installed games across {params.platform}."
                if games
                else f"No installed games detected for {params.platform}."
            )
            return GameUpdaterResponse(
                action="list",
                platform=params.platform,
                games=games,
                message=msg,
                scheduled_time=self._scheduled_time,
            )

        if action in ("update", "launch"):
            target_name = params.game_name or "all games"
            msg = f"{action.capitalize()} requested for {target_name} ({len(games)} games cataloged)."
            return GameUpdaterResponse(
                action=action,
                platform=params.platform,
                games=games,
                message=msg,
                scheduled_time=self._scheduled_time,
            )

        return GameUpdaterResponse(
            action=action,
            platform=params.platform,
            games=games,
            message="Unknown action",
        )

