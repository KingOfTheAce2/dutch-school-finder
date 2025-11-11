"""
Transportation service for calculating routes and travel times
Integrates with NS API, 9292 API, and Google Maps
"""
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp
import asyncio
from .distance import haversine_distance

logger = logging.getLogger(__name__)

# API Configuration
NS_API_KEY = os.getenv("NS_API_KEY", "")  # Dutch Railways API
NINETY_TWO_API_KEY = os.getenv("9292_API_KEY", "")  # 9292 Public Transit API
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")  # Google Maps API


class TransportationService:
    """Service for calculating transportation routes and times"""

    @staticmethod
    def calculate_walking_time(distance_km: float) -> Dict[str, any]:
        """
        Calculate walking time and details
        Average walking speed: 5 km/h
        """
        if distance_km <= 0:
            return None

        duration_minutes = int((distance_km / 5.0) * 60)

        return {
            "mode": "walking",
            "distance_km": round(distance_km, 2),
            "duration_minutes": duration_minutes,
            "icon": "🚶",
            "display": f"🚶 {duration_minutes} min walk"
        }

    @staticmethod
    def calculate_cycling_time(distance_km: float) -> Dict[str, any]:
        """
        Calculate cycling time and details
        Average cycling speed in NL: 15 km/h (Dutch cycling is fast!)
        """
        if distance_km <= 0:
            return None

        duration_minutes = int((distance_km / 15.0) * 60)

        return {
            "mode": "cycling",
            "distance_km": round(distance_km, 2),
            "duration_minutes": duration_minutes,
            "icon": "🚴",
            "display": f"🚴 {duration_minutes} min by bike"
        }

    @staticmethod
    def calculate_driving_time(distance_km: float) -> Dict[str, any]:
        """
        Calculate driving time and details
        Average urban speed: 30 km/h (accounting for traffic)
        """
        if distance_km <= 0:
            return None

        duration_minutes = int((distance_km / 30.0) * 60)

        return {
            "mode": "driving",
            "distance_km": round(distance_km, 2),
            "duration_minutes": duration_minutes,
            "icon": "🚗",
            "display": f"🚗 {duration_minutes} min drive"
        }

    @staticmethod
    async def calculate_public_transit_route(
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        departure_time: Optional[datetime] = None
    ) -> Optional[Dict[str, any]]:
        """
        Calculate public transit route using 9292 API or fallback estimation

        In production, this would integrate with:
        - 9292 API for complete public transit routing
        - NS API for train-specific routes

        For now, provides intelligent estimation based on distance
        """
        distance_km = haversine_distance(from_lat, from_lon, to_lat, to_lon)

        if distance_km <= 0:
            return None

        # If APIs are not configured, use intelligent estimation
        if not NINETY_TWO_API_KEY and not NS_API_KEY:
            return TransportationService._estimate_public_transit(distance_km)

        # TODO: Implement actual API calls when keys are available
        try:
            # This is where we would call the 9292 or NS API
            # For now, fall back to estimation
            return TransportationService._estimate_public_transit(distance_km)
        except Exception as e:
            logger.warning(f"Public transit API call failed: {e}, using estimation")
            return TransportationService._estimate_public_transit(distance_km)

    @staticmethod
    def _estimate_public_transit(distance_km: float) -> Dict[str, any]:
        """
        Estimate public transit time based on distance

        Assumptions for Dutch public transit:
        - < 2 km: Walk, no transit worth it
        - 2-5 km: Bus/tram (average 20 km/h with stops + 5 min wait)
        - 5-15 km: Bus/metro (average 25 km/h + 8 min wait)
        - > 15 km: Train involved (average 40 km/h + 10 min wait)
        """
        if distance_km < 2:
            return None  # Walking is better

        if distance_km < 5:
            # Bus or tram
            travel_time = int((distance_km / 20.0) * 60)
            wait_time = 5
            total_time = travel_time + wait_time

            return {
                "mode": "public_transit",
                "distance_km": round(distance_km, 2),
                "duration_minutes": total_time,
                "icon": "🚌",
                "transit_type": "bus_tram",
                "display": f"🚌 {total_time} min (bus/tram)",
                "details": {
                    "lines": ["Estimated route"],
                    "transfers": 0,
                    "wait_time_minutes": wait_time
                }
            }

        elif distance_km < 15:
            # Bus/metro system
            travel_time = int((distance_km / 25.0) * 60)
            wait_time = 8
            total_time = travel_time + wait_time

            return {
                "mode": "public_transit",
                "distance_km": round(distance_km, 2),
                "duration_minutes": total_time,
                "icon": "🚇",
                "transit_type": "bus_metro",
                "display": f"🚇 {total_time} min (metro/bus)",
                "details": {
                    "lines": ["Metro or bus line"],
                    "transfers": 1,
                    "wait_time_minutes": wait_time
                }
            }

        else:
            # Train involved
            travel_time = int((distance_km / 40.0) * 60)
            wait_time = 10
            total_time = travel_time + wait_time

            return {
                "mode": "public_transit",
                "distance_km": round(distance_km, 2),
                "duration_minutes": total_time,
                "icon": "🚂",
                "transit_type": "train",
                "display": f"🚂 {total_time} min (train + bus)",
                "details": {
                    "lines": ["NS Train line + local transport"],
                    "transfers": 1,
                    "wait_time_minutes": wait_time
                }
            }

    @staticmethod
    async def calculate_all_routes(
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        include_school_bus: bool = False,
        school_bus_info: Optional[Dict] = None
    ) -> List[Dict[str, any]]:
        """
        Calculate all transportation routes

        Returns a list of all available transportation options sorted by duration
        """
        distance_km = haversine_distance(from_lat, from_lon, to_lat, to_lon)

        routes = []

        # Walking
        walking = TransportationService.calculate_walking_time(distance_km)
        if walking and walking["duration_minutes"] <= 45:  # Only show if < 45 min walk
            routes.append(walking)

        # Cycling (very common in NL!)
        cycling = TransportationService.calculate_cycling_time(distance_km)
        if cycling and cycling["duration_minutes"] <= 60:  # Only show if < 1 hour
            routes.append(cycling)

        # Public transit
        public_transit = await TransportationService.calculate_public_transit_route(
            from_lat, from_lon, to_lat, to_lon
        )
        if public_transit:
            routes.append(public_transit)

        # Driving
        driving = TransportationService.calculate_driving_time(distance_km)
        if driving:
            routes.append(driving)

        # School bus
        if include_school_bus and school_bus_info:
            routes.append({
                "mode": "school_bus",
                "icon": "🚌",
                "display": f"🚌 School bus available",
                "bus_route_name": school_bus_info.get("route_name"),
                "bus_pickup_time": school_bus_info.get("pickup_time"),
                "bus_pickup_location": school_bus_info.get("pickup_location"),
                "details": school_bus_info
            })

        # Sort by duration (except school bus)
        regular_routes = [r for r in routes if r["mode"] != "school_bus"]
        school_bus_routes = [r for r in routes if r["mode"] == "school_bus"]

        regular_routes.sort(key=lambda x: x.get("duration_minutes", float("inf")))

        return regular_routes + school_bus_routes

    @staticmethod
    def format_route_display(routes: List[Dict[str, any]]) -> str:
        """
        Format routes for display in UI

        Example:
        🚶 12 min walk
        🚴 6 min by bike
        🚌 2 buses, 18 min total (Line 22 → Line 5)
        🚗 8 min drive
        🚌 School bus available (Route B, pickup 8:15 AM)
        """
        if not routes:
            return "Transportation information not available"

        display_lines = []
        for route in routes:
            display_lines.append(route["display"])

        return "\n".join(display_lines)

    @staticmethod
    async def get_ns_train_info(from_station: str, to_station: str) -> Optional[Dict]:
        """
        Get train information from NS API

        Requires NS API key for production use
        """
        if not NS_API_KEY:
            logger.info("NS API key not configured")
            return None

        # TODO: Implement NS API integration
        # This would call the NS API to get real train schedules
        return None

    @staticmethod
    def calculate_morning_commute_time(
        base_duration_minutes: int,
        departure_time: Optional[datetime] = None
    ) -> int:
        """
        Adjust travel time based on morning commute traffic

        Morning rush hour in NL: 7:30-9:00 AM
        Adds 20-30% to travel time during rush hour
        """
        if not departure_time:
            departure_time = datetime.now().replace(hour=8, minute=0)

        hour = departure_time.hour

        # Morning rush hour
        if 7 <= hour <= 9:
            return int(base_duration_minutes * 1.25)
        # Slightly busy
        elif 6 <= hour <= 10:
            return int(base_duration_minutes * 1.15)
        # Normal time
        else:
            return base_duration_minutes


# Example usage and API endpoint helpers
async def get_transportation_for_school(
    school_lat: float,
    school_lon: float,
    from_address_lat: float,
    from_address_lon: float,
    include_school_bus: bool = False,
    school_bus_info: Optional[Dict] = None
) -> List[Dict[str, any]]:
    """
    Main function to get all transportation options for a school
    """
    service = TransportationService()

    routes = await service.calculate_all_routes(
        from_address_lat,
        from_address_lon,
        school_lat,
        school_lon,
        include_school_bus=include_school_bus,
        school_bus_info=school_bus_info
    )

    # Add morning commute adjustment
    for route in routes:
        if "duration_minutes" in route and route["mode"] != "school_bus":
            morning_time = service.calculate_morning_commute_time(
                route["duration_minutes"]
            )
            route["morning_commute_minutes"] = morning_time
            if morning_time != route["duration_minutes"]:
                route["display"] += f" (morning: {morning_time} min)"

    return routes
