"""Tests for worldview feature."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from wx.config import Settings, load_settings
from wx.fetchers import Alert, Observation
from wx.orchestrator import Orchestrator, RegionStats, RegionView, Worldview


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return load_settings(offline=True)


@pytest.fixture
def orchestrator(settings: Settings) -> Orchestrator:
    """Create test orchestrator."""
    return Orchestrator(settings)


def test_worldview_offline_deterministic(orchestrator: Orchestrator) -> None:
    """Test offline mode returns deterministic synthetic data."""
    worldview = orchestrator.handle_worldview()

    assert isinstance(worldview, Worldview)
    assert len(worldview.regions) == 2

    # Check US region
    us_region = worldview.regions[0]
    assert us_region.name == "US"
    assert "coast" in us_region.summary.lower()
    assert us_region.stats.tmin == 45.0
    assert us_region.stats.tmax == 85.0
    assert len(us_region.alerts) > 0

    # Check Europe region
    eu_region = worldview.regions[1]
    assert eu_region.name == "Europe"
    assert "weather" in eu_region.summary.lower()
    assert eu_region.stats.tmin == 10.0
    assert eu_region.stats.tmax == 25.0

    # Check metadata
    assert worldview.meta["samples_us"] == 0
    assert worldview.meta["samples_eu"] == 0
    assert "Offline synthetic data" in worldview.meta["sources"]


def test_worldview_online_mocked(settings: Settings) -> None:
    """Test online mode with mocked fetchers."""
    settings.offline = False
    orchestrator = Orchestrator(settings)

    # Mock observations
    mock_us_obs = [
        Observation(lat=40.7, lon=-74.0, temp=20.0, wind=5.0, gust=10.0, precip_prob=30.0),
        Observation(lat=34.0, lon=-118.2, temp=25.0, wind=7.0, gust=12.0, precip_prob=10.0),
    ]
    mock_eu_obs = [
        Observation(lat=51.5, lon=-0.1, temp=15.0, wind=12.0, gust=20.0, precip_prob=60.0),
        Observation(lat=48.9, lon=2.3, temp=18.0, wind=8.0, gust=15.0, precip_prob=40.0),
    ]

    # Mock alerts
    mock_us_alerts = [
        Alert(event="Tornado Warning", severity="Severe", areas=["Texas", "Oklahoma"]),
        Alert(event="Flood Watch", severity="Moderate", areas=["Louisiana"]),
    ]
    mock_eu_alerts = [
        Alert(event="Wind Warning", severity="Severe", areas=["UK", "Netherlands"]),
    ]

    with (
        patch("wx.orchestrator.fetch_openmeteo_points") as mock_fetch_points,
        patch("wx.orchestrator.fetch_us_alerts") as mock_fetch_us,
        patch("wx.orchestrator.fetch_eu_alerts") as mock_fetch_eu,
    ):
        mock_fetch_points.side_effect = [mock_us_obs, mock_eu_obs]
        mock_fetch_us.return_value = mock_us_alerts
        mock_fetch_eu.return_value = mock_eu_alerts

        worldview = orchestrator.handle_worldview()

        assert len(worldview.regions) == 2
        assert worldview.meta["samples_us"] == 2
        assert worldview.meta["samples_eu"] == 2

        # Check stats computation
        us_region = worldview.regions[0]
        assert us_region.stats.tmin == 20.0
        assert us_region.stats.tmax == 25.0
        assert us_region.stats.pop_max == 30.0

        eu_region = worldview.regions[1]
        assert eu_region.stats.tmin == 15.0
        assert eu_region.stats.tmax == 18.0
        assert eu_region.stats.wind_max == 12.0


def test_compute_region_stats(orchestrator: Orchestrator) -> None:
    """Test region stats computation."""
    observations = [
        Observation(lat=40.7, lon=-74.0, temp=20.0, wind=5.0, gust=10.0, precip_prob=30.0),
        Observation(lat=34.0, lon=-118.2, temp=25.0, wind=7.0, gust=12.0, precip_prob=10.0),
        Observation(lat=42.3, lon=-71.1, temp=18.0, wind=3.0, gust=8.0, precip_prob=50.0),
    ]

    stats = orchestrator._compute_region_stats(observations)

    assert stats.tmin == 18.0
    assert stats.tmax == 25.0
    assert stats.pop_max == 50.0
    assert stats.wind_max == 7.0
    assert stats.gust_max == 12.0


def test_compute_region_stats_empty(orchestrator: Orchestrator) -> None:
    """Test region stats with no observations."""
    stats = orchestrator._compute_region_stats([])

    assert stats.tmin is None
    assert stats.tmax is None
    assert stats.pop_max is None
    assert stats.wind_max is None
    assert stats.gust_max is None


def test_generate_region_summary(orchestrator: Orchestrator) -> None:
    """Test region summary generation."""
    observations = [
        Observation(lat=40.7, lon=-74.0, temp=20.0, wind=5.0, gust=10.0, precip_prob=35.0),
        Observation(lat=34.0, lon=-118.2, temp=25.0, wind=7.0, gust=12.0, precip_prob=10.0),
    ]
    alerts = [
        Alert(event="Heat Advisory", severity="Moderate", areas=["California"]),
    ]

    summary = orchestrator._generate_region_summary("Test", observations, alerts)

    assert "20–25°" in summary
    assert "precip" in summary
    assert "alert" in summary


def test_summarize_alerts(orchestrator: Orchestrator) -> None:
    """Test alert summarization."""
    alerts = [
        Alert(event="Tornado Warning", severity="Severe", areas=["Texas", "Oklahoma"]),
        Alert(event="Tornado Warning", severity="Severe", areas=["Kansas"]),
        Alert(event="Flood Watch", severity="Moderate", areas=["Louisiana", "Mississippi"]),
        Alert(event="Heat Advisory", severity="Minor", areas=["Arizona"]),
    ]

    summary = orchestrator._summarize_alerts(alerts)

    # Should group by event
    assert len(summary) <= 5
    tornado_entry = next((a for a in summary if a["event"] == "Tornado Warning"), None)
    assert tornado_entry is not None
    assert tornado_entry["count"] == 2


def test_summarize_alerts_empty(orchestrator: Orchestrator) -> None:
    """Test alert summarization with no alerts."""
    summary = orchestrator._summarize_alerts([])
    assert summary == []


def test_worldview_json_output(orchestrator: Orchestrator) -> None:
    """Test worldview JSON output schema."""
    from io import StringIO

    from rich.console import Console

    from wx.render import render_worldview

    worldview = orchestrator.handle_worldview()

    # Use StringIO to capture raw output without ANSI codes
    output_buffer = StringIO()
    console = Console(file=output_buffer, force_terminal=False, legacy_windows=False)

    render_worldview(worldview, console=console, json_mode=True, verbose=False)

    output = json.loads(output_buffer.getvalue())

    # Verify JSON schema
    assert "regions" in output
    assert "meta" in output
    assert len(output["regions"]) == 2

    for region in output["regions"]:
        assert "name" in region
        assert "summary" in region
        assert "stats" in region
        assert "alerts" in region
        assert "tmin" in region["stats"]
        assert "tmax" in region["stats"]


def test_worldview_timeout_handling(settings: Settings) -> None:
    """Test worldview handles timeouts gracefully."""
    settings.offline = False
    orchestrator = Orchestrator(settings)

    with (
        patch("wx.orchestrator.fetch_openmeteo_points") as mock_fetch_points,
        patch("wx.orchestrator.fetch_us_alerts") as mock_fetch_us,
        patch("wx.orchestrator.fetch_eu_alerts") as mock_fetch_eu,
    ):
        # Simulate partial failures
        mock_fetch_points.side_effect = [[], []]  # Empty results simulate failure
        mock_fetch_us.return_value = []
        mock_fetch_eu.return_value = []

        worldview = orchestrator.handle_worldview()

        # Should still return valid worldview with empty data
        assert isinstance(worldview, Worldview)
        assert len(worldview.regions) == 2
        assert worldview.meta["samples_us"] == 0
        assert worldview.meta["samples_eu"] == 0


def test_cli_worldview_no_args(monkeypatch) -> None:
    """Test CLI invokes worldview when no args provided."""
    from wx.cli import main

    # Mock the orchestrator's handle_worldview
    with (
        patch("wx.cli.load_settings") as mock_settings,
        patch("wx.cli.Orchestrator") as mock_orch_class,
        patch("wx.cli.render_worldview") as mock_render,
    ):
        mock_settings.return_value = load_settings(offline=True)
        mock_orch = MagicMock()
        mock_orch_class.return_value = mock_orch

        # Create a synthetic worldview
        mock_worldview = Worldview(
            regions=[
                RegionView(
                    name="US",
                    summary="Test",
                    stats=RegionStats(tmin=50.0, tmax=80.0, pop_max=30.0, wind_max=10.0, gust_max=20.0),
                    alerts=[],
                )
            ],
            meta={"samples_us": 0, "samples_eu": 0, "fetch_ms": 0, "sources": []},
        )
        mock_orch.handle_worldview.return_value = mock_worldview

        try:
            main([])
        except SystemExit:
            pass

        # Verify worldview was called
        mock_orch.handle_worldview.assert_called_once()
        mock_render.assert_called_once()


def test_severe_weather_filtering() -> None:
    """Test severe weather filtering."""
    from wx.fetchers import _is_severe_weather

    # Should match severe weather
    assert _is_severe_weather("Tornado Warning") is True
    assert _is_severe_weather("Flash Flood Warning") is True
    assert _is_severe_weather("Severe Thunderstorm Warning") is True
    assert _is_severe_weather("Flood Watch") is True
    assert _is_severe_weather("TORNADO EMERGENCY") is True
    assert _is_severe_weather("Particularly Dangerous Situation") is True

    # Should NOT match non-severe weather
    assert _is_severe_weather("Heat Advisory") is False
    assert _is_severe_weather("Wind Advisory") is False
    assert _is_severe_weather("Winter Weather Advisory") is False
    assert _is_severe_weather("Air Quality Alert") is False


def test_worldview_severe_only(settings: Settings) -> None:
    """Test worldview with severe_only filter."""
    settings.offline = False
    orchestrator = Orchestrator(settings)

    # Mock observations and alerts
    mock_us_obs = [
        Observation(lat=40.7, lon=-74.0, temp=20.0, wind=5.0),
    ]
    mock_eu_obs = [
        Observation(lat=51.5, lon=-0.1, temp=15.0, wind=12.0),
    ]

    # Mix of severe and non-severe alerts
    mock_us_alerts = [
        Alert(event="Tornado Warning", severity="Severe", areas=["Oklahoma"]),
        Alert(event="Heat Advisory", severity="Moderate", areas=["Texas"]),
        Alert(event="Flash Flood Warning", severity="Severe", areas=["Louisiana"]),
        Alert(event="Wind Advisory", severity="Minor", areas=["Kansas"]),
    ]
    mock_eu_alerts = [
        Alert(event="Wind Warning", severity="Moderate", areas=["UK"]),
    ]

    with (
        patch("wx.orchestrator.fetch_openmeteo_points") as mock_fetch_points,
        patch("wx.orchestrator.fetch_us_alerts") as mock_fetch_us,
        patch("wx.orchestrator.fetch_eu_alerts") as mock_fetch_eu,
    ):
        mock_fetch_points.side_effect = [mock_us_obs, mock_eu_obs]

        # When severe_only=True, should only return severe alerts
        def us_alerts_filtered(*, offline, severe_only):
            if severe_only:
                return [a for a in mock_us_alerts if _is_severe_weather(a.event)]
            return mock_us_alerts

        def eu_alerts_filtered(*, offline, severe_only):
            if severe_only:
                return [a for a in mock_eu_alerts if _is_severe_weather(a.event)]
            return mock_eu_alerts

        mock_fetch_us.side_effect = us_alerts_filtered
        mock_fetch_eu.side_effect = eu_alerts_filtered

        from wx.fetchers import _is_severe_weather

        worldview = orchestrator.handle_worldview(severe_only=True)

        # Should only have severe weather alerts
        us_region = worldview.regions[0]
        assert worldview.meta["severe_only"] is True
        # Should have 2 severe alerts (Tornado Warning, Flash Flood Warning)
        assert len(us_region.alerts) > 0
        for alert_summary in us_region.alerts:
            assert _is_severe_weather(alert_summary["event"])
