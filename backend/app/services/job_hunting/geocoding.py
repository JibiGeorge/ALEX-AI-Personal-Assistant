"""
Geographical Location Resolver and Coordinate Mapping for ALEX Job Hunting Module.
Provides verified coordinates for cities and regions to support the Interactive Job Location Map.
Ensures remote jobs without a physical location are explicitly marked without inventing coordinates.
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

# Comprehensive database of global tech hubs with verified latitude & longitude
CITY_COORDINATES: Dict[str, Dict[str, Any]] = {
    "san francisco": {"lat": 37.7749, "lng": -122.4194, "city": "San Francisco", "state": "CA", "country": "United States"},
    "san jose": {"lat": 37.3382, "lng": -121.8863, "city": "San Jose", "state": "CA", "country": "United States"},
    "mountain view": {"lat": 37.3861, "lng": -122.0839, "city": "Mountain View", "state": "CA", "country": "United States"},
    "palo alto": {"lat": 37.4419, "lng": -122.1430, "city": "Palo Alto", "state": "CA", "country": "United States"},
    "sunnyvale": {"lat": 37.3688, "lng": -122.0363, "city": "Sunnyvale", "state": "CA", "country": "United States"},
    "oakland": {"lat": 37.8044, "lng": -122.2712, "city": "Oakland", "state": "CA", "country": "United States"},
    "los angeles": {"lat": 34.0522, "lng": -118.2437, "city": "Los Angeles", "state": "CA", "country": "United States"},
    "san diego": {"lat": 32.7157, "lng": -117.1611, "city": "San Diego", "state": "CA", "country": "United States"},
    "seattle": {"lat": 47.6062, "lng": -122.3321, "city": "Seattle", "state": "WA", "country": "United States"},
    "bellevue": {"lat": 47.6101, "lng": -122.2015, "city": "Bellevue", "state": "WA", "country": "United States"},
    "new york": {"lat": 40.7128, "lng": -74.0060, "city": "New York", "state": "NY", "country": "United States"},
    "brooklyn": {"lat": 40.6782, "lng": -73.9442, "city": "New York", "state": "NY", "country": "United States"},
    "nyc": {"lat": 40.7128, "lng": -74.0060, "city": "New York", "state": "NY", "country": "United States"},
    "austin": {"lat": 30.2672, "lng": -97.7431, "city": "Austin", "state": "TX", "country": "United States"},
    "dallas": {"lat": 32.7767, "lng": -96.7970, "city": "Dallas", "state": "TX", "country": "United States"},
    "houston": {"lat": 29.7604, "lng": -95.3698, "city": "Houston", "state": "TX", "country": "United States"},
    "boston": {"lat": 42.3601, "lng": -71.0589, "city": "Boston", "state": "MA", "country": "United States"},
    "cambridge": {"lat": 42.3736, "lng": -71.1097, "city": "Cambridge", "state": "MA", "country": "United States"},
    "chicago": {"lat": 41.8781, "lng": -87.6298, "city": "Chicago", "state": "IL", "country": "United States"},
    "denver": {"lat": 39.7392, "lng": -104.9903, "city": "Denver", "state": "CO", "country": "United States"},
    "boulder": {"lat": 40.0150, "lng": -105.2705, "city": "Boulder", "state": "CO", "country": "United States"},
    "atlanta": {"lat": 33.7490, "lng": -84.3880, "city": "Atlanta", "state": "GA", "country": "United States"},
    "miami": {"lat": 25.7617, "lng": -80.1918, "city": "Miami", "state": "FL", "country": "United States"},
    "washington": {"lat": 38.9072, "lng": -77.0369, "city": "Washington", "state": "DC", "country": "United States"},
    "toronto": {"lat": 43.6532, "lng": -79.3832, "city": "Toronto", "state": "ON", "country": "Canada"},
    "vancouver": {"lat": 49.2827, "lng": -123.1207, "city": "Vancouver", "state": "BC", "country": "Canada"},
    "montreal": {"lat": 45.5017, "lng": -73.5673, "city": "Montreal", "state": "QC", "country": "Canada"},
    "london": {"lat": 51.5074, "lng": -0.1278, "city": "London", "state": None, "country": "United Kingdom"},
    "manchester": {"lat": 53.4808, "lng": -2.2426, "city": "Manchester", "state": None, "country": "United Kingdom"},
    "dublin": {"lat": 53.3498, "lng": -6.2603, "city": "Dublin", "state": None, "country": "Ireland"},
    "berlin": {"lat": 52.5200, "lng": 13.4050, "city": "Berlin", "state": None, "country": "Germany"},
    "munich": {"lat": 48.1351, "lng": 11.5820, "city": "Munich", "state": None, "country": "Germany"},
    "frankfurt": {"lat": 50.1109, "lng": 8.6821, "city": "Frankfurt", "state": None, "country": "Germany"},
    "amsterdam": {"lat": 52.3676, "lng": 4.9041, "city": "Amsterdam", "state": None, "country": "Netherlands"},
    "paris": {"lat": 48.8566, "lng": 2.3522, "city": "Paris", "state": None, "country": "France"},
    "zurich": {"lat": 47.3769, "lng": 8.5417, "city": "Zurich", "state": None, "country": "Switzerland"},
    "geneva": {"lat": 46.2044, "lng": 6.1432, "city": "Geneva", "state": None, "country": "Switzerland"},
    "stockholm": {"lat": 59.3293, "lng": 18.0686, "city": "Stockholm", "state": None, "country": "Sweden"},
    "copenhagen": {"lat": 55.6761, "lng": 12.5683, "city": "Copenhagen", "state": None, "country": "Denmark"},
    "madrid": {"lat": 40.4168, "lng": -3.7038, "city": "Madrid", "state": None, "country": "Spain"},
    "barcelona": {"lat": 41.3879, "lng": 2.1699, "city": "Barcelona", "state": None, "country": "Spain"},
    "warsaw": {"lat": 52.2297, "lng": 21.0122, "city": "Warsaw", "state": None, "country": "Poland"},
    "krakow": {"lat": 50.0647, "lng": 19.9450, "city": "Krakow", "state": None, "country": "Poland"},
    "bangalore": {"lat": 12.9716, "lng": 77.5946, "city": "Bangalore", "state": "KA", "country": "India"},
    "bengaluru": {"lat": 12.9716, "lng": 77.5946, "city": "Bangalore", "state": "KA", "country": "India"},
    "hyderabad": {"lat": 17.3850, "lng": 78.4867, "city": "Hyderabad", "state": "TG", "country": "India"},
    "pune": {"lat": 18.5204, "lng": 73.8567, "city": "Pune", "state": "MH", "country": "India"},
    "mumbai": {"lat": 19.0760, "lng": 72.8777, "city": "Mumbai", "state": "MH", "country": "India"},
    "delhi": {"lat": 28.6139, "lng": 77.2090, "city": "Delhi NCR", "state": "DL", "country": "India"},
    "gurgaon": {"lat": 28.4595, "lng": 77.0266, "city": "Gurgaon", "state": "HR", "country": "India"},
    "gurugram": {"lat": 28.4595, "lng": 77.0266, "city": "Gurgaon", "state": "HR", "country": "India"},
    "noida": {"lat": 28.5355, "lng": 77.3910, "city": "Noida", "state": "UP", "country": "India"},
    "chennai": {"lat": 13.0827, "lng": 80.2707, "city": "Chennai", "state": "TN", "country": "India"},
    "singapore": {"lat": 1.3521, "lng": 103.8198, "city": "Singapore", "state": None, "country": "Singapore"},
    "tokyo": {"lat": 35.6762, "lng": 139.6503, "city": "Tokyo", "state": None, "country": "Japan"},
    "sydney": {"lat": -33.8688, "lng": 151.2093, "city": "Sydney", "state": "NSW", "country": "Australia"},
    "melbourne": {"lat": -37.8136, "lng": 144.9631, "city": "Melbourne", "state": "VIC", "country": "Australia"},
    "tel aviv": {"lat": 32.0853, "lng": 34.7818, "city": "Tel Aviv", "state": None, "country": "Israel"},
    "dubai": {"lat": 25.2048, "lng": 55.2708, "city": "Dubai", "state": None, "country": "United Arab Emirates"},
    "sao paulo": {"lat": -23.5505, "lng": -46.6333, "city": "São Paulo", "state": "SP", "country": "Brazil"},
}


def resolve_location_coordinates(
    location_str: str,
    modality_str: str = "remote",
) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str], Optional[str], bool]:
    """
    Analyzes a raw location string and modality to extract verifiable geographical coordinates.
    
    Returns:
        (latitude, longitude, city, state, country, is_remote)
    
    Strict Rule: If the location is purely remote or lacks a verifiable physical hub,
    returns latitude=None, longitude=None rather than fabricating coordinates.
    """
    raw = (location_str or "").strip()
    norm = raw.lower()
    mod = (modality_str or "").lower()

    is_purely_remote = False
    if "remote" in norm or "anywhere" in norm or "worldwide" in norm or "global" in norm:
        # Check if it also mentions a specific city (e.g., "Remote - San Francisco, CA" or "Hybrid - London")
        has_city = False
        for city_key in CITY_COORDINATES:
            if re.search(r"\b" + re.escape(city_key) + r"\b", norm):
                has_city = True
                break
        if not has_city:
            is_purely_remote = True
    elif not norm:
        is_purely_remote = True

    if is_purely_remote and "onsite" not in mod and "hybrid" not in mod:
        return None, None, None, None, None, True

    # Check for city matches
    for city_key, data in CITY_COORDINATES.items():
        if re.search(r"\b" + re.escape(city_key) + r"\b", norm):
            return (
                data["lat"],
                data["lng"],
                data["city"],
                data["state"],
                data["country"],
                "remote" in mod or "remote" in norm,
            )

    # Country level fallback with primary capital/hub coordinates if specifically identified
    if "ireland" in norm:
        return 53.3498, -6.2603, "Dublin", None, "Ireland", "remote" in mod or "remote" in norm
    if "germany" in norm:
        return 52.5200, 13.4050, "Berlin", None, "Germany", "remote" in mod or "remote" in norm
    if "united kingdom" in norm or "uk" in norm:
        return 51.5074, -0.1278, "London", None, "United Kingdom", "remote" in mod or "remote" in norm
    if "canada" in norm:
        return 43.6532, -79.3832, "Toronto", "ON", "Canada", "remote" in mod or "remote" in norm
    if "india" in norm:
        return 12.9716, 77.5946, "Bangalore", "KA", "India", "remote" in mod or "remote" in norm

    return None, None, None, None, None, "remote" in mod or "remote" in norm

