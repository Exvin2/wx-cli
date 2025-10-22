"""Marine weather data from NOAA buoys."""

from __future__ import annotations

from typing import Any

import httpx

from .fetchers import DEFAULT_TIMEOUT, USER_AGENT, _create_client, _safe_float


def get_nearby_buoys(
    lat: float, lon: float, *, radius_nm: int = 100, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> list[dict[str, Any]]:
    """Find NOAA buoys within radius of a location.

    Args:
        lat: Latitude
        lon: Longitude
        radius_nm: Search radius in nautical miles
        offline: Skip network requests
        timeout: Request timeout in seconds

    Returns:
        List of buoy metadata dictionaries
    """
    if offline:
        return []

    # NOAA's National Data Buoy Center stations
    url = "https://www.ndbc.noaa.gov/activestations.xml"

    try:
        with _create_client(timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            # Parse XML for nearby stations
            # For now, return empty - full implementation needs XML parsing
            return []
    except (httpx.HTTPError, ValueError):
        return []


def get_buoy_observations(
    station_id: str, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    """Get latest observations from a NOAA buoy.

    Args:
        station_id: NOAA station ID (e.g., '46042')
        offline: Skip network requests
        timeout: Request timeout in seconds

    Returns:
        Dictionary with buoy observations or None
    """
    if offline:
        return None

    # Latest observation in real-time
    url = f"https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"

    try:
        with _create_client(timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.text

            # Parse the text format (space-separated values)
            lines = data.strip().split("\n")
            if len(lines) < 3:
                return None

            # Header line 1: field names
            # Header line 2: units
            # Data lines: actual observations
            headers = lines[0].split()
            units = lines[1].split()
            latest = lines[2].split()

            if len(latest) < len(headers):
                return None

            observation = {"station_id": station_id}

            # Map common fields
            field_map = {
                "WDIR": "wind_direction_deg",
                "WSPD": "wind_speed_mps",
                "GST": "gust_speed_mps",
                "WVHT": "wave_height_m",
                "DPD": "dominant_wave_period_s",
                "APD": "average_wave_period_s",
                "MWD": "wave_direction_deg",
                "PRES": "pressure_hpa",
                "ATMP": "air_temp_c",
                "WTMP": "water_temp_c",
                "DEWP": "dewpoint_c",
                "VIS": "visibility_nm",
                "TIDE": "tide_ft",
            }

            for i, header in enumerate(headers):
                if header in field_map and i < len(latest):
                    value = latest[i]
                    # Convert 'MM' (missing) to None
                    if value == "MM":
                        observation[field_map[header]] = None
                    else:
                        observation[field_map[header]] = _safe_float(value)

            return observation

    except (httpx.HTTPError, ValueError):
        return None


def get_marine_forecast(
    lat: float, lon: float, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    """Get NOAA marine forecast for a location.

    Args:
        lat: Latitude
        lon: Longitude
        offline: Skip network requests
        timeout: Request timeout in seconds

    Returns:
        Dictionary with marine forecast or None
    """
    if offline:
        return None

    # Get marine forecast from NWS
    url = f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}"

    try:
        with _create_client(timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()

            forecast_marine_url = data.get("properties", {}).get("forecastGridData")
            if not forecast_marine_url:
                return None

            # Get the gridded forecast
            forecast_response = client.get(forecast_marine_url)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()

            properties = forecast_data.get("properties", {})

            return {
                "wave_height": properties.get("waveHeight"),
                "wave_period": properties.get("wavePeriod"),
                "wave_direction": properties.get("waveDirection"),
                "wind_wave_height": properties.get("windWaveHeight"),
                "swell_height": properties.get("swellHeight"),
                "swell_period": properties.get("swellPeriod"),
                "swell_direction": properties.get("swellDirection"),
                "water_temperature": properties.get("waterTemperature"),
            }

    except (httpx.HTTPError, ValueError, KeyError):
        return None
