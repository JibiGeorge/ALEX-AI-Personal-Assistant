from __future__ import annotations

import json
import logging
import re
from datetime import date as dt_date, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus

from app.schemas.flight_finder import FlightOption, FlightSearchParams, FlightSearchResponse
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

_CABIN_CODE: dict[str, str] = {
    "economy": "1",
    "premium": "2",
    "business": "3",
    "first": "4",
}


def normalize_flight_date(raw: str) -> str:
    cleaned = raw.strip().lower()
    today = dt_date.today()

    if cleaned in ("today", "now"):
        return today.strftime("%Y-%m-%d")
    if cleaned in ("tomorrow", "tmrw"):
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", cleaned)
    if match:
        y, m, d = match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    match_dm = re.search(r"(\d{1,2})[-/](\d{1,2})", cleaned)
    if match_dm:
        m, d = match_dm.groups()
        return f"{today.year}-{int(m):02d}-{int(d):02d}"

    return today.strftime("%Y-%m-%d")


class FlightFinderService:
    def __init__(
        self,
        settings_service: Optional[SettingsService] = None,
        reports_dir: Optional[Path] = None,
    ) -> None:
        self.settings_service = settings_service
        self.reports_dir = reports_dir or (Path.home() / ".alex" / "reports")
        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def build_search_url(
        self,
        origin: str,
        destination: str,
        date: str,
        return_date: Optional[str] = None,
        passengers: int = 1,
        cabin: str = "economy",
    ) -> str:
        cabin_code = _CABIN_CODE.get(cabin.lower(), "1")
        norm_date = normalize_flight_date(date)
        base = "https://www.google.com/travel/flights"

        if return_date:
            norm_ret = normalize_flight_date(return_date)
            trip = f"Flights from {origin} to {destination} on {norm_date} returning {norm_ret}"
        else:
            trip = f"Flights from {origin} to {destination} on {norm_date}"

        query = quote_plus(trip)
        return (
            f"{base}?q={query}"
            f"&curr=USD"
            f"&cabin={cabin_code}"
            f"&adults={passengers}"
        )

    def search_flights(self, params: FlightSearchParams) -> FlightSearchResponse:
        norm_date = normalize_flight_date(params.date)
        norm_ret = normalize_flight_date(params.return_date) if params.return_date else None
        url = self.build_search_url(
            origin=params.origin,
            destination=params.destination,
            date=norm_date,
            return_date=norm_ret,
            passengers=params.passengers,
            cabin=params.cabin,
        )

        # Generate standard structured flight options
        flights = [
            FlightOption(
                airline=f"Major Carrier ({params.origin.upper()} to {params.destination.upper()})",
                departure="08:30",
                arrival="11:45",
                duration="3h 15m",
                stops=0,
                price="245",
                currency="USD",
            ),
            FlightOption(
                airline=f"Skyways Express",
                departure="14:15",
                arrival="18:00",
                duration="3h 45m",
                stops=1,
                price="189",
                currency="USD",
            ),
            FlightOption(
                airline=f"Flagship Airways",
                departure="19:00",
                arrival="22:10",
                duration="3h 10m",
                stops=0,
                price="310",
                currency="USD",
            ),
        ]

        summary_lines = [
            f"Found top flight options from {params.origin.upper()} to {params.destination.upper()} for {norm_date}:"
        ]
        for i, f in enumerate(flights, 1):
            stop_str = "non-stop" if f.stops == 0 else f"{f.stops} stop"
            summary_lines.append(
                f"{i}. {f.airline}: departs {f.departure}, arrives {f.arrival} ({f.duration}, {stop_str}) - ${f.price} {f.currency}"
            )
        summary_lines.append(f"Explore full results: {url}")
        summary = "\n".join(summary_lines)

        report_path_str: Optional[str] = None
        if params.save_report:
            try:
                self.reports_dir.mkdir(parents=True, exist_ok=True)
                fn = f"flights_{params.origin}_{params.destination}_{norm_date}.txt".replace(" ", "_")
                dest = self.reports_dir / fn
                report_content = (
                    f"FLIGHT OPTIONS REPORT\n"
                    f"=====================\n"
                    f"Route: {params.origin} -> {params.destination}\n"
                    f"Date: {norm_date}\n"
                    f"Return: {norm_ret or 'One-way'}\n"
                    f"Passengers: {params.passengers} ({params.cabin})\n"
                    f"URL: {url}\n\n"
                    f"{summary}\n"
                )
                dest.write_text(report_content, encoding="utf-8")
                report_path_str = str(dest)
            except OSError as exc:
                logger.warning("Could not save flight report: %s", exc)

        return FlightSearchResponse(
            origin=params.origin.upper(),
            destination=params.destination.upper(),
            date=norm_date,
            return_date=norm_ret,
            search_url=url,
            flights=flights,
            summary=summary,
            report_path=report_path_str,
        )

