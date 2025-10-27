"""Security validation functions for input sanitization and validation."""

from __future__ import annotations

import math
import re
from typing import Any


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


def validate_radar_station(station: str) -> str:
    """Validate radar station ID against NOAA RIDGE station whitelist.
    
    Args:
        station: Radar station ID (e.g., KOKX, KDMX)
        
    Returns:
        Validated and normalized station ID (uppercase)
        
    Raises:
        ValidationError: If station ID is invalid
    """
    if not station:
        raise ValidationError("Radar station ID cannot be empty")
    
    # Normalize to uppercase
    station_upper = station.upper().strip()
    
    # NOAA radar stations are 4 characters starting with K (CONUS) or P (Pacific)
    # Also T (Caribbean), plus a few others
    if not re.match(r'^[KPTIC][A-Z]{3}$', station_upper):
        raise ValidationError(
            f"Invalid radar station format: {station}. "
            "Expected 4-letter code (e.g., KOKX, KDMX, KFTG)"
        )
    
    # Length check (defense in depth)
    if len(station_upper) != 4:
        raise ValidationError(f"Invalid radar station length: {station}")
    
    return station_upper


def validate_icao_station(station_id: str) -> str:
    """Validate ICAO station identifier for aviation weather.
    
    Args:
        station_id: ICAO station code (e.g., KDEN, EGLL, RJTT)
        
    Returns:
        Validated and normalized station ID (uppercase)
        
    Raises:
        ValidationError: If station ID is invalid
    """
    if not station_id:
        raise ValidationError("ICAO station ID cannot be empty")
    
    # Normalize
    station_upper = station_id.upper().strip()
    
    # ICAO codes are exactly 4 letters
    if not re.match(r'^[A-Z]{4}$', station_upper):
        raise ValidationError(
            f"Invalid ICAO station format: {station_id}. "
            "Expected 4-letter code (e.g., KDEN, EGLL, RJTT)"
        )
    
    # Length check
    if len(station_upper) != 4:
        raise ValidationError(f"Invalid ICAO station length: {station_id}")
    
    return station_upper


def validate_buoy_id(station_id: str) -> str:
    """Validate NOAA buoy station identifier.
    
    Args:
        station_id: Buoy station ID (e.g., 46042, AAMC1)
        
    Returns:
        Validated and normalized station ID (uppercase)
        
    Raises:
        ValidationError: If station ID is invalid
    """
    if not station_id:
        raise ValidationError("Buoy station ID cannot be empty")
    
    # Normalize
    station_upper = station_id.upper().strip()
    
    # NOAA buoy IDs are typically 5 alphanumeric characters
    # Can be all numbers (46042) or mixed (AAMC1)
    if not re.match(r'^[A-Z0-9]{5}$', station_upper):
        raise ValidationError(
            f"Invalid buoy station format: {station_id}. "
            "Expected 5-character alphanumeric code (e.g., 46042, AAMC1)"
        )
    
    # Length check
    if len(station_upper) != 5:
        raise ValidationError(f"Invalid buoy station length: {station_id}")
    
    return station_upper


def validate_coordinates(lat: float, lon: float) -> tuple[float, float]:
    """Validate and sanitize latitude and longitude coordinates.
    
    Args:
        lat: Latitude value
        lon: Longitude value
        
    Returns:
        Tuple of validated (lat, lon) rounded to 4 decimal places
        
    Raises:
        ValidationError: If coordinates are invalid
    """
    # Type check
    if not isinstance(lat, (int, float)):
        raise ValidationError(f"Latitude must be numeric, got {type(lat).__name__}")
    
    if not isinstance(lon, (int, float)):
        raise ValidationError(f"Longitude must be numeric, got {type(lon).__name__}")
    
    # Check for special float values
    if math.isnan(lat) or math.isinf(lat):
        raise ValidationError(f"Invalid latitude: {lat} (cannot be NaN or Inf)")
    
    if math.isnan(lon) or math.isinf(lon):
        raise ValidationError(f"Invalid longitude: {lon} (cannot be NaN or Inf)")
    
    # Range validation
    if not (-90 <= lat <= 90):
        raise ValidationError(f"Latitude out of range: {lat} (must be -90 to 90)")
    
    if not (-180 <= lon <= 180):
        raise ValidationError(f"Longitude out of range: {lon} (must be -180 to 180)")
    
    # Round to 4 decimal places (about 11 meters precision)
    return round(lat, 4), round(lon, 4)


def validate_location_input(location: str, max_length: int = 100) -> str:
    """Validate and sanitize location name input.
    
    Args:
        location: User-provided location string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized location string
        
    Raises:
        ValidationError: If location input is invalid
    """
    if not location:
        raise ValidationError("Location cannot be empty")

    # Check for control characters and null bytes BEFORE stripping (security)
    if any(ord(c) < 32 or c == '\x00' for c in location):
        raise ValidationError("Location contains invalid control characters")

    # Strip whitespace
    location = location.strip()

    # Check for empty after stripping
    if not location:
        raise ValidationError("Location cannot be empty")

    # Length check
    if len(location) > max_length:
        raise ValidationError(
            f"Location name too long: {len(location)} characters "
            f"(max {max_length})"
        )
    
    # Allow alphanumeric, spaces, and common punctuation for place names
    # Examples: "New York", "Saint-Denis", "O'Fallon", "Mexico, MO"
    if not re.match(r'^[a-zA-Z0-9\s\-,.\'()]+$', location):
        raise ValidationError(
            f"Location contains invalid characters: {location}. "
            "Only letters, numbers, spaces, and punctuation (- , . ' ( )) allowed"
        )
    
    return location


def validate_notification_condition(condition: str) -> dict[str, Any]:
    """Validate and parse notification condition with strict whitelist.
    
    Args:
        condition: Condition string (e.g., "temp < 32", "wind > 50")
        
    Returns:
        Dictionary with parsed condition: {
            'variable': str,
            'operator': str,
            'threshold': float
        }
        
    Raises:
        ValidationError: If condition is invalid or malicious
    """
    if not condition:
        raise ValidationError("Condition cannot be empty")
    
    # Length limit to prevent DoS
    if len(condition) > 100:
        raise ValidationError(f"Condition too long: {len(condition)} characters")
    
    # Parse with strict regex
    # Format: "variable operator threshold"
    # Example: "temp < 32" or "wind >= 50.5"
    pattern = r'^([a-z_][a-z0-9_]*)\s*([<>=!]+)\s*(-?\d+(?:\.\d+)?)$'
    match = re.match(pattern, condition.strip(), re.IGNORECASE)
    
    if not match:
        raise ValidationError(
            f"Invalid condition format: {condition}. "
            'Expected format: "variable operator value" (e.g., "temp < 32")'
        )
    
    variable, operator, threshold_str = match.groups()
    
    # Whitelist allowed operators
    ALLOWED_OPERATORS = {'<', '<=', '>', '>=', '==', '!='}
    if operator not in ALLOWED_OPERATORS:
        raise ValidationError(
            f"Invalid operator: {operator}. "
            f"Allowed: {', '.join(ALLOWED_OPERATORS)}"
        )
    
    # Whitelist allowed variable names
    ALLOWED_VARIABLES = {
        'temp', 'temperature',
        'wind', 'wind_speed',
        'gust', 'wind_gust',
        'humidity',
        'precip', 'precipitation', 'precip_chance',
        'aqi', 'air_quality',
        'pressure',
        'visibility',
        'dewpoint',
        'feels_like'
    }
    
    if variable.lower() not in ALLOWED_VARIABLES:
        raise ValidationError(
            f"Invalid variable: {variable}. "
            f"Allowed: {', '.join(sorted(ALLOWED_VARIABLES))}"
        )
    
    # Parse threshold
    try:
        threshold = float(threshold_str)
    except (ValueError, OverflowError) as e:
        raise ValidationError(f"Invalid threshold value: {threshold_str}") from e
    
    # Check for reasonable threshold ranges
    if math.isnan(threshold) or math.isinf(threshold):
        raise ValidationError(f"Invalid threshold: {threshold}")
    
    # Sanity check on threshold magnitude
    if abs(threshold) > 1e6:
        raise ValidationError(f"Threshold too large: {threshold}")
    
    return {
        'variable': variable.lower(),
        'operator': operator,
        'threshold': threshold
    }


def validate_condition_simple(condition: str) -> bool:
    """Simple validation check for condition string (returns bool).
    
    Args:
        condition: Condition string
        
    Returns:
        True if valid, False otherwise
    """
    try:
        validate_notification_condition(condition)
        return True
    except ValidationError:
        return False


def sanitize_string_for_logging(value: str, max_length: int = 50) -> str:
    """Sanitize string for safe logging (remove control chars, truncate).
    
    Args:
        value: String to sanitize
        max_length: Maximum length
        
    Returns:
        Sanitized string safe for logging
    """
    if not value:
        return ""
    
    # Remove control characters
    sanitized = ''.join(c if ord(c) >= 32 else '?' for c in value)
    
    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized
