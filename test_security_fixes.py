#!/usr/bin/env python3
"""Security tests for Phase 1 vulnerability fixes."""

import math
import pytest

# Import validation functions
from wx.security import (
    ValidationError,
    validate_radar_station,
    validate_icao_station,
    validate_buoy_id,
    validate_coordinates,
    validate_location_input,
    validate_notification_condition,
)


class TestRadarStationValidation:
    """Test radar station ID validation (Critical #1 - SSRF fix)."""

    def test_valid_radar_stations(self):
        """Test valid radar station IDs."""
        # CONUS stations
        assert validate_radar_station("KOKX") == "KOKX"
        assert validate_radar_station("KDMX") == "KDMX"
        assert validate_radar_station("KFTG") == "KFTG"
        
        # Pacific stations
        assert validate_radar_station("PHKI") == "PHKI"
        
        # Lowercase should be normalized
        assert validate_radar_station("kokx") == "KOKX"
        assert validate_radar_station("kdmx") == "KDMX"

    def test_invalid_radar_stations(self):
        """Test invalid radar station IDs are rejected."""
        # Path traversal attempts
        with pytest.raises(ValidationError, match="Invalid radar station"):
            validate_radar_station("../../../etc/passwd")
        
        with pytest.raises(ValidationError, match="Invalid radar station"):
            validate_radar_station("../../../../config")
        
        # Too short/long
        with pytest.raises(ValidationError, match="Invalid radar station"):
            validate_radar_station("KOK")
        
        with pytest.raises(ValidationError, match="Invalid radar station"):
            validate_radar_station("KOKXX")
        
        # Invalid characters
        with pytest.raises(ValidationError, match="Invalid radar station"):
            validate_radar_station("K0KX")  # Number
        
        with pytest.raises(ValidationError, match="Invalid radar station"):
            validate_radar_station("KOKX;")  # Special char
        
        # Empty
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_radar_station("")
        
        # Null byte injection
        with pytest.raises(ValidationError):
            validate_radar_station("KOKX\x00")


class TestICAOStationValidation:
    """Test ICAO station ID validation (Critical #3 - SSRF fix)."""

    def test_valid_icao_stations(self):
        """Test valid ICAO station IDs."""
        assert validate_icao_station("KDEN") == "KDEN"
        assert validate_icao_station("EGLL") == "EGLL"
        assert validate_icao_station("RJTT") == "RJTT"
        assert validate_icao_station("LFPG") == "LFPG"
        
        # Lowercase normalization
        assert validate_icao_station("kden") == "KDEN"

    def test_invalid_icao_stations(self):
        """Test invalid ICAO station IDs are rejected."""
        # Path traversal
        with pytest.raises(ValidationError, match="Invalid ICAO station"):
            validate_icao_station("../../../etc/passwd")
        
        # Wrong length
        with pytest.raises(ValidationError, match="Invalid ICAO station"):
            validate_icao_station("KDE")
        
        with pytest.raises(ValidationError, match="Invalid ICAO station"):
            validate_icao_station("KDENN")
        
        # Numbers
        with pytest.raises(ValidationError, match="Invalid ICAO station"):
            validate_icao_station("KD3N")
        
        # Special characters
        with pytest.raises(ValidationError, match="Invalid ICAO station"):
            validate_icao_station("KDEN;DROP TABLE;")
        
        # Empty
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_icao_station("")


class TestBuoyIDValidation:
    """Test NOAA buoy ID validation (Critical #4 - SSRF fix)."""

    def test_valid_buoy_ids(self):
        """Test valid buoy IDs."""
        assert validate_buoy_id("46042") == "46042"
        assert validate_buoy_id("AAMC1") == "AAMC1"
        assert validate_buoy_id("44025") == "44025"
        
        # Lowercase normalization
        assert validate_buoy_id("aamc1") == "AAMC1"

    def test_invalid_buoy_ids(self):
        """Test invalid buoy IDs are rejected."""
        # Path traversal
        with pytest.raises(ValidationError, match="Invalid buoy station"):
            validate_buoy_id("../../../../../config")
        
        # Wrong length
        with pytest.raises(ValidationError, match="Invalid buoy station"):
            validate_buoy_id("4604")
        
        with pytest.raises(ValidationError, match="Invalid buoy station"):
            validate_buoy_id("460422")
        
        # Special characters
        with pytest.raises(ValidationError, match="Invalid buoy station"):
            validate_buoy_id("4604;")
        
        # Empty
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_buoy_id("")


class TestCoordinateValidation:
    """Test coordinate validation (High #8 - URL injection fix)."""

    def test_valid_coordinates(self):
        """Test valid coordinates."""
        # Normal coordinates
        lat, lon = validate_coordinates(40.7128, -74.0060)  # New York
        assert lat == 40.7128
        assert lon == -74.0060
        
        # Edge cases
        lat, lon = validate_coordinates(90, 180)  # Max values
        assert lat == 90
        assert lon == 180
        
        lat, lon = validate_coordinates(-90, -180)  # Min values
        assert lat == -90
        assert lon == -180
        
        # Integers should work
        lat, lon = validate_coordinates(40, -74)
        assert lat == 40.0
        assert lon == -74.0

    def test_invalid_coordinates(self):
        """Test invalid coordinates are rejected."""
        # NaN
        with pytest.raises(ValidationError, match="cannot be NaN"):
            validate_coordinates(float('nan'), -74.0060)
        
        with pytest.raises(ValidationError, match="cannot be NaN"):
            validate_coordinates(40.7128, float('nan'))
        
        # Infinity
        with pytest.raises(ValidationError, match="cannot be.*Inf"):
            validate_coordinates(float('inf'), -74.0060)
        
        with pytest.raises(ValidationError, match="cannot be.*Inf"):
            validate_coordinates(40.7128, float('-inf'))
        
        # Out of range
        with pytest.raises(ValidationError, match="out of range"):
            validate_coordinates(91, -74.0060)  # lat > 90
        
        with pytest.raises(ValidationError, match="out of range"):
            validate_coordinates(-91, -74.0060)  # lat < -90
        
        with pytest.raises(ValidationError, match="out of range"):
            validate_coordinates(40.7128, 181)  # lon > 180
        
        with pytest.raises(ValidationError, match="out of range"):
            validate_coordinates(40.7128, -181)  # lon < -180
        
        # Non-numeric
        with pytest.raises(ValidationError, match="must be numeric"):
            validate_coordinates("40.7128", -74.0060)  # type: ignore
        
        with pytest.raises(ValidationError, match="must be numeric"):
            validate_coordinates(40.7128, "-74.0060")  # type: ignore


class TestLocationInputValidation:
    """Test location input validation."""

    def test_valid_locations(self):
        """Test valid location inputs."""
        assert validate_location_input("New York") == "New York"
        assert validate_location_input("Saint-Denis") == "Saint-Denis"
        assert validate_location_input("O'Fallon") == "O'Fallon"
        assert validate_location_input("Mexico, MO") == "Mexico, MO"
        assert validate_location_input("  London  ") == "London"  # Strips whitespace

    def test_invalid_locations(self):
        """Test invalid location inputs are rejected."""
        # Empty
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_location_input("")

        # Only whitespace (treated as empty after strip)
        with pytest.raises(ValidationError):  # Could be "empty" or "invalid characters"
            validate_location_input("   ")
        
        # Too long
        with pytest.raises(ValidationError, match="too long"):
            validate_location_input("A" * 101)
        
        # Control characters
        with pytest.raises(ValidationError, match="control characters"):
            validate_location_input("London\n")

        # Null byte (Python strings handle this specially, so check with regex)
        with pytest.raises(ValidationError):  # Either control char or invalid char
            validate_location_input("London\x00malicious")
        
        # Invalid characters
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_location_input("London;DROP TABLE;")
        
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_location_input("London<script>")


class TestNotificationConditionValidation:
    """Test notification condition validation (Critical #2 - Code injection fix)."""

    def test_valid_conditions(self):
        """Test valid condition strings."""
        # Basic conditions
        parsed = validate_notification_condition("temp < 32")
        assert parsed['variable'] == 'temp'
        assert parsed['operator'] == '<'
        assert parsed['threshold'] == 32.0
        
        parsed = validate_notification_condition("wind >= 50")
        assert parsed['variable'] == 'wind'
        assert parsed['operator'] == '>='
        assert parsed['threshold'] == 50.0
        
        parsed = validate_notification_condition("aqi > 150")
        assert parsed['variable'] == 'aqi'
        assert parsed['operator'] == '>'
        assert parsed['threshold'] == 150.0
        
        # Negative numbers
        parsed = validate_notification_condition("temp < -10")
        assert parsed['threshold'] == -10.0
        
        # Decimals
        parsed = validate_notification_condition("wind > 50.5")
        assert parsed['threshold'] == 50.5
        
        # Whitespace handling
        parsed = validate_notification_condition("  temp   <   32  ")
        assert parsed['variable'] == 'temp'
        assert parsed['threshold'] == 32.0

    def test_invalid_conditions(self):
        """Test invalid conditions are rejected."""
        # Empty
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_notification_condition("")
        
        # Too long (DoS prevention)
        with pytest.raises(ValidationError, match="too long"):
            validate_notification_condition("temp < " + "9" * 200)
        
        # Invalid format
        with pytest.raises(ValidationError, match="Invalid condition format"):
            validate_notification_condition("temp")  # Missing operator and value
        
        with pytest.raises(ValidationError, match="Invalid condition format"):
            validate_notification_condition("temp < ")  # Missing value
        
        # Invalid operator
        with pytest.raises(ValidationError, match="Invalid operator"):
            validate_notification_condition("temp <> 32")
        
        # Invalid variable name (code injection attempt)
        # These are caught by regex format validation or variable whitelist
        with pytest.raises(ValidationError):  # Caught at format level
            validate_notification_condition("__import__('os').system('ls') < 1")

        with pytest.raises(ValidationError):  # Caught at format level
            validate_notification_condition("eval('1+1') < 2")

        # SQL injection attempt
        with pytest.raises(ValidationError):  # Caught at format or variable level
            validate_notification_condition("temp';DROP TABLE users;-- < 32")

        # Command injection attempt
        with pytest.raises(ValidationError):  # Caught at format level
            validate_notification_condition("temp;ls < 32")
        
        # Invalid threshold (non-numeric)
        with pytest.raises(ValidationError):  # Caught at format level (regex expects digits)
            validate_notification_condition("temp < abc")
        
        # NaN/Inf (caught at format level since "nan" isn't a number in regex)
        with pytest.raises(ValidationError):  # Format error or threshold error
            validate_notification_condition("temp < nan")


class TestIntegrationSecurityTests:
    """Integration tests for security fixes in actual modules."""

    def test_radar_module_rejects_malicious_input(self):
        """Test radar module rejects path traversal."""
        from wx.radar import RadarFetcher
        
        fetcher = RadarFetcher()
        
        # Should raise ValueError for invalid station
        with pytest.raises(ValueError):
            fetcher.get_radar_image("../../../etc/passwd")
        
        with pytest.raises(ValueError):
            fetcher.get_radar_image("INVALID_STATION_123")

    def test_aviation_module_rejects_malicious_input(self):
        """Test aviation module rejects invalid ICAO codes."""
        from wx.aviation import get_metar, get_taf
        
        # Should raise ValueError for invalid station
        with pytest.raises(ValueError):
            get_metar("../../../etc/passwd", offline=True)
        
        with pytest.raises(ValueError):
            get_taf("INVALID123", offline=True)

    def test_marine_module_rejects_malicious_input(self):
        """Test marine module rejects invalid buoy IDs."""
        from wx.marine import get_buoy_observations
        
        # Should raise ValueError for invalid station
        with pytest.raises(ValueError):
            get_buoy_observations("../../../../config", offline=True)
        
        with pytest.raises(ValueError):
            get_buoy_observations("TOOLONG123", offline=True)

    def test_fetchers_reject_invalid_coordinates(self):
        """Test fetchers module rejects invalid coordinates."""
        from wx.fetchers import get_nws_forecast_grid
        
        # NaN
        with pytest.raises(ValueError):
            get_nws_forecast_grid(float('nan'), -74.0060, offline=True)
        
        # Out of range
        with pytest.raises(ValueError):
            get_nws_forecast_grid(91, -74.0060, offline=True)
        
        with pytest.raises(ValueError):
            get_nws_forecast_grid(40.7128, 181, offline=True)

    def test_notifications_reject_malicious_conditions(self):
        """Test notifications module rejects code injection attempts."""
        from wx.notifications import NotificationManager
        from pathlib import Path
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = NotificationManager(Path(tmpdir))
            
            # Code injection attempts should be rejected
            with pytest.raises(ValueError):
                manager.add_rule(
                    "evil",
                    "__import__('os').system('ls')",
                    "London"
                )
            
            with pytest.raises(ValueError):
                manager.add_rule(
                    "evil2",
                    "eval('1+1') < 2",
                    "London"
                )
            
            # SQL injection attempt
            with pytest.raises(ValueError):
                manager.add_rule(
                    "evil3",
                    "temp';DROP TABLE users;-- < 32",
                    "London"
                )


def run_security_tests():
    """Run all security tests and report results."""
    import sys
    
    print("=" * 80)
    print("PHASE 1 SECURITY FIXES - TEST SUITE")
    print("=" * 80)
    print()
    
    # Run pytest with verbose output
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    print()
    print("=" * 80)
    if exit_code == 0:
        print("✓ ALL SECURITY TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 80)
    
    return exit_code


if __name__ == "__main__":
    import sys
    sys.exit(run_security_tests())
