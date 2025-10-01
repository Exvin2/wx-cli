"""Lightweight data fetchers for wx Feature Packs."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_TIMEOUT = 3.0
USER_AGENT = "wx-cli/0.1 (+https://github.com/Exvin2/claudex-cli)"


@dataclass(slots=True)
class FetchResult:
    """Capture metadata for debugging fetch operations."""

    name: str
    elapsed: float
    succeeded: bool
    detail: str | None = None


def _create_client(timeout: float) -> httpx.Client:
    return httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})


def _safe_request(method: str, url: str, *, params: dict[str, Any] | None = None,
                  timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any] | None:
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


def get_point_context(place_or_latlon: str, *, offline: bool = False,
                      timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any] | None:
    """Resolve a place name or coordinate string into lat/lon metadata."""

    if offline:
        return None

    coordinate = _parse_latlon(place_or_latlon)
    if coordinate:
        lat, lon = coordinate
        tz_url = "https://api.open-meteo.com/v1/timezone"
        tz_data = _safe_request("GET", tz_url, params={"latitude": lat, "longitude": lon}, timeout=timeout)
        tz_name = tz_data.get("timezone") if tz_data else None
        return {
            "input": place_or_latlon,
            "resolved": place_or_latlon,
            "lat": lat,
            "lon": lon,
            "tz": tz_name,
        }

    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    payload = _safe_request("GET", geo_url,
                            params={"name": place_or_latlon, "count": 1, "language": "en"},
                            timeout=timeout)
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


def get_quick_obs(lat: float, lon: float, *, offline: bool = False,
                  timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any] | None:
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


def get_quick_alerts(lat: float, lon: float, *, offline: bool = False,
                     timeout: float = DEFAULT_TIMEOUT) -> list[dict[str, Any]]:
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
        alerts.append({
            "event": props.get("event"),
            "severity": props.get("severity"),
            "expires_iso": props.get("ends"),
        })
    return alerts


def get_quick_profile(lat: float, lon: float, *, offline: bool = False,
                      timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any] | None:
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
