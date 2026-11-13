from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class FlightOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    airline: str
    departure: str
    arrival: str
    duration: str
    stops: int = 0
    price: Optional[str] = None
    currency: str = "USD"


class FlightSearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str = Field(description="Departure airport code or city name, e.g. 'JFK' or 'New York'")
    destination: str = Field(description="Arrival airport code or city name, e.g. 'LHR' or 'London'")
    date: str = Field(description="Departure date in YYYY-MM-DD or natural language format, e.g. '2026-12-15' or 'tomorrow'")
    return_date: Optional[str] = Field(default=None, description="Optional return date in YYYY-MM-DD format")
    passengers: int = Field(default=1, ge=1, le=9, description="Number of passengers")
    cabin: Literal["economy", "premium", "business", "first"] = Field(default="economy", description="Cabin class")
    save_report: bool = Field(default=False, description="Save flight options report to workspace reports directory")


class FlightSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str
    destination: str
    date: str
    return_date: Optional[str] = None
    search_url: str
    flights: list[FlightOption]
    summary: str
    report_path: Optional[str] = None

