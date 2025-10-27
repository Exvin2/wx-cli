"""Lightweight data fetchers for wx Feature Packs."""

from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_TIMEOUT = 3.0
USER_AGENT = "wx-cli/0.1 (+https://github.com/Exvin2/claudex-cli)"


@dataclass(slots=True)
class Observation:
    """Represents a weather observation at a point."""

    lat: float
    lon: float
    temp: float | None = None
    feels_like: float | None = None
    wind: float | None = None
    gust: float | None = None
    precip_prob: float | None = None
    cloud_cover: float | None = None


@dataclass(slots=True)
class Alert:
    """Represents a weather alert."""

    event: str
    severity: str
    areas: list[str]
    expires_iso: str | None = None


@dataclass(slots=True)
class FetchResult:
    """Capture metadata for debugging fetch operations."""

    name: str
    elapsed: float
    succeeded: bool
    detail: str | None = None


def _create_client(timeout: float) -> httpx.Client:
    return httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})


def _safe_request(
    method: str, url: str, *, params: dict[str, Any] | None = None, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    try:
        with _create_client(timeout) as client:
            response = client.request(method, url, params=params)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError):
        return None


def _parse_latlon(value: str) -> tuple[float, float] | None:
    if "," not in value:
        return None
    left, right = value.split(",", maxsplit=1)
    try:
        return float(left.strip()), float(right.strip())
    except ValueError:
        return None


def get_point_context(
    place_or_latlon: str, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    """Resolve a place name or coordinate string into lat/lon metadata."""

    if offline:
        return None

    coordinate = _parse_latlon(place_or_latlon)
    if coordinate:
        lat, lon = coordinate
        tz_url = "https://api.open-meteo.com/v1/timezone"
        tz_data = _safe_request(
            "GET", tz_url, params={"latitude": lat, "longitude": lon}, timeout=timeout
        )
        tz_name = tz_data.get("timezone") if tz_data else None
        return {
            "input": place_or_latlon,
            "resolved": place_or_latlon,
            "lat": lat,
            "lon": lon,
            "tz": tz_name,
        }

    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    payload = _safe_request(
        "GET",
        geo_url,
        params={"name": place_or_latlon, "count": 1, "language": "en"},
        timeout=timeout,
    )
    if not payload or not payload.get("results"):
        return None

    result = payload["results"][0]
    tz_name = result.get("timezone")
    lat = result.get("latitude")
    lon = result.get("longitude")
    if lat is None or lon is None:
        return None

    return {
        "input": place_or_latlon,
        "resolved": result.get("name") or place_or_latlon,
        "lat": float(lat),
        "lon": float(lon),
        "tz": tz_name,
    }


def get_quick_obs(
    lat: float, lon: float, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    """Return a minimal snapshot of current conditions."""

    if offline:
        return None

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,wind_speed_10m,wind_gusts_10m,precipitation,visibility,cloud_base",  # noqa: E501
        "timezone": "UTC",
    }
    payload = _safe_request("GET", url, params=params, timeout=timeout)
    if not payload:
        return None

    current = payload.get("current") or {}
    return {
        "temp": _safe_float(current.get("temperature_2m")),
        "feels_like": _safe_float(current.get("apparent_temperature")),
        "wind": _safe_float(current.get("wind_speed_10m")),
        "gust": _safe_float(current.get("wind_gusts_10m")),
        "precip_last_hr": _safe_float(current.get("precipitation")),
        "vis_km": _safe_float(current.get("visibility")),
        "ceiling_m": _safe_float(current.get("cloud_base")),
    }


def get_quick_alerts(
    lat: float, lon: float, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> list[dict[str, Any]]:
    """Fetch active alert headlines for a point."""

    if offline:
        return []

    url = "https://api.weather.gov/alerts/active"
    params = {"point": f"{lat:.3f},{lon:.3f}"}
    try:
        with _create_client(timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return []

    features = data.get("features", [])
    alerts: list[dict[str, Any]] = []
    for feature in features[:5]:
        props = feature.get("properties", {})
        alerts.append(
            {
                "event": props.get("event"),
                "severity": props.get("severity"),
                "expires_iso": props.get("ends"),
            }
        )
    return alerts


def get_quick_profile(
    lat: float, lon: float, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    """Fetch a minimal instability/wind profile snapshot."""

    if offline:
        return None

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "convective_available_potential_energy,convective_inhibition,wind_speed_700hPa,wind_speed_500hPa,precipitable_water,cloud_base",  # noqa: E501
        "forecast_days": 1,
        "timezone": "UTC",
    }
    payload = _safe_request("GET", url, params=params, timeout=timeout)
    if not payload:
        return None

    hourly = payload.get("hourly") or {}
    cape = _first_value(hourly.get("convective_available_potential_energy"))
    cin = _first_value(hourly.get("convective_inhibition"))
    shear = None
    winds_700 = _first_value(hourly.get("wind_speed_700hPa"))
    winds_500 = _first_value(hourly.get("wind_speed_500hPa"))
    if winds_700 is not None and winds_500 is not None:
        shear = round(abs(float(winds_500) - float(winds_700)) * 1.94384)  # m/s -> kt

    return {
        "cape_jkg": _safe_int(cape),
        "cin_jkg": _safe_int(cin),
        "shear06_kt": _safe_int(shear),
        "pwat_in": _safe_float(_first_value(hourly.get("precipitable_water"))),
        "lcl_m": _safe_int(_first_value(hourly.get("cloud_base"))),
        "lapse_700_500_cpkm": None,
    }


def _first_value(values: list[Any] | None) -> Any:
    if not values:
        return None
    return values[0]


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def fetch_openmeteo_points(
    points: list[tuple[float, float]], *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> list[Observation]:
    """Fetch current conditions for multiple points using Open-Meteo."""
    if offline or not points:
        return []

    observations: list[Observation] = []

    def fetch_point(lat: float, lon: float) -> Observation | None:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,wind_speed_10m,wind_gusts_10m,cloud_cover",
            "hourly": "precipitation_probability",
            "forecast_hours": 6,
            "timezone": "UTC",
        }
        try:
            with _create_client(timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                current = data.get("current", {})
                hourly = data.get("hourly", {})
                precip_probs = hourly.get("precipitation_probability", [])
                max_precip = max((_safe_float(p) for p in precip_probs if p is not None), default=None)

                return Observation(
                    lat=lat,
                    lon=lon,
                    temp=_safe_float(current.get("temperature_2m")),
                    feels_like=_safe_float(current.get("apparent_temperature")),
                    wind=_safe_float(current.get("wind_speed_10m")),
                    gust=_safe_float(current.get("wind_gusts_10m")),
                    precip_prob=max_precip,
                    cloud_cover=_safe_float(current.get("cloud_cover")),
                )
        except (httpx.HTTPError, ValueError, KeyError):
            return None

    # Fetch in parallel with thread pool
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_point, lat, lon): (lat, lon) for lat, lon in points}
        for future in as_completed(futures):
            result = future.result()
            if result:
                observations.append(result)

    return observations


def fetch_us_alerts(
    *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT, severe_only: bool = False
) -> list[Alert]:
    """Fetch nationwide US alerts from NWS CAP feed."""
    if offline:
        return []

    url = "https://api.weather.gov/alerts/active"
    try:
        with _create_client(timeout) as client:
            response = client.get(url, params={"status": "actual"})
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return []

    features = data.get("features", [])
    alerts: list[Alert] = []

    for feature in features:
        props = feature.get("properties", {})
        event = props.get("event")
        severity = props.get("severity", "Unknown")
        areas_data = props.get("areaDesc", "")
        areas = [a.strip() for a in areas_data.split(";") if a.strip()][:3]  # Limit to 3 areas
        expires = props.get("ends")

        if event:
            # Filter for severe weather if requested
            if severe_only and not _is_severe_weather(event):
                continue
            alerts.append(Alert(event=event, severity=severity, areas=areas, expires_iso=expires))

    return alerts


def _is_severe_weather(event: str) -> bool:
    """Check if an alert is severe weather (flood, tornado, severe thunderstorm)."""
    from .config import SEVERE_WEATHER_KEYWORDS

    event_lower = event.lower()
    return any(keyword in event_lower for keyword in SEVERE_WEATHER_KEYWORDS)


def fetch_eu_alerts(
    *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT, severe_only: bool = False
) -> list[Alert]:
    """Fetch Europe-wide alerts from MeteoAlarm CAP feed."""
    if offline:
        return []

    import xml.etree.ElementTree as ET

    # MeteoAlarm consolidated feed
    url = "https://meteoalarm.org/documents/rss/wflag-rss-all.xml"

    try:
        with _create_client(timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            xml_content = response.text
    except (httpx.HTTPError, ValueError):
        return []

    # Parse XML
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return []

    alerts: list[Alert] = []

    # Look for CAP alert elements (namespace might vary)
    # Common namespaces for CAP feeds
    namespaces = {
        "cap": "urn:oasis:names:tc:emergency:cap:1.2",
        "atom": "http://www.w3.org/2005/Atom",
    }

    # Try to parse as RSS first
    for item in root.findall(".//item"):
        try:
            title = item.find("title")
            description = item.find("description")
            pubdate = item.find("pubDate")

            if title is not None and title.text:
                event_text = title.text.strip()

                # Extract severity from description if available
                severity = "Unknown"
                if description is not None and description.text:
                    desc_lower = description.text.lower()
                    if "extreme" in desc_lower:
                        severity = "Extreme"
                    elif "severe" in desc_lower:
                        severity = "Severe"
                    elif "moderate" in desc_lower:
                        severity = "Moderate"
                    elif "minor" in desc_lower:
                        severity = "Minor"

                # Extract area from title (usually format: "AlertType - Area")
                areas = []
                if " - " in event_text:
                    parts = event_text.split(" - ")
                    if len(parts) > 1:
                        areas = [parts[1].strip()]
                    event_text = parts[0].strip()

                # Filter for severe weather if requested
                if severe_only and not _is_severe_weather(event_text):
                    continue

                alerts.append(
                    Alert(
                        event=event_text,
                        severity=severity,
                        areas=areas if areas else ["Europe"],
                        expires_iso=pubdate.text if pubdate is not None else None,
                    )
                )
        except (AttributeError, ValueError):
            continue

    # Try CAP format as fallback
    if not alerts:
        for alert_elem in root.findall(".//cap:alert", namespaces):
            try:
                info = alert_elem.find("cap:info", namespaces)
                if info is None:
                    continue

                event_elem = info.find("cap:event", namespaces)
                severity_elem = info.find("cap:severity", namespaces)
                expires_elem = info.find("cap:expires", namespaces)

                if event_elem is None or not event_elem.text:
                    continue

                event_text = event_elem.text.strip()

                # Extract areas
                areas = []
                for area_elem in info.findall("cap:area", namespaces):
                    area_desc = area_elem.find("cap:areaDesc", namespaces)
                    if area_desc is not None and area_desc.text:
                        areas.append(area_desc.text.strip())

                # Filter for severe weather if requested
                if severe_only and not _is_severe_weather(event_text):
                    continue

                alerts.append(
                    Alert(
                        event=event_text,
                        severity=severity_elem.text if severity_elem is not None else "Unknown",
                        areas=areas[:3] if areas else ["Europe"],
                        expires_iso=expires_elem.text if expires_elem is not None else None,
                    )
                )
            except (AttributeError, ValueError):
                continue

    return alerts


def get_nws_forecast_grid(
    lat: float, lon: float, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    """Fetch NWS gridded forecast data for a location.

    Args:
        lat: Latitude
        lon: Longitude
        offline: Offline mode
        timeout: Request timeout

    Returns:
        Dictionary with grid_id, grid_x, grid_y, and periods list

    Raises:
        ValueError: If coordinates are invalid
    """
    from .security import validate_coordinates, ValidationError

    # SECURITY: Validate coordinates before URL construction
    try:
        lat, lon = validate_coordinates(lat, lon)
    except ValidationError as e:
        raise ValueError(str(e)) from e

    if offline:
        return None

    # First, get the grid point metadata
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    try:
        with _create_client(timeout) as client:
            response = client.get(points_url)
            response.raise_for_status()
            points_data = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    # Extract forecast URL
    properties = points_data.get("properties", {})
    forecast_url = properties.get("forecast")
    forecast_hourly_url = properties.get("forecastHourly")
    grid_id = properties.get("gridId")
    grid_x = properties.get("gridX")
    grid_y = properties.get("gridY")

    if not forecast_url:
        return None

    # Fetch the forecast
    try:
        with _create_client(timeout) as client:
            forecast_response = client.get(forecast_url)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
    except (httpx.HTTPError, ValueError):
        return None

    # Extract periods
    periods = forecast_data.get("properties", {}).get("periods", [])

    return {
        "grid_id": grid_id,
        "grid_x": grid_x,
        "grid_y": grid_y,
        "forecast_url": forecast_url,
        "forecast_hourly_url": forecast_hourly_url,
        "periods": periods[:7],  # Next 7 periods (roughly 3-4 days)
        "updated": forecast_data.get("properties", {}).get("updated"),
    }


def get_nws_observation_stations(
    lat: float, lon: float, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> list[dict[str, Any]]:
    """Fetch nearby NWS observation stations for a location.

    Args:
        lat: Latitude
        lon: Longitude
        offline: Offline mode
        timeout: Request timeout

    Returns:
        List of station dictionaries

    Raises:
        ValueError: If coordinates are invalid
    """
    from .security import validate_coordinates, ValidationError

    # SECURITY: Validate coordinates before URL construction
    try:
        lat, lon = validate_coordinates(lat, lon)
    except ValidationError as e:
        raise ValueError(str(e)) from e

    if offline:
        return []

    # Get stations near the point
    url = f"https://api.weather.gov/points/{lat},{lon}/stations"
    try:
        with _create_client(timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return []

    features = data.get("features", [])
    stations = []

    for feature in features[:5]:  # Limit to 5 nearest stations
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [])

        stations.append(
            {
                "station_id": props.get("stationIdentifier"),
                "name": props.get("name"),
                "lat": coords[1] if len(coords) > 1 else None,
                "lon": coords[0] if len(coords) > 0 else None,
                "elevation": props.get("elevation", {}).get("value"),
            }
        )

    return stations


def get_nws_latest_observation(
    station_id: str, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    """Fetch the latest observation from a specific NWS station."""
    if offline:
        return None

    url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
    try:
        with _create_client(timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    props = data.get("properties", {})

    return {
        "station_id": station_id,
        "timestamp": props.get("timestamp"),
        "temp_c": _safe_float(props.get("temperature", {}).get("value")),
        "dewpoint_c": _safe_float(props.get("dewpoint", {}).get("value")),
        "wind_direction": _safe_float(props.get("windDirection", {}).get("value")),
        "wind_speed_mps": _safe_float(props.get("windSpeed", {}).get("value")),
        "wind_gust_mps": _safe_float(props.get("windGust", {}).get("value")),
        "barometric_pressure_pa": _safe_float(props.get("barometricPressure", {}).get("value")),
        "visibility_m": _safe_float(props.get("visibility", {}).get("value")),
        "relative_humidity": _safe_float(props.get("relativeHumidity", {}).get("value")),
        "heat_index_c": _safe_float(props.get("heatIndex", {}).get("value")),
        "wind_chill_c": _safe_float(props.get("windChill", {}).get("value")),
        "cloud_layers": props.get("cloudLayers", []),
        "present_weather": props.get("presentWeather", []),
    }


def get_nws_hourly_forecast(
    lat: float, lon: float, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> list[dict[str, Any]]:
    """Fetch NWS hourly forecast for a location.

    Args:
        lat: Latitude
        lon: Longitude
        offline: Offline mode
        timeout: Request timeout

    Returns:
        List of hourly forecast periods

    Raises:
        ValueError: If coordinates are invalid
    """
    from .security import validate_coordinates, ValidationError

    # SECURITY: Validate coordinates before URL construction
    try:
        lat, lon = validate_coordinates(lat, lon)
    except ValidationError as e:
        raise ValueError(str(e)) from e

    if offline:
        return []

    # Get the grid point first
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    try:
        with _create_client(timeout) as client:
            response = client.get(points_url)
            response.raise_for_status()
            points_data = response.json()
    except (httpx.HTTPError, ValueError):
        return []

    forecast_hourly_url = points_data.get("properties", {}).get("forecastHourly")
    if not forecast_hourly_url:
        return []

    # Fetch hourly forecast
    try:
        with _create_client(timeout) as client:
            forecast_response = client.get(forecast_hourly_url)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
    except (httpx.HTTPError, ValueError):
        return []

    periods = forecast_data.get("properties", {}).get("periods", [])
    return periods[:24]  # Next 24 hours


def get_comprehensive_nws_data(
    lat: float, lon: float, *, offline: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any]:
    """Fetch comprehensive NWS data for a location (gridded forecast, stations, observations, alerts)."""
    if offline:
        return {
            "forecast": None,
            "hourly_forecast": [],
            "stations": [],
            "latest_observation": None,
            "alerts": [],
        }

    result: dict[str, Any] = {
        "forecast": None,
        "hourly_forecast": [],
        "stations": [],
        "latest_observation": None,
        "alerts": [],
    }

    # Fetch all data concurrently
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_forecast = executor.submit(get_nws_forecast_grid, lat, lon, offline=offline, timeout=timeout)
        future_hourly = executor.submit(get_nws_hourly_forecast, lat, lon, offline=offline, timeout=timeout)
        future_stations = executor.submit(get_nws_observation_stations, lat, lon, offline=offline, timeout=timeout)
        future_alerts = executor.submit(get_quick_alerts, lat, lon, offline=offline, timeout=timeout)

        # Collect results
        result["forecast"] = future_forecast.result()
        result["hourly_forecast"] = future_hourly.result()
        result["stations"] = future_stations.result()
        result["alerts"] = future_alerts.result()

        # Get latest observation from nearest station if available
        stations = result["stations"]
        if stations and stations[0].get("station_id"):
            station_id = stations[0]["station_id"]
            result["latest_observation"] = get_nws_latest_observation(
                station_id, offline=offline, timeout=timeout
            )

    return result
