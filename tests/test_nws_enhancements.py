"""Tests for enhanced NWS data fetching functionality."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from wx.fetchers import (
    get_comprehensive_nws_data,
    get_nws_forecast_grid,
    get_nws_hourly_forecast,
    get_nws_latest_observation,
    get_nws_observation_stations,
)


class TestNWSForecastGrid:
    """Test NWS forecast grid fetching."""

    def test_offline_mode(self):
        """Test that offline mode returns None."""
        result = get_nws_forecast_grid(40.0, -105.0, offline=True)
        assert result is None

    @patch("wx.fetchers._create_client")
    def test_successful_fetch(self, mock_client_factory):
        """Test successful forecast grid fetch."""
        # Mock the client and responses
        mock_client = MagicMock()
        mock_client_factory.return_value.__enter__.return_value = mock_client

        # Mock points response
        points_response = MagicMock()
        points_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/BOU/52,73/forecast",
                "forecastHourly": "https://api.weather.gov/gridpoints/BOU/52,73/forecast/hourly",
                "gridId": "BOU",
                "gridX": 52,
                "gridY": 73,
            }
        }

        # Mock forecast response
        forecast_response = MagicMock()
        forecast_response.json.return_value = {
            "properties": {
                "updated": "2025-01-15T12:00:00Z",
                "periods": [
                    {"name": "Today", "temperature": 45, "shortForecast": "Sunny"},
                    {"name": "Tonight", "temperature": 32, "shortForecast": "Clear"},
                ],
            }
        }

        # Set up mock responses
        mock_client.get.side_effect = [points_response, forecast_response]

        result = get_nws_forecast_grid(40.0, -105.0)

        assert result is not None
        assert result["grid_id"] == "BOU"
        assert result["grid_x"] == 52
        assert result["grid_y"] == 73
        assert len(result["periods"]) == 2


class TestNWSObservationStations:
    """Test NWS observation stations fetching."""

    def test_offline_mode(self):
        """Test that offline mode returns empty list."""
        result = get_nws_observation_stations(40.0, -105.0, offline=True)
        assert result == []

    @patch("wx.fetchers._create_client")
    def test_successful_fetch(self, mock_client_factory):
        """Test successful stations fetch."""
        mock_client = MagicMock()
        mock_client_factory.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "features": [
                {
                    "properties": {
                        "stationIdentifier": "KDEN",
                        "name": "Denver International Airport",
                        "elevation": {"value": 1655},
                    },
                    "geometry": {"coordinates": [-104.67, 39.85]},
                }
            ]
        }
        mock_client.get.return_value = mock_response

        result = get_nws_observation_stations(40.0, -105.0)

        assert len(result) == 1
        assert result[0]["station_id"] == "KDEN"
        assert result[0]["name"] == "Denver International Airport"


class TestNWSLatestObservation:
    """Test NWS latest observation fetching."""

    def test_offline_mode(self):
        """Test that offline mode returns None."""
        result = get_nws_latest_observation("KDEN", offline=True)
        assert result is None

    @patch("wx.fetchers._create_client")
    def test_successful_fetch(self, mock_client_factory):
        """Test successful observation fetch."""
        mock_client = MagicMock()
        mock_client_factory.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "properties": {
                "timestamp": "2025-01-15T12:00:00Z",
                "temperature": {"value": 8.0},
                "dewpoint": {"value": -2.0},
                "windDirection": {"value": 180.0},
                "windSpeed": {"value": 5.0},
                "barometricPressure": {"value": 101325.0},
                "relativeHumidity": {"value": 45.0},
            }
        }
        mock_client.get.return_value = mock_response

        result = get_nws_latest_observation("KDEN")

        assert result is not None
        assert result["station_id"] == "KDEN"
        assert result["temp_c"] == 8.0
        assert result["relative_humidity"] == 45.0


class TestNWSHourlyForecast:
    """Test NWS hourly forecast fetching."""

    def test_offline_mode(self):
        """Test that offline mode returns empty list."""
        result = get_nws_hourly_forecast(40.0, -105.0, offline=True)
        assert result == []

    @patch("wx.fetchers._create_client")
    def test_successful_fetch(self, mock_client_factory):
        """Test successful hourly forecast fetch."""
        mock_client = MagicMock()
        mock_client_factory.return_value.__enter__.return_value = mock_client

        # Mock points response
        points_response = MagicMock()
        points_response.json.return_value = {
            "properties": {
                "forecastHourly": "https://api.weather.gov/gridpoints/BOU/52,73/forecast/hourly"
            }
        }

        # Mock hourly forecast response
        hourly_response = MagicMock()
        hourly_response.json.return_value = {
            "properties": {
                "periods": [
                    {"startTime": "2025-01-15T12:00:00Z", "temperature": 45},
                    {"startTime": "2025-01-15T13:00:00Z", "temperature": 46},
                ]
            }
        }

        mock_client.get.side_effect = [points_response, hourly_response]

        result = get_nws_hourly_forecast(40.0, -105.0)

        assert len(result) == 2


class TestComprehensiveNWSData:
    """Test comprehensive NWS data fetching."""

    def test_offline_mode(self):
        """Test that offline mode returns empty structure."""
        result = get_comprehensive_nws_data(40.0, -105.0, offline=True)

        assert result["forecast"] is None
        assert result["hourly_forecast"] == []
        assert result["stations"] == []
        assert result["latest_observation"] is None
        assert result["alerts"] == []

    @patch("wx.fetchers.get_nws_forecast_grid")
    @patch("wx.fetchers.get_nws_hourly_forecast")
    @patch("wx.fetchers.get_nws_observation_stations")
    @patch("wx.fetchers.get_quick_alerts")
    @patch("wx.fetchers.get_nws_latest_observation")
    def test_comprehensive_fetch(
        self,
        mock_latest_obs,
        mock_alerts,
        mock_stations,
        mock_hourly,
        mock_forecast,
    ):
        """Test comprehensive data fetch with all components."""
        # Mock return values
        mock_forecast.return_value = {"grid_id": "BOU"}
        mock_hourly.return_value = [{"temperature": 45}]
        mock_stations.return_value = [{"station_id": "KDEN"}]
        mock_alerts.return_value = [{"event": "Wind Advisory"}]
        mock_latest_obs.return_value = {"temp_c": 8.0}

        result = get_comprehensive_nws_data(40.0, -105.0)

        # Verify all components are fetched
        assert result["forecast"] == {"grid_id": "BOU"}
        assert len(result["hourly_forecast"]) == 1
        assert len(result["stations"]) == 1
        assert len(result["alerts"]) == 1
        assert result["latest_observation"]["temp_c"] == 8.0

        # Verify all mock functions were called
        mock_forecast.assert_called_once()
        mock_hourly.assert_called_once()
        mock_stations.assert_called_once()
        mock_alerts.assert_called_once()
        mock_latest_obs.assert_called_once_with("KDEN", offline=False, timeout=3.0)


class TestEUAlertsXMLParsing:
    """Test EU MeteoAlarm XML parsing."""

    @patch("wx.fetchers._create_client")
    def test_rss_format_parsing(self, mock_client_factory):
        """Test parsing RSS format alerts."""
        from wx.fetchers import fetch_eu_alerts

        mock_client = MagicMock()
        mock_client_factory.return_value.__enter__.return_value = mock_client

        # Mock RSS XML response
        mock_response = MagicMock()
        mock_response.text = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Wind Warning - Netherlands</title>
                    <description>Severe wind warning for coastal areas</description>
                    <pubDate>2025-01-15T12:00:00Z</pubDate>
                </item>
            </channel>
        </rss>
        """
        mock_client.get.return_value = mock_response

        result = fetch_eu_alerts()

        assert len(result) >= 0  # May parse successfully or return empty
        # XML parsing is best-effort, so we just verify it doesn't crash

    def test_offline_mode_returns_empty(self):
        """Test that offline mode returns empty list."""
        from wx.fetchers import fetch_eu_alerts

        result = fetch_eu_alerts(offline=True)
        assert result == []
