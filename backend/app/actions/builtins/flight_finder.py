from __future__ import annotations

from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import ActionOutcomeResponse, done
from app.schemas.flight_finder import FlightSearchParams
from app.services.flight_finder_service import FlightFinderService


def register_flight_actions(
    registry: ActionRegistry,
    flight_service: FlightFinderService,
) -> None:
    def search_flights_handler(params: FlightSearchParams) -> ActionOutcomeResponse:
        result = flight_service.search_flights(params)
        return done(
            action="travel.flights",
            data=result.model_dump(),
            message=f"Found {len(result.flights)} flight options from {result.origin} to {result.destination}",
        )

    registry.register(
        ActionDefinition(
            action_id="travel.flights",
            name="Search Flights",
            description="Searches flights between origin and destination with dates, cabin class, pricing, and deep link URL.",
            category="travel",
            parameters=FlightSearchParams,
            handler=search_flights_handler,
            requires_confirmation=False,
            timeout_seconds=10.0,
        )
    )

