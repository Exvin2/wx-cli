"""Tests for weather storytelling module."""

import json
from datetime import datetime

import pytest

from wx.config import Settings, load_settings
from wx.storyteller import (
    ConfidenceNote,
    Decision,
    Storyteller,
    Timeline,
    TimelinePhase,
    WeatherStory,
    _build_timeline_viz,
)


def test_timeline_phase_creation():
    """Test TimelinePhase dataclass."""
    phase = TimelinePhase(
        start_time="7am",
        end_time="12pm",
        description="Morning clearing",
        key_changes=["Clouds dissipate", "Temperatures rise"],
        confidence=0.8,
    )

    assert phase.start_time == "7am"
    assert phase.end_time == "12pm"
    assert phase.description == "Morning clearing"
    assert len(phase.key_changes) == 2
    assert phase.confidence == 0.8

    # Test to_dict
    phase_dict = phase.to_dict()
    assert phase_dict["start_time"] == "7am"
    assert phase_dict["confidence"] == 0.8


def test_decision_creation():
    """Test Decision dataclass."""
    decision = Decision(
        activity="Morning commute",
        recommendation="Leave 15 minutes early",
        reasoning="Rain will increase visibility issues",
        timing="6:30-7:00am",
        confidence=0.75,
    )

    assert decision.activity == "Morning commute"
    assert decision.recommendation == "Leave 15 minutes early"
    assert decision.timing == "6:30-7:00am"
    assert decision.confidence == 0.75

    # Test to_dict
    decision_dict = decision.to_dict()
    assert decision_dict["activity"] == "Morning commute"


def test_confidence_note_creation():
    """Test ConfidenceNote dataclass."""
    confidence = ConfidenceNote(
        primary_uncertainty="Timing of frontal passage",
        alternative_scenarios=["Front arrives 2 hours earlier", "Front stalls offshore"],
        confidence_level="Medium",
        rationale="Model spread is moderate",
    )

    assert confidence.primary_uncertainty == "Timing of frontal passage"
    assert len(confidence.alternative_scenarios) == 2
    assert confidence.confidence_level == "Medium"

    # Test to_dict
    conf_dict = confidence.to_dict()
    assert conf_dict["primary_uncertainty"] == "Timing of frontal passage"
    assert len(conf_dict["alternative_scenarios"]) == 2


def test_timeline_from_raw_phases():
    """Test Timeline construction from raw data."""
    raw_phases = [
        {
            "start_time": "7am",
            "end_time": "12pm",
            "description": "Morning phase",
            "key_changes": ["Change 1", "Change 2"],
            "confidence": 0.8,
        },
        {
            "start_time": "12pm",
            "end_time": "6pm",
            "description": "Afternoon phase",
            "key_changes": ["Change 3"],
            "confidence": 0.7,
        },
    ]

    timeline = Timeline.from_raw_phases(raw_phases)

    assert len(timeline.phases) == 2
    assert timeline.phases[0].start_time == "7am"
    assert timeline.phases[1].end_time == "6pm"
    assert timeline.visualization  # Should have visualization string


def test_build_timeline_viz():
    """Test timeline visualization generation."""
    phases = [
        TimelinePhase("7am", "12pm", "Morning", [], 0.8),
        TimelinePhase("12pm", "6pm", "Afternoon", [], 0.7),
        TimelinePhase("6pm", "10pm", "Evening", [], 0.6),
    ]

    viz = _build_timeline_viz(phases)

    # Check for box-drawing characters
    assert "├─" in viz
    assert "└─" in viz
    assert "7am–12pm" in viz
    assert "Evening" in viz


def test_build_timeline_viz_empty():
    """Test timeline visualization with no phases."""
    viz = _build_timeline_viz([])
    assert viz == ""


def test_weather_story_creation():
    """Test WeatherStory dataclass."""
    timeline = Timeline(
        phases=[TimelinePhase("7am", "12pm", "Morning", ["Clear skies"], 0.8)],
        visualization="test viz",
    )

    decisions = [
        Decision(
            activity="Commute",
            recommendation="Normal timing",
            reasoning="Conditions favorable",
            timing="7-9am",
            confidence=0.9,
        )
    ]

    confidence = ConfidenceNote(
        primary_uncertainty="Cloud timing",
        alternative_scenarios=["Earlier clearing"],
        confidence_level="High",
        rationale="Model agreement",
    )

    story = WeatherStory(
        setup="High pressure dominates",
        current="Clear skies, 45°F",
        evolution=timeline,
        meteorology="Stable air mass",
        decisions=decisions,
        confidence=confidence,
        bottom_line="Great day ahead",
        meta={"location": "Seattle", "provider": "test"},
    )

    assert story.setup == "High pressure dominates"
    assert story.current == "Clear skies, 45°F"
    assert len(story.decisions) == 1
    assert story.bottom_line == "Great day ahead"

    # Test to_dict
    story_dict = story.to_dict()
    assert story_dict["setup"] == "High pressure dominates"
    assert story_dict["bottom_line"] == "Great day ahead"
    assert "evolution" in story_dict
    assert "decisions" in story_dict


def test_weather_story_json_serialization():
    """Test that WeatherStory can be serialized to JSON."""
    story = WeatherStory(
        setup="Test setup",
        current="Test current",
        evolution=Timeline(phases=[], visualization=""),
        meteorology="Test meteorology",
        decisions=[],
        confidence=ConfidenceNote(
            primary_uncertainty="Test uncertainty",
            alternative_scenarios=[],
            confidence_level="Medium",
            rationale="Test rationale",
        ),
        bottom_line="Test bottom line",
        meta={"test": "data"},
    )

    # Should not raise
    story_json = json.dumps(story.to_dict())
    assert story_json
    assert "Test setup" in story_json

    # Should be able to parse back
    parsed = json.loads(story_json)
    assert parsed["setup"] == "Test setup"
    assert parsed["bottom_line"] == "Test bottom line"


def test_storyteller_parse_story_response_with_valid_json():
    """Test parsing a valid AI response."""
    settings = load_settings(offline=True)
    storyteller = Storyteller(settings)

    # Create a mock ForecasterResponse with valid JSON in raw_text
    from wx.forecaster import ForecasterResponse

    valid_json = {
        "setup": "Cold front approaching",
        "current": "Cloudy, 50°F",
        "evolution": {
            "phases": [
                {
                    "start_time": "now",
                    "end_time": "6pm",
                    "description": "Clouds thicken",
                    "key_changes": ["Wind increases"],
                    "confidence": 0.7,
                }
            ]
        },
        "meteorology": "Frontal dynamics",
        "decisions": [
            {
                "activity": "Outdoor plans",
                "recommendation": "Have backup",
                "reasoning": "Rain likely",
                "timing": "afternoon",
                "confidence": 0.6,
            }
        ],
        "confidence": {
            "primary_uncertainty": "Timing",
            "alternative_scenarios": ["Earlier arrival"],
            "confidence_level": "Medium",
            "rationale": "Model spread",
        },
        "bottom_line": "Plan for changing conditions",
    }

    response = ForecasterResponse(
        sections={},
        confidence={"value": 70},
        used_feature_fields=["forecast", "obs"],
        bottom_line="Test",
        raw_text=json.dumps(valid_json),
        provider="test",
        prompt_summary="test query",
    )

    story = storyteller._parse_story_response(response, "Seattle", "weather today")

    assert story.setup == "Cold front approaching"
    assert story.current == "Cloudy, 50°F"
    assert len(story.evolution.phases) == 1
    assert len(story.decisions) == 1
    assert story.confidence.confidence_level == "Medium"
    assert story.bottom_line == "Plan for changing conditions"
    assert story.meta["location"] == "Seattle"
    assert story.meta["provider"] == "test"


def test_storyteller_parse_story_response_with_fallback():
    """Test parsing when AI returns malformed data."""
    settings = load_settings(offline=True)
    storyteller = Storyteller(settings)

    from wx.forecaster import ForecasterResponse

    # Malformed JSON - should use sections fallback
    response = ForecasterResponse(
        sections={
            "setup": "Fallback setup",
            "current": "Fallback current",
            "meteorology": "Fallback meteorology",
        },
        confidence={"value": 50},
        used_feature_fields=[],
        bottom_line="Fallback bottom line",
        raw_text="not valid json",
        provider="test",
        prompt_summary="test query",
    )

    story = storyteller._parse_story_response(response, "Denver", "weather query")

    # Should use fallback values
    assert story.setup == "Fallback setup"
    assert story.current == "Fallback current"
    assert story.meteorology == "Fallback meteorology"
    assert story.bottom_line == "Fallback bottom line"
    assert story.meta["location"] == "Denver"


def test_storyteller_format_feature_pack():
    """Test feature pack formatting for AI."""
    settings = load_settings(offline=True)
    storyteller = Storyteller(settings)

    feature_pack = {
        "location": "Seattle, WA",
        "coordinates": {"lat": 47.6, "lon": -122.3},
        "current_conditions": {"temp": 50, "wind": 10},
        "forecast": {"periods": []},
        "alerts": [],
        "should_be_excluded": "this field should not appear",
        "timestamp": "2024-01-01T12:00:00",
    }

    formatted = storyteller._format_feature_pack(feature_pack)

    # Should be valid JSON
    parsed = json.loads(formatted)

    # Should include relevant keys
    assert "location" in parsed
    assert "current_conditions" in parsed
    assert "forecast" in parsed
    assert "alerts" in parsed

    # Should exclude non-relevant keys
    assert "should_be_excluded" not in parsed


def test_timeline_phase_defaults():
    """Test TimelinePhase default values."""
    phase = TimelinePhase(
        start_time="7am", end_time="12pm", description="Test"
        # key_changes and confidence should use defaults
    )

    assert phase.key_changes == []
    assert phase.confidence == 0.7


def test_decision_defaults():
    """Test Decision default values."""
    decision = Decision(
        activity="Test", recommendation="Test rec", reasoning="Test reason"
        # timing and confidence should use defaults
    )

    assert decision.timing is None
    assert decision.confidence == 0.7


def test_confidence_note_defaults():
    """Test ConfidenceNote default values."""
    confidence = ConfidenceNote(primary_uncertainty="Test uncertainty")

    assert confidence.alternative_scenarios == []
    assert confidence.confidence_level == "Medium"
    assert confidence.rationale == ""
