"""Aviation weather data (METAR/TAF)."""

from __future__ import annotations

from typing import Any

import httpx

from .fetchers import DEFAULT_TIMEOUT, USER_AGENT, _create_client


def get_metar(
    station_id: str, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    """Get METAR (aviation weather observation) for a station.

    Args:
        station_id: ICAO station code (e.g., 'KDEN' for Denver)
        offline: Skip network requests
        timeout: Request timeout in seconds

    Returns:
        Dictionary with METAR data or None

    Raises:
        ValueError: If station ID is invalid
    """
    from .security import validate_icao_station, ValidationError

    # SECURITY: Validate ICAO station ID before URL construction
    try:
        station_id = validate_icao_station(station_id)
    except ValidationError as e:
        raise ValueError(str(e)) from e

    if offline:
        return None

    # NOAA Aviation Weather Center (using validated station ID)
    url = f"https://aviationweather.gov/cgi-bin/data/metar.php?ids={station_id}&format=json"

    try:
        with _create_client(timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            # Return the first METAR
            metar = data[0] if isinstance(data, list) else data

            return {
                "station_id": metar.get("icaoId"),
                "observation_time": metar.get("obsTime"),
                "raw_text": metar.get("rawOb"),
                "temp_c": metar.get("temp"),
                "dewpoint_c": metar.get("dewp"),
                "wind_dir_deg": metar.get("wdir"),
                "wind_speed_kt": metar.get("wspd"),
                "wind_gust_kt": metar.get("wgst"),
                "visibility_mi": metar.get("visib"),
                "altimeter_inhg": metar.get("altim"),
                "sea_level_pressure_mb": metar.get("slp"),
                "flight_category": metar.get("fltcat"),
                "sky_conditions": metar.get("cover"),
                "weather_conditions": metar.get("wx"),
                "clouds": metar.get("clouds"),
            }

    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        return None


def get_taf(
    station_id: str, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    """Get TAF (aviation forecast) for a station.

    Args:
        station_id: ICAO station code (e.g., 'KDEN' for Denver)
        offline: Skip network requests
        timeout: Request timeout in seconds

    Returns:
        Dictionary with TAF data or None

    Raises:
        ValueError: If station ID is invalid
    """
    from .security import validate_icao_station, ValidationError

    # SECURITY: Validate ICAO station ID before URL construction
    try:
        station_id = validate_icao_station(station_id)
    except ValidationError as e:
        raise ValueError(str(e)) from e

    if offline:
        return None

    # NOAA Aviation Weather Center (using validated station ID)
    url = f"https://aviationweather.gov/cgi-bin/data/taf.php?ids={station_id}&format=json"

    try:
        with _create_client(timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            # Return the first TAF
            taf = data[0] if isinstance(data, list) else data

            return {
                "station_id": taf.get("icaoId"),
                "issue_time": taf.get("issueTime"),
                "bulletin_time": taf.get("bulletinTime"),
                "valid_time_from": taf.get("validTimeFrom"),
                "valid_time_to": taf.get("validTimeTo"),
                "raw_text": taf.get("rawTAF"),
                "forecasts": taf.get("forecast", []),
            }

    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        return None


def find_nearest_airport(
    lat: float, lon: float, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> str | None:
    """Find the nearest airport station ID for aviation weather.

    Args:
        lat: Latitude
        lon: Longitude
        offline: Skip network requests
        timeout: Request timeout in seconds

    Returns:
        ICAO station code or None
    """
    if offline:
        return None

    # Use NWS to find nearest point, which includes grid info
    url = f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}"

    try:
        with _create_client(timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()

            # Try to get radar station (often co-located with airports)
            radar = data.get("properties", {}).get("radarStation")
            if radar:
                return radar

            # Fallback: try to derive from CWA or gridId
            grid_id = data.get("properties", {}).get("gridId")
            if grid_id:
                # Common mapping of grid offices to airports
                grid_to_icao = {
                    "BOU": "KDEN",  # Boulder -> Denver
                    "DEN": "KDEN",  # Denver
                    "SEW": "KSEA",  # Seattle
                    "LOT": "KORD",  # Chicago
                    "OKX": "KJFK",  # New York
                    "MIA": "KMIA",  # Miami
                    # Add more mappings as needed
                }
                return grid_to_icao.get(grid_id)

            return None

    except (httpx.HTTPError, ValueError, KeyError):
        return None
