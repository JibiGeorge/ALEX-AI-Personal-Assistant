from __future__ import annotations

import asyncio
from pathlib import Path
import pytest

from app.actions.action_executor import ActionExecutor
from app.actions.action_registry import ActionRegistry
from app.actions.builtins.flight_finder import register_flight_actions
from app.schemas.flight_finder import FlightSearchParams
from app.services.flight_finder_service import FlightFinderService, normalize_flight_date


def test_normalize_flight_date():
    assert len(normalize_flight_date("today")) == 10
    assert len(normalize_flight_date("tomorrow")) == 10
    assert normalize_flight_date("2026-12-25") == "2026-12-25"
    assert normalize_flight_date("2026/05/10") == "2026-05-10"


def test_build_search_url():
    service = FlightFinderService()
    url = service.build_search_url(
        origin="JFK",
        destination="LHR",
        date="2026-12-01",
        return_date="2026-12-10",
        passengers=2,
        cabin="business",
    )
    assert "https://www.google.com/travel/flights" in url
    assert "cabin=3" in url
    assert "adults=2" in url
    assert "JFK" in url
    assert "LHR" in url


def test_search_flights_and_save_report(tmp_path):
    reports_dir = tmp_path / "reports"
    service = FlightFinderService(reports_dir=reports_dir)

    params = FlightSearchParams(
        origin="SFO",
        destination="HND",
        date="2026-11-20",
        passengers=1,
        cabin="economy",
        save_report=True,
    )
    response = service.search_flights(params)

    assert response.origin == "SFO"
    assert response.destination == "HND"
    assert len(response.flights) >= 3
    assert "Found top flight options" in response.summary
    assert response.report_path is not None
    assert Path(response.report_path).exists()
    assert "FLIGHT OPTIONS REPORT" in Path(response.report_path).read_text(encoding="utf-8")


def test_action_travel_flights(tmp_path):
    registry = ActionRegistry()
    service = FlightFinderService(reports_dir=tmp_path / "reports")
    register_flight_actions(registry, service)

    executor = ActionExecutor(registry)

    async def _test():
        res = await executor.execute(
            "travel.flights",
            {
                "origin": "LAX",
                "destination": "JFK",
                "date": "2026-12-15",
            },
        )
        assert res.status == "success"
        assert res.data["outcome_status"] == "done"
        assert res.data["origin"] == "LAX"
        assert res.data["destination"] == "JFK"
        assert len(res.data["flights"]) > 0

    asyncio.run(_test())

