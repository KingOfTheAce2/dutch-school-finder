"""
Geocoding utilities for converting addresses to coordinates
Uses OpenStreetMap Nominatim (free, no API key required)
"""
import logging
import time
from typing import Optional, Tuple
import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DutchSchoolFinder/1.0"


def geocode_address(address: str, city: str, country: str = "Netherlands") -> Optional[Tuple[float, float]]:
    """
    Geocode an address to latitude/longitude coordinates

    Args:
        address: Street address (e.g., "Hoofdweg 123")
        city: City name (e.g., "Amsterdam")
        country: Country name (default: "Netherlands")

    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    # Build full address string
    full_address = f"{address}, {city}, {country}"

    params = {
        "q": full_address,
        "format": "json",
        "limit": 1,
        "countrycodes": "nl",  # Limit to Netherlands
    }

    headers = {
        "User-Agent": USER_AGENT
    }

    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        results = response.json()

        if results and len(results) > 0:
            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            logger.info(f"Geocoded '{full_address}' to ({lat}, {lon})")
            return (lat, lon)
        else:
            logger.warning(f"No geocoding results for '{full_address}'")
            return None

    except Exception as e:
        logger.error(f"Geocoding error for '{full_address}': {e}")
        return None


def geocode_city(city: str, country: str = "Netherlands") -> Optional[Tuple[float, float]]:
    """
    Geocode just a city name to get center coordinates

    Args:
        city: City name
        country: Country name

    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    params = {
        "city": city,
        "country": country,
        "format": "json",
        "limit": 1,
    }

    headers = {
        "User-Agent": USER_AGENT
    }

    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        results = response.json()

        if results and len(results) > 0:
            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            logger.info(f"Geocoded city '{city}' to ({lat}, {lon})")
            return (lat, lon)
        else:
            logger.warning(f"No geocoding results for city '{city}'")
            return None

    except Exception as e:
        logger.error(f"Geocoding error for city '{city}': {e}")
        return None


def batch_geocode_with_delay(addresses: list, delay: float = 1.0) -> dict:
    """
    Geocode multiple addresses with delay between requests
    (Nominatim requires max 1 request per second)

    Args:
        addresses: List of (address, city) tuples
        delay: Delay in seconds between requests

    Returns:
        Dictionary mapping address keys to (lat, lon) tuples
    """
    results = {}

    for i, (address, city) in enumerate(addresses):
        key = f"{address}, {city}"
        coords = geocode_address(address, city)

        if coords:
            results[key] = coords

        # Add delay to respect rate limits (except for last request)
        if i < len(addresses) - 1:
            time.sleep(delay)

    return results
