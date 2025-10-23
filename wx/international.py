"""International weather data sources - UK Met Office, Environment Canada, and others."""

from __future__ import annotations

from typing import Any

import requests


class MetOfficeAPI:
    """UK Met Office DataPoint API integration."""

    BASE_URL = "http://datapoint.metoffice.gov.uk/public/data"

    def __init__(self, api_key: str | None = None, timeout: int = 10):
        """Initialize Met Office API client.

        Args:
            api_key: Met Office DataPoint API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def get_forecast(
        self, location_id: str, *, offline: bool = False
    ) -> dict[str, Any] | None:
        """Get forecast for UK location.

        Args:
            location_id: Met Office location ID
            offline: Offline mode

        Returns:
            Forecast data or None
        """
        if offline or not self.api_key:
            return None

        try:
            url = f"{self.BASE_URL}/val/wxfcs/all/json/{location_id}"
            params = {"res": "3hourly", "key": self.api_key}

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            return response.json()

        except (requests.RequestException, OSError):
            return None

    def get_observations(
        self, location_id: str, *, offline: bool = False
    ) -> dict[str, Any] | None:
        """Get current observations for UK location.

        Args:
            location_id: Met Office location ID
            offline: Offline mode

        Returns:
            Observation data or None
        """
        if offline or not self.api_key:
            return None

        try:
            url = f"{self.BASE_URL}/val/wxobs/all/json/{location_id}"
            params = {"res": "hourly", "key": self.api_key}

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            return response.json()

        except (requests.RequestException, OSError):
            return None

    def search_location(
        self, query: str, *, offline: bool = False
    ) -> list[dict[str, Any]]:
        """Search for UK locations.

        Args:
            query: Location search query
            offline: Offline mode

        Returns:
            List of matching locations
        """
        if offline or not self.api_key:
            return []

        try:
            url = f"{self.BASE_URL}/val/wxfcs/all/json/sitelist"
            params = {"key": self.api_key}

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Filter locations by query
            locations = data.get("Locations", {}).get("Location", [])
            query_lower = query.lower()

            matches = [
                loc
                for loc in locations
                if query_lower in loc.get("name", "").lower()
            ]

            return matches[:10]  # Return top 10 matches

        except (requests.RequestException, OSError):
            return []


class EnvironmentCanadaAPI:
    """Environment Canada weather data integration."""

    BASE_URL = "https://dd.weather.gc.ca"
    CITY_XML_URL = "https://weather.gc.ca/rss/city"

    def __init__(self, timeout: int = 10):
        """Initialize Environment Canada API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()

    def get_forecast(
        self, province: str, city_code: str, *, offline: bool = False
    ) -> dict[str, Any] | None:
        """Get forecast for Canadian location.

        Args:
            province: Province code (e.g., 'on', 'bc', 'qc')
            city_code: City code (e.g., 's0000458' for Toronto)
            offline: Offline mode

        Returns:
            Forecast data or None
        """
        if offline:
            return None

        try:
            # RSS feed for city
            url = f"{self.CITY_XML_URL}/{city_code}_{province}_e.xml"

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse XML (simplified - would need proper XML parsing)
            return {"raw_xml": response.text, "format": "rss"}

        except (requests.RequestException, OSError):
            return None

    def get_observations(
        self, station_id: str, *, offline: bool = False
    ) -> dict[str, Any] | None:
        """Get current observations for Canadian station.

        Args:
            station_id: Station ID
            offline: Offline mode

        Returns:
            Observation data or None
        """
        if offline:
            return None

        try:
            # Weather observations
            url = f"https://weather.gc.ca/weatherOffice/weatherOffice_e.html?id={station_id}"

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Would need HTML parsing
            return {"raw_html": response.text, "format": "html"}

        except (requests.RequestException, OSError):
            return None


class InternationalWeatherRouter:
    """Route weather requests to appropriate international service."""

    # Country to service mapping
    COUNTRY_SERVICES = {
        "GB": "metoffice",  # United Kingdom
        "UK": "metoffice",
        "CA": "environment_canada",  # Canada
        "US": "nws",  # United States
        "AU": "bom",  # Australia
        "NZ": "metservice",  # New Zealand
        "DE": "dwd",  # Germany
        "FR": "meteofrance",  # France
        "JP": "jma",  # Japan
        "IN": "imd",  # India
    }

    # Known UK city coordinates (sampling)
    UK_CITIES = {
        "london": {"lat": 51.5074, "lon": -0.1278, "location_id": "352409"},
        "manchester": {"lat": 53.4808, "lon": -2.2426, "location_id": "310013"},
        "birmingham": {"lat": 52.4862, "lon": -1.8904, "location_id": "310004"},
        "leeds": {"lat": 53.8008, "lon": -1.5491, "location_id": "310274"},
        "glasgow": {"lat": 55.8642, "lon": -4.2518, "location_id": "310237"},
        "liverpool": {"lat": 53.4084, "lon": -2.9916, "location_id": "310109"},
        "edinburgh": {"lat": 55.9533, "lon": -3.1883, "location_id": "310075"},
        "bristol": {"lat": 51.4545, "lon": -2.5879, "location_id": "310013"},
        "cardiff": {"lat": 51.4816, "lon": -3.1791, "location_id": "310028"},
        "belfast": {"lat": 54.5973, "lon": -5.9301, "location_id": "310021"},
    }

    # Canadian city codes (sampling)
    CANADA_CITIES = {
        "toronto": {"province": "on", "city_code": "s0000458"},
        "montreal": {"province": "qc", "city_code": "s0000635"},
        "vancouver": {"province": "bc", "city_code": "s0000141"},
        "ottawa": {"province": "on", "city_code": "s0000430"},
        "calgary": {"province": "ab", "city_code": "s0000047"},
        "edmonton": {"province": "ab", "city_code": "s0000045"},
        "quebec": {"province": "qc", "city_code": "s0000620"},
        "winnipeg": {"province": "mb", "city_code": "s0000193"},
        "halifax": {"province": "ns", "city_code": "s0000318"},
    }

    @classmethod
    def detect_country(cls, location: str, lat: float | None = None, lon: float | None = None) -> str:
        """Detect country from location string or coordinates.

        Args:
            location: Location string
            lat: Latitude
            lon: Longitude

        Returns:
            Country code
        """
        location_lower = location.lower()

        # Check UK cities
        if location_lower in cls.UK_CITIES or any(
            keyword in location_lower for keyword in ["uk", "britain", "england", "scotland", "wales"]
        ):
            return "GB"

        # Check Canada
        if location_lower in cls.CANADA_CITIES or "canada" in location_lower:
            return "CA"

        # Check for US (default for now)
        if lat is not None and lon is not None:
            # Rough bounding boxes
            if 49.0 <= lat <= 71.0 and -141.0 <= lon <= -52.0:  # Canada
                return "CA"
            elif 49.0 <= lat <= 61.0 and -11.0 <= lon <= 2.0:  # UK
                return "GB"
            elif 24.0 <= lat <= 49.0 and -125.0 <= lon <= -66.0:  # US
                return "US"

        return "US"  # Default

    @classmethod
    def get_service_for_location(cls, location: str, lat: float | None = None, lon: float | None = None) -> str:
        """Get appropriate weather service for location.

        Args:
            location: Location string
            lat: Latitude
            lon: Longitude

        Returns:
            Service name
        """
        country = cls.detect_country(location, lat, lon)
        return cls.COUNTRY_SERVICES.get(country, "nws")

    @classmethod
    def get_uk_location_id(cls, location: str) -> str | None:
        """Get Met Office location ID for UK city.

        Args:
            location: City name

        Returns:
            Location ID or None
        """
        location_lower = location.lower()
        city_data = cls.UK_CITIES.get(location_lower)

        if city_data:
            return city_data["location_id"]

        return None

    @classmethod
    def get_canada_location_info(cls, location: str) -> dict[str, str] | None:
        """Get Environment Canada location info.

        Args:
            location: City name

        Returns:
            Province and city code dict or None
        """
        location_lower = location.lower()
        return cls.CANADA_CITIES.get(location_lower)


def get_international_weather(
    location: str,
    *,
    lat: float | None = None,
    lon: float | None = None,
    api_keys: dict[str, str] | None = None,
    offline: bool = False,
) -> dict[str, Any]:
    """Get weather from appropriate international source.

    Args:
        location: Location string
        lat: Latitude
        lon: Longitude
        api_keys: Dict of API keys for different services
        offline: Offline mode

    Returns:
        Weather data with source information
    """
    router = InternationalWeatherRouter()
    service = router.get_service_for_location(location, lat, lon)

    result = {
        "location": location,
        "service": service,
        "data": None,
        "error": None,
    }

    if offline:
        result["error"] = "Offline mode"
        return result

    if api_keys is None:
        api_keys = {}

    try:
        if service == "metoffice":
            # UK Met Office
            api_key = api_keys.get("metoffice")
            if not api_key:
                result["error"] = "Met Office API key required. Get one from: https://www.metoffice.gov.uk/datapoint"
                return result

            met_office = MetOfficeAPI(api_key)
            location_id = router.get_uk_location_id(location)

            if location_id:
                forecast = met_office.get_forecast(location_id)
                observations = met_office.get_observations(location_id)

                result["data"] = {
                    "forecast": forecast,
                    "observations": observations,
                    "location_id": location_id,
                }
            else:
                # Search for location
                matches = met_office.search_location(location)
                if matches:
                    result["data"] = {"search_results": matches}
                else:
                    result["error"] = "Location not found in Met Office database"

        elif service == "environment_canada":
            # Environment Canada
            canada_api = EnvironmentCanadaAPI()
            location_info = router.get_canada_location_info(location)

            if location_info:
                forecast = canada_api.get_forecast(
                    location_info["province"], location_info["city_code"]
                )
                result["data"] = {"forecast": forecast}
            else:
                result["error"] = "Location not found in Environment Canada database"

        else:
            # Default to NWS (already implemented)
            result["service"] = "nws"
            result["error"] = "Use standard NWS commands for US locations"

    except Exception as e:  # noqa: BLE001
        result["error"] = str(e)

    return result


def format_metoffice_forecast(data: dict[str, Any]) -> str:
    """Format Met Office forecast data for display.

    Args:
        data: Met Office forecast data

    Returns:
        Formatted string
    """
    if not data or "SiteRep" not in data:
        return "No forecast data available"

    try:
        site_rep = data["SiteRep"]
        dv = site_rep["DV"]
        location = dv["Location"]

        lines = []
        lines.append(f"Location: {location['name']}")
        lines.append(f"Elevation: {location.get('elevation', 'Unknown')}m")
        lines.append("")

        # Periods (days)
        for period in location.get("Period", []):
            date = period.get("value", "Unknown date")
            lines.append(f"Date: {date}")

            # Reps (time periods)
            for rep in period.get("Rep", []):
                time = rep.get("$", "Unknown time")
                temp = rep.get("T", "?")
                feels_like = rep.get("F", "?")
                wind_speed = rep.get("S", "?")
                wind_dir = rep.get("D", "?")
                weather = rep.get("W", "?")
                precip_prob = rep.get("Pp", "?")

                lines.append(f"  {time}: {temp}°C (feels {feels_like}°C)")
                lines.append(f"    Wind: {wind_speed} mph {wind_dir}")
                lines.append(f"    Weather: {weather}")
                lines.append(f"    Precip: {precip_prob}%")

        return "\n".join(lines)

    except (KeyError, TypeError):
        return "Error formatting forecast data"
